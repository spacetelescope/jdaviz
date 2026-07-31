from traitlets import Bool, List, Unicode
import numpy as np

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.template_mixin import SelectPluginComponent, UnitSelectPluginComponent
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.data.linelists.query_helpers import to_jdaviz_line_list, load_db, list_elements

__all__ = ['SpectralLineDatabaseResolver']


@loader_resolver_registry('spectral line database')
class SpectralLineDatabaseResolver(BaseResolver):
    """Interactive resolver that queries the built-in emission-line database.

    Users search by spectral range, element, and/or line-name substring,
    then stage individual results to build up an output
    ``QTable(linename, rest)`` that is consumed by ``LineListImporter``.

    Example usage from a notebook::

        ldr = viz.loaders['spectral line database']
        ldr.wavelength_min = "6500"
        ldr.wavelength_max = "6600"
        ldr.wavelength_unit = "Angstrom"
        ldr.element = "H"
        ldr.search()
        ldr.stage_line('H-alpha')           # by name
        ldr.stage_line(*ldr.search_results)  # stage all results at once
        ldr.load()
    """

    template_file = (__file__, "spectral_line_db.vue")
    requires_api_support = False

    title = Unicode("Spectral Line Database").tag(sync=True)

    # search parameters
    wavelength_min = Unicode("").tag(sync=True)
    wavelength_max = Unicode("").tag(sync=True)
    wavelength_unit_items = List().tag(sync=True)
    wavelength_unit_selected = Unicode("Angstrom").tag(sync=True)
    element_items = List([]).tag(sync=True)
    element_selected = Unicode("(any)").tag(sync=True)
    name_contains = Unicode("", allow_none=True).tag(sync=True)

    # search results
    search_results = List([]).tag(sync=True)  # read-only
    search_results_loading = Bool(False).tag(sync=True)
    search_status = Unicode("").tag(sync=True)

    # staged lines
    staged_lines = List([]).tag(sync=True)  # read-only

    def __init__(self, *args, **kwargs):
        self._db = None
        self._search_result_table = None
        super().__init__(*args, **kwargs)

        self.wavelength_unit = UnitSelectPluginComponent(self,
                                                         items='wavelength_unit_items',
                                                         selected='wavelength_unit_selected',
                                                         manual_options=["Angstrom", "nm", "um"])
        self.element = SelectPluginComponent(self,
                                             items='element_items',
                                             selected='element_selected')

        self._load_db()

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

    @property
    def input(self):
        return None

    def _check_is_valid(self):
        if self._db is None:
            return "No spectral lines database loaded."
        return ""

    def parse_input(self):
        if not self.staged_lines or self._db is None:
            return None
        staged_names = [r["line_name"] for r in self.staged_lines]
        names = np.array([str(n) for n in self._db["line_name"]])
        mask = np.isin(names, staged_names)
        lines_to_load = self._db[mask]
        if len(lines_to_load) == 0:
            return None
        return to_jdaviz_line_list(lines_to_load)

    def search(self):
        """Run a database query using the current filter values.

        Populates ``search_results`` with matching lines.

        Returns
        -------
        search_results: list of dict
            Each dict has keys ``line_name``, ``rest_wavelength``,
            ``wavelength_unit``, and ``element``.
        """
        if self._db is None:
            self.search_status = "Database not loaded."
            return []

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

            rows = []
            for row in result:
                rows.append({
                    "line_name": str(row["line_name"]),
                    "rest_wavelength": float(row["rest_wavelength"]),
                    "wavelength_unit": str(row["wavelength_unit"]),
                    "element": str(row["element"]) if row["element"] else "",
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

        return self.search_results

    def stage_line(self, *args):
        """Stage one or more lines.

        Parameters
        ----------
        *args : str or dict
            Each argument is either:

            * A **string** line name — the matching row is looked up in the
              database.  Example: ``ldr.stage_line('H-alpha')``.
            * A **dict** as returned by ``search_results`` — used directly
              with no database lookup.  Example:
              ``ldr.stage_line(*ldr.search_results)``.

            Lines already staged are silently skipped.
        """
        staged_names = {r["line_name"] for r in self.staged_lines}
        new_rows = list(self.staged_lines)
        changed = False
        for arg in args:
            if isinstance(arg, str):
                row_dict = self._lookup_db(arg)
                if row_dict is None:
                    raise ValueError(f"Line name '{arg}' not found in database.")
            elif isinstance(arg, dict):
                row_dict = arg
            else:
                raise TypeError(f"Expected str or dict, got {type(arg).__name__}")
            name = row_dict["line_name"]
            if name not in staged_names:
                new_rows.append(row_dict)
                staged_names.add(name)
                changed = True
        if changed:
            self.staged_lines = new_rows
            self._resolver_input_updated()

    def unstage_line(self, *args):
        """Unstage one or more lines.

        Parameters
        ----------
        *args : str or dict
            Each argument is either a **string** line name or a **dict** from
            ``search_results`` / ``staged_lines``.  Lines not currently staged
            are silently ignored.
        """
        names_to_remove = set()
        for arg in args:
            if isinstance(arg, str):
                names_to_remove.add(arg)
            elif isinstance(arg, dict):
                names_to_remove.add(arg["line_name"])
            else:
                raise TypeError(f"Expected str or dict, got {type(arg).__name__}")
        new_rows = [r for r in self.staged_lines if r["line_name"] not in names_to_remove]
        if len(new_rows) != len(self.staged_lines):
            self.staged_lines = new_rows
            self._resolver_input_updated()

    def clear_staged(self):
        """Remove all staged lines."""
        if self.staged_lines:
            self.staged_lines = []
            self._resolver_input_updated()

    def vue_search(self, _=None):
        self.search()

    def vue_stage_line(self, data):
        if isinstance(data, dict):
            self.stage_line(data)

    def vue_unstage_line(self, data):
        if isinstance(data, dict):
            self.unstage_line(data)

    def vue_clear_staged(self, _=None):
        self.clear_staged()

    def _load_db(self):
        try:
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

    def _lookup_db(self, name):
        """Return a search-result dict for *name* from the DB, or None if not found."""
        if self._db is None:
            return None
        names = np.array([str(n) for n in self._db["line_name"]])
        idx_arr = np.where(names == name)[0]
        if len(idx_arr) == 0:
            return None
        row = self._db[idx_arr[0]]
        return {
            "line_name": str(row["line_name"]),
            "rest_wavelength": float(row["rest_wavelength"]),
            "wavelength_unit": str(row["wavelength_unit"]),
            "element": str(row["element"]) if row["element"] else "",
        }
