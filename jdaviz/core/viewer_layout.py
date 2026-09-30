# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Validate and edit viewer layouts without constructing widgets."""

from collections.abc import Mapping, Sequence
from copy import deepcopy
import math


LAYOUT_VERSION = 1
WEIGHT_PRECISION = 12

_DOCUMENT_FIELDS = {"version", "root", "maximizedViewerId"}
_NODE_FIELDS = {"type", "weight"}


class ViewerLayoutError(ValueError):
    """Raised when viewer-layout data violates the versioned schema."""


def _object(value, path, fields):
    if not isinstance(value, Mapping):
        raise ViewerLayoutError(f"{path}: must be an object")
    unknown = value.keys() - fields
    if unknown:
        raise ViewerLayoutError(f"{path}: unknown field(s): {', '.join(map(str, unknown))}")
    return dict(value)


def _array(value, path):
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ViewerLayoutError(f"{path}: must be an array")
    return value


def _string(value, path):
    if not isinstance(value, str) or not value:
        raise ViewerLayoutError(f"{path}: must be a non-empty string")
    return value


def _weight(value, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ViewerLayoutError(f"{path}: must be a number")
    try:
        number = float(value)
    except OverflowError:
        number = math.inf
    if not math.isfinite(number):
        raise ViewerLayoutError(f"{path}: must be finite")
    if number <= 0:
        raise ViewerLayoutError(f"{path}: must be greater than zero")
    return number


def _normalize_weights(children):
    # Scale before summing to avoid overflow, then use the same twelve-digit
    # precision as JavaScript. Correct the largest sibling so none become zero.
    scale = max(child["weight"] for child in children)
    weights = [child["weight"] / scale for child in children]
    total = math.fsum(weights)
    weights = [max(round(weight / total, WEIGHT_PRECISION), 10 ** -WEIGHT_PRECISION)
               for weight in weights]
    largest = weights.index(max(weights))
    weights[largest] = round(weights[largest] + (1 - math.fsum(weights)), WEIGHT_PRECISION)
    for child, weight in zip(children, weights):
        child["weight"] = weight


def validate_and_normalize(layout, *, viewer_ids=None):
    """Return a validated deep copy of a version-1 layout.

    Fill default weights and active tabs, normalize sibling weights to sum to
    one, prune empty nodes, collapse one-child splits, and discard root weight.
    A collapsed child inherits its split's weight in the enclosing split.
    When ``viewer_ids`` is supplied, require
    exactly that set of live viewers, each occurring once in the tree.
    """
    result = _object(layout, "layout", _DOCUMENT_FIELDS)
    if isinstance(result.get("version"), bool) or result.get("version") != LAYOUT_VERSION:
        raise ViewerLayoutError(f"layout.version: must be {LAYOUT_VERSION}")
    result["version"] = LAYOUT_VERSION
    if "root" not in result:
        raise ViewerLayoutError("layout.root: is required")

    seen_viewers = set()
    if result["root"] is not None:
        result["root"] = _normalize_node(result["root"], "layout.root", seen_viewers,
                                         is_root=True)
    if viewer_ids is not None:
        expected = set(viewer_ids)
        missing = sorted(expected - seen_viewers)
        unknown = sorted(seen_viewers - expected)
        if missing or unknown:
            raise ViewerLayoutError(
                f"layout: missing viewer IDs: {missing!r}; unknown viewer IDs: {unknown!r}")
    if "maximizedViewerId" in result:
        maximized_id = _string(result["maximizedViewerId"], "layout.maximizedViewerId")
        if maximized_id not in seen_viewers:
            raise ViewerLayoutError(
                f"layout.maximizedViewerId: does not refer to a viewer: {maximized_id!r}")
        # A maximized stack always shows its active tab.
        result["maximizedViewerId"] = _find_stack(result["root"], maximized_id)["activeViewerId"]
    return result


def _normalize_node(value, path, seen_viewers, *, is_root=False):
    """Return a normalized copy of a node, or `None` when it has no viewers."""
    node = _object(value, path, _NODE_FIELDS | {"children", "viewers", "activeViewerId"})
    node_type = node.get("type")
    if node_type not in ("row", "column", "stack"):
        raise ViewerLayoutError(f"{path}.type: must be 'row', 'column', or 'stack'")
    invalid_fields = {"children"} if node_type == "stack" else {"viewers", "activeViewerId"}
    if invalid_fields & node.keys():
        raise ViewerLayoutError(f"{path}: unknown field(s) for {node_type}")
    if is_root:
        node.pop("weight", None)
    else:
        node["weight"] = _weight(node.get("weight", 1), f"{path}.weight")
    if node_type == "stack":
        return _normalize_stack(node, path, seen_viewers)
    return _normalize_split(node, path, seen_viewers, is_root=is_root)


def _normalize_stack(node, path, seen_viewers):
    node["viewers"] = list(_array(node.get("viewers"), f"{path}.viewers"))
    if not node["viewers"]:
        return None
    for index, viewer_id in enumerate(node["viewers"]):
        _string(viewer_id, f"{path}.viewers[{index}]")
        if viewer_id in seen_viewers:
            raise ViewerLayoutError(f"{path}: viewer ID {viewer_id!r} occurs more than once")
        seen_viewers.add(viewer_id)
    if node.get("activeViewerId") not in node["viewers"]:
        node["activeViewerId"] = node["viewers"][0]
    return node


def _normalize_split(node, path, seen_viewers, *, is_root):
    children = _array(node.get("children"), f"{path}.children")
    node["children"] = [normalized for index, child in enumerate(children)
                        if (normalized := _normalize_node(
                            child, f"{path}.children[{index}]", seen_viewers)) is not None]
    if not node["children"]:
        return None
    if len(node["children"]) == 1:
        # Collapse the split; its only child takes over its place and weight.
        child = node["children"][0]
        if is_root:
            child.pop("weight", None)
        else:
            child["weight"] = node["weight"]
        return child
    _normalize_weights(node["children"])
    return node


def _nodes(node):
    if node is not None:
        yield node
        for child in node.get("children", ()):
            yield from _nodes(child)


def _find_stack(root, viewer_id):
    return next(node for node in _nodes(root)
                if viewer_id in node.get("viewers", ()))


def iter_viewer_ids(layout):
    """Return viewer IDs in tree and tab order from an already valid layout."""
    return tuple(viewer_id for node in _nodes(layout["root"])
                 for viewer_id in node.get("viewers", ()))


def add_viewer(layout, viewer_id, *, container="column"):
    """Append a one-viewer stack in the application's existing split direction."""
    if viewer_id in iter_viewer_ids(layout):
        raise ViewerLayoutError(f"viewer ID {viewer_id!r} already occurs in the layout")
    result = deepcopy(layout)
    stack = {"type": "stack", "viewers": [viewer_id]}
    root = result["root"]
    if root is None:
        result["root"] = stack
    elif root["type"] == container:
        root["children"].append(stack)
    else:
        result["root"] = {"type": container, "children": [root, stack]}
    if result["root"]["type"] == container:
        for child in result["root"]["children"]:
            child["weight"] = 1
    return validate_and_normalize(result)


def remove_viewer(layout, viewer_id):
    """Remove a viewer, prune empty nodes, and collapse one-child splits.

    Removing the active tab selects its previous neighbor, or its next neighbor
    when removing the first tab. An unknown viewer is a no-op on a normalized
    layout. The input is never mutated.
    """
    result = deepcopy(layout)
    for node in _nodes(result["root"]):
        if node["type"] != "stack" or viewer_id not in node["viewers"]:
            continue
        removed_index = node["viewers"].index(viewer_id)
        node["viewers"].remove(viewer_id)
        if node.get("activeViewerId") == viewer_id and node["viewers"]:
            node["activeViewerId"] = node["viewers"][max(0, removed_index - 1)]
        if result.get("maximizedViewerId") == viewer_id:
            if node["viewers"]:
                result["maximizedViewerId"] = node.get("activeViewerId", node["viewers"][0])
            else:
                del result["maximizedViewerId"]
    return validate_and_normalize(result)


def rename_viewer(layout, old_id, new_id):
    """Keep layout membership and tab selection in sync with an explicit ID rename."""
    result = deepcopy(layout)
    for node in _nodes(result["root"]):
        if node["type"] == "stack":
            node["viewers"] = [new_id if item == old_id else item for item in node["viewers"]]
            if node.get("activeViewerId") == old_id:
                node["activeViewerId"] = new_id
    if result.get("maximizedViewerId") == old_id:
        result["maximizedViewerId"] = new_id
    return validate_and_normalize(result)
