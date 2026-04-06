from __future__ import annotations

import json
from pathlib import Path

from jsonschema.validators import validator_for


def main() -> int:
    schema_dir = Path(__file__).resolve().parents[1] / "schemas"
    schema_paths = sorted(schema_dir.glob("*.schema.json"))
    if not schema_paths:
        raise SystemExit("No schema files found.")

    for path in schema_paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        print(f"validated {path.relative_to(schema_dir.parent)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
