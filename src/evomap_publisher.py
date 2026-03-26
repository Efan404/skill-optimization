"""EvoMap GEP-A2A Publisher — publish Gene+Capsule bundles to evomap.ai."""

import hashlib
import json
import os
import random
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# EvoMap GEP-A2A protocol constants
EVO_BASE_URL = "https://evomap.ai"
PROTOCOL = "gep-a2a"
PROTOCOL_VERSION = "1.0.0"
CAPSULE_SCHEMA_VERSION = "1.5.0"

# Node identity — must match the registered node_id
DEFAULT_SENDER_ID = "skill-optimization-research"
_EVOMAP_SECRETS_FILE = Path(__file__).resolve().parent.parent / ".evomap_secrets.json"


def _load_node_secret() -> str | None:
    """Load saved node_secret from local secrets file."""
    if _EVOMAP_SECRETS_FILE.exists():
        try:
            data = json.loads(_EVOMAP_SECRETS_FILE.read_text())
            return data.get("node_secret")
        except Exception:
            return None
    return None


def save_node_secret(node_secret: str) -> None:
    """Save node_secret to local secrets file (gitignored)."""
    data = {"node_secret": node_secret}
    _EVOMAP_SECRETS_FILE.write_text(json.dumps(data, indent=2))
    print(f"[evomap] node_secret saved to {_EVOMAP_SECRETS_FILE}")


# Domain → EvoMap Gene category mapping
CATEGORY_MAP = {
    "latex": "typesetting",
    "database_forensics": "repair",
    "cryptography": "repair",
    "operations_research": "optimization",
    "latex_typesetting": "typesetting",
    "database_forensics": "repair",
    "cryptanalysis": "repair",
}


def _canonical_json(obj: dict) -> str:
    """Return canonical JSON string: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def compute_canonical_hash(obj: dict) -> str:
    """Compute sha256:<hex> asset_id from a dict using canonical JSON."""
    canonical = _canonical_json(obj)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _build_envelope(message_type: str, sender_id: str, payload: dict) -> dict:
    """Build a GEP-A2A protocol envelope."""
    return {
        "protocol": PROTOCOL,
        "protocol_version": PROTOCOL_VERSION,
        "message_type": message_type,
        "message_id": f"msg_{int(time.time())}_{random.randrange(0x100000000):08x}",
        "sender_id": sender_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": payload,
    }


def _post(endpoint: str, body: dict) -> dict:
    """POST JSON to evomap.ai/a2a/{endpoint} and return parsed response."""
    url = f"{EVO_BASE_URL}/a2a/{endpoint}"
    body_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    # Include Bearer token if we have a saved node_secret
    secret = _load_node_secret()
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def register_node(sender_id: str = DEFAULT_SENDER_ID) -> dict:
    """Register this node with the EvoMap hub via gep.hello.

    On success, saves the returned node_secret to .evomap_secrets.json
    so subsequent publish calls can authenticate.
    """
    payload = {
        "capabilities": {
            "supported_types": ["Gene", "Capsule"],
            "protocol_version": PROTOCOL_VERSION,
        },
        "model": "skill-optimization-research-node",
    }
    envelope = _build_envelope("hello", sender_id, payload)
    resp = _post("hello", envelope)
    # node_secret lives at payload.node_secret (top-level) in hello response
    if isinstance(resp, dict):
        node_secret = (
            resp.get("payload", {}).get("node_secret")
            or resp.get("node_secret")
        )
    else:
        node_secret = None
    if node_secret:
        save_node_secret(node_secret)
    return resp


def _extract_procedure_steps(procedure: list) -> list[str]:
    """Extract plain-text step descriptions from skill procedure list."""
    steps = []
    for item in procedure:
        if isinstance(item, dict) and "step" in item:
            # Take first 200 chars of step text, strip whitespace
            text = item["step"].strip().replace("\n", " ")[:200]
            steps.append(text)
    return steps


def _extract_trigger_keywords(skill: dict) -> list[str]:
    """Derive trigger keywords from skill name, domain, and task_type."""
    name = skill.get("name", "")
    domain = skill.get("domain", "")
    task_type = skill.get("task_type", "")
    when_to_use = skill.get("when_to_use", "")

    # Extract key terms from when_to_use (first 200 chars is enough)
    trigger_set = set()
    # Name words
    for word in name.replace("-", " ").replace("_", " ").split():
        if len(word) > 3:
            trigger_set.add(word.lower())
    # Domain and task_type
    trigger_set.add(domain.lower())
    trigger_set.add(task_type.lower())
    # Notable keywords from when_to_use
    important = ["latex", "overfull", "hbox", "sqlite", "wal", "xor", "feal",
                 "cryptanalysis", "differential", "database", "recovery"]
    for kw in important:
        if kw in when_to_use.lower():
            trigger_set.add(kw)

    return sorted(trigger_set)


def build_gene(skill: dict, sender_id: str = DEFAULT_SENDER_ID) -> dict:
    """Build a Gene object from a skill dict.

    The Gene is the atomic capability unit — a one-liner summary plus category.
    asset_id is computed AFTER building but BEFORE inclusion in the envelope.
    """
    name = skill.get("name", "")
    domain = skill.get("domain", "")
    when_to_use = skill.get("when_to_use", "")[:200]

    category = CATEGORY_MAP.get(domain, "optimization")

    gene = {
        "type": "Gene",
        "summary": f"[{domain}] {name}: {when_to_use}",
        "category": category,
    }
    gene["asset_id"] = compute_canonical_hash(gene)
    return gene


def build_capsule(
    skill: dict,
    gene_asset_id: str,
    evidence: dict | None = None,
) -> dict:
    """Build a Capsule object (v1.5.0 schema) from a skill dict.

    The Capsule is the Gene + validation evidence bundle.
    evidence is an optional dict with keys like:
        benchmark, evidence_level, dev_set, test_set, key_optimization, etc.
        If None, defaults to "conceptual" level.
    """
    name = skill.get("name", "")
    domain = skill.get("domain", "")
    task_type = skill.get("task_type", "")
    description_block = skill.get("# Description", "") or skill.get("description", "")
    when_to_use = skill.get("when_to_use", "")
    when_not_to_use = skill.get("when_not_to_use", "")
    procedure = skill.get("procedure", [])
    common_failures = skill.get("common_failures", [])
    verification = skill.get("verification", "")

    steps = _extract_procedure_steps(procedure)
    failure_list = []
    for f in common_failures:
        if isinstance(f, dict) and "failure" in f:
            failure_list.append(f["failure"].strip()[:200])
        elif isinstance(f, str):
            failure_list.append(f.strip()[:200])

    capsule = {
        "type": "Capsule",
        "schema_version": CAPSULE_SCHEMA_VERSION,
        "asset_id": "",  # set after canonical hash
        "name": name,
        "domain": domain,
        "task_type": task_type,
        "triggers": _extract_trigger_keywords(skill),
        "description": description_block.strip()[:500] if description_block else "",
        "when_to_use": when_to_use.strip()[:300],
        "when_not_to_use": when_not_to_use.strip()[:300],
        "strategy": steps,
        "failure_modes": failure_list,
        "verification": verification.strip()[:300] if verification else "",
        "evidence": evidence or {
            "evidence_level": "conceptual",
            "benchmark": "SkillsBench (pending)",
            "note": "Skill defined but not yet evaluated on SkillsBench",
        },
    }
    capsule["asset_id"] = compute_canonical_hash(capsule)
    return capsule


def publish_bundle(
    gene: dict,
    capsule: dict,
    sender_id: str = DEFAULT_SENDER_ID,
) -> dict:
    """Publish a Gene+Capsule bundle to EvoMap via /a2a/publish."""
    payload = {
        "assets": [gene, capsule],
    }
    envelope = _build_envelope("publish", sender_id, payload)
    return _post("publish", envelope)


def publish_skill(
    skill_path: str,
    sender_id: str = DEFAULT_SENDER_ID,
    evidence: dict | None = None,
) -> dict:
    """Full pipeline: load skill YAML, build Gene+Capsule, publish to EvoMap.

    Args:
        skill_path: Path to the skill YAML file.
        sender_id: GEP-A2A sender node ID.
        evidence: Optional evidence dict to embed in the Capsule.
                  If None, uses conceptual-level placeholder.

    Returns:
        The parsed JSON response from EvoMap /a2a/publish.
    """
    import yaml

    with open(skill_path, "r") as f:
        skill = yaml.safe_load(f)

    gene = build_gene(skill, sender_id)
    capsule = build_capsule(skill, gene["asset_id"], evidence)

    print(f"[evomap_publisher] Gene asset_id : {gene['asset_id']}")
    print(f"[evomap_publisher] Capsule asset_id: {capsule['asset_id']}")

    response = publish_bundle(gene, capsule, sender_id)
    return response


def hello() -> dict:
    """Register this project node with EvoMap hub."""
    return register_node(DEFAULT_SENDER_ID)
