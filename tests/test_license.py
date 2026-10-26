"""Story 6.1: repository states MIT license and dependency compatibility."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_license_file_states_mit():
    text = (ROOT / "LICENSE").read_text()
    assert "MIT License" in text
    assert "Alfonso Bonillas" in text
    assert "alioit.com" in text


def test_readme_names_mit_license_and_rights():
    text = (ROOT / "README.md").read_text()
    assert "MIT License" in text
    assert "LICENSE" in text
    assert "Alfonso Bonillas" in text
    assert "alioit.com" in text
    assert "hold the rights" in text.lower() or "rights to this codebase" in text.lower()


def test_package_metadata_declares_mit():
    text = (ROOT / "pyproject.toml").read_text()
    assert "LICENSE" in text
    assert "MIT License" in text or 'license = { file = "LICENSE" }' in text
    assert 'name = "route-optimizer"' in text


def test_dependency_licenses_recorded_and_compatible():
    text = (ROOT / "DEPENDENCY_LICENSES.md").read_text()
    assert "MIT" in text
    for package in ("Django", "PuLP", "numpy", "pandas", "pyodbc"):
        assert package in text
    assert "Yes" in text
    assert "compatible" in text.lower() or "Compatible" in text
