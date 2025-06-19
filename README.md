<p align="center">
  <img src="https://img.shields.io/badge/AI%20PR%20Helper-%F0%9F%9A%80-blueviolet?style=for-the-badge" alt="AI PR Helper"/>
  <a href="https://pypi.org/project/prpolish/"><img src="https://img.shields.io/pypi/v/prpolish?style=for-the-badge&color=blue" alt="PyPI version"></a>
  <a href="https://github.com/yashg4509/prpolish/blob/main/LICENSE"><img src="https://img.shields.io/github/license/yashg4509/prpolish?style=for-the-badge&color=success" alt="License"></a>
</p>

<h1 align="center">prpolish: AI-Powered Pull Request Helper 🚀</h1>

<p align="center">
  <b>Supercharge your GitHub PRs with AI-generated titles, descriptions, and quality checks.</b><br/>
  <i>Make every PR shine ✨</i>
</p>

---

## 💡 Why prpolish?

> Writing great pull requests is hard. Most devs (including us!) struggle with:
> - Vague or low-effort PR titles and descriptions
> - Forgetting to link issues, docs, or tickets
> - Missing tests or unclear testing instructions
> - Inconsistent PR templates across teams

**prpolish** fixes this by using AI (OpenAI GPT) to generate high-quality, context-aware PR titles and descriptions, and to run "vibe checks" for PR quality—all from your terminal.

---

## ⚡ Quickstart

```bash
pip install prpolish
export OPENAI_API_KEY=sk-...
prpolish generate
```

- Instantly get a polished PR title and description, ready to copy or edit.
- Optionally, run vibe checks to catch low-quality commits or missing tests.
- Use your own PR templates, or let prpolish auto-detect them.

---

## Features

- **AI-Powered PR Title & Description Generator**: Context-aware, customizable, and always editable.
- **Vibe Check Warnings**: Flags low-quality commits, missing tests, and more.
- **CLI Interface**: Simple, interactive, and scriptable.
- **Custom Templates**: Use your own PR templates (string or file).
- **LLM-Powered, with Fallbacks**: Uses OpenAI GPT for best results, with smart heuristics if no API key.
- **Failsafe Defaults**: Always allows user editing and review.

---

## 🛠️ How It Works

1. **Analyzes your branch:**  
   Reads your commit messages, changed files, and branch name.
2. **Generates PR content:**  
   Uses OpenAI GPT (if available) or smart heuristics to create a professional PR title and description.
3. **Runs vibe checks:**  
   Optionally, flags issues like vague commits or missing tests. <br/>
   <sub>⚠️ <b>Note:</b> Vibe checks require an OpenAI API key and do <b>not</b> fall back to heuristics.</sub>
4. **Lets you edit and save:**  
   Copy to clipboard, save drafts, or open in your editor.
5. **Creates the PR:**  
   Pushes your branch and opens a PR via GitHub CLI (optional).

---

## 💻 CLI Usage

```bash
# Generate PR title and description
prpolish generate [--template <str|path>] [--save, -s title|description|both] [--fast, -f]

# Generate only the PR title
prpolish generate-title [--template <str|path>] [--save, -s]

# Generate only the PR description
prpolish generate-desc [--template <str|path>] [--save, -s]
```

- `--save, -s`: Save title, description, or both to draft files.
- `--fast, -f`: Automatically create the PR and commit it.

---

## ⚙️ Requirements

- Python 3.7+
- [OpenAI API key](https://platform.openai.com/account/api-keys) (for AI features)
- [GitHub CLI](https://cli.github.com/) (for auto PR creation, optional)

> Without an API key, the generations fall back on heuristic measures, but they are not as accurate usually.
---

## 📝 Custom PR Templates

Provide your own template using the `--template` flag (string or file path).  
If a `pull_request_template.md` exists, prpolish will auto-detect and use it.

---

## ❓ FAQ & Troubleshooting

<details>
<summary><b>What if I don't have an OpenAI API key?</b></summary>

- PR title/description generation will use smart heuristics instead of AI.
- Vibe checks will not work without an API key.
</details>

<details>
<summary><b>What if I don't have GitHub CLI (gh)?</b></summary>

You can still copy the PR title/description and create the PR manually.
</details>

<details>
<summary><b>Can I use my team's PR template?</b></summary>

Yes! Use `--template` or place a `pull_request_template.md` in your repo.
</details>

---

## 📄 License

[MIT](LICENSE)  
_Made by [@yashg4509](https://github.com/yashg4509)_

---

## 🏆 Shoutout

<div align="center" style="margin: 2em 0;">
  <b>Big thanks to <a href="https://graphite.dev/">Graphite</a> for their <a href="https://graphite.dev/guides/topic/pull-requests">excellent guides on PR best practices</a>, which inspired the prompts and structure in prpolish.</b>
</div>
