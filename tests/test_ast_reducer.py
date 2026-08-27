from pathlib import Path
from autoreview.ast_reducer import reduce_python_code

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def test_ast_reduction_size_and_validity():
    snippet_path = FIXTURES_DIR / "sample_snippet.py"
    content = snippet_path.read_text(encoding="utf-8")
    
    # Run AST reduction targeting "analyze_data"
    reduced_code, orig_chars, red_chars = reduce_python_code(content, target="analyze_data")
    
    # 1. Assert size reduction is > 30%
    # (reduced_char_count / original_char_count) should be < 0.70
    savings_pct = (1 - (red_chars / orig_chars)) * 100
    assert savings_pct > 30, f"Reduction savings was only {savings_pct:.2f}%, expected > 30%"

    # 2. Check syntax validity by compiling
    try:
        compile(reduced_code, "<string>", "exec")
    except SyntaxError as e:
        assert False, f"Reduced code is not syntactically valid: {e}"

    # 3. Assert target and used helper are present
    assert "def analyze_data(" in reduced_code
    assert "def calculate_average(" in reduced_code

    # 4. Assert unused function body is not present
    # Note: we replaced the body with newlines, but the string "def unused_helper_function"
    # itself should not be present in the final source output
    assert "def unused_helper_function(" not in reduced_code
