from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="prpolish",
    packages=find_packages(),
    version="0.2.7",
    install_requires=[
        "click",
        "GitPython",
        "pyperclip"
    ],
    entry_points={
        "console_scripts": [
            "prpolish=prpolish.cli:main"
        ]
    },
    author="Yash Gupta",
    author_email="ysgupta@wisc.edu",
    description="A CLI tool to generate PR titles and descriptions for Git repositories",
    url="https://github.com/yashg4509/prpolish",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    long_description=long_description,
    long_description_content_type="text/markdown",
)
