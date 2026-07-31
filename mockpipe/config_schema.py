"""Structural (shape/type) validation for the raw config dict, using pydantic.

This is deliberately additive, not a replacement for the existing validation in
config.py/field.py/action.py: it catches basic structural mistakes (missing
keys, wrong types, non-list tables/fields/actions) with clear, unified error
messages before that deeper, semantics-aware validation runs (imposter/effect/
where-clause DSL parsing, cross-table/field references, action-type-specific
required keys). Extra/unrecognised keys are allowed here on purpose - that is
still enforced downstream by validate_keys(), so this layer never rejects a
config the rest of mockpipe would otherwise accept.

Split in two, matching Config's own two-stage validation:
- ConfigSettingsSchema: the top-level settings, checked in Config.__init__.
  `tables` is intentionally not part of this - a Config can be constructed
  without one yet (only load_datasets() requires it).
- TableSchema: the shape of a single entry in `tables`, checked in
  load_datasets() once the key is confirmed present.
"""

from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict


class _PermissiveModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class OutputSchema(_PermissiveModel):
    format: str = "json"
    path: str = "extract"
    batch_size: int = 1
    url: Optional[str] = None


class FullLoadSchema(_PermissiveModel):
    include_deletes: bool = False
    frequency: int = 100


class ConfigSettingsSchema(_PermissiveModel):
    db_path: str = "mockpipe.db"
    delete_behaviour: str = "soft"
    inter_action_delay: float = 0.5
    action_results_limit: int = 1000
    output: OutputSchema = OutputSchema()
    full_load: Optional[FullLoadSchema] = None
    seed: Optional[int] = None


class FieldSchema(_PermissiveModel):
    name: str
    type: str
    value: str


class ActionSchema(_PermissiveModel):
    name: str
    action: str
    frequency: float
    field: Optional[str] = None
    value: Optional[str] = None
    where_condition: Optional[str] = None
    arguments: Optional[List[Any]] = None
    effect: Optional[str] = None
    effect_count: Optional[Union[str, int]] = None
    action_condition: Optional[str] = None


class TableSchema(_PermissiveModel):
    name: str
    fields: List[FieldSchema]
    actions: List[ActionSchema]
