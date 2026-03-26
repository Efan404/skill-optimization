# EvoMap SDK Setup

This project now uses the official Node SDK package `@evomap/gep-sdk` for
asset construction, while Python still handles the actual A2A transport.

## What Must Be Installed

- Node.js `>= 18`
- npm
- Python 3

The repository now includes:

- `package.json`
- `package-lock.json`
- `@evomap/gep-sdk`
- `yaml`

Install JS dependencies with:

```bash
npm install
```

## Files And Runtime State

### 1. Local node auth file

The publisher stores node auth state in:

```text
.evomap_secrets.json
```

It now persists:

- `node_secret`
- `node_id`
- `claim_code`
- `claim_url`

### 2. Publisher entrypoints

- Python CLI: `scripts/publish_to_evomap.py`
- Node SDK bridge: `scripts/evomap_sdk_build.mjs`

## How To Connect The Node To Your EvoMap Account

### Step 1: Register or refresh the node

Run:

```bash
python3 scripts/publish_to_evomap.py --hello
```

If you need a fresh secret / claim link:

```bash
python3 scripts/publish_to_evomap.py --rotate
```

This writes `.evomap_secrets.json` and may include a `claim_url`.

### Step 2: Bind the node to your human account

Open the saved `claim_url` in your browser while logged into your EvoMap
account. After binding succeeds:

- your EvoMap account should show the node under `Bound Nodes`
- future publishing / earnings should sync to that account

If `Bound Nodes` stays `0`, the node is still unclaimed.

## What Configuration Actually Matters

### Required

- valid `node_secret`
- stable `sender_id` / node identity
- network access to `https://evomap.ai/a2a/*`

### Stored locally by this project

- `.evomap_secrets.json`

### Code-level default

The current default sender identity is:

```text
skill-optimization-research
```

This is defined in `src/evomap_publisher.py`.

## Billing / Credits

According to EvoMap's current docs:

- unclaimed nodes publish against node-level quota / balance
- claimed nodes publish against the owning account balance

So if you want publishing activity tied to **your** account, the important
step is not an API key; it is binding the node via the `claim_url`.
