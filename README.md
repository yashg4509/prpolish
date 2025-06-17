<!-- HERO SECTION -->
<p align="center">
  <img src="https://img.shields.io/badge/AI%20PR%20Helper-%F0%9F%9A%80-blueviolet?style=for-the-badge" alt="AI PR Helper"/>
</p>
<h1 align="center">prpolish: AI-Powered PR Helper</h1>
<p align="center">
  <b>Supercharge your pull requests with AI-generated titles, descriptions, and quality checks!</b><br/>
  <i>Make every PR shine ✨</i>
</p>

<!-- BADGES -->
<p align="center">
  <a href="https://pypi.org/project/prpolish/"><img src="https://img.shields.io/pypi/v/prpolish?style=for-the-badge&color=blue" alt="PyPI version"></a>
  <a href="https://github.com/yashg4509/prpolish/blob/main/LICENSE"><img src="https://img.shields.io/github/license/yashg4509/prpolish?style=for-the-badge&color=success" alt="License"></a>
</p>

---

<!-- DEMO GIF/IMAGE -->
<p align="center">
  COMING SOON
  <br/>
  <i>Above: Example of prpolish generating a beautiful PR description and running vibe checks</i>
</p>

---

## Features

- <b>PR Title & Description Generator:</b> AI-powered, context-aware, and customizable.
- <b>Vibe Check Warnings:</b> Flags low-quality commits, missing tests, and more.
- <b>CLI Interface:</b> Simple, interactive, and scriptable.
- <b>Custom Templates:</b> Use your own PR templates (string or file).
- <b>LLM-Powered:</b> Uses OpenAI GPT for best results, with fallback heuristics.
- <b>Failsafe Defaults:</b> Always allows user editing and review.

---

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Install GitHub CLI for auto PR creation
# https://cli.github.com/
```

---

## Usage

```bash
# Generate PR title and description
prpolish generate [--template <str|path>] [--save, -s title|description|both] [--fast, -f]

# Generate only the PR title
prpolish generate-title [--template <str|path>] [--save, -s]

# Generate only the PR description
prpolish generate-desc [--template <str|path>] [--save, -s]

```

## Flags 
`-save, -s`: allows you to save either the title, description, or both (default) to a draft file
`--fast, -f`: automatically creates the PR and commits it

---

## LLM-Powered PR Descriptions

1. Get your OpenAI API key from <a href="https://platform.openai.com/account/api-keys" target="_blank">OpenAI</a>
2. Set it in your environment:

```bash
export OPENAI_API_KEY=sk-...
```

If no API key is set, the tool falls back to a heuristic generator.

---

## Custom PR Templates

You can provide your own template for the PR description using the `--template` flag. This can be either a string or a path to a file containing your template. 

If you already have a `pull_request_template.md`, it will automatically detect it and use it.

---

## License

<p align="center">
  <a href="https://github.com/yashg4509/prpolish/blob/main/LICENSE"><img src="https://img.shields.io/github/license/yashg4509/prpolish?style=flat-square&color=success" alt="License"></a>
</p>

<p align="center">
  <sub>Made by <a href="https://github.com/yashg4509">@yashg4509</a></sub>
</p> 
