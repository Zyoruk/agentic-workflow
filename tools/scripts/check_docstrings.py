#!/usr/bin/env python3
"""Script to check and fix docstring formatting in Python files."""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional, Union


class DocstringValidator:
    """Validates and fixes docstring formatting and content."""

    def __init__(self):
        """Initialize the validator."""
        self.issues: List[Dict[str, Any]] = []
        self.cross_refs: Dict[str, Set[str]] = {}

    def validate_and_fix_emphasis(self, docstring: str, node_name: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Check and fix emphasis/strong markers.

        Args:
            docstring: The docstring to validate.
            node_name: Name of the node being validated.

        Returns:
            Tuple of (fixed docstring, list of issues)
        """
        issues = []
        # Check for unclosed emphasis/strong markers
        emphasis_pattern = r'(?<!\*)\*(?!\*)[^*]*$'
        strong_pattern = r'\*\*[^*]*$'

        if re.search(emphasis_pattern, docstring, re.MULTILINE):
            issues.append({
                'type': 'emphasis',
                'node': node_name,
                'message': 'Unclosed emphasis marker (*) in docstring'
            })
            # Fix by closing the emphasis marker
            fixed_docstring = re.sub(emphasis_pattern, '*', docstring)
            return fixed_docstring, issues

        if re.search(strong_pattern, docstring, re.MULTILINE):
            issues.append({
                'type': 'strong',
                'node': node_name,
                'message': 'Unclosed strong marker (**) in docstring'
            })
            # Fix by closing the strong marker
            fixed_docstring = re.sub(strong_pattern, '**', docstring)
            return fixed_docstring, issues

        return docstring, []

    def validate_and_fix_cross_refs(self, docstring: str, node_name: str, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Check and fix cross-reference issues.

        Args:
            docstring: The docstring to validate.
            node_name: Name of the node being validated.
            file_path: Path to the file being validated.

        Returns:
            Tuple of (fixed docstring, list of issues)
        """
        issues = []
        # Find all cross-references in the docstring
        cross_ref_pattern = r':(?:class|func|meth|attr|exc|obj):`([^`]+)`'
        matches = re.finditer(cross_ref_pattern, docstring)

        for match in matches:
            ref_name = match.group(1)
            if ref_name not in self.cross_refs:
                self.cross_refs[ref_name] = set()
            self.cross_refs[ref_name].add(file_path)

            # If this is a duplicate reference, add :no-index: to the docstring
            if len(self.cross_refs[ref_name]) > 1:
                issues.append({
                    'type': 'cross_ref',
                    'node': node_name,
                    'message': f'Duplicate cross-reference to {ref_name}'
                })
                if not docstring.strip().endswith(':no-index:'):
                    fixed_docstring = docstring.rstrip() + '\n\n:no-index:'
                    return fixed_docstring, issues

        return docstring, []

    def validate_and_fix_indentation(self, docstring: str, node_name: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Check and fix indentation in docstring.

        Args:
            docstring: The docstring to validate.
            node_name: Name of the node being validated.

        Returns:
            Tuple of (fixed docstring, list of issues)
        """
        issues = []
        lines = docstring.split('\n')
        if len(lines) > 1:
            # Find the most common indentation
            indents = [len(line) - len(line.lstrip()) for line in lines[1:] if line.strip()]
            if indents:
                common_indent = max(set(indents), key=indents.count)
                fixed_lines = [lines[0]]  # Keep first line as is
                for i, line in enumerate(lines[1:], 1):
                    if line.strip():
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent != common_indent:
                            issues.append({
                                'type': 'indentation',
                                'node': node_name,
                                'line': i + 1,
                                'message': 'Inconsistent indentation in docstring'
                            })
                            # Fix indentation
                            fixed_line = ' ' * common_indent + line.lstrip()
                            fixed_lines.append(fixed_line)
                        else:
                            fixed_lines.append(line)
                    else:
                        fixed_lines.append(line)
                return '\n'.join(fixed_lines), issues
        return docstring, []

    def validate_and_fix_literals(self, docstring: str, node_name: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Check and fix literal formatting.

        Args:
            docstring: The docstring to validate.
            node_name: Name of the node being validated.

        Returns:
            Tuple of (fixed docstring, list of issues)
        """
        issues = []
        # Find unclosed literal markers
        literal_pattern = r'`[^`]*$'
        if re.search(literal_pattern, docstring, re.MULTILINE):
            issues.append({
                'type': 'literal',
                'node': node_name,
                'message': 'Unclosed literal marker (`) in docstring'
            })
            # Fix by closing the literal marker
            fixed_docstring = re.sub(literal_pattern, '`', docstring)
            return fixed_docstring, issues
        return docstring, []

    def validate_and_fix_block_quotes(self, docstring: str, node_name: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Check and fix block quote formatting.

        Args:
            docstring: The docstring to validate.
            node_name: Name of the node being validated.

        Returns:
            Tuple of (fixed docstring, list of issues)
        """
        issues = []
        lines = docstring.split('\n')
        fixed_lines = []
        in_block_quote = False
        for i, line in enumerate(lines):
            if line.strip().startswith('>>>'):
                in_block_quote = True
                fixed_lines.append(line)
            elif in_block_quote and not line.strip():
                in_block_quote = False
                fixed_lines.append(line)
            elif in_block_quote and not line.strip().startswith('>>>') and not line.strip().startswith('...'):
                issues.append({
                    'type': 'block_quote',
                    'node': node_name,
                    'line': i + 1,
                    'message': 'Block quote ends without a blank line'
                })
                # Add blank line before non-block quote content
                fixed_lines.append('')
                fixed_lines.append(line)
                in_block_quote = False
            else:
                fixed_lines.append(line)
        return '\n'.join(fixed_lines), issues

    def validate_and_fix_duplicate_descriptions(self, docstring: str, node_name: str, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Check and fix duplicate object descriptions.

        Args:
            docstring: The docstring to validate.
            node_name: Name of the node being validated.
            file_path: Path to the file being validated.

        Returns:
            Tuple of (fixed docstring, list of issues)
        """
        issues = []
        if '__init__.py' in file_path:
            issues.append({
                'type': 'duplicate',
                'node': node_name,
                'message': 'Duplicate object description, consider using :no-index:'
            })
            # Add :no-index: to the docstring
            if not docstring.strip().endswith(':no-index:'):
                fixed_docstring = docstring.rstrip() + '\n\n:no-index:'
                return fixed_docstring, issues
        return docstring, []


def get_docstring(node: ast.AST) -> Optional[str]:
    """Get docstring from an AST node.

    Args:
        node: AST node to get docstring from.

    Returns:
        Docstring if found, None otherwise.
    """
    if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
        return None

    if not node.body:
        return None

    first_node = node.body[0]
    if isinstance(first_node, ast.Expr) and isinstance(first_node.value, ast.Str):
        return first_node.value.s
    return None


def fix_docstring_in_file(filepath: str, validator: DocstringValidator) -> None:
    """Fix docstring issues in a file.

    Args:
        filepath: Path to the file to fix.
        validator: DocstringValidator instance.
    """
    with open(filepath, 'r') as f:
        content = f.read()

    tree = ast.parse(content)
    modified = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            docstring = get_docstring(node)
            if docstring:
                # Apply fixes
                fixed_docstring, issues = validator.validate_and_fix_indentation(docstring, node.name)
                fixed_docstring, literal_issues = validator.validate_and_fix_literals(fixed_docstring, node.name)
                fixed_docstring, block_quote_issues = validator.validate_and_fix_block_quotes(fixed_docstring, node.name)
                fixed_docstring, cross_ref_issues = validator.validate_and_fix_cross_refs(
                    fixed_docstring, node.name, filepath
                )
                fixed_docstring, emphasis_issues = validator.validate_and_fix_emphasis(fixed_docstring, node.name)

                if issues or literal_issues or block_quote_issues or cross_ref_issues or emphasis_issues:
                    # Replace the docstring in the file content
                    content = content.replace(docstring, fixed_docstring)
                    modified = True
                    print(f'  Fixed issues in {node.name}:')
                    for issue in issues + literal_issues + block_quote_issues + cross_ref_issues + emphasis_issues:
                        print(f'    - {issue["type"]}: {issue["message"]}')
                        if 'line' in issue:
                            print(f'      Line {issue["line"]}')

    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f'  ✅ Fixed docstring issues in {filepath}')


def check_docstrings(path: str, fix: bool = False) -> None:
    """Check and optionally fix docstrings in Python files.

    Args:
        path: Path to the directory containing Python files.
        fix: Whether to automatically fix issues.
    """
    validator = DocstringValidator()

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                print(f'\nChecking {filepath}...')
                try:
                    if fix:
                        fix_docstring_in_file(filepath, validator)
                    else:
                        with open(filepath, 'r') as f:
                            tree = ast.parse(f.read())
                            for node in ast.walk(tree):
                                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                                    docstring = get_docstring(node)
                                    if docstring:
                                        print(f'  Found docstring in {node.name}')
                                        validator.validate_and_fix_indentation(docstring, node.name)
                                        validator.validate_and_fix_literals(docstring, node.name)
                                        validator.validate_and_fix_block_quotes(docstring, node.name)
                                        validator.validate_and_fix_cross_refs(docstring, node.name, filepath)
                                        validator.validate_and_fix_emphasis(docstring, node.name)
                                    else:
                                        print(f'  Missing docstring in {node.name}')

                        if validator.issues:
                            print('\n  Issues found:')
                            for issue in validator.issues:
                                print(f'    - {issue["type"]}: {issue["message"]} in {issue["node"]}')
                                if 'line' in issue:
                                    print(f'      Line {issue["line"]}')
                except Exception as e:
                    print(f'  Error processing {filepath}: {e}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python check_docstrings.py <path> [--fix]')
        sys.exit(1)

    path = sys.argv[1]
    fix = len(sys.argv) > 2 and sys.argv[2] == '--fix'
    check_docstrings(path, fix)
