"""JSON Schema helpers: ToolSpec params -> MCP inputSchema.

MCP tools carry ``inputSchema`` (JSON Schema draft-07 subset) so foreign
agents validate args client-side. We generate it from the lightweight
``{name: type}`` maps used by ToolRegistry plus optional metadata
(required, defaults, enums, descriptions).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

__all__ = ["pytype_to_schema", "build_input_schema"]

_PY = {
    "str": {"type": "string"},
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "bool": {"type": "boolean"},
    "any": {},
    "list": {"type": "array"},
    "dict": {"type": "object"},
}


def pytype_to_schema(t: str) -> Dict[str, Any]:
    return dict(_PY.get(t, {}))


def build_input_schema(params: Dict[str, str],
                       required: List[str] | None = None,
                       descriptions: Dict[str, str] | None = None,
                       defaults: Dict[str, Any] | None = None,
                       enums: Dict[str, List[Any]] | None = None) -> Dict[str, Any]:
    required = required if required is not None else sorted(params)
    descriptions, defaults, enums = descriptions or {}, defaults or {}, enums or {}
    props: Dict[str, Any] = {}
    for name, t in params.items():
        sch: Dict[str, Any] = pytype_to_schema(t)
        if name in descriptions:
            sch["description"] = descriptions[name]
        if name in defaults:
            sch["default"] = defaults[name]
        if name in enums:
            sch["enum"] = enums[name]
        props[name] = sch
    return {"type": "object", "properties": props, "required": required,
            "additionalProperties": True}
