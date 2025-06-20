import click
from prpolish import git_utils, pr_description, vibe_check, clipboard
import os
import subprocess
import tempfile
import shutil
import sys
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError
import importlib.metadata

# Helper decorator to require a git repo for commands
def require_git_repo(f):
    def wrapper(*args, **kwargs):
        try:
            Repo(os.getcwd())
        except (InvalidGitRepositoryError, NoSuchPathError):
            raise click.ClickException("This command must be run inside a Git repository.")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@click.group()
@click.version_option(importlib.metadata.version("prpolish"), '--version', '-v', message="%(version)s")
def main():
    """Entry point"""
    pass


@main.command()
@click.option('--template', default=None, help='Custom PR description template (string or path to file)')
@click.option('--save', '-s', is_flag=False, flag_value='both', default=None, expose_value=True, type=click.Choice(['title', 'description', 'both'], case_sensitive=False), help='Save PR title, description, or both to draft files. If used without an argument, saves both.')
@click.option('--fast', '-f', is_flag=True, default=False, help='Automatically create the PR with no prompts')
@require_git_repo
def generate(template, save, fast):
    """
    Generate PR title/description and optionally run vibe checks or create a PR.
    Handles user prompts, template detection, and PR creation logic.
    """
    repo_path = os.getcwd()
    commit_messages = git_utils.get_commit_messages(repo_path)
    changed_files = git_utils.get_changed_files(repo_path)
    branch_name = git_utils.get_branch_name(repo_path)

    # Warn if on main or master branch
    if branch_name in ("main", "master"):
        click.echo("[WARNING] You are on the main/master branch. It is recommended to create PRs from a feature branch.")

    # If no changes, skip LLM calls and output message
    if not commit_messages and not changed_files:
        click.echo("No changes detected on this branch.")
        return

    # Require API key for LLM features
    if not os.environ.get("OPENAI_API_KEY"):
        raise click.ClickException("\n[ERROR] The OPENAI_API_KEY environment variable is not set.\nPlease set it to use PR generation features. Example:\n\n    export OPENAI_API_KEY=sk-...\n")

    # --- PR Template Detection ---
    def find_github_pr_template(repo_path):
        """
        Search for a GitHub pull request template in common locations within the repository.
        Returns the template content as a string if found, else None.
        """
        from pathlib import Path
        possible_paths = [
            Path(repo_path) / ".github/pull_request_template.md",
            Path(repo_path) / "docs/pull_request_template.md",
            Path(repo_path) / "pull_request_template.md",
        ]
        for path in possible_paths:
            if path.exists():
                return path.read_text()
        return None

    # Support both direct string and file path for template
    template_str = None
    if template:
        # If template is a file path, read its contents
        if os.path.isfile(template):
            with open(template, 'r') as f:
                template_str = f.read()
        else:
            template_str = template
    else:
        # If no template provided, check for GitHub PR template
        template_str = find_github_pr_template(repo_path)

    # --- PR Title Generation ---
    # Use LLM to generate PR title and description, fallback to heuristics if no API key
    title, title_cost = pr_description.generate_pr_title_llm(commit_messages, changed_files, branch_name, template=template_str, repo_path=repo_path)
    desc, desc_cost = pr_description.generate_pr_description_llm(commit_messages, changed_files, branch_name, template=template_str, repo_path=repo_path)
    total_cost = title_cost + desc_cost
    # Remove markdown code block wrappers if present
    if desc.strip().startswith("```markdown"):
        desc = desc.strip()[len("```markdown"):].strip()
        if desc.endswith("```"):
            desc = desc[:-3].strip()
    elif desc.strip().startswith("```"):
        desc = desc.strip()[3:].strip()
        if desc.endswith("```"):
            desc = desc[:-3].strip()

    # --- Related Resources Manual Prompt (for description only) ---
    import re
    related_section_pattern = re.compile(r"(# Related Resources\n)(.*?)(\n# |\n#|\n$)", re.DOTALL)
    match = related_section_pattern.search(desc)
    if click.confirm("Would you like to add related resources (issues, docs, tickets, etc.)?", default=False):
        click.echo("Enter related resources (one per line, leave blank to finish):")
        lines = []
        while True:
            line = click.prompt('', default='', show_default=False)
            if not line.strip():
                break
            lines.append(line.strip())
        # Label resource links using heuristics (Jira, GitHub, etc)
        labeled_lines, other_lines = pr_description.label_related_resource_links(lines)
        all_lines = labeled_lines + other_lines
        user_related = '\n'.join(f'- {line}' for line in all_lines)
        if user_related:
            user_related += '\n'  # Ensure a blank line after the last resource
        # Replace the section
        desc = related_section_pattern.sub(r"\1" + user_related + r"\3", desc)
    else:
        # Remove the section entirely if not adding resources
        desc = related_section_pattern.sub('', desc)

    # Helper to try creating a PR using gh
    def try_create_pr_with_gh(title, desc, branch_name, remote="origin"):
        try:
            click.echo(f"Pushing branch {branch_name} to {remote}...")
            subprocess.run(["git", "push", "-u", remote, branch_name], check=True)
        except Exception as e:
            click.echo(f"[ERROR] Failed to push branch: {e}")
            return False
        try:
            click.echo("Opening PR using GitHub CLI (gh)...")
            if not check_gh_setup_interactive():
                # After interactive setup, check if gh is now set up
                if check_gh_setup():
                    click.echo("gh setup complete. Retrying PR creation...")
                    return try_create_pr_with_gh(title, desc, branch_name, remote)
                else:
                    click.echo("gh setup was not completed. Skipping PR creation.")
                    return False
            subprocess.run([
                "gh", "pr", "create",
                "--title", title,
                "--body", desc,
                "--head", branch_name
            ], check=True)
            click.echo("PR created!")
            return True
        except Exception as e:
            click.echo("[ERROR] Failed to create PR using GitHub CLI. You can create the PR manually using the title and description below.")
            click.echo("\nPR Title:\n" + title + "\n\nPR Description:\n" + desc + "\n")
            return False

    # Output logic
    if fast:
        # Fast mode: no prompts, just create PR
        try_create_pr_with_gh(title, desc, branch_name)
        # Optionally save if --save is set
        if save and save in ('title', 'both'):
            draft_path = os.path.join(repo_path, "PR_TITLE_DRAFT.txt")
            with open(draft_path, "w") as f:
                f.write(title)
            click.echo(f"Saved to {draft_path}")
        if save and save in ('description', 'both'):
            draft_path = os.path.join(repo_path, "PR_DESCRIPTION_DRAFT.txt")
            with open(draft_path, "w") as f:
                f.write(desc)
            click.echo(f"Saved to {draft_path}")
        return
    # Default: generate both
    click.echo(f"\n🔖 PR Title:\n{title}\n")
    if click.confirm("Edit PR title?", default=False):
        title = click.edit(title) or title
        click.echo(f"\nEdited PR Title:\n{title}\n")
    click.echo(f"\n📝 PR Description:\n{desc}\n")
    if click.confirm("Edit PR description in your editor?", default=False):
        desc = click.edit(desc, extension=".md") or desc
        click.echo(f"\nEdited PR Description:\n{desc}\n")
    if save and save in ('title', 'both'):
        draft_path = os.path.join(repo_path, "PR_TITLE_DRAFT.txt")
        with open(draft_path, "w") as f:
            f.write(title)
        click.echo(f"Saved to {draft_path}")
    if save and save in ('description', 'both'):
        draft_path = os.path.join(repo_path, "PR_DESCRIPTION_DRAFT.txt")
        with open(draft_path, "w") as f:
            f.write(desc)
        click.echo(f"Saved to {draft_path}")
    if click.confirm("Copy both to clipboard?", default=True):
        clipboard.copy_to_clipboard(f"{title}\n\n{desc}")
        click.echo("Copied both to clipboard!")

    # Option to run vibe checks
    if click.confirm("Would you like to run vibe checks?", default=False):
        warnings = vibe_check.run_vibe_checks(commit_messages, changed_files)
        click.echo("⚠ Vibe Checks:")
        for w in warnings:
            click.echo(w)
        click.echo("")

    # Option to create PR automatically
    if click.confirm("Would you like to create a PR automatically (push branch and open PR)?", default=False):
        try_create_pr_with_gh(title, desc, branch_name)

@main.command('generate-title')
@click.option('--template', default=None, help='Custom PR title template (string or path to file)')
@click.option('--save', '-s', is_flag=True, default=False, help='Save PR title to draft file')
@require_git_repo
def generate_title(template, save):
    """Generate only the PR title."""
    repo_path = os.getcwd()
    commit_messages = git_utils.get_commit_messages(repo_path)
    changed_files = git_utils.get_changed_files(repo_path)
    branch_name = git_utils.get_branch_name(repo_path)
    # Warn if on main or master branch
    if branch_name in ("main", "master"):
        click.echo("[WARNING] You are on the main/master branch. It is recommended to create PRs from a feature branch.")
    if not commit_messages and not changed_files:
        click.echo("No changes detected on this branch.")
        return
    if not os.environ.get("OPENAI_API_KEY"):
        raise click.ClickException("\n[ERROR] The OPENAI_API_KEY environment variable is not set.\nPlease set it to use PR generation features. Example:\n\n    export OPENAI_API_KEY=sk-...\n")
    template_str = None
    if template:
        if os.path.isfile(template):
            with open(template, 'r') as f:
                template_str = f.read()
        else:
            template_str = template
    title, title_cost = pr_description.generate_pr_title_llm(commit_messages, changed_files, branch_name, template=template_str, repo_path=repo_path)
    click.echo(f"\n🔖 PR Title:\n{title}\n")
    if click.confirm("Edit PR title?", default=False):
        title = click.edit(title) or title
        click.echo(f"\nEdited PR Title:\n{title}\n")
    if save:
        draft_path = os.path.join(repo_path, "PR_TITLE_DRAFT.txt")
        with open(draft_path, "w") as f:
            f.write(title)
        click.echo(f"Saved to {draft_path}")
    if click.confirm("Copy to clipboard?", default=True):
        clipboard.copy_to_clipboard(title)
        click.echo("Copied to clipboard!")

@main.command('generate-desc')
@click.option('--template', default=None, help='Custom PR description template (string or path to file)')
@click.option('--save', '-s', is_flag=True, default=False, help='Save PR description to draft file')
@require_git_repo
def generate_desc(template, save):
    """Generate only the PR description."""
    repo_path = os.getcwd()
    commit_messages = git_utils.get_commit_messages(repo_path)
    changed_files = git_utils.get_changed_files(repo_path)
    branch_name = git_utils.get_branch_name(repo_path)
    # Warn if on main or master branch
    if branch_name in ("main", "master"):
        click.echo("[WARNING] You are on the main/master branch. It is recommended to create PRs from a feature branch.")
    if not commit_messages and not changed_files:
        click.echo("No changes detected on this branch.")
        return
    if not os.environ.get("OPENAI_API_KEY"):
        raise click.ClickException("\n[ERROR] The OPENAI_API_KEY environment variable is not set.\nPlease set it to use PR generation features. Example:\n\n    export OPENAI_API_KEY=sk-...\n")
    template_str = None
    if template:
        if os.path.isfile(template):
            with open(template, 'r') as f:
                template_str = f.read()
        else:
            template_str = template
    desc, desc_cost = pr_description.generate_pr_description_llm(commit_messages, changed_files, branch_name, template=template_str, repo_path=repo_path)
    # Remove markdown code block wrappers if present
    if desc.strip().startswith("```markdown"):
        desc = desc.strip()[len("```markdown"):].strip()
        if desc.endswith("```"):
            desc = desc[:-3].strip()
    elif desc.strip().startswith("```"):
        desc = desc.strip()[3:].strip()
        if desc.endswith("```"):
            desc = desc[:-3].strip()
    import re
    related_section_pattern = re.compile(r"(# Related Resources\n)(.*?)(\n# |\n#|\n$)", re.DOTALL)
    match = related_section_pattern.search(desc)
    if click.confirm("Would you like to add related resources (issues, docs, tickets, etc.)?", default=False):
        click.echo("Enter related resources (one per line, leave blank to finish):")
        lines = []
        while True:
            line = click.prompt('', default='', show_default=False)
            if not line.strip():
                break
            lines.append(line.strip())
        # Label resource links using heuristics (Jira, GitHub, etc)
        labeled_lines, other_lines = pr_description.label_related_resource_links(lines)
        all_lines = labeled_lines + other_lines
        user_related = '\n'.join(f'- {line}' for line in all_lines)
        if user_related:
            user_related += '\n'  # Ensure a blank line after the last resource
        # Replace the section
        if match:
            desc = related_section_pattern.sub(r"\1" + user_related + r"\3", desc)
        else:
            desc += "\n\n# Related Resources\n" + user_related
    else:
        desc = related_section_pattern.sub('', desc)
    click.echo(f"\n📝 PR Description:\n{desc}\n")
    if click.confirm("Edit PR description in your editor?", default=False):
        desc = click.edit(desc, extension=".md") or desc
        click.echo(f"\nEdited PR Description:\n{desc}\n")
    if save:
        draft_path = os.path.join(repo_path, "PR_DESCRIPTION_DRAFT.txt")
        with open(draft_path, "w") as f:
            f.write(desc)
        click.echo(f"Saved to {draft_path}")
    if click.confirm("Copy to clipboard?", default=True):
        clipboard.copy_to_clipboard(desc)
        click.echo("Copied to clipboard!")

def check_gh_setup():
    """
    Check if GitHub CLI (gh) is installed and authenticated.
    Returns True if setup, False otherwise.
    """
    # Check if gh is installed
    if not shutil.which("gh"):
        return False
    # Check if gh is authenticated
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    return "You are not logged into any GitHub hosts" not in result.stdout

def try_install_gh():
    """
    Attempt to install GitHub CLI (gh) using the appropriate package manager.
    Only supports Homebrew (macOS) and apt (Linux).
    """
    if sys.platform == "darwin":
        if shutil.which("brew"):
            click.echo("Attempting to install gh with Homebrew...")
            subprocess.run(["brew", "install", "gh"])
        else:
            click.echo("Homebrew not found. Please install Homebrew or install gh manually from https://cli.github.com/")
    elif sys.platform.startswith("linux"):
        click.echo("Attempting to install gh with apt (you may be prompted for your password)...")
        subprocess.run(["sudo", "apt", "install", "gh"])
    else:
        click.echo("Automatic install not supported on this OS. Please install gh manually from https://cli.github.com/")

def try_auth_gh():
    """
    Start the GitHub CLI authentication process.
    """
    click.echo("Starting gh authentication...")
    subprocess.run(["gh", "auth", "login"])

@click.command('setup-gh')
def setup_gh():
    """
    Attempt to install and authenticate the GitHub CLI (gh).
    Guides the user through installation and authentication if needed.
    """
    if not shutil.which("gh"):
        if click.confirm("gh is not installed. Attempt to install it now?", default=True):
            try_install_gh()
        else:
            click.echo("Please install gh manually from https://cli.github.com/")
            return
    if shutil.which("gh"):
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if "You are not logged into any GitHub hosts" in result.stdout:
            if click.confirm("gh is not authenticated. Run 'gh auth login' now?", default=True):
                try_auth_gh()
            else:
                click.echo("Please run 'gh auth login' manually.")
        else:
            click.echo("gh is already authenticated!")
    else:
        click.echo("gh is still not installed. Please install it manually.")

main.add_command(setup_gh)

def check_gh_setup_interactive():
    """
    Interactively check and set up GitHub CLI (gh) if not already set up.
    Returns True if setup, False otherwise.
    """
    if not check_gh_setup():
        if click.confirm("gh is not set up. Would you like to set it up now?", default=True):
            setup_gh.invoke(click.Context(setup_gh))
        else: 
            click.echo("Skipping automatic PR creation. Please set up gh and try again.")
        return False
    return True

if __name__ == "__main__":
    main() 