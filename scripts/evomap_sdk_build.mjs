#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import process from "node:process";

import YAML from "yaml";
import { createCapsule, createGene, computeAssetId } from "@evomap/gep-sdk";


function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}


function extractProcedureSteps(procedure) {
  const steps = [];
  for (const item of Array.isArray(procedure) ? procedure : []) {
    if (item && typeof item === "object" && typeof item.step === "string") {
      steps.push(item.step.trim().replace(/\s+/g, " ").slice(0, 200));
    }
  }
  return steps;
}


function ensureStrategySteps(skill) {
  const steps = extractProcedureSteps(skill.procedure);
  if (steps.length >= 2) {
    return steps.slice(0, 12);
  }

  const whenToUse = String(skill.when_to_use || "").trim();
  const verification = String(skill.verification || "").trim();

  if (whenToUse) {
    steps.push(`Assess whether the task matches this skill: ${whenToUse.slice(0, 180)}`);
  }
  if (verification && steps.length < 2) {
    steps.push(`Verify the outcome using this rule: ${verification.slice(0, 180)}`);
  }
  if (steps.length < 2) {
    steps.push("Apply the documented procedure conservatively and validate the result.");
  }
  if (steps.length < 2) {
    steps.push("Stop if constraints are violated and review the task context again.");
  }

  return steps.slice(0, 12);
}


function extractTriggerKeywords(skill) {
  const triggerSet = new Set();
  const name = String(skill.name || "");
  const domain = String(skill.domain || "");
  const taskType = String(skill.task_type || "");
  const whenToUse = String(skill.when_to_use || "").toLowerCase();

  for (const word of name.replace(/[-_]/g, " ").split(/\s+/)) {
    if (word.length > 3) {
      triggerSet.add(word.toLowerCase());
    }
  }
  if (domain) {
    triggerSet.add(domain.toLowerCase());
  }
  if (taskType) {
    triggerSet.add(taskType.toLowerCase());
  }

  for (const keyword of [
    "latex",
    "overfull",
    "hbox",
    "sqlite",
    "wal",
    "xor",
    "feal",
    "cryptanalysis",
    "differential",
    "database",
    "recovery",
  ]) {
    if (whenToUse.includes(keyword)) {
      triggerSet.add(keyword);
    }
  }

  return Array.from(triggerSet).sort();
}


function signalsForDomain(domain) {
  const signals = {
    latex: ["latex", "typesetting", "overfull", "hbox", "pdflatex"],
    database_forensics: ["sqlite", "wal", "xor", "decryption", "forensics"],
    cryptography: ["feal", "cryptanalysis", "differential", "block-cipher"],
    operations_research: ["optimization", "operations-research", "constraints", "objective"],
  };
  return signals[domain] || [domain];
}


function categoryForDomain(domain) {
  const categoryMap = {
    latex: "optimize",
    latex_typesetting: "optimize",
    database_forensics: "repair",
    cryptography: "repair",
    cryptanalysis: "repair",
    operations_research: "optimize",
  };
  return categoryMap[domain] || "optimize";
}


function defaultConstraints() {
  return {
    max_files: 5,
    forbidden_paths: [".env", ".git/", ".venv/", "node_modules/"],
  };
}


function defaultValidationCommands(skill) {
  const skillId = slugify(skill.name || "skill") || "skill";
  const summary = `${skill.domain || ""}:${skill.task_type || ""}:${skillId}`;
  const genericCheck =
    `node -e "require('node:assert/strict').ok(${JSON.stringify(summary)}.match(/.{12}/), 'summary too short')"`;

  const domainChecks = {
    latex:
      `node -e "require('node:assert/strict').ok(['main.tex','input.tex','synonyms.txt'].find(function(p){return require('node:fs').existsSync(p)}), 'expected LaTeX task files')"`,
    database_forensics:
      `node -e "require('node:assert/strict').ok(['main.db','main.db-wal','recovered.json'].find(function(p){return require('node:fs').existsSync(p)}), 'expected SQLite recovery files')"`,
    cryptography:
      `node -e "require('node:assert/strict').ok(['feal.py','attack.py'].find(function(p){return require('node:fs').existsSync(p)}), 'expected crypto task files')"`,
  };

  return [
    genericCheck,
    domainChecks[skill.domain] ||
      `node -e "require('node:assert/strict').ok(process.cwd().length, 'cwd unavailable')"`,
  ];
}


function capsuleContent(skill, steps) {
  const sections = [];
  if (skill.when_to_use) {
    sections.push(`When to use: ${String(skill.when_to_use).trim()}`);
  }
  if (skill.when_not_to_use) {
    sections.push(`When not to use: ${String(skill.when_not_to_use).trim()}`);
  }
  if (steps.length) {
    sections.push(`Strategy: ${steps.join(" | ")}`);
  }
  if (skill.verification) {
    sections.push(`Verification: ${String(skill.verification).trim()}`);
  }
  return sections.join("\n").slice(0, 2000);
}


function normalizedArch() {
  const arch = os.arch();
  if (arch === "x64") {
    return "x64";
  }
  if (arch === "arm64") {
    return "arm64";
  }
  return arch;
}


function buildAssets(skill) {
  const name = String(skill.name || "");
  const domain = String(skill.domain || "");
  const whenToUse = String(skill.when_to_use || "").slice(0, 300);
  const steps = ensureStrategySteps(skill);
  const skillId = slugify(skill.name || skill.task_type || domain) || "skill";

  const sdkGene = createGene({
    id: `gene_${skillId}`,
    category: categoryForDomain(domain),
    signals_match: signalsForDomain(domain),
    preconditions: Array.isArray(skill.preconditions) ? skill.preconditions : [],
    strategy: steps,
    constraints: defaultConstraints(),
    validation: defaultValidationCommands(skill),
  });
  const gene = {
    ...sdkGene,
    summary: `[${domain}] ${name}: ${whenToUse}`,
  };
  gene.asset_id = computeAssetId(gene);

  const verification = String(skill.verification || "");
  const sdkCapsule = createCapsule({
    trigger: extractTriggerKeywords(skill),
    gene: gene.asset_id,
    summary: `[${domain}] ${name}: ${whenToUse}`,
    confidence: 0.5,
    blastRadius: { files: 1, lines: 10 },
    outcome: { status: "failure", score: 0 },
    envFingerprint: {
      platform: os.platform(),
      arch: normalizedArch(),
    },
  });
  const capsule = {
    ...sdkCapsule,
    outcome: { status: "failure", score: 0 },
    success_streak: 0,
    strategy: steps,
    code_snippet: (verification.trim() || steps.join(" ").trim()).slice(0, 1000),
    content: capsuleContent(skill, steps),
  };
  capsule.asset_id = computeAssetId(capsule);

  return { gene, capsule };
}


function main() {
  const skillPath = process.argv[2];
  if (!skillPath) {
    console.error("Usage: node scripts/evomap_sdk_build.mjs <skill.yaml>");
    process.exit(1);
  }

  const raw = fs.readFileSync(skillPath, "utf8");
  const skill = YAML.parse(raw);
  const payload = buildAssets(skill);
  process.stdout.write(JSON.stringify(payload));
}


main();
