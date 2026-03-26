import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import yaml

import src.evomap_publisher as evomap_publisher
from src.evomap_publisher import build_capsule, build_gene, compute_canonical_hash


PROJECT_ROOT = Path(__file__).parent.parent
SKILLSBENCH_SKILL = PROJECT_ROOT / "skills" / "skillsbench" / "curated" / "overfull_hbox.yaml"
SDK_HELPER = PROJECT_ROOT / "scripts" / "evomap_sdk_build.mjs"


def load_skill(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def test_build_gene_includes_required_gep_fields():
    skill = load_skill(SKILLSBENCH_SKILL)

    gene = build_gene(skill)

    assert gene["type"] == "Gene"
    assert gene["schema_version"] == "1.5.0"
    assert gene["id"].startswith("gene_")
    assert gene["category"] in {"repair", "optimize", "innovate"}
    assert isinstance(gene["signals_match"], list) and gene["signals_match"]
    assert all(isinstance(signal, str) and len(signal) >= 3 for signal in gene["signals_match"])
    assert len(gene["strategy"]) >= 2
    assert all(isinstance(step, str) and step.strip() for step in gene["strategy"])
    assert isinstance(gene["preconditions"], list) and gene["preconditions"]
    assert gene["constraints"]["max_files"] >= 1
    assert isinstance(gene["constraints"]["forbidden_paths"], list)
    assert isinstance(gene["validation"], list) and gene["validation"]
    assert all(cmd.startswith(("node ", "npm ", "npx ")) for cmd in gene["validation"])
    assert any(
        "throw new Error" in cmd
        or "assert." in cmd
        or "node:assert/strict" in cmd
        for cmd in gene["validation"]
    )
    assert not all("console.log" in cmd for cmd in gene["validation"])
    assert all(";" not in cmd for cmd in gene["validation"])
    assert all(">" not in cmd for cmd in gene["validation"])

    gene_no_id = {k: v for k, v in gene.items() if k != "asset_id"}
    assert gene["asset_id"] == compute_canonical_hash(gene_no_id)


def test_build_capsule_includes_required_publish_fields_and_substance():
    skill = load_skill(SKILLSBENCH_SKILL)

    gene = build_gene(skill)
    capsule = build_capsule(skill, gene["asset_id"])

    assert capsule["type"] == "Capsule"
    assert capsule["schema_version"] == "1.5.0"
    assert isinstance(capsule["trigger"], list) and capsule["trigger"]
    assert capsule["gene"] == gene["asset_id"]
    assert isinstance(capsule["summary"], str) and len(capsule["summary"]) >= 20
    assert 0 <= capsule["confidence"] <= 1
    assert capsule["blast_radius"]["files"] >= 1
    assert capsule["blast_radius"]["lines"] >= 1
    assert capsule["outcome"]["status"] in {"success", "failure"}
    assert isinstance(capsule["success_streak"], int) and capsule["success_streak"] >= 0
    assert "platform" in capsule["env_fingerprint"]
    assert "arch" in capsule["env_fingerprint"]

    substance_fields = [
        capsule.get("content", ""),
        capsule.get("diff", ""),
        "".join(capsule.get("strategy", [])) if isinstance(capsule.get("strategy"), list) else capsule.get("strategy", ""),
        capsule.get("code_snippet", ""),
    ]
    assert any(isinstance(value, str) and len(value) >= 50 for value in substance_fields)

    capsule_no_id = {k: v for k, v in capsule.items() if k != "asset_id"}
    assert capsule["asset_id"] == compute_canonical_hash(capsule_no_id)


def test_operations_research_domain_uses_valid_gene_category():
    skill = {
        "name": "or-model-skill",
        "domain": "operations_research",
        "task_type": "or_model_identification",
        "when_to_use": "Use this skill to identify optimization model components from a natural language description.",
        "preconditions": ["An optimization problem description is available."],
        "procedure": [
            {"step": "Identify the decision variables from the problem statement."},
            {"step": "Map the objective and constraints before selecting an answer."},
        ],
    }

    gene = build_gene(skill)

    assert gene["category"] in {"repair", "optimize", "innovate"}


def test_sdk_helper_builds_gene_and_capsule_from_skill_yaml():
    result = subprocess.run(
        ["node", str(SDK_HELPER), str(SKILLSBENCH_SKILL)],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)

    assert "gene" in payload
    assert "capsule" in payload
    assert payload["gene"]["type"] == "Gene"
    assert payload["capsule"]["type"] == "Capsule"
    assert payload["capsule"]["gene"] == payload["gene"]["asset_id"]


def test_publish_skill_uses_sdk_bridge_assets(monkeypatch):
    fake_payload = {
        "gene": {"type": "Gene", "asset_id": "sha256:gene123"},
        "capsule": {
            "type": "Capsule",
            "asset_id": "sha256:capsule123",
            "gene": "sha256:gene123",
        },
    }
    captured = {}

    def fake_run(args, capture_output, text, check):
        captured["args"] = args
        return SimpleNamespace(stdout=json.dumps(fake_payload))

    def fake_publish_bundle(gene, capsule, sender_id):
        captured["gene"] = gene
        captured["capsule"] = capsule
        captured["sender_id"] = sender_id
        return {"ok": True}

    monkeypatch.setattr(evomap_publisher, "subprocess", SimpleNamespace(run=fake_run), raising=False)
    monkeypatch.setattr(evomap_publisher, "publish_bundle", fake_publish_bundle)

    response = evomap_publisher.publish_skill(str(SKILLSBENCH_SKILL))

    assert captured["args"][1].endswith("evomap_sdk_build.mjs")
    assert captured["gene"] == fake_payload["gene"]
    assert captured["capsule"] == fake_payload["capsule"]
    assert response == {"ok": True}


def test_register_node_persists_claim_metadata(tmp_path, monkeypatch):
    secrets_path = tmp_path / ".evomap_secrets.json"
    response = {
        "payload": {"node_secret": "a" * 64},
        "your_node_id": "node_demo_123",
        "claim_code": "REEF-4X7K",
        "claim_url": "https://evomap.ai/claim/REEF-4X7K",
    }

    monkeypatch.setattr(evomap_publisher, "_EVOMAP_SECRETS_FILE", secrets_path)
    monkeypatch.setattr(evomap_publisher, "_post", lambda endpoint, body: response)

    evomap_publisher.register_node("node_demo_123")

    saved = json.loads(secrets_path.read_text())
    assert saved["node_secret"] == "a" * 64
    assert saved["node_id"] == "node_demo_123"
    assert saved["claim_code"] == "REEF-4X7K"
    assert saved["claim_url"] == "https://evomap.ai/claim/REEF-4X7K"


def test_get_sender_id_prefers_saved_node_id(tmp_path, monkeypatch):
    secrets_path = tmp_path / ".evomap_secrets.json"
    secrets_path.write_text(json.dumps({
        "node_secret": "a" * 64,
        "node_id": "node_saved_456",
    }))

    monkeypatch.setattr(evomap_publisher, "_EVOMAP_SECRETS_FILE", secrets_path)

    assert evomap_publisher.get_sender_id() == "node_saved_456"
