#!/usr/bin/env node
// schema-contract.mjs — BLOCKING gate (drift-risk-map Finding C7).
//
// The viewer hand-mirrors the document model: it dispatches on object `type`,
// flow `type`, and inline `kind` with hardcoded branches. Nothing asserted that
// the SET of types the viewer knows equals the SET the model defines, so a new
// model type shipped a viewer that silently dropped or mis-rendered it — a
// classic silent drift.
//
// This reconciles the viewer's declared surface (viewer/dev/type-registry.json)
// against the model's discriminators, read from schema/framegraph-v2.schema.json
// (itself byte-gated to models/framegraph.py by `schema-check`). Every model
// discriminator must be either rendered (supported) or explicitly listed
// (unsupported, with a reason); every claimed type must be real or a declared
// out-of-profile extension. Drift becomes a loud, non-zero exit.
//
// Dependency-free (node built-ins only) so CI runs it without `npm ci`.
//
// Usage:
//   node viewer/dev/schema-contract.mjs              # gate the current tree
//   node viewer/dev/schema-contract.mjs --self-test  # prove the gate catches drift
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");
const SCHEMA_PATH = path.join(ROOT, "docs/schema/framegraph-v2.schema.json");
const REGISTRY_PATH = path.join(__dirname, "type-registry.json");

const DIMENSIONS = ["object_types", "flow_types", "inline_kinds"];

// Derive the model's three discriminator sets from the JSON Schema, the same way
// the models define them: locate each union (a property whose members are a
// oneOf/anyOf of >=4 $refs) and collect the literal `type`/`kind` of its members.
// Located by content (must contain known anchor values), not by container-field
// name, so a field rename in the model does not silently break the gate.
export function schemaDiscriminators(schema) {
  const defs = schema.$defs || {};
  const memberRefs = (node) => {
    for (const key of ["oneOf", "anyOf"]) {
      if (node && Array.isArray(node[key])) {
        return node[key].filter((m) => m && m.$ref).map((m) => m.$ref.split("/").pop());
      }
    }
    return [];
  };
  const constsOf = (refs, field) => {
    const out = new Set();
    for (const ref of refs) {
      const prop = ((defs[ref] || {}).properties || {})[field];
      if (prop && Object.prototype.hasOwnProperty.call(prop, "const")) out.add(prop.const);
    }
    return out;
  };
  const unions = [];
  for (const def of Object.values(defs)) {
    for (const pd of Object.values(def.properties || {})) {
      const refs = memberRefs(pd.items || pd);
      if (refs.length >= 4) unions.push(refs);
    }
  }
  const pick = (field, ...anchors) => {
    for (const refs of unions) {
      const consts = constsOf(refs, field);
      if (anchors.every((a) => consts.has(a))) return consts;
    }
    return null;
  };
  return {
    object_types: pick("type", "rect", "text"),
    flow_types: pick("type", "paragraph", "heading"),
    inline_kinds: pick("kind", "link", "ref"),
  };
}

// Compare the model sets against the registry. Returns a list of human-readable
// violations (empty = in sync). Five distinct drift modes, one message each.
export function contractViolations(schemaSets, registry) {
  const v = [];
  for (const dim of DIMENSIONS) {
    const schemaSet = schemaSets[dim];
    if (!schemaSet) {
      v.push(`${dim}: could not locate this union in the schema — the model was restructured; revisit schema-contract.mjs.`);
      continue;
    }
    const supported = new Set((registry.supported || {})[dim] || []);
    const unsupported = new Set(Object.keys((registry.unsupported || {})[dim] || {}));
    const extensions = new Set((registry.extensions || {})[dim] || []);
    for (const t of schemaSet) {
      if (!supported.has(t) && !unsupported.has(t)) {
        v.push(`${dim}: model defines "${t}" but the viewer neither renders it (supported) nor declares it (unsupported). Add it to one in type-registry.json.`);
      }
    }
    for (const t of supported) {
      if (!schemaSet.has(t) && !extensions.has(t)) {
        v.push(`${dim}: viewer claims "${t}" but the model has no such type and it is not a declared extension. Remove it or add it to extensions.`);
      }
      if (unsupported.has(t)) v.push(`${dim}: "${t}" is in both supported and unsupported.`);
    }
    for (const t of unsupported) {
      if (!schemaSet.has(t)) v.push(`${dim}: unsupported "${t}" is no longer in the model — drop the stale allowlist entry.`);
    }
    for (const t of extensions) {
      if (!supported.has(t)) v.push(`${dim}: declared extension "${t}" is not in supported.`);
    }
  }
  return v;
}

const loadJSON = (p) => JSON.parse(fs.readFileSync(p, "utf8"));

function runSelfTest(schemaSets, registry) {
  // Injected model drift in every dimension must be caught.
  const poisoned = {
    object_types: new Set([...schemaSets.object_types, "__ghost_obj__"]),
    flow_types: new Set([...schemaSets.flow_types, "__ghost_flow__"]),
    inline_kinds: new Set([...schemaSets.inline_kinds, "__ghost_inline__"]),
  };
  const caught = contractViolations(poisoned, registry);
  const ghosts = ["__ghost_obj__", "__ghost_flow__", "__ghost_inline__"];
  const missed = ghosts.filter((g) => !caught.some((m) => m.includes(g)));
  // A stale allowlist entry must be caught.
  const stale = JSON.parse(JSON.stringify(registry));
  stale.unsupported = stale.unsupported || {};
  stale.unsupported.inline_kinds = { ...(stale.unsupported.inline_kinds || {}), __stale_kind__: "x" };
  const staleCaught = contractViolations(schemaSets, stale).some((m) => m.includes("__stale_kind__"));
  if (missed.length || !staleCaught) {
    console.error(`SELF-TEST FAILED: uncaught injected types=[${missed.join(", ") || "none"}], staleCaught=${staleCaught}`);
    return 1;
  }
  console.log("schema-contract self-test OK: injected model drift (3 dims) and a stale allowlist entry were all caught.");
  return 0;
}

function main() {
  const schema = loadJSON(SCHEMA_PATH);
  const registry = loadJSON(REGISTRY_PATH);
  const schemaSets = schemaDiscriminators(schema);

  if (process.argv.includes("--self-test")) {
    process.exit(runSelfTest(schemaSets, registry));
  }

  const violations = contractViolations(schemaSets, registry);
  if (violations.length) {
    console.error("viewer ⇄ model contract drift (drift-risk-map C7):\n  " + violations.join("\n  "));
    console.error("\nReconcile viewer/dev/type-registry.json with the model, then re-run.");
    process.exit(1);
  }
  const size = (s) => (s ? s.size : 0);
  console.log(
    `viewer ⇄ model contract OK — ${size(schemaSets.object_types)} object, ` +
    `${size(schemaSets.flow_types)} flow, ${size(schemaSets.inline_kinds)} inline ` +
    `model discriminators all reconciled (rendered or explicitly unsupported).`
  );
}

const invokedDirectly = path.resolve(process.argv[1] || "") === path.resolve(fileURLToPath(import.meta.url));
if (invokedDirectly) main();
