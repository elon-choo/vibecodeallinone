"""Validate all SKILL.md files have required frontmatter fields."""

import glob
from pathlib import Path

import yaml
import pytest

REPO_ROOT = Path(__file__).parent.parent
REQUIRED_FIELDS = ["name", "description", "license", "allowed-tools"]


def get_skill_paths():
    pattern = str(REPO_ROOT / "skills" / "*" / "SKILL.md")
    return sorted(glob.glob(pattern))


@pytest.fixture(params=get_skill_paths(), ids=lambda p: Path(p).parent.name)
def skill_path(request):
    return request.param


def test_frontmatter_exists(skill_path):
    """SKILL.md starts with YAML frontmatter delimiters."""
    content = Path(skill_path).read_text()
    assert content.startswith("---"), f"{skill_path}: missing opening '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{skill_path}: missing closing '---'"


def test_frontmatter_valid_yaml(skill_path):
    """Frontmatter is parseable YAML."""
    content = Path(skill_path).read_text()
    if not content.startswith("---"):
        pytest.skip("no frontmatter")
    raw = content.split("---", 2)[1]
    meta = yaml.safe_load(raw)
    assert isinstance(meta, dict), f"{skill_path}: frontmatter is not a YAML mapping"


def test_frontmatter_required_fields(skill_path):
    """All required fields are present."""
    content = Path(skill_path).read_text()
    if not content.startswith("---"):
        pytest.skip("no frontmatter")
    raw = content.split("---", 2)[1]
    meta = yaml.safe_load(raw)
    if not isinstance(meta, dict):
        pytest.skip("invalid frontmatter")
    missing = [f for f in REQUIRED_FIELDS if f not in meta]
    assert not missing, f"{skill_path}: missing fields: {missing}"


def test_skill_count():
    """There are exactly 12 skills."""
    paths = get_skill_paths()
    assert len(paths) == 12, f"Expected 12 skills, found {len(paths)}: {[Path(p).parent.name for p in paths]}"
