import json
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_declares_uv_managed_python_project():
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml should exist for uv-managed installs"

    data = tomllib.loads(pyproject_path.read_text())
    project = data["project"]

    assert project["name"] == "skill-optimization-demo"
    assert project["requires-python"] == ">=3.12,<3.13"

    deps = set(project["dependencies"])
    assert "openai>=1.0.0" in deps
    assert "tqdm>=4.60.0" in deps

    dependency_groups = data["dependency-groups"]
    assert "dev" in dependency_groups
    assert "pytest>=8.0" in dependency_groups["dev"]


def test_package_json_exposes_repo_entrypoint_scripts():
    package_json_path = PROJECT_ROOT / "package.json"
    package = json.loads(package_json_path.read_text())

    scripts = package["scripts"]
    assert scripts["evomap:build"] == "node scripts/evomap_sdk_build.mjs"
    assert scripts["evomap:list"] == "uv run python scripts/publish_to_evomap.py --list"


def test_repo_level_repro_docs_and_docker_files_exist():
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert "uv sync --dev" in readme
    assert "docker build -t skill-optimization-dev ." in readme
    assert "docs/setup_and_repro.md" in readme

    setup_doc = PROJECT_ROOT / "docs" / "setup_and_repro.md"
    assert setup_doc.exists(), "Detailed setup guide should exist"
    setup_text = setup_doc.read_text()
    assert "npm ci" in setup_text
    assert "uv run pytest" in setup_text
    assert ".evomap_secrets.json" in setup_text

    dockerfile = PROJECT_ROOT / "Dockerfile"
    assert dockerfile.exists(), "Repo-level Dockerfile should exist"
    docker_text = dockerfile.read_text()
    assert "FROM python:3.12-slim" in docker_text
    assert "uv sync --frozen --dev" in docker_text
    assert "npm ci" in docker_text

    dockerignore = PROJECT_ROOT / ".dockerignore"
    assert dockerignore.exists(), ".dockerignore should exist"
    ignore_entries = dockerignore.read_text()
    for entry in [".git", ".worktrees", ".venv", "node_modules", "results", ".env", ".evomap_secrets.json"]:
        assert entry in ignore_entries
