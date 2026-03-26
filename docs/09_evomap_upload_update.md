# EvoMap Upload Update

This note summarizes the current state of the EvoMap publishing work on
`main` as of 2026-03-27.

## Current Status

- Real `POST /a2a/publish` has succeeded for one SkillsBench skill bundle.
- The bundle was accepted by the hub and returned a decision payload instead
  of a schema error.
- The current decision is `quarantine`, not `promoted`.
- The publisher now uses the official Node SDK `@evomap/gep-sdk` for asset
  construction, while Python still handles `hello`, `publish`, local secret
  storage, and CLI orchestration.

In practice, this means the upload pipeline is working end-to-end, but the
asset is not yet a fully promoted public marketplace asset.

## Published Bundle

- Bundle ID: `bundle_97243e945bd23b25`
- Gene asset ID:
  `sha256:2149e05f60e118bad0f22881d9d2196e70212fe6831d0c125945fb1c1908cc12`
- Capsule asset ID:
  `sha256:c120a9745b6739f3bd4d1caf35010ad1fe68c383d177dfa772f6176c64b6dd94`
- Hub decision: `quarantine`
- Hub reason: `safety_candidate`

These asset pages are reachable and can be shared:

- Gene:
  `https://evomap.ai/asset/sha256%3A2149e05f60e118bad0f22881d9d2196e70212fe6831d0c125945fb1c1908cc12`
- Capsule:
  `https://evomap.ai/asset/sha256%3Ac120a9745b6739f3bd4d1caf35010ad1fe68c383d177dfa772f6176c64b6dd94`

Because the current state is `quarantine`, these URLs should be treated as
"shareable inspection links" rather than proof of final marketplace
promotion.

## What Changed In The Repo

- Official SDK bridge:
  [scripts/evomap_sdk_build.mjs](/Users/efan404/Codes/research/skill-optimization/scripts/evomap_sdk_build.mjs)
- Python publisher transport:
  [src/evomap_publisher.py](/Users/efan404/Codes/research/skill-optimization/src/evomap_publisher.py)
- CLI entrypoint:
  [scripts/publish_to_evomap.py](/Users/efan404/Codes/research/skill-optimization/scripts/publish_to_evomap.py)
- Setup and account binding guide:
  [docs/evomap_sdk_setup.md](/Users/efan404/Codes/research/skill-optimization/docs/evomap_sdk_setup.md)

The current publisher behavior is:

1. Build `Gene` and `Capsule` through the official Node SDK bridge.
2. Fall back to the local Python builder if the SDK bridge fails.
3. Register a node with `hello` and persist local auth state in
   `.evomap_secrets.json`.
4. Publish a bundle to `https://evomap.ai/a2a/publish`.

## Account Binding Status

The local publisher can authenticate with a node secret, but account binding
is still a separate step.

Current local check:

- `.evomap_secrets.json` contains `node_secret`
- `.evomap_secrets.json` does not currently contain `node_id`
- `.evomap_secrets.json` does not currently contain `claim_url`
- The referenced EvoMap account snapshot shows `Bound Nodes = 0`

So the pipeline can publish, but the node is not yet clearly bound to the
human EvoMap account.

To bind the node to a user account:

```bash
python3 scripts/publish_to_evomap.py --rotate
```

Then open the generated `claim_url` while logged into EvoMap. After a
successful claim, the EvoMap account should show at least one bound node.

## Existing Reuse Options: SDK, MCP, Skill

The current integration options are:

- SDK: `@evomap/gep-sdk` on npm
- MCP server: `@evomap/gep-mcp-server` on npm
- Official Evolver client / workflow reference in EvoMap docs
- Public Skill Store and skills.sh ecosystem for reusable skills

What we verified:

- `@evomap/gep-sdk`
  - npm version: `1.0.1`
  - repo: `https://github.com/EvoMap/gep-sdk-js`
- `@evomap/gep-mcp-server`
  - npm version: `1.0.2`
  - repo: `https://github.com/EvoMap/gep-mcp-server`
  - description: MCP server exposing GEP capabilities to MCP-compatible
    agents
- Public skill search via `npx skills find evomap` returns at least:
  - `evomap/evolver@capability-evolver`
  - `nowloady/evomapscriptshub001@evomap`
  - `aaaaqwq/claude-code-skills@evomap`
  - `keoy7am/skill-evomap@evomap`

At the time of writing, this repository does not include a local
pre-installed EvoMap-specific skill under the current Codex skill
directories.

## Recommended Next Step

The next high-value step is to add an `EvolutionEvent` to the published
bundle. That does not guarantee promotion, but it makes the bundle more
complete, improves auditability, and matches EvoMap's documented preference
for a three-asset bundle.
