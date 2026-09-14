"""Unit tests for FileFilter, binary detection, and path security."""

import pytest
from code_intelligence.filter.file_filter import FileFilter


def test_path_traversal_detection():
    # Dangerous path traversal
    assert FileFilter.is_safe_path("../../etc/passwd") is False
    assert FileFilter.is_safe_path("src/../../../root") is False
    assert FileFilter.is_safe_path("a/b/../../..") is False

    # Safe paths
    assert FileFilter.is_safe_path("src/payment.py") is True
    assert FileFilter.is_safe_path("app/controllers/index.ts") is True

    # Sanitize raises on traversal
    with pytest.raises(ValueError):
        FileFilter.sanitize_path("../../secret.py")

    assert FileFilter.sanitize_path("src/nested/file.py") == "src/nested/file.py"


def test_ignore_patterns():
    ff = FileFilter()
    assert ff.is_indexable_file("node_modules/express/index.js") is False
    assert ff.is_indexable_file(".git/config") is False
    assert ff.is_indexable_file("dist/bundle.js") is False
    assert ff.is_indexable_file("coverage/lcov.info") is False
    assert ff.is_indexable_file("package-lock.json") is False
    assert ff.is_indexable_file("poetry.lock") is False
    assert ff.is_indexable_file("app.pyc") is False

    # Valid source files
    assert ff.is_indexable_file("src/services/payment.py") is True
    assert ff.is_indexable_file("components/Button.tsx") is True


def test_binary_file_detection():
    # Null byte detection
    binary_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    text_content = b"def hello_world():\n    return 'OK'\n"

    assert FileFilter.is_binary(binary_content) is True
    assert FileFilter.is_binary(text_content) is False


def test_large_file_protection():
    ff = FileFilter(max_file_size_bytes=1000, max_source_lines=50)

    # Size limit
    huge_bytes = b"x = 1\n" * 300  # ~1800 bytes
    ok_size, err_size = ff.check_file_limits("big.py", huge_bytes)
    assert ok_size is False
    assert "exceeds limit" in err_size

    # Line limit
    many_lines = b"x\n" * 60
    ok_lines, err_lines = ff.check_file_limits("many.py", many_lines)
    assert ok_lines is False
    assert "exceeding limit" in err_lines
