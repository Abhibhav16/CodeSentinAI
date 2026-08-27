import logging
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node
from typing import Optional, Tuple, Set, Dict

logger = logging.getLogger("autoreview.ast_reducer")

# Initialize tree-sitter Python language and parser
PY_LANGUAGE = Language(tspython.language())

def get_parser() -> Parser:
    parser = Parser(PY_LANGUAGE)
    return parser

def get_node_name(node: Node, source_bytes: bytes) -> Optional[str]:
    """Extract the name identifier from a function or class definition node."""
    name_node = node.child_by_field_name("name")
    if name_node:
        return name_node.text.decode("utf-8")
    return None

def traverse_for_identifiers(node: Node, source_bytes: bytes, identifiers: Set[str]) -> None:
    """Recursively traverse a node to gather all identifier names."""
    if node.type == "identifier":
        name = node.text.decode("utf-8")
        identifiers.add(name)
    for child in node.children:
        traverse_for_identifiers(child, source_bytes, identifiers)

def get_dependencies(node: Node, defined_names: Set[str], source_bytes: bytes) -> Set[str]:
    """Find all top-level definitions referenced inside the body of the given node."""
    identifiers: Set[str] = set()
    
    # We want to scan the body or children of this definition.
    # To avoid matching the node's own name, we can traverse its children except the 'name' field if we want,
    # but simply removing the node's own name from the resolved set is cleaner.
    node_name = get_node_name(node, source_bytes)
    
    traverse_for_identifiers(node, source_bytes, identifiers)
    
    # Filter to only keep identifiers that are defined at the top-level
    deps = identifiers.intersection(defined_names)
    if node_name in deps:
        deps.remove(node_name)
    return deps

def auto_detect_target(definitions: Dict[str, Tuple[str, Node]], source_bytes: bytes) -> Optional[str]:
    """
    Heuristically auto-detects the target function/class.
    1. Look for class named 'Solution' (typical in DSA).
    2. Look for any class/function containing 'solve', 'solution', or 'main' (case-insensitive).
    3. Default to the last defined top-level class or function.
    """
    if not definitions:
        return None

    # Heuristic 1: class 'Solution'
    if "Solution" in definitions and definitions["Solution"][0] == "class_definition":
        return "Solution"

    # Heuristic 2: 'solve', 'solution', 'main'
    keywords = ["solve", "solution", "main"]
    for name, (node_type, _) in definitions.items():
        name_lower = name.lower()
        if any(kw in name_lower for kw in keywords):
            return name

    # Heuristic 3: last defined top-level class/function
    # We sort by their start_byte to find the last one defined
    sorted_defs = sorted(definitions.items(), key=lambda item: item[1][1].start_byte)
    if sorted_defs:
        return sorted_defs[-1][0]

    return None

def reduce_python_code(content: str, target: Optional[str] = None) -> Tuple[str, int, int]:
    """
    Reduces the Python code to only contain imports, global context, and
    the target definition plus its transitively referenced helper definitions.
    
    Returns:
        (reduced_code, original_char_count, reduced_char_count)
    """
    source_bytes = content.encode("utf-8")
    original_char_count = len(content)

    parser = get_parser()
    tree = parser.parse(source_bytes)
    root = tree.root_node

    # 1. Identify all top-level class/function definitions
    definitions: Dict[str, Tuple[str, Node]] = {}
    for child in root.children:
        if child.type in ("function_definition", "class_definition"):
            name = get_node_name(child, source_bytes)
            if name:
                definitions[name] = (child.type, child)

    if not definitions:
        # No classes/functions defined, nothing to reduce
        return content, original_char_count, original_char_count

    # 2. Determine target
    actual_target = target
    if not actual_target:
        actual_target = auto_detect_target(definitions, source_bytes)
        
    if not actual_target or actual_target not in definitions:
        # If target isn't found in definitions, cannot reduce confidently
        logger.warning(f"Target '{actual_target}' not found in definitions. Returning full content.")
        return content, original_char_count, original_char_count

    # 3. Build dependency graph
    defined_names = set(definitions.keys())
    dep_graph: Dict[str, Set[str]] = {}
    for name, (_, node) in definitions.items():
        dep_graph[name] = get_dependencies(node, defined_names, source_bytes)

    # 4. Find all required definitions using BFS/DFS
    required_names: Set[str] = {actual_target}
    queue = [actual_target]
    while queue:
        current = queue.pop(0)
        for dep in dep_graph.get(current, set()):
            if dep not in required_names:
                required_names.add(dep)
                queue.append(dep)

    # 5. Excise excluded definitions (replacing with newlines to preserve line numbers)
    excluded_ranges = []
    for child in root.children:
        if child.type in ("function_definition", "class_definition"):
            name = get_node_name(child, source_bytes)
            if name and name not in required_names:
                excluded_ranges.append((child.start_byte, child.end_byte))

    # Reconstruct the code by replacing excluded ranges with newlines
    new_bytes = bytearray()
    last_idx = 0
    # Sort excluded ranges just in case (tree-sitter children should already be sorted)
    excluded_ranges.sort(key=lambda x: x[0])
    
    for start, end in excluded_ranges:
        new_bytes.extend(source_bytes[last_idx:start])
        # Count how many newlines are in the excluded block
        excluded_block = source_bytes[start:end]
        newline_count = excluded_block.count(b"\n")
        new_bytes.extend(b"\n" * newline_count)
        last_idx = end
    new_bytes.extend(source_bytes[last_idx:])

    reduced_code = new_bytes.decode("utf-8")
    reduced_char_count = len(reduced_code)

    # Estimate tokens: 1 token ~ 3.5 characters for source code
    orig_tokens = int(original_char_count / 3.5)
    red_tokens = int(reduced_char_count / 3.5)
    savings_pct = (1 - (reduced_char_count / original_char_count)) * 100 if original_char_count > 0 else 0

    logger.info(
        f"Context reduction complete. Target: {actual_target}. "
        f"Characters: {original_char_count} -> {reduced_char_count} ({savings_pct:.1f}% savings). "
        f"Estimated Tokens: {orig_tokens} -> {red_tokens}."
    )

    return reduced_code, original_char_count, reduced_char_count
