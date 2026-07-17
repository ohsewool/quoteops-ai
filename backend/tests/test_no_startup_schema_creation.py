from pathlib import Path


def test_runtime_source_does_not_create_schema_implicitly() -> None:
    runtime_files = [
        path
        for path in Path("backend").rglob("*.py")
        if "tests" not in path.parts and "__pycache__" not in path.parts
    ]

    assert all("create_all(" not in path.read_text(encoding="utf-8") for path in runtime_files)
