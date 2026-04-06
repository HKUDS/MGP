from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "openapi" / "mgp-openapi.yaml"


class OpenAPIValidationError(Exception):
    pass


def _load_openapi() -> dict[str, Any]:
    document = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise OpenAPIValidationError("OpenAPI root must be an object.")
    return document


def _resolve_pointer(document: dict[str, Any], ref: str) -> Any:
    current: Any = document
    for part in ref.removeprefix("#/").split("/"):
        if not isinstance(current, dict) or part not in current:
            raise OpenAPIValidationError(f"Unresolvable internal reference: {ref}")
        current = current[part]
    return current


def _resolve_external_ref(base_path: Path, ref: str) -> Any:
    relative_path, _, fragment = ref.partition("#")
    target_path = (base_path.parent / relative_path).resolve()
    if not target_path.exists():
        raise OpenAPIValidationError(f"Referenced file does not exist: {ref}")

    if target_path.suffix in {".yaml", ".yml"}:
        contents: Any = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    else:
        contents = json.loads(target_path.read_text(encoding="utf-8"))

    if not fragment:
        return contents

    current: Any = contents
    for part in fragment.removeprefix("/").split("/"):
        if not isinstance(current, dict) or part not in current:
            raise OpenAPIValidationError(f"Unresolvable fragment reference: {ref}")
        current = current[part]
    return current


def _walk_refs(node: Any, base_path: Path, document: dict[str, Any], refs: list[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
            if ref.startswith("#/"):
                _resolve_pointer(document, ref)
            else:
                _resolve_external_ref(base_path, ref)
        for value in node.values():
            _walk_refs(value, base_path, document, refs)
    elif isinstance(node, list):
        for value in node:
            _walk_refs(value, base_path, document, refs)


def _validate_path_item(path_name: str, path_item: Any) -> None:
    if not isinstance(path_item, dict):
        raise OpenAPIValidationError(f"Path item must be an object: {path_name}")

    operations = {method: payload for method, payload in path_item.items() if method in {"get", "post"}}
    if not operations:
        raise OpenAPIValidationError(f"Path item has no supported operations: {path_name}")

    for method, operation in operations.items():
        if not isinstance(operation, dict):
            raise OpenAPIValidationError(f"Operation must be an object: {method.upper()} {path_name}")
        if "operationId" not in operation:
            raise OpenAPIValidationError(f"Missing operationId for {method.upper()} {path_name}")
        if method == "post" and "requestBody" not in operation:
            raise OpenAPIValidationError(f"Missing requestBody for {method.upper()} {path_name}")
        if "responses" not in operation or "200" not in operation["responses"]:
            raise OpenAPIValidationError(f"Missing 200 response for {method.upper()} {path_name}")


def main() -> int:
    openapi = _load_openapi()

    if openapi.get("openapi") != "3.1.0":
        raise OpenAPIValidationError("MGP OpenAPI document must declare openapi: 3.1.0")

    for required_key in ("info", "paths", "components"):
        if required_key not in openapi:
            raise OpenAPIValidationError(f"Missing required OpenAPI top-level key: {required_key}")

    if "version" not in openapi["info"]:
        raise OpenAPIValidationError("OpenAPI info.version is required.")

    operation_ids: set[str] = set()
    for path_name, path_item in openapi["paths"].items():
        _validate_path_item(path_name, path_item)
        for method in ("get", "post"):
            operation = path_item.get(method)
            if not operation:
                continue
            operation_id = operation["operationId"]
            if operation_id in operation_ids:
                raise OpenAPIValidationError(f"Duplicate operationId found: {operation_id}")
            operation_ids.add(operation_id)

    refs: list[str] = []
    _walk_refs(openapi, OPENAPI_PATH, openapi, refs)
    if not refs:
        raise OpenAPIValidationError("Expected at least one $ref in the OpenAPI document.")

    print(f"validated {OPENAPI_PATH.relative_to(ROOT)}")
    print(f"resolved {len(refs)} references")
    print(f"validated {len(operation_ids)} operations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
