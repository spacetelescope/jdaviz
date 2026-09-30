# Licensed under a 3-clause BSD style license - see LICENSE.rst

from copy import deepcopy

import pytest

from jdaviz.core.viewer_layout import (
    add_viewer, iter_viewer_ids, remove_viewer, rename_viewer,
    ViewerLayoutError, validate_and_normalize,
)


def stack(*viewers, **options):
    return {"type": "stack", "viewers": list(viewers), **options}


def test_normalization_defaults_and_proportions_without_mutation():
    layout = {"version": 1, "root": {"type": "row", "weight": 99, "children": [
        stack("one", weight=1), stack("two", "three", weight=3, activeViewerId="missing"),
    ]}, "maximizedViewerId": "three"}
    original = deepcopy(layout)
    normalized = validate_and_normalize(layout, viewer_ids=["one", "two", "three"])

    assert layout == original
    assert "weight" not in normalized["root"]
    assert [child["weight"] for child in normalized["root"]["children"]] == [0.25, 0.75]
    assert normalized["root"]["children"][1]["activeViewerId"] == "two"
    assert normalized["maximizedViewerId"] == "two"
    equivalent = deepcopy(layout)
    equivalent["root"]["children"][0]["weight"] = 25
    equivalent["root"]["children"][1]["weight"] = 75
    assert normalized == validate_and_normalize(equivalent)
    equivalent["root"]["children"].reverse()
    assert normalized != validate_and_normalize(equivalent)


@pytest.mark.parametrize("layout,match", [
    ({"version": 2, "root": None}, "version"),
    ({"version": True, "root": None}, "version"),
    ({"version": 1}, "root"),
    ({"version": 1, "root": None, "vendorState": {}}, "unknown field"),
    ({"version": 1, "root": {"type": "row", "children": [None]}}, "must be an object"),
    ({"version": 1, "root": {"type": "row"}}, "must be an array"),
    ({"version": 1, "root": stack("v", id="unneeded")}, "unknown field"),
    ({"version": 1, "root": stack("v", minWidth=120)}, "unknown field"),
    ({"version": 1, "root": stack("v", "v")}, "occurs more than once"),
    ({"version": 1, "root": stack(123)}, "non-empty string"),
    ({"version": 1, "root": stack("v"), "maximizedViewerId": "missing"}, "refer to a viewer"),
])
def test_invalid_schema(layout, match):
    with pytest.raises(ViewerLayoutError, match=match):
        validate_and_normalize(layout)


@pytest.mark.parametrize("weight", ["1", True, 0, -1, float("nan"), float("inf")])
def test_invalid_weights(weight):
    with pytest.raises(ViewerLayoutError):
        validate_and_normalize({"version": 1, "root": {
            "type": "row", "children": [stack("v", weight=weight)],
        }})


def test_exact_viewer_membership_and_extreme_weights():
    with pytest.raises(ViewerLayoutError, match="missing viewer IDs.*unknown viewer IDs"):
        validate_and_normalize({"version": 1, "root": stack("known", "unknown")},
                               viewer_ids=["known", "missing"])
    layout = {"version": 1, "root": {"type": "row", "children": [
        stack("one", weight=1e308), stack("two", weight=1e308), stack("three", weight=1e-300),
    ]}}
    weights = [node["weight"] for node in validate_and_normalize(layout)["root"]["children"]]
    assert weights == [0.499999999999, 0.5, 1e-12]
    assert sum(weights) == 1


@pytest.mark.parametrize("container", ["row", "column"])
def test_add_first_viewer_then_wrap_and_extend_split(container):
    empty = {"version": 1, "root": None}
    first = add_viewer(empty, "one", container=container)
    assert first == {"version": 1, "root": stack("one", activeViewerId="one")}
    assert empty["root"] is None
    second = add_viewer(first, "two", container=container)
    third = add_viewer(second, "three", container=container)
    assert first["root"]["type"] == "stack"
    assert second["root"]["type"] == container
    assert iter_viewer_ids(third) == ("one", "two", "three")
    assert [node["weight"] for node in third["root"]["children"]] == pytest.approx([1 / 3] * 3)
    with pytest.raises(ViewerLayoutError, match="already occurs"):
        add_viewer(third, "one")


def test_add_equalizes_top_level_only():
    layout = {"version": 1, "root": {"type": "row", "children": [
        stack("one", weight=1), stack("two", weight=3),
    ]}}
    result = add_viewer(layout, "three")
    assert [node["weight"] for node in result["root"]["children"]] == [0.5, 0.5]
    assert [node["weight"] for node in result["root"]["children"][0]["children"]] == [0.25, 0.75]


def test_remove_active_viewer_keeps_surviving_stack_maximized():
    layout = {"version": 1, "root": stack("one", "two", activeViewerId="two"),
              "maximizedViewerId": "two"}
    original = deepcopy(layout)
    result = remove_viewer(layout, "two")
    assert layout == original
    assert result == {"version": 1, "root": stack("one", activeViewerId="one"),
                      "maximizedViewerId": "one"}
    assert remove_viewer(result, "unknown") == result
    assert remove_viewer(result, "one") == {"version": 1, "root": None}


def test_id_rename_updates_tabs_and_maximization_without_mutation():
    layout = {"version": 1, "root": stack("one", "two", activeViewerId="two"),
              "maximizedViewerId": "two"}
    original = deepcopy(layout)
    result = rename_viewer(layout, "two", "renamed")
    assert layout == original
    assert result == {"version": 1,
                      "root": stack("one", "renamed", activeViewerId="renamed"),
                      "maximizedViewerId": "renamed"}
    with pytest.raises(ViewerLayoutError, match="occurs more than once"):
        rename_viewer(layout, "two", "one")


def test_remove_prunes_empty_nodes_and_collapses_splits():
    layout = {"version": 1, "root": {"type": "column", "children": [
        stack("one"), {"type": "row", "children": [stack("two")]},
    ]}, "maximizedViewerId": "one"}
    result = remove_viewer(layout, "one")
    assert result["root"] == stack("two", activeViewerId="two")
    assert iter_viewer_ids(result) == ("two",)
    assert "maximizedViewerId" not in result


@pytest.mark.parametrize("root", [None, stack(), {"type": "column", "children": []},
                                  {"type": "row", "children": [stack()]}])
def test_empty_nodes_are_pruned(root):
    assert validate_and_normalize({"version": 1, "root": root}, viewer_ids=[]) == {
        "version": 1, "root": None}


def test_collapse_preserves_parent_weight_and_nested_proportions():
    layout = {"version": 1, "root": {"type": "row", "children": [
        {"type": "column", "weight": 3, "children": [
            stack(), {"type": "row", "weight": 99, "children": [
                stack("one", weight=1), stack("two", weight=3),
            ]},
        ]},
        stack("three", weight=1),
    ]}}
    normalized = validate_and_normalize(layout)
    children = normalized["root"]["children"]
    assert [node["weight"] for node in children] == [0.75, 0.25]
    assert children[0]["type"] == "row"  # Preserve resize grouping.
    assert [node["weight"] for node in children[0]["children"]] == [0.25, 0.75]
    assert validate_and_normalize(normalized) == normalized


def test_removal_preserves_collapsed_split_outer_weight():
    layout = {"version": 1, "root": {"type": "row", "children": [
        {"type": "column", "weight": 3, "children": [
            stack("one", weight=99), stack("two", weight=1),
        ]}, stack("three", weight=1),
    ]}}
    result = remove_viewer(layout, "one")
    assert result["root"]["children"] == [
        stack("two", activeViewerId="two", weight=0.75),
        stack("three", activeViewerId="three", weight=0.25),
    ]


@pytest.mark.parametrize("removed,active,expected", [
    ("three", "three", "two"), ("two", "two", "one"),
    ("one", "one", "two"), ("one", "three", "three"),
])
def test_removal_selects_neighbor_and_keeps_maximized_stack(removed, active, expected):
    layout = {"version": 1, "root": stack("one", "two", "three", activeViewerId=active),
              "maximizedViewerId": active}
    result = remove_viewer(layout, removed)
    assert result["root"]["activeViewerId"] == expected
    assert result["maximizedViewerId"] == expected
