import ast
import os
import re
from typing import Literal

ALLOWED_DSA_MODULES = {
    "math", "collections", "itertools", "bisect", "heapq", "typing",
    "sys", "array", "functools", "re", "string", "random", "json",
    "datetime", "copy", "typing_extensions"
}

def is_git_diff(content: str, filename: str = None) -> bool:
    """Detects if the file or content looks like a git diff."""
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in (".diff", ".patch"):
            return True
            
    # Heuristics based on content
    if content.startswith("diff --git"):
        return True
    
    # Check for typical diff headers
    lines = content.splitlines()
    has_minus = False
    has_plus = False
    for line in lines[:20]:  # Check first 20 lines
        if line.startswith("--- a/"):
            has_minus = True
        elif line.startswith("+++ b/"):
            has_plus = True
        if has_minus and has_plus:
            return True
            
    return False

class DSACandidateVisitor(ast.NodeVisitor):
    def __init__(self):
        self.is_dsa_compatible = True
        self.has_definitions = False
        self.imported_modules = set()

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            parts = name.name.split('.')
            self.imported_modules.add(parts[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            parts = node.module.split('.')
            self.imported_modules.add(parts[0])
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detect calls to open() or other disk/network operations
        if isinstance(node.func, ast.Name):
            if node.func.id == 'open':
                self.is_dsa_compatible = False
        elif isinstance(node.func, ast.Attribute):
            # Detect things like socket.socket, sqlite3.connect, requests.get
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                if module_name in ('socket', 'sqlite3', 'requests', 'urllib', 'http'):
                    self.is_dsa_compatible = False
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.has_definitions = True
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.has_definitions = True
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.has_definitions = True
        self.generic_visit(node)

def classify_content(content: str, filename: str = None) -> Literal["dsa_problem", "pr_diff", "snippet"]:
    """
    Classifies a code submission into "dsa_problem", "pr_diff", or "snippet".
    """
    if is_git_diff(content, filename):
        return "pr_diff"

    # If it's not a Python file and not a diff, default to snippet
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext != ".py":
            return "snippet"

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # If it doesn't parse as Python, treat it as snippet
        return "snippet"

    visitor = DSACandidateVisitor()
    visitor.visit(tree)

    # If it doesn't define any functions or classes, it's just a script snippet
    if not visitor.has_definitions:
        return "snippet"

    # If it called open() or other blacklisted I/O operations
    if not visitor.is_dsa_compatible:
        return "snippet"

    # Check if all imported modules are in the allowed list of standard DSA modules
    for mod in visitor.imported_modules:
        if mod not in ALLOWED_DSA_MODULES:
            return "snippet"

    return "dsa_problem"
