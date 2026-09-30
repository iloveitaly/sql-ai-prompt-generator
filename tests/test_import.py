"""Test llm-sql-prompt."""

import llm_sql_prompt


def test_import() -> None:
    """Test that the package can be imported."""
    assert isinstance(llm_sql_prompt.__name__, str)


def test_version() -> None:
    """Test that the version is available."""
    assert isinstance(llm_sql_prompt.__version__, str)
