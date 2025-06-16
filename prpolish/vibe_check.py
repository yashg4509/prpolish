from typing import List
import requests
import os
import re
import click

def run_vibe_checks(commit_messages: List[str], changed_files: List[str]) -> List[str]:
    """Analyze commits and files for quality signals using OpenAI LLM, fallback to heuristics if unavailable."""
    prompt = f'''
You are an expert code reviewer. Analyze the following commit messages and changed files for PR quality issues.

Instructions:
- Be concise and direct.
- Return a markdown bullet list of actionable warnings or suggestions.
- Flag low-quality or vague commit messages, missing or insufficient tests, and any other issues that could reduce PR quality or maintainability. Examples include commits containing words like "wip", "fix", "final", "pls work", "temp", or "test".
- If everything looks good, say so in a single bullet.

**Heuristics to apply:**
- If more than 10 files are changed and no test files are present, flag this as a concern.
- If no test files are present at all, mention it.
- Flag any commit messages that are empty or just placeholders (like "." or "-").

**Context:**
- Commit messages: {commit_messages}
- Changed files: {changed_files}
'''
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        # Raise a Click exception if no API key is set (LLM features require it)
        raise click.ClickException("\n[ERROR] The OPENAI_API_KEY environment variable is not set.\nPlease set it to use LLM features. Example:\n\n    export OPENAI_API_KEY=sk-...\n")
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
                "max_tokens": 256,
                "temperature": 0.5
            },
            timeout=6
        )
        if response.ok and "choices" in response.json():
            content = response.json()["choices"][0]["message"]["content"].strip()
            # Parse markdown bullet list to list of strings
            return [line.lstrip('-* ').strip() for line in content.split('\n') if line.strip().startswith(('-', '*'))]
        else:
            return [f"[OpenAI API error: {response.text}]"]
    except Exception as e:
        return [f"[OpenAI API error: {e}]"]
    

    # Fallback to heuristic (should not be reached if API key is set)
    warnings = []
    # Detect low-quality commit messages using regex
    low_quality_patterns = re.compile(r"wip|fix|final|pls work|temp|test", re.IGNORECASE)
    low_quality = [msg for msg in commit_messages if low_quality_patterns.search(msg)]
    if low_quality:
        warnings.append(f"❌ {len(low_quality)} low-quality commit message(s) found: {', '.join(low_quality[:2])}{'...' if len(low_quality)>2 else ''}")
    else:
        warnings.append("✅ No low-quality commit messages found.")
    # Detect if test files are present
    test_files = [f for f in changed_files if 'test' in f or f.endswith('.test.js') or '__tests__' in f]
    if len(changed_files) > 10 and not test_files:
        warnings.append("❌ Large change (>10 files) but no test files detected.")
    elif not test_files:
        warnings.append("⚠ No test files detected in this stack.")
    else:
        warnings.append("✅ Test files present.")
    # Detect empty or placeholder commit messages
    empty_msgs = [msg for msg in commit_messages if not msg.strip() or msg.strip() in ['.', '-']]
    if empty_msgs:
        warnings.append(f"⚠ {len(empty_msgs)} commit(s) with empty or placeholder description.")
    else:
        warnings.append("✅ All commits have descriptions.")
    return warnings 