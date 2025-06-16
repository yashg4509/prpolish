"""
Clipboard utility for copying text to the system clipboard.
Uses pyperclip for cross-platform support.
"""
import pyperclip

def copy_to_clipboard(text: str):
    """
    Copy the given text to the system clipboard.
    """
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as e:
        raise RuntimeError(f"Failed to copy to clipboard: {e}") 