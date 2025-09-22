from astropy.coordinates import SkyCoord
from astropy.table import Table, QTable
import astropy.units as u
import numpy as np
from traitlets import Bool, List, Unicode, observe

from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import SelectPluginComponent
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.user_api import ImporterUserApi

__all__ = ['CatalogImporter']


@loader_importer_registry("Catalog")
class CatalogImporter(BaseImporterToDataCollection):

    template_file = __file__, "./catalog.vue"

    col_ra_items = List().tag(sync=True)
    col_ra_selected = Unicode().tag(sync=True)

    col_dec_items = List().tag(sync=True)
    col_dec_selected = Unicode().tag(sync=True)

    col_ra_has_unit = Bool().tag(sync=True)  # if input already has units
    col_ra_unit_items = List().tag(sync=True)
    col_ra_unit_selected = Unicode().tag(sync=True)

    col_dec_has_unit = Bool().tag(sync=True)  # if input already has units
    col_dec_unit_items = List().tag(sync=True)
    col_dec_unit_selected = Unicode().tag(sync=True)

    # for non- ra and dec columns that the user wants to load
    col_other_items = List().tag(sync=True)
    col_other_selected = List().tag(sync=True)
    col_other_multiselect = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_valid:
            return

        self.col_ra = SelectPluginComponent(self,
                                            items='col_ra_items',
                                            selected='col_ra_selected',
                                            manual_options=self._guess_ra_dec_cols('ra'))
        self.col_dec = SelectPluginComponent(self,
                                             items='col_dec_items',
                                             selected='col_dec_selected',
                                             manual_options=self._guess_ra_dec_cols('dec'))

        # making these a dropdown for now with some hard-coded unit choices
        # this could either be more flexible with a text input field which
        # is then validated as a unit, or a note to use a quantity table
        # if you want other units
        self.col_ra_unit = SelectPluginComponent(self,
                                                 items='col_ra_unit_items',
                                                 selected='col_ra_unit_selected',
                                                 manual_options=self._valid_coord_units('ra'))
        self.col_dec_unit = SelectPluginComponent(self,
                                                  items='col_dec_unit_items',
                                                  selected='col_dec_unit_selected',
                                                  manual_options=self._valid_coord_units('dec'))

        self.col_other = SelectPluginComponent(self,
                                               items='col_other_items',
                                               selected='col_other_selected',
                                               manual_options=self.input.colnames,
                                               multiselect='col_other_multiselect')

    def _guess_ra_dec_cols(self, col):
        """
        Rough guess at detecting ra, dec columns from input table by checking
        for the presence of a SkyCoord column, and if none exists then checking
        against some common source catalog column names, to determine initial
        selection for the column select dropdown. If no good candidate is found,
        the initial selection in the drop down for ra, dec columns will be the
        0th and 1stcolumns , respectivley.
        """

        tab = self.input
        colnames = self.input.colnames

        if colnames is None:
            return

        col_is_sc = [isinstance(tab[colnames[i]], SkyCoord) for i in range(len(colnames))]

        if np.any(col_is_sc):
            idx = np.where(col_is_sc)[0][0]

        else:
            all_column_names = np.array(x.lower() for x in colnames)
            get_idx = lambda x, s, d: np.where(np.isin(x, s))[0][0] if np.any(np.isin(x, s)) else d  # noqa

            if col == 'ra':
                col_possibilities = ['right ascension', 'ra', 'ra_deg', 'radeg',
                                     'radegrees', 'right ascension (degrees)',
                                     'ra_obj', 'raj2000', 'ra2000']
                idx = get_idx(all_column_names, col_possibilities, 0)
            elif col == 'dec':
                col_possibilities = ['declination', 'dec', 'dec_deg', 'decdeg',
                                     'decdegrees', 'declination (degrees)',
                                     'dec_obj', 'obj_dec', 'decj2000', 'dec2000']
                idx = get_idx(all_column_names, col_possibilities, 1)

        return colnames if idx == 0 else (colnames[idx:] + colnames[:idx])

    def _valid_coord_units(self, coord):
        """Valid choices for Ra, Dec units."""

        choices = ['deg', 'rad', 'arcmin', 'arcsec']

        if coord == 'ra':
            choices += ['hour minute second']
        elif coord == 'dec':
            choices += ['degree arcmin arcsec']

        return choices

    @observe('col_ra_selected')
    def _on_ra_col_selected(self, msg):
        """Check if the selected 'ra' column has units assigned already"""

        ra = self.col_ra_selected
        dec = self.col_dec_selected

        if ra == dec and not isinstance(self.input[ra], SkyCoord):
            self.resolver.import_disabled = True
        else:
            self.resolver.import_disabled = False

        has_units = False
        if hasattr(self.input[ra], 'unit'):
            if self.input[ra].unit is not None:
                has_units = True
                # ra column unit must be an angle unit
                if self.input[ra].unit.physical_type != 'angle':
                    has_units = False

        elif isinstance(self.input[self.col_ra_selected], SkyCoord):
            has_units = True

        if ra == dec and not isinstance(self.input[dec], SkyCoord):
            self.import_disabled = True
        else:
            self.import_disabled = False

        self.col_ra_has_unit = has_units

    @observe('col_dec_selected')
    def _on_dec_col_selected(self, msg):
        """Check if the selected 'dec' column has units assigned already"""

        ra = self.col_ra_selected
        dec = self.col_dec_selected

        if ra == dec:
            self.import_disabled = False

        has_units = False
        if hasattr(self.input[dec], 'unit'):
            if self.input[dec].unit is not None:
                has_units = True
                # dec column unit must be an angle unit
                if self.input[dec].unit.physical_type != 'angle':
                    has_units = False

        elif isinstance(self.input[dec], SkyCoord):
            has_units = True

        if ra == dec and not isinstance(self.input[dec], SkyCoord):
            self.import_disabled = True
        else:
            self.import_disabled = False

        self.col_dec_has_unit = has_units

    @staticmethod
    def _get_supported_viewers():
        return [{'label': 'Image', 'reference': 'imviz-image-viewer'}]

    @property
    def user_api(self):
        expose = ['col_ra', 'col_dec', 'col_other']
        return ImporterUserApi(self, expose=expose)

    @property
    def is_valid(self):
        if self.app.state.catalogs_in_dc is False:
            return False
        if self.app.config not in ('deconfigged', 'imviz', 'mastviz'):
            # NOTE: temporary during deconfig process
            return False
        if isinstance(self.input, (Table, QTable)) and len(self.input):
            return True
        return False

    @property
    def output_cols(self):

        # we will always have RA and Dec
        cols_all = [self.col_ra_selected, self.col_dec_selected] + self.col_other_selected

        return [col for col in set(cols_all) if col in self.input.colnames]

    @property
    def output(self):

        if (self.col_ra_selected not in self.input.colnames) or (self.col_dec_selected not in self.input.colnames):  # noqa
            return

        table = self.input[self.output_cols]
        output_table = QTable()

        # rename RA and Dec columns so that table in data collection always has
        # the same RA, Dec column names internally, add and units if they weren't
        # loaded in with units assigned (QTable)
        ra = None
        dec = None
        if isinstance(self.input[self.col_ra_selected], SkyCoord):
            ra = self.input[self.col_ra_selected].ra
        if isinstance(self.input[self.col_dec_selected], SkyCoord):
            dec = self.input[self.col_dec_selected].dec

        if ra is not None:
            output_table['Right Ascension'] = ra
        else:
            output_table['Right Ascension'] = table[self.col_ra_selected]
            # add units to ra if they weren't loaded in with units assigned
            if not self.col_ra_has_unit:
                output_table['Right Ascension'] *= u.Unit(self.col_ra_unit_selected)
        if dec is not None:
            output_table['Declination'] = dec
        else:
            output_table['Declination'] = table[self.col_dec_selected]
            if not self.col_dec_has_unit:
                output_table['Declination'] *= u.Unit(self.col_dec_unit_selected)

        # add additional columns to output table
        for col in self.output_cols:
            if col not in output_table.colnames + [self.col_ra_selected, self.col_dec_selected]:
                output_table[col] = table[col]

        return output_table
