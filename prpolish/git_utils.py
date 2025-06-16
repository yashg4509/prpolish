"""
Utilities for interacting with a Git repository to extract commit messages, changed files, branch names, and diffs.

All functions assume the current working directory is a Git repository.
If the repository uses 'main' as the default branch, it is preferred; otherwise, 'master' is used as a fallback.
"""
from git import Repo
from typing import List
import hashlib
from git.exc import InvalidGitRepositoryError, NoSuchPathError
import click


def get_commit_messages(repo_path: str = '.') -> List[str]:
    """
    Return a list of commit messages in the current branch/stack (not in main/master).
    """
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise click.ClickException("This command must be run inside a Git repository.")
    branch = repo.active_branch
    main_branch = repo.heads['main'] if 'main' in repo.heads else repo.heads['master']
    commits = list(repo.iter_commits(f'{main_branch.name}..{branch.name}'))
    return [commit.message.strip() for commit in reversed(commits)]


def get_changed_files(repo_path: str = '.') -> List[str]:
    """
    Return a list of changed files in the current branch/stack (not in main/master).
    """
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise click.ClickException("This command must be run inside a Git repository.")
    branch = repo.active_branch
    main_branch = repo.heads['main'] if 'main' in repo.heads else repo.heads['master']
    diff = repo.git.diff('--name-only', f'{main_branch.name}..{branch.name}')
    return diff.splitlines()


def get_branch_name(repo_path: str = '.') -> str:
    """
    Return the current branch name.

    Args:
        repo_path (str): Path to the git repository (default: current directory).
    Returns:
        str: Name of the current branch.
    """
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise click.ClickException("This command must be run inside a Git repository.")
    return repo.active_branch.name


def get_diff(repo_path: str = '.') -> str:
    """
    Return the full git diff between the current branch and main/master as a string.
    """
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise click.ClickException("This command must be run inside a Git repository.")
    branch = repo.active_branch
    main_branch = repo.heads['main'] if 'main' in repo.heads else repo.heads['master']
    return repo.git.diff(f'{main_branch.name}..{branch.name}')
