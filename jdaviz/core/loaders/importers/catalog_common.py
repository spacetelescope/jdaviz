import re

import astropy.units as u

from traitlets import Bool, List

from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import SelectPluginComponent

__all__ = ['BaseCatalogImporter']


class BaseCatalogImporter(BaseImporterToDataCollection):
    """
    Shared logic for importers that load tabular catalogs (source catalogs,
    spectral line lists, etc.) and need to let the user assign table columns
    to specific roles (e.g. RA/Dec, a spectral location, a source ID), with
    reasonable auto-detected defaults.

    Subclasses remain responsible for creating their own role-specific
    ``SelectPluginComponent`` instances (``col_ra``, ``col_x``,
    ``spectral_loc``, etc.), but can use the guessing helpers below to build
    the ``manual_options`` for those components, and can use
    ``_init_col_other`` for the "additional columns" selector that is common
    to all of these importers.
    """

    # additional (optional) columns to load alongside the role-specific ones.
    # shared across all catalog-style importers.
    col_other_items = List().tag(sync=True)
    col_other_selected = List().tag(sync=True)
    col_other_multiselect = Bool(True).tag(sync=True)

    def _init_col_other(self, colnames):
        """
        Create the shared 'additional columns' multiselect component from
        ``colnames``. Call this once column names for the current input are
        known (i.e. after any extension/table selection is resolved).
        """
        self.col_other = SelectPluginComponent(
            self,
            items='col_other_items',
            selected='col_other_selected',
            manual_options=list(colnames),
            multiselect='col_other_multiselect',
        )

    def _update_col_items_and_selected(self, base_attr, options, select_first=True):
        """
        Update a column-selection component's items/selected traitlets in
        place (e.g. in response to a change of input table/extension).
        """
        items_attr = f'{base_attr}_items'
        selected_attr = f'{base_attr}_selected'

        setattr(self, items_attr, [{'label': item} for item in options])
        self.send_state(items_attr)

        if select_first:
            setattr(self, selected_attr, options[0] if options else None)
        else:
            setattr(self, selected_attr, [])
        self.send_state(selected_attr)

    @staticmethod
    def _reorder_cols_with_best_guess(colnames, idx):
        """
        Reorder ``colnames`` so the best-guess column (at ``idx``) appears
        first, followed by the ``'---'`` (no selection) sentinel placed
        second (so it doesn't require scrolling past every column to reach
        it), followed by the remaining columns in their original relative
        order (wrapping around).

        If ``idx`` is None (no guess found), ``'---'`` is placed first
        instead, so no column is auto-selected.
        """
        colnames = list(colnames)
        if idx is None:
            return ['---'] + colnames
        return_cols = colnames if idx == 0 else (colnames[idx:] + colnames[:idx])
        return [return_cols[0]] + ['---'] + return_cols[1:]

    @staticmethod
    def _guess_col_by_name_pattern(colnames, patterns, exclude_words=None):
        """
        Find the index of the first column in ``colnames`` whose name
        (split into tokens on whitespace/underscore/hyphen/period) matches
        one of ``patterns``. Patterns are tried in priority order; all
        columns are checked against a given pattern before moving to the
        next pattern.

        Parameters
        ----------
        colnames : list of str
        patterns : compiled regex, or list of compiled regex
            Tried in priority order.
        exclude_words : iterable of str, optional
            Tokens which should never count as a match (e.g. generic words
            that coincidentally match a pattern).

        Returns
        -------
        int or None
        """
        if not isinstance(patterns, (list, tuple)):
            patterns = [patterns]
        exclude_words = set(exclude_words or [])

        for pattern in patterns:
            for i, col in enumerate(colnames):
                tokens = re.split(r'[\s_\-\.]+', str(col).lower().strip())
                if any(token in exclude_words for token in tokens):
                    continue
                if any(pattern.search(t) for t in tokens):
                    return i
        return None

    @staticmethod
    def _guess_col_by_unit_physical_type(input_table, colnames, physical_types):
        """
        Find the index of the first column in ``colnames`` whose astropy
        unit has a physical type in ``physical_types`` (e.g. ``'angle'`` for
        RA/Dec, or ``'length'``/``'frequency'``/``'energy'``/``'wavenumber'``
        for a spectral axis).
        """
        for i, col in enumerate(colnames):
            col_data = input_table[col]
            unit = getattr(col_data, 'unit', None)
            if unit is not None and str(u.Unit(unit).physical_type) in physical_types:
                return i
        return None

    @staticmethod
    def _guess_col_by_instance_type(input_table, colnames, instance_type, per_row=False):
        """
        Find the index of the first column in ``colnames`` whose data (or,
        if ``per_row``, whose first element) is an instance of
        ``instance_type`` (e.g. a ``SkyCoord`` or ``PixCoord`` column).
        """
        for i, col in enumerate(colnames):
            col_data = input_table[col]
            candidate = col_data[0] if per_row else col_data
            if isinstance(candidate, instance_type):
                return i
        return None
