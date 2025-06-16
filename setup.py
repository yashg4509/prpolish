from setuptools import setup, find_packages

setup(
    name="prpolish",
    version="0.1",
    packages=find_packages(),
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
)
