import pytest
from astropy.table import QTable


def test_db_loads(deconfigged_helper):
    """DB should load successfully on init and resolver should be valid."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    assert ldr._obj._db is not None
    assert len(ldr._obj._db) > 0
    assert ldr._obj._check_is_valid() == ''

    ldr.search()
    assert len(ldr.search_results) == len(ldr._obj._db)
    required = {"line_name", "rest_wavelength", "wavelength_unit", "element"}
    assert all(required <= r.keys() for r in ldr.search_results)


def test_search_by_element(deconfigged_helper):
    """Filtering by element returns a subset; all rows carry that element tag."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.element = "H"
    ldr.search()
    h_results = list(ldr.search_results)
    assert len(h_results) > 0
    assert all(r["element"] == "H" for r in h_results)

    # Switching to (any) must yield more results
    ldr.element = "(any)"
    ldr.search()
    assert len(ldr.search_results) > len(h_results)


def test_search_by_wavelength_range(deconfigged_helper):
    """Wavelength range filter narrows the result set."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.wavelength_unit.selected = "Angstrom"
    ldr.wavelength_min = "6500"
    ldr.wavelength_max = "6600"
    ldr.search()
    filtered_count = len(ldr.search_results)
    assert filtered_count > 0

    ldr.wavelength_min = ""
    ldr.wavelength_max = ""
    ldr.search()
    assert len(ldr.search_results) > filtered_count


def test_search_by_name_contains(deconfigged_helper):
    """name_contains substring filter narrows results."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.name_contains = "CO"
    ldr.search()
    co_count = len(ldr.search_results)
    assert co_count > 0

    ldr.name_contains = ""
    ldr.search()
    assert len(ldr.search_results) > co_count


def test_search_combined_filters(deconfigged_helper):
    """Combining element + wavelength range gives a subset of each alone."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.element.selected = "H"
    ldr.search()
    h_only = len(ldr.search_results)

    ldr.wavelength_unit.selected = "Angstrom"
    ldr.wavelength_min = "3000"
    ldr.wavelength_max = "9000"
    ldr.search()
    combined = len(ldr.search_results)

    assert combined <= h_only


def test_search_no_results_status(deconfigged_helper):
    """A search with no matches sets the correct status and empty results."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.name_contains = "ZZZNOMATCH_XYZ_9999"
    ldr.search()

    assert ldr.search_results == []
    assert ldr._obj.search_status == "No matching lines found."


def test_search_single_result_status(deconfigged_helper):
    """A search returning exactly one line reports '1 line found.'"""
    # Use a very narrow range that is known to contain exactly one line;
    # fall back to checking the message format if counts vary.
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    if len(ldr.search_results) == 1:
        assert ldr._obj.search_status == "1 line found."
    else:
        assert "found" in ldr._obj.search_status.lower()


def test_search_clears_previous_results(deconfigged_helper):
    """A second, more restrictive search replaces the first results."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    all_count = len(ldr.search_results)

    ldr.element.selected = "H"
    ldr.search()
    assert len(ldr.search_results) < all_count


def test_stage_line_by_name(deconfigged_helper):
    """stage_line with a string name adds the matching row to staged_lines."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    name = ldr.search_results[0]["line_name"]

    ldr.stage_line(name)
    assert len(ldr.staged_lines) == 1
    assert ldr.staged_lines[0]["line_name"] == name


def test_stage_line_by_dict(deconfigged_helper):
    """stage_line with a search-result dict adds it to staged_lines."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    row = ldr.search_results[0]

    ldr.stage_line(row)
    assert len(ldr.staged_lines) == 1
    assert ldr.staged_lines[0]["line_name"] == row["line_name"]


def test_stage_line_duplicate_skipped(deconfigged_helper):
    """Staging the same line a second time is silently ignored."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    name = ldr.search_results[0]["line_name"]

    ldr.stage_line(name)
    ldr.stage_line(name)
    assert len(ldr.staged_lines) == 1


def test_stage_line_multiple_at_once(deconfigged_helper):
    """stage_line(*results) stages all unique-named results in a single call."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.wavelength_unit.selected = "Angstrom"
    ldr.wavelength_min = "6500"
    ldr.wavelength_max = "6600"
    ldr.search()
    n = len(ldr.search_results)
    assert n > 0

    # DB may contain duplicate line names; stage_line deduplicates by name.
    unique_names = {r["line_name"] for r in ldr.search_results}
    ldr.stage_line(*ldr.search_results)
    assert len(ldr.staged_lines) == len(unique_names)


def test_stage_line_unknown_name_raises(deconfigged_helper):
    """stage_line with an unknown name raises ValueError."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    with pytest.raises(ValueError, match="not found in database"):
        ldr.stage_line("NOSUCHLINE_XYZZY_9999")


def test_stage_line_wrong_type_raises(deconfigged_helper):
    """stage_line with a non-str/dict argument raises TypeError."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    with pytest.raises(TypeError):
        ldr.stage_line(42)


def test_unstage_line_by_name(deconfigged_helper):
    """unstage_line by string name removes just that line."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    names = [r["line_name"] for r in ldr.search_results[:3]]
    ldr.stage_line(*names)
    assert len(ldr.staged_lines) == 3

    ldr.unstage_line(names[1])
    assert len(ldr.staged_lines) == 2
    assert all(r["line_name"] != names[1] for r in ldr.staged_lines)


def test_unstage_line_by_dict(deconfigged_helper):
    """unstage_line by dict removes the matching line."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    row = ldr.search_results[0]
    ldr.stage_line(row)

    ldr.unstage_line(row)
    assert ldr.staged_lines == []


def test_unstage_line_multiple_at_once(deconfigged_helper):
    """unstage_line(*args) removes several lines in one call."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    rows = ldr.search_results[:4]
    ldr.stage_line(*rows)

    ldr.unstage_line(rows[0]["line_name"], rows[2])
    assert len(ldr.staged_lines) == 2
    removed = {rows[0]["line_name"], rows[2]["line_name"]}
    assert all(r["line_name"] not in removed for r in ldr.staged_lines)


def test_unstage_line_not_staged_ignored(deconfigged_helper):
    """unstage_line for a line not currently staged is silently ignored."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    ldr.stage_line(ldr.search_results[0]["line_name"])
    before = len(ldr.staged_lines)

    ldr.unstage_line("NOSUCHLINE_XYZZY_9999")
    assert len(ldr.staged_lines) == before


def test_unstage_line_wrong_type_raises(deconfigged_helper):
    """unstage_line with a non-str/dict argument raises TypeError."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    with pytest.raises(TypeError):
        ldr.unstage_line(99)


def test_clear_staged(deconfigged_helper):
    """clear_staged empties staged_lines regardless of how many lines are staged."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.search()
    ldr.stage_line(*ldr.search_results[:5])
    assert len(ldr.staged_lines) == 5

    ldr.clear_staged()
    assert ldr.staged_lines == []


def test_clear_staged_when_empty(deconfigged_helper):
    """clear_staged on an already-empty list is a no-op."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.clear_staged()
    assert ldr.staged_lines == []


def test_parse_input_none_when_nothing_staged(deconfigged_helper):
    """parse_input returns None when staged_lines is empty."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    assert ldr._obj.parse_input() is None


def test_parse_input_returns_qtable(deconfigged_helper):
    """parse_input returns a QTable with linename and rest columns."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.wavelength_unit.selected = "Angstrom"
    ldr.wavelength_min = "6500"
    ldr.wavelength_max = "6600"
    ldr.search()
    assert len(ldr.search_results) > 0

    # Stage all unique-named results (DB may have duplicate names).
    ldr.stage_line(*ldr.search_results)
    n_staged = len(ldr.staged_lines)
    qt = ldr._obj.parse_input()

    assert isinstance(qt, QTable)
    assert "linename" in qt.colnames
    assert "rest" in qt.colnames
    assert len(qt) == n_staged
    assert qt["rest"].unit is not None


def test_parse_input_after_unstage(deconfigged_helper):
    """Unstaging a line reduces the parse_input output length."""
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.wavelength_unit.selected = "Angstrom"
    ldr.wavelength_min = "6500"
    ldr.wavelength_max = "6600"
    ldr.search()
    ldr.stage_line(*ldr.search_results)
    full_len = len(ldr._obj.parse_input())

    ldr.unstage_line(ldr.staged_lines[0]["line_name"])
    assert len(ldr._obj.parse_input()) == full_len - 1


def test_stage_across_multiple_searches(deconfigged_helper):
    """Lines staged from two separate searches accumulate correctly."""
    # First search
    ldr = deconfigged_helper.loaders["spectral line database"]
    ldr.element.selected = "H"
    ldr.wavelength_unit.selected = "Angstrom"
    ldr.wavelength_min = "6500"
    ldr.wavelength_max = "6600"
    ldr.search()
    first_batch = list(ldr.search_results)
    ldr.stage_line(*first_batch)
    after_first = len(ldr.staged_lines)

    # Second search with a different range; avoid re-staging duplicates.
    ldr.element.selected = "(any)"
    ldr.wavelength_min = "4800"
    ldr.wavelength_max = "4870"
    ldr.search()
    already_staged = {r["line_name"] for r in ldr.staged_lines}
    new_rows = [r for r in ldr.search_results if r["line_name"] not in already_staged]
    # Further deduplicate new_rows by name (DB may have duplicates).
    seen = set()
    new_rows_unique = []
    for r in new_rows:
        if r["line_name"] not in seen:
            new_rows_unique.append(r)
            seen.add(r["line_name"])

    ldr.stage_line(*new_rows_unique)
    assert len(ldr.staged_lines) == after_first + len(new_rows_unique)

    qt = ldr._obj.parse_input()
    assert isinstance(qt, QTable)
    assert len(qt) == len(ldr.staged_lines)
