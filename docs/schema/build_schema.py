#!/usr/bin/env python3
"""
build_schema.py — generate frameforge-v2.schema.json FROM the Pydantic models.

This closes complement recommendation #3: the schema is no longer hand-authored
and lagging — it is emitted from `models/frameforge.py` (the single source of
truth), so the schema and the models cannot drift. Run this whenever the models
change; CI should fail if the committed schema differs from a fresh build.

Usage:
    python3 build_schema.py                 # write ../schema/frameforge-v2.schema.json
    python3 build_schema.py --check         # exit non-zero if the file is stale
    python3 build_schema.py path/to/doc.yml # also validate a document against the models
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.normpath(os.path.join(HERE, "..", "models"))
SCHEMA_PATH = os.path.normpath(os.path.join(HERE, "..", "schema", "frameforge-v2.schema.json"))
sys.path.insert(0, MODELS_DIR)

import frameforge as fg  # noqa: E402


def build() -> dict:
    schema = fg.Document.model_json_schema(ref_template="#/$defs/{model}")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    # Version-pinned, resolvable `$id`: a document self-declares conformance against
    # an exact schema version (e.g. `"$schema": ".../2.2.0/frameforge-v2.schema.json"`),
    # rather than an unversioned major line. The `version` mirrors HEAD_VERSION so the
    # two never drift. (Item 4: a resolvable, versioned schema URL.)
    schema["$id"] = f"https://frameforge.dev/schema/{fg.HEAD_VERSION}/frameforge-v2.schema.json"
    schema["version"] = fg.HEAD_VERSION
    schema["title"] = (
        f"FrameForge v2 (HEAD {fg.HEAD_VERSION}) — generated from the Pydantic models "
        f"(core conformance profile)"
    )
    return schema


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("document", nargs="?", help="optional document to validate against the models")
    ap.add_argument("--check", action="store_true", help="fail if the on-disk schema is stale")
    args = ap.parse_args(argv)

    schema = build()
    text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        on_disk = open(SCHEMA_PATH, encoding="utf-8").read() if os.path.exists(SCHEMA_PATH) else ""
        if on_disk != text:
            print("STALE: schema/frameforge-v2.schema.json differs from a fresh build. Run build_schema.py.")
            return 1
        print("OK: schema is in sync with the models.")
        return 0

    os.makedirs(os.path.dirname(SCHEMA_PATH), exist_ok=True)
    with open(SCHEMA_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Wrote {SCHEMA_PATH}  ({len(schema.get('$defs', {}))} $defs)")

    if args.document:
        import yaml
        doc = yaml.safe_load(open(args.document, encoding="utf-8"))
        try:
            fg.Document.model_validate(doc)
            print(f"VALID against the models: {args.document}")
        except Exception as exc:  # noqa: BLE001
            print(f"INVALID: {args.document}\n{exc}")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
