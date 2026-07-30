from traitlets import Bool, List, Unicode

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.template_mixin import SelectPluginComponent, UnitSelectPluginComponent
from jdaviz.core.user_api import LoaderUserApi

__all__ = ['SpectralLineDatabaseResolver']


@loader_resolver_registry('spectral line database')
class SpectralLineDatabaseResolver(BaseResolver):
    """Interactive resolver that queries the built-in emission-line database.

    Users search by spectral range, element, and/or line-name substring,
    then stage individual results to build up an output
    ``QTable(linename, rest)`` that is consumed by ``LineListImporter``.

    Example usage from a notebook::

        ldr = viz.loaders['spectral line database']
        ldr.wave_min = "6500"
        ldr.wave_max = "6600"
        ldr.spectral_unit_selected = "Angstrom"
        ldr.element_selected = "H"
        ldr.search()
        ldr.stage_line(0)   # stage the first result
        ldr.load()
    """

    template_file = (__file__, "spectral_line_db.vue")
    requires_api_support = False

    title = Unicode("Spectral Line Database").tag(sync=True)

    # ---- Search parameters ----
    wavelength_min = Unicode("").tag(sync=True)
    wavelength_max = Unicode("").tag(sync=True)
    wavelength_unit_items = List().tag(sync=True)
    wavelength_unit_selected = Unicode("Angstrom").tag(sync=True)
    element_items = List([]).tag(sync=True)
    element_selected = Unicode("(any)").tag(sync=True)
    name_contains = Unicode("", allow_none=True).tag(sync=True)

    # ---- Search results (read-only via API) ----
    search_results = List([]).tag(sync=True)
    search_results_loading = Bool(False).tag(sync=True)
    search_status = Unicode("").tag(sync=True)

    # ---- Staged lines (read-only via API) ----
    staged_lines = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._db = None
        self._search_result_table = None
        # Each entry is a 1-row Table slice from _search_result_table
        self._staged_db_rows = []
        super().__init__(*args, **kwargs)

        self.wavelength_unit = UnitSelectPluginComponent(self,
                                                         items='wavelength_unit_items',
                                                         selected='wavelength_unit_selected',
                                                         manual_options=["Angstrom", "nm", "um"])
        self.element = SelectPluginComponent(self,
                                             items='element_items',
                                             selected='element_selected')

        self._load_db()

    # ---- User API ----

    @property
    def user_api(self):
        return LoaderUserApi(
            self,
            expose=[
                'wavelength_min', 'wavelength_max', 'wavelength_unit',
                'element', 'name_contains',
                'search', 'stage_line', 'unstage_line', 'clear_staged',
                'search_results', 'staged_lines',
            ],
            readonly=['search_results', 'staged_lines'],
        )

    # ---- BaseResolver interface ----

    @property
    def input(self):
        # This resolver has no external input; it is driven entirely by the UI.
        return None

    def _check_is_valid(self):
        if self._db is None:
            return "Could not load the spectral lines database."
        return ""

    def parse_input(self):
        if not self._staged_db_rows:
            return None
        from astropy.table import vstack
        from jdaviz.data.linelists.query_helpers import to_jdaviz_line_list
        staged_table = vstack(self._staged_db_rows)
        return to_jdaviz_line_list(staged_table)

    # ---- Public API methods ----

    def search(self):
        """Run a database query using the current filter traitlet values.

        Populates ``search_results`` with matching lines. Each entry is a dict
        with keys ``index``, ``line_name``, ``rest_wavelength``,
        ``wavelength_unit``, ``element``, and ``already_staged``.

        Equivalent to clicking the Search button in the UI.
        """
        if self._db is None:
            self.search_status = "Database not loaded."
            return

        self.search_results_loading = True
        try:
            from jdaviz.data.linelists.query_helpers import get_lines

            element = (
                None
                if not self.element_selected or self.element_selected == "(any)"
                else self.element_selected
            )
            name_contains = (self.name_contains or "").strip() or None

            try:
                wave_min = float(self.wavelength_min) if self.wavelength_min.strip() else None
            except ValueError:
                wave_min = None
            try:
                wave_max = float(self.wavelength_max) if self.wavelength_max.strip() else None
            except ValueError:
                wave_max = None

            result = get_lines(
                self._db,
                name_contains=name_contains,
                wave_min=wave_min,
                wave_max=wave_max,
                unit=self.wavelength_unit.selected,
                element=element,
            )
            self._search_result_table = result

            staged_keys = self._staged_keys()
            rows = []
            for i, row in enumerate(result):
                key = _row_key(row)
                rows.append({
                    "index": i,
                    "line_name": str(row["line_name"]),
                    "rest_wavelength": float(row["rest_wavelength"]),
                    "wavelength_unit": str(row["wavelength_unit"]),
                    "element": str(row["element"]) if row["element"] else "",
                    "already_staged": key in staged_keys,
                })
            self.search_results = rows

            n = len(result)
            if n == 0:
                self.search_status = "No matching lines found."
            elif n == 1:
                self.search_status = "1 line found."
            else:
                self.search_status = f"{n} lines found."

        except Exception as e:
            self.search_status = f"Search error: {e}"
            self.search_results = []
        finally:
            self.search_results_loading = False

    def stage_line(self, idx):
        """Stage a single line from the current ``search_results`` by its index.

        Parameters
        ----------
        idx : int
            Index into ``search_results`` (the ``index`` field of each row).
            Silently ignored if the line is already staged.

        Equivalent to clicking the ``+`` button next to a search result row.
        """
        if self._search_result_table is None or idx >= len(self._search_result_table):
            return
        row = self._search_result_table[idx]
        if _row_key(row) in self._staged_keys():
            return  # already staged — silently ignore
        self._staged_db_rows.append(self._search_result_table[idx: idx + 1])
        self._sync_staged()
        self._resolver_input_updated()

    def unstage_line(self, idx):
        """Remove a staged line by its position in ``staged_lines``.

        Parameters
        ----------
        idx : int
            Zero-based index into ``staged_lines``.

        Equivalent to clicking the ``-`` button next to a staged line.
        """
        if idx < 0 or idx >= len(self._staged_db_rows):
            return
        self._staged_db_rows.pop(idx)
        self._sync_staged()
        self._resolver_input_updated()

    def clear_staged(self):
        """Remove all staged lines.

        Equivalent to clicking the "Clear all" button.
        """
        self._staged_db_rows.clear()
        self._sync_staged()
        self._resolver_input_updated()

    # ---- Vue-callable wrappers (template uses the name without the vue_ prefix) ----

    def vue_search(self, _=None):
        self.search()

    def vue_stage_line(self, data):
        idx = data.get("index") if isinstance(data, dict) else None
        if idx is not None:
            self.stage_line(idx)

    def vue_unstage_line(self, data):
        idx = data.get("index") if isinstance(data, dict) else None
        if idx is not None:
            self.unstage_line(idx)

    def vue_clear_staged(self, _=None):
        self.clear_staged()

    # ---- Internal helpers ----

    def _load_db(self):
        try:
            from jdaviz.data.linelists.query_helpers import load_db, list_elements
            self._db = load_db()
            elements = list_elements(self._db)
            unparsed = "(unparsed)" in elements
            labels = (
                ["(any)"]
                + [k for k in elements if k != "(unparsed)"]
                + (["(unparsed)"] if unparsed else [])
            )
            self.element_items = [{"label": lbl} for lbl in labels]
        except Exception:
            self._db = None

    def _staged_keys(self):
        """Return a set of (line_name, rest_wavelength, wavelength_unit) tuples for staged rows."""
        keys = set()
        for tbl in self._staged_db_rows:
            keys.add((
                str(tbl["line_name"][0]),
                float(tbl["rest_wavelength"][0]),
                str(tbl["wavelength_unit"][0]),
            ))
        return keys

    def _sync_staged(self):
        """Sync _staged_db_rows to the staged_lines traitlet and refresh already_staged flags."""
        self.staged_lines = [
            {
                "line_name": str(tbl["line_name"][0]),
                "rest_wavelength": float(tbl["rest_wavelength"][0]),
                "wavelength_unit": str(tbl["wavelength_unit"][0]),
                "element": str(tbl["element"][0]) if tbl["element"][0] else "",
            }
            for tbl in self._staged_db_rows
        ]
        if self.search_results:
            staged_keys = self._staged_keys()
            self.search_results = [
                {**row, "already_staged": _row_key_from_dict(row) in staged_keys}
                for row in self.search_results
            ]


# ---- Module-level helpers ----

def _row_key(row):
    """Key for an astropy Row object."""
    return (str(row["line_name"]), float(row["rest_wavelength"]), str(row["wavelength_unit"]))


def _row_key_from_dict(d):
    """Key from a search-result dict."""
    return (d["line_name"], d["rest_wavelength"], d["wavelength_unit"])
