from astropy.table import QTable
import numpy as np
from traitlets import Unicode, Bool, observe


from jdaviz.core.loaders.importers import BaseImporterToPlugin
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.template_mixin import AutoTextField
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['LineListImporter']


@loader_importer_registry('Line List')
class LineListImporter(BaseImporterToPlugin):
    template_file = __file__, "line_list.vue"

    line_list_label_value = Unicode().tag(sync=True)
    line_list_label_default = Unicode().tag(sync=True)
    line_list_label_auto = Bool(True).tag(sync=True)
    line_list_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, resolver, parser, input, **kwargs):
        super().__init__(app, resolver, parser, input, **kwargs)
        self.line_list_label_default = 'Imported'
        self.line_list_label = AutoTextField(self, 'line_list_label_value',
                                             'line_list_label_default',
                                             'line_list_label_auto',
                                             'line_list_label_invalid_msg')

        self.observe(self._on_label_changed, 'line_list_label_value')
        self._on_label_changed()

    @staticmethod
    def _rest_col_name(table):
        """Name of the rest-value column in ``table`` ('rest' or 'rest wavelength'),
        or None if neither is present."""
        for col_name in ('rest', 'rest wavelength'):
            if col_name in table.colnames:
                return col_name
        return None

    def _check_is_valid(self):
        """
        Checks if the input is a valid QTable with required columns.

        The output of this method is wrapped by the IsValidWrapper
        helper class that converts the string to an inverted boolean,
        i.e. empty string => True, non-empty string => False
        since the string (when filled) carries error information.
        Furthermore, the actual 'is_valid' check is handled by the ValidatorMixin
        that wraps the check in a try/except statement so that individual
        '_check_is_valid' calls no longer need to catch potential failures.
        """
        if not isinstance(self.input, QTable):
            return 'Input must be a QTable.'

        # Check for required columns
        if "linename" not in self.input.colnames:
            return "Input must have a 'linename' column."

        rest_col = self._rest_col_name(self.input)
        if rest_col is None:
            return "Input must have a 'rest' or 'rest wavelength' column."

        # Check that rest column has units
        if not hasattr(self.input[rest_col], 'unit') or self.input[rest_col].unit is None:
            return f"'{rest_col}' column must be an astropy Quantity object."

        # Check for positive rest values
        if np.any(self.input[rest_col] <= 0):
            return 'All rest values must be positive.'

        if not self.has_default_plugin:
            return f'{self.default_plugin} plugin not available.'

        return ''

    @property
    def user_api(self):
        return ImporterUserApi(self, expose=['line_list_label'])

    @property
    def default_plugin(self):
        return 'Line Lists'

    def _on_label_changed(self, msg={}):
        if not len(self.line_list_label_value.strip()):
            self.line_list_label_invalid_msg = 'line_list_label must be provided'
            return

        # Check if the label already exists in loaded lists
        if hasattr(self.app, '_jdaviz_helper'):
            plg = self.app._jdaviz_helper.plugins.get('Line Lists', None)
            if plg is not None and self.line_list_label_value in plg._obj.loaded_lists:
                self.line_list_label_invalid_msg = (
                    f'line list "{self.line_list_label_value}" already exists'
                )
                return

        self.line_list_label_invalid_msg = ''

    @observe('line_list_label_invalid_msg')
    def _set_import_disabled(self, change={}):
        # Set import_disabled_msg based on validation errors
        # Empty msg = enabled, non-empty = disabled
        if not self.is_valid:
            rest_col = self._rest_col_name(self.input) if isinstance(self.input, QTable) else None
            if not isinstance(self.input, QTable):
                self.import_disabled_msg = 'Input must be an astropy QTable'
            elif "linename" not in self.input.colnames:
                self.import_disabled_msg = 'Table must have a "linename" column'
            elif rest_col is None:
                self.import_disabled_msg = 'Table must have a "rest" or "rest wavelength" column'
            elif not hasattr(self.input[rest_col], 'unit') or self.input[rest_col].unit is None:
                self.import_disabled_msg = f'The "{rest_col}" column must have astropy units'
            elif np.any(self.input[rest_col] <= 0):
                self.import_disabled_msg = 'All rest values must be positive'
            else:
                self.import_disabled_msg = 'Line list plugin not available'
        else:
            self.import_disabled_msg = self.line_list_label_invalid_msg

    def __call__(self):
        """Execute the import by calling the plugin's import_line_list method."""
        if self.line_list_label_invalid_msg:
            raise ValueError(self.line_list_label_invalid_msg)

        if not self.is_valid:
            raise ValueError("Invalid line list table - check required columns and units")

        # Prepare the table with the user-specified listname
        table = self.input.copy()

        # the plugin expects the rest-value column to be named 'rest'
        rest_col = self._rest_col_name(table)
        if rest_col is not None and rest_col != 'rest':
            table.rename_column(rest_col, 'rest')

        # Set the listname in metadata so the plugin will use it
        if not hasattr(table, 'meta'):
            table.meta = {}
        table.meta['name'] = self.line_list_label_value

        # Call the plugin's import method with show=False to match preset behavior
        plg = self.app._jdaviz_helper.plugins['Line Lists']
        plg._obj.import_line_list(table, show=False)
