from typing import List
import requests
import os
import click
import re
import json
from prpolish import git_utils

def generate_pr_description(commit_messages: List[str], changed_files: List[str], branch_name: str, template: str = None) -> str:
    """
    Generate a PR description based on commits, files, and branch info.
    Supports a custom template with variables: {commit_messages}, {changed_files}, {branch_name}.
    """
    if not commit_messages:
        return "No detailed commit messages found. Consider explaining why this fix matters."

    if template:
        # Format template with available variables
        return template.format(
            commit_messages='\n'.join(commit_messages),
            changed_files='\n'.join(changed_files),
            branch_name=branch_name
        )

    # Default best-practices structure
    summary = commit_messages[0] if commit_messages else f"Changes on branch `{branch_name}`."
    related = "(Add links to issues, docs, or tickets here if relevant.)"
    changes = '\n'.join(f"- {msg}" for msg in commit_messages)
    files_summary = ', '.join(changed_files[:3])
    if len(changed_files) > 3:
        files_summary += f", and {len(changed_files)-3} more files"
    changes += f"\n\n**Main files changed:** {files_summary}"
    test_files = [f for f in changed_files if 'test' in f or f.endswith('.test.js') or '__tests__' in f]
    if test_files:
        testing = f"Test files updated: {', '.join(test_files[:2])}{'...' if len(test_files)>2 else ''}."
    else:
        testing = "No test files detected. Please describe how this was tested."
    out_of_scope = "(Note any related work not addressed in this PR.)"
    # Compose markdown with required sections
    return f"""# Summary\n{summary}\n\n# Related Resources\n{related}\n\n# Changes\n{changes}\n\n# Testing\n{testing}\n\n# Out of Scope\n{out_of_scope}"""

def summarize_diff_via_api(diff: str) -> (str, float):
    """
    Summarize a diff using an external API (OpenAI). Returns (summary, cost_in_usd).
    """
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        return ("[No API key set, cannot summarize diff]", 0.0)
    prompt = f"""
Summarize the following git diff for a pull request. Be concise and focus on the main changes, not line-by-line details.

diff:
{diff}
"""
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 128,
                "temperature": 0.2
            },
            timeout=8
        )
        if response.ok and "choices" in response.json():
            content = response.json()["choices"][0]["message"]["content"].strip()
            usage = response.json().get("usage", {})
            # OpenAI pricing: $0.0015/1K input tokens, $0.002/1K output tokens (gpt-3.5-turbo)
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = (input_tokens / 1000 * 0.0015) + (output_tokens / 1000 * 0.002)
            return content, cost
        else:
            return f"[OpenAI API error: {response.text}]", 0.0
    except Exception as e:
        return f"[OpenAI API error: {e}]", 0.0

def generate_pr_description_llm(commit_messages: List[str], changed_files: List[str], branch_name: str, template: str = None, repo_path: str = '.') -> (str, float):
    """
    Generate a PR description using OpenAI (if API key set), else fallback to heuristic.
    Returns (description, cost_in_usd).
    """
    if not commit_messages and not changed_files:
        return "No changes detected on this branch. Make sure all changes are added and committed.", 0.0
    try:
        diff = git_utils.get_diff(repo_path)
    except Exception:
        diff = "[Could not retrieve diff]"
    diff_summary, cost1 = summarize_diff_via_api(diff)
    prompt = ""

    # Construct LLM prompt with all required context and section headings
    prompt += f'''
You are an expert software engineer and code reviewer. Write a high-quality, professional pull request (PR) description for the following changes, following these best practices:

- ONLY use the information provided below. Do NOT invent, search, or assume any additional information.
- Start with a concise summary of what and why.
- Add a section for related resources (links to issues, docs, tickets, etc. if any).
- Break down the changes in bullet points, explaining what, why, and how.
- Include a section on testing: how to test, scenarios considered, or what should be tested.
- Mention any out-of-scope work (things not addressed but relevant for future work).

Format your response in Markdown with these section headings (do not add or remove sections):

# Summary
# Related Resources
# Changes
# Testing
# Out of Scope

**Context:**
- Branch: `{branch_name}`
- Commit messages: {commit_messages}
- Changed files: {changed_files}
- Diff summary: {diff_summary}
'''
    
    if template:
        # If a template is provided, append it as a guide for the LLM
        prompt += f"\nUse the following template as a guide:\n{template}\n"

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        # Fallback to heuristic if no API key
        return generate_pr_description(commit_messages, changed_files, branch_name, template=template), cost1
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 512,
                "temperature": 0.2
            },
            timeout=8
        )
        cost2 = 0.0
        if response.ok and "choices" in response.json():
            content = response.json()["choices"][0]["message"]["content"].strip()
            usage = response.json().get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost2 = (input_tokens / 1000 * 0.0015) + (output_tokens / 1000 * 0.002)
            # Ensure all required sections are present
            required_sections = ["# Summary", "# Related Resources", "# Changes", "# Testing", "# Out of Scope"]
            if all(section in content for section in required_sections):
                return content, cost1 + cost2
            else:
                # Fallback to heuristic if LLM output is missing sections
                return generate_pr_description(commit_messages, changed_files, branch_name, template=template), cost1 + cost2
        else:
            return f"[OpenAI API error: {response.text}]", cost1
    except Exception as e:
        return f"[OpenAI API error: {e}]", cost1
    return generate_pr_description(commit_messages, changed_files, branch_name, template=template), cost1

def detect_related_resources(commit_messages: List[str], branch_name: str, changed_files: List[str]) -> List[str]:
    """
    Detect related resources (issue/ticket/doc references) from commit messages, branch name, and changed files.
    """
    patterns = [
        r'#\\d+',                # GitHub/GitLab issue numbers
        r'[A-Z]{2,}-\\d+',       # JIRA/Linear ticket keys
        r'https?://\\S+',        # URLs (docs, tickets, etc.)
    ]
    regex = re.compile('|'.join(patterns))
    detected = set()
    for msg in commit_messages:
        detected.update(regex.findall(msg))
    detected.update(regex.findall(branch_name))
    for fname in changed_files:
        detected.update(regex.findall(fname))
    return sorted(detected)

def label_related_resource_links(resource_lines: List[str]) -> (List[str], List[str]):
    """
    Label resource links with their type (Jira, Confluence, Drive, etc).
    Returns (labeled, other).
    """
    labeled = []
    other = []
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    heuristics = [
        (re.compile(r"jira\\.com|atlassian\\.net"), "Jira Ticket"),
        (re.compile(r"confluence\\.com|confluence\\."), "Documentation"),
        (re.compile(r"drive\\.google\\.com"), "Documentation"),
        (re.compile(r"github\\.com/.+?/issues/"), "GitHub Issue"),
        (re.compile(r"linear\\.app"), "Linear Ticket"),
        (re.compile(r"docs\\.google\\.com"), "Documentation"),
    ]
    def heuristic_label(line):
        """
        Heuristically label a resource line based on known patterns.
        """
        for pattern, label in heuristics:
            if pattern.search(line):
                return f"{label}: {line}", label
        return line, None
    # Heuristic fallback (LLM support can be added similarly)
    for line in resource_lines:
        labeled_line, label = heuristic_label(line.strip())
        if label:
            labeled.append(labeled_line)
        else:
            other.append(line.strip())
    return labeled, other

# --- PR Title Generation ---
def generate_pr_title(commit_messages: List[str], changed_files: List[str], branch_name: str, template: str = None) -> str:
    """
    Generate a PR title based on commit messages, files, and branch info.
    Supports a custom template with variables: {commit_messages}, {changed_files}, {branch_name}.
    """
    if template:
        return template.format(
            commit_messages='; '.join(commit_messages),
            changed_files=', '.join(changed_files),
            branch_name=branch_name
        )
    # Best practice: Use first good commit message if possible
    def is_good_commit(msg):
        """
        Heuristic to determine if a commit message is suitable for a PR title.
        """
        # Heuristic: not empty, not WIP/temp, not too short, not just 'fix', etc.
        if not msg or len(msg) < 8:
            return False
        bad_patterns = [r"wip", r"temp", r"pls work", r"final", r"test", r"update code", r"bug fix", r"fix bug", r"pr for"]
        for pat in bad_patterns:
            if re.search(pat, msg, re.IGNORECASE):
                return False
        return True

    # Try to find a good commit message
    for msg in commit_messages:
        if is_good_commit(msg):
            # If it already looks like a conventional commit, use as is
            if re.match(r"^(feat|fix|docs|chore|refactor|test|style|perf|ci|build|revert|merge|release)(\([^)]+\))?: ", msg):
                return msg.split("\n")[0].strip()
            # Otherwise, try to synthesize a conventional commit style
            # Guess type from keywords
            lower = msg.lower()
            if "fix" in lower:
                prefix = "fix: "
            elif "add" in lower or "implement" in lower or "feature" in lower:
                prefix = "feat: "
            elif "doc" in lower:
                prefix = "docs: "
            elif "refactor" in lower:
                prefix = "refactor: "
            elif "test" in lower:
                prefix = "test: "
          
            # Try to extract issue/ticket refs
            refs = re.findall(r"#\d+|[A-Z]{2,}-\d+", msg)
            ref_str = f" ({' '.join(refs)})" if refs else ""
            return f"{prefix}{msg.strip()}{ref_str}"[:80]
    # Fallback: synthesize from branch name and files
    if branch_name:
        # Try to extract ticket/issue from branch name
        refs = re.findall(r"#\d+|[A-Z]{2,}-\d+", branch_name)
        ref_str = f" ({' '.join(refs)})" if refs else ""
        # Try to guess type
        if branch_name.startswith("feat"):
            prefix = "feat: "
        elif branch_name.startswith("fix"):
            prefix = "fix: "
        elif branch_name.startswith("docs"):
            prefix = "docs: "
        elif branch_name.startswith("refactor"):
            prefix = "refactor: "
        else:
            prefix = "chore: "
        # Add a short summary of main file changed
        file_hint = f" [{changed_files[0]}]" if changed_files else ""
        return f"{prefix}{branch_name.replace('-', ' ')}{file_hint}{ref_str}"[:80]
    return "chore: update code"

def generate_pr_title_llm(commit_messages: List[str], changed_files: List[str], branch_name: str, template: str = None, repo_path: str = '.') -> (str, float):
    """
    Generate a PR title using OpenAI (if API key set), else fallback to heuristic.
    Returns (title, cost_in_usd). Supports a custom template as a guide.
    """
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        return generate_pr_title(commit_messages, changed_files, branch_name, template=template), 0.0
    try:
        diff = git_utils.get_diff(repo_path)
    except Exception:
        diff = "[Could not retrieve diff]"
    diff_summary, cost1 = summarize_diff_via_api(diff)
    prompt = f'''
You are an expert software engineer and code reviewer. Write a high-quality, professional pull request (PR) TITLE for the following changes, following these best practices:
- Be concise and descriptive (ideally under 50 characters, max 80).
- Use imperative mood ("add", "fix", "update").
- Follow conventional commit style: prefix with feat, fix, docs, chore, etc.
- Reference issues/tickets if present (e.g., closes #123).
- Do NOT include a description, only the title.
- Do NOT invent or assume extra context.

**Context:**
- Branch: {branch_name}
- Commit messages: {commit_messages}
- Changed files: {changed_files}
- Diff summary: {diff_summary}
'''
    if template:
        prompt += f"\nUse the following template as a guide for the title:\n{template}\n"
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 32,
                "temperature": 0.2
            },
            timeout=8
        )
        cost2 = 0.0
        if response.ok and "choices" in response.json():
            content = response.json()["choices"][0]["message"]["content"].strip()
            usage = response.json().get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost2 = (input_tokens / 1000 * 0.0015) + (output_tokens / 1000 * 0.002)
            return content.split("\n")[0][:80], cost1 + cost2
        else:
            return generate_pr_title(commit_messages, changed_files, branch_name, template=template), cost1
    except Exception:
        return generate_pr_title(commit_messages, changed_files, branch_name, template=template), cost1 