#!/usr/bin/env python3
"""
Cleanup script to remove JavaScript comments from HTML files.

This script recursively finds all HTML files in the project and removes
JavaScript comments (// and /* */) from within <script> tags only.

Features:
- Uses BeautifulSoup for robust HTML parsing (no regex for HTML)
- Uses a proper tokenizer for JavaScript comment removal (handles strings correctly)
- Preserves HTML comments and structure
- Creates backup files by default
- Supports dry-run mode

Dependencies:
- beautifulsoup4 (already in requirements.txt)
"""

import os
import sys
import shutil
from pathlib import Path

# Auto-activate virtual environment if it exists
try:
    venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'activate_this.py')
    if os.path.exists(venv_path):
        with open(venv_path) as f:
            exec(f.read(), {'__file__': venv_path})
except Exception:
    # If venv activation fails, continue without it
    pass

from bs4 import BeautifulSoup


def find_html_files(root_dir):
    """Recursively find all HTML files in the given directory."""
    html_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'node_modules']]

        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))

    return sorted(html_files)


def remove_js_comments(js_code):
    """
    Remove JavaScript comments from JavaScript code using a proper tokenizer.

    This function properly handles:
    - Single-line comments: // ...
    - Multi-line comments: /* ... */
    - Comments inside strings are preserved
    - Nested contexts are handled correctly
    """
    if not js_code:
        return js_code

    result = []
    i = 0
    length = len(js_code)

    while i < length:
        char = js_code[i]

        # Handle string literals (single and double quotes)
        if char in ('"', "'"):
            quote_char = char
            result.append(char)
            i += 1

            # Find the end of the string, handling escape sequences
            while i < length:
                char = js_code[i]
                result.append(char)
                if char == quote_char:
                    # Check if it's escaped
                    escape_count = 0
                    j = i - 1
                    while j >= 0 and js_code[j] == '\\':
                        escape_count += 1
                        j -= 1
                    if escape_count % 2 == 0:  # Not escaped
                        break
                elif char == '\\':
                    # Skip the escaped character
                    i += 1
                    if i < length:
                        result.append(js_code[i])
                i += 1
            i += 1
            continue

        # Handle multi-line comments /* ... */
        elif i + 1 < length and js_code[i:i+2] == '/*':
            # Skip to the end of the comment
            i += 2
            while i + 1 < length and js_code[i:i+2] != '*/':
                i += 1
            if i + 1 < length:
                i += 2  # Skip the */
            continue

        # Handle single-line comments // ...
        elif i + 1 < length and js_code[i:i+2] == '//':
            # Skip to the end of the line
            while i < length and js_code[i] != '\n':
                i += 1
            continue

        # Regular character
        else:
            result.append(char)
            i += 1

    return ''.join(result)


def remove_js_comments_from_html(content):
    """
    Remove JavaScript comments from within <script> tags in HTML content.

    Uses BeautifulSoup for robust HTML parsing and preserves all HTML structure.
    """
    soup = BeautifulSoup(content, 'html.parser')

    # Find all script tags
    script_tags = soup.find_all('script')

    for script_tag in script_tags:
        if script_tag.string:  # Only process if there's actual content
            original_content = script_tag.string
            cleaned_content = remove_js_comments(original_content)

            # Clean up excessive blank lines (more than 2 consecutive)
            import re
            cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)

            script_tag.string = cleaned_content

    return str(soup)


def process_file(file_path, dry_run=False, backup=True):
    """Process a single HTML file to remove JavaScript comments."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        modified_content = remove_js_comments_from_html(original_content)

        if original_content == modified_content:
            print(f"No changes needed: {file_path}")
            return False

        if dry_run:
            print(f"Would modify: {file_path}")
            return True

        # Create backup if requested
        if backup:
            backup_path = file_path + '.backup'
            shutil.copy2(file_path, backup_path)
            print(f"Created backup: {backup_path}")

        # Write modified content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        print(f"Processed: {file_path}")
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to run the cleanup script."""
    import argparse

    parser = argparse.ArgumentParser(description='Remove JavaScript comments from HTML files')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Show what would be changed without making changes')
    parser.add_argument('--no-backup', action='store_true',
                       help='Do not create backup files')
    parser.add_argument('--directory', '-d', default='.',
                       help='Directory to process (default: current directory)')
    parser.add_argument('--files', nargs='*',
                       help='Specific files to process instead of scanning directory')

    args = parser.parse_args()

    # Resolve the directory path
    if args.files:
        html_files = [os.path.abspath(f) for f in args.files if f.endswith('.html')]
    else:
        root_dir = os.path.abspath(args.directory)
        print(f"Scanning for HTML files in: {root_dir}")
        html_files = find_html_files(root_dir)

    if not html_files:
        print("No HTML files found.")
        return

    print(f"Found {len(html_files)} HTML files")

    modified_count = 0
    for file_path in html_files:
        if process_file(file_path, dry_run=args.dry_run, backup=not args.no_backup):
            modified_count += 1

    if args.dry_run:
        print(f"\nDry run complete. Would modify {modified_count} files.")
    else:
        print(f"\nProcessing complete. Modified {modified_count} files.")

    if not args.dry_run and not args.no_backup and modified_count > 0:
        print("Backup files created with '.backup' extension.")


if __name__ == '__main__':
    main()
