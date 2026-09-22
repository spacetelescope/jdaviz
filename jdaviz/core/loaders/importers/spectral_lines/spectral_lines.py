from astropy.table import Table, QTable
import astropy.units as u
import re
from traitlets import Bool, List, Unicode, observe

from jdaviz.core.loaders.importers import BaseCatalogImporter
from jdaviz.core.template_mixin import SelectPluginComponent
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['SpectralLinesImporter']

# Physical types that represent valid spectral axes
_SPECTRAL_PHYSICAL_TYPES = ('length', 'frequency', 'energy', 'wavenumber')

# Regex patterns for guessing spectral location columns by name
_SPECTRAL_LOC_PATTERNS = [
    re.compile(r'^wavelength$|wavelength|^wave$|^wav$|^wl$|^lambda$|^lam$'
               r'|^restwave$|^rest_wave$', re.IGNORECASE),
    re.compile(r'^frequency$|frequency|^freq$|^nu$'
               r'|^restfreq$|^rest_freq$', re.IGNORECASE),
    re.compile(r'^wavenumber$|wavenumber|^wave_number$', re.IGNORECASE),
    re.compile(r'^energy$', re.IGNORECASE),
]

# Regex patterns for guessing line name columns
_LINENAME_PATTERNS = [
    re.compile(r'^linename$|line_name|^name$|^id$', re.IGNORECASE),
]


@loader_importer_registry("Spectral Lines")
class SpectralLinesImporter(BaseCatalogImporter):
    """
    Importer for spectral line list tables.

    Accepts an astropy ``Table`` or ``QTable``, and lets the user designate a
    spectral location column along with its unit.
    """

    template_file = __file__, "./spectral_lines.vue"

    # --- spectral location column ---
    spectral_loc_items = List().tag(sync=True)
    spectral_loc_selected = Unicode().tag(sync=True)
    # True when the selected column already carries valid spectral units,
    # so the unit dropdown can be hidden.
    spectral_loc_has_unit = Bool(False).tag(sync=True)

    # --- spectral unit (shown when spectral_loc_has_unit is False) ---
    spectral_loc_unit_items = List().tag(sync=True)
    spectral_loc_unit_selected = Unicode().tag(sync=True)

    # --- line name column (optional, column index is used if no selection) ---
    linename_items = List().tag(sync=True)
    linename_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_valid:
            return

        input_table = self.input

        self.spectral_loc = SelectPluginComponent(
            self,
            items='spectral_loc_items',
            selected='spectral_loc_selected',
            manual_options=self._guess_spectral_loc_col(),
            filters=[self._filter_numeric_col],
            apply_filters_to_manual_options=True,
        )

        self.spectral_loc_unit = SelectPluginComponent(
            self,
            items='spectral_loc_unit_items',
            selected='spectral_loc_unit_selected',
            manual_options=self._valid_spectral_units(),
        )

        self.linename = SelectPluginComponent(self,
                                              items='linename_items',
                                              selected='linename_selected',
                                              manual_options=self._guess_linename_col())  # noqa

        self._init_col_other(input_table.colnames)

    def _check_is_valid(self):
        if not getattr(self._app.state, 'dev_loaders', False):
            return ('Spectral Lines importer is under active development '
                    '(requires dev_loaders to be enabled).')

        if not isinstance(self.input, (Table, QTable)):
            return 'Input must be an astropy Table or QTable.'

        if len(self.input) == 0:
            return 'Input table is empty.'

        return ''

    @property
    def import_confidence_score(self):
        if self.resolver.__class__.__name__ == 'SpectralLineDatabaseResolver':
            return 2

        if not isinstance(self.input, (Table, QTable)):
            return -1

        def _has_selected_col(attr):
            selected = getattr(self, f'{attr}_selected', None)
            return selected not in ('---', '', None)

        has_spectral_loc = _has_selected_col('spectral_loc')
        has_linename = _has_selected_col('linename')
        if has_spectral_loc and has_linename:
            return 1
        if has_spectral_loc:
            return -1
        return -2

    def _guess_spectral_loc_col(self):
        """
        Guess the spectral location column from common naming conventions.

        First checks whether any column already carries a recognised spectral
        unit (length, frequency, energy, or wavenumber).  If none, falls back
        to pattern-matching against common column names.

        Returns a list of column names ordered so the best guess is first,
        followed by ``'---'`` (no selection) and then the remaining columns.
        If no match is found, ``'---'`` is the first item.
        """
        tab = self.input
        colnames = tab.colnames

        idx = self._guess_col_by_unit_physical_type(tab, colnames, _SPECTRAL_PHYSICAL_TYPES)

        if idx is None:
            idx = self._guess_col_by_name_pattern(colnames, _SPECTRAL_LOC_PATTERNS)

        return self._reorder_cols_with_best_guess(colnames, idx)

    def _guess_linename_col(self):
        """
        Guess the line name column from common naming conventions.

        Returns a list of column names ordered so the best guess is first,
        followed by ``'---'`` (no selection) and then the remaining columns.
        If no match is found, ``'---'`` is the first item, which will result in
        the index of the column being used as the line name.
        """
        input_table = self.input
        colnames = input_table.colnames

        for pattern in _LINENAME_PATTERNS:
            for i, col in enumerate(colnames):
                tokens = re.split(r'[\s_\-\.]+', col.lower().strip())
                if any(pattern.search(t) for t in tokens):
                    return_cols = colnames if i == 0 else (colnames[i:] + colnames[:i])
                    return [return_cols[0]] + ['---'] + list(return_cols[1:])

        return ['---'] + list(colnames)

    def _filter_numeric_col(self, item):
        """
        Filter for ``spectral_loc``: keep only the ``'---'`` sentinel and
        columns whose values can be cast to float.
        """
        label = item.get('label') if isinstance(item, dict) else item
        if label == '---':
            return True
        input_table = self.input
        if not isinstance(input_table, (Table, QTable)):
            return True
        if label not in input_table.colnames:
            return True
        try:
            input_table[label].astype(float)
            return True
        except (AttributeError, ValueError):
            return False

    @staticmethod
    def _valid_spectral_units():
        """Return valid spectral unit choices."""
        return [
            'Angstrom', 'nm', 'um', 'mm', 'm',
            'Hz', 'kHz', 'MHz', 'GHz', 'THz',
            'eV', 'keV',
            '1/cm',
        ]

    @observe('spectral_loc_selected')
    def _on_spectral_loc_selected(self, msg):
        """
        React to a change in the selected spectral location column. Determines
        whether the column already has valid spectral units and sets
        ``spectral_loc_has_unit`` accordingly (controlling the unit dropdown
        visibility), and sets ``import_disabled_msg`` when no valid column is
        selected.
        """
        col = self.spectral_loc_selected

        if col in ('---', '', None):
            # No column selected – hide unit dropdown and block import
            self.spectral_loc_has_unit = True
            self.import_disabled_msg = (
                'Cannot import spectral lines without a Spectral Location column. '
                'Select a column under Definitions.'
            )
            return

        input_table = self.input
        if not isinstance(input_table, (Table, QTable)):
            return

        has_units = False
        if col in input_table.colnames:
            col_data = input_table[col]
            if hasattr(col_data, 'unit') and col_data.unit is not None:
                physical_type = str(u.Unit(col_data.unit).physical_type)
                has_units = physical_type in _SPECTRAL_PHYSICAL_TYPES

        self.spectral_loc_has_unit = has_units
        self.import_disabled_msg = ''

    @property
    def user_api(self):
        expose = ['spectral_loc', 'spectral_loc_unit', 'col_other']
        return ImporterUserApi(self, expose=expose)

    @staticmethod
    def _get_supported_viewers():
        return [
            {'label': 'Table', 'reference': 'table-viewer'}
        ]

    @property
    def output_cols(self):
        """Ordered list of column names that will appear in ``output``."""
        input_table = self.input
        if not isinstance(input_table, (Table, QTable)):
            return []

        cols = []
        if self.spectral_loc_selected not in ('---', '', None):
            cols.append(self.spectral_loc_selected)
        for col in self.col_other_selected:
            if col not in cols:
                cols.append(col)
        return [col for col in cols if col in input_table.colnames]

    @property
    def output(self):
        """
        Build the output ``QTable`` to add to the data collection.
        """
        input_table = self.input
        if not isinstance(input_table, (Table, QTable)):
            return None

        output_table = QTable()

        # Line name column (optional, use column index if not specified)
        if self.linename_selected not in ('---', '', None):
            col_name = self.linename_selected
            if col_name in input_table.colnames:
                output_table[col_name] = input_table[col_name]
                output_table.meta['_jdaviz_loader_linename_col'] = col_name

        # Spectral location column
        if self.spectral_loc_selected not in ('---', '', None):
            col_name = self.spectral_loc_selected
            col_data = input_table[col_name]

            if not self.spectral_loc_has_unit:
                # Column has no (or non-spectral) units – apply the chosen unit
                col_data = col_data.astype(float) * u.Unit(self.spectral_loc_unit_selected)

            output_table[col_name] = col_data
            output_table.meta['_jdaviz_loader_spectral_loc_col'] = col_name

        # Additional columns
        for col in self.col_other_selected:
            if col not in output_table.colnames and col in input_table.colnames:
                output_table[col] = input_table[col]

        return output_table
