import json
import math
from dataclasses import dataclass, field, replace

import numpy as np


__all__ = ['PluginTableRowSync', 'PluginTableRowSyncGroup',
           'decode_row_sync_recipe', 'encode_row_sync_recipe']


_DIRECTIONS = ('both', 'from_plugin', 'to_plugin')
_VALUE_KINDS = ('scalar', 'enum', 'data_label')


def _validate_identifier(value, name):
    if not isinstance(value, str) or not value or not value.isidentifier():
        raise ValueError(f"{name} must be a non-empty Python identifier")


@dataclass(frozen=True)
class PluginTableRowSync:
    """Declaration for one plugin attribute stored in one catalog column."""

    attribute: str
    traitlet: str
    label: str | None = None
    selectors: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    direction: str = 'both'
    value_kind: str = 'scalar'
    manual_values: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        _validate_identifier(self.attribute, 'attribute')
        _validate_identifier(self.traitlet, 'traitlet')
        if self.direction not in _DIRECTIONS:
            raise ValueError(f"direction must be one of {_DIRECTIONS}")
        if self.value_kind not in _VALUE_KINDS:
            raise ValueError(f"value_kind must be one of {_VALUE_KINDS}")
        if self.manual_values and self.value_kind != 'data_label':
            raise ValueError("manual_values are only valid for data_label attributes")
        for selector, value in self.selectors:
            _validate_identifier(selector, 'selector')
            if not isinstance(value, str) or not value:
                raise ValueError("selector values must be non-empty strings")

    def rename_selector(self, selector, old_value, new_value):
        selectors = tuple((key, new_value if key == selector and value == old_value else value)
                          for key, value in self.selectors)
        return replace(self, selectors=selectors)


@dataclass(frozen=True)
class PluginTableRowSyncGroup:
    """Declaration for plugin attributes packed into one JSON catalog column."""

    group: str
    members: tuple[PluginTableRowSync, ...]
    label: str | None = None
    direction: str = 'both'

    def __post_init__(self):
        _validate_identifier(self.group, 'group')
        if self.direction not in _DIRECTIONS:
            raise ValueError(f"direction must be one of {_DIRECTIONS}")
        if not self.members:
            raise ValueError("members must contain at least one attribute")
        attributes = [member.attribute for member in self.members]
        if len(attributes) != len(set(attributes)):
            raise ValueError("group member attributes must be unique")


def _json_native(value):
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("row-sync recipes cannot contain non-finite values")
        return value
    if isinstance(value, (list, tuple)):
        return [_json_native(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("row-sync recipe keys must be strings")
        return {key: _json_native(item) for key, item in value.items()}
    raise TypeError(f"unsupported row-sync recipe value: {type(value).__name__}")


def encode_row_sync_recipe(values):
    """Return a canonical JSON string for a packed plugin recipe."""
    payload = {'values': _json_native(values)}
    return json.dumps(payload, allow_nan=False, separators=(',', ':'), sort_keys=True)


def decode_row_sync_recipe(value):
    """Decode and validate a packed plugin recipe JSON string.
    """
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid row-sync recipe JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("row-sync recipe values must be a mapping")
    values = payload.get('values')
    if not isinstance(values, dict):
        raise ValueError("row-sync recipe values must be a mapping")
    return values
