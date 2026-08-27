from pathlib import Path
from autoreview.classifier import classify_content

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def test_classifier_dsa():
    dsa_path = FIXTURES_DIR / "sample_dsa.py"
    content = dsa_path.read_text(encoding="utf-8")
    result = classify_content(content, dsa_path.name)
    assert result == "dsa_problem"

def test_classifier_snippet():
    snippet_path = FIXTURES_DIR / "sample_snippet.py"
    content = snippet_path.read_text(encoding="utf-8")
    result = classify_content(content, snippet_path.name)
    assert result == "snippet"

def test_classifier_diff():
    diff_path = FIXTURES_DIR / "sample_pr.diff"
    content = diff_path.read_text(encoding="utf-8")
    result = classify_content(content, diff_path.name)
    assert result == "pr_diff"

def test_classifier_third_party_imports():
    # Django or numpy imports should force classification as snippet
    content = """import numpy as np
def mean_val(arr):
    return np.mean(arr)
"""
    result = classify_content(content, "numpy_test.py")
    assert result == "snippet"

def test_classifier_io():
    # File I/O should force classification as snippet
    content = """def read_config():
    with open("config.txt", "r") as f:
        return f.read()
"""
    result = classify_content(content, "io_test.py")
    assert result == "snippet"

def test_classifier_no_definitions():
    # Only top-level expressions should be classified as snippet
    content = """print("Hello, world!")
x = 10 + 20
"""
    result = classify_content(content, "flat_script.py")
    assert result == "snippet"
