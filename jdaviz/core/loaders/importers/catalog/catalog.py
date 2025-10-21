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

    # for catalogs with source positions in sky coordinates
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

    # for catalogs with source positions in pixel coordinates
    col_x_items = List().tag(sync=True)
    col_x_selected = Unicode().tag(sync=True)
    col_y_items = List().tag(sync=True)
    col_y_selected = Unicode().tag(sync=True)

    # additional (optional) non-position columns to load (e.g. flux, id)
    col_other_items = List().tag(sync=True)
    col_other_selected = List().tag(sync=True)
    col_other_multiselect = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_valid:
            return

        # dropdowns for catalogs with source positions in sky coordinates
        self.col_ra = SelectPluginComponent(self,
                                            items='col_ra_items',
                                            selected='col_ra_selected',
                                            manual_options=self._guess_coord_cols('ra'))
        self.col_dec = SelectPluginComponent(self,
                                             items='col_dec_items',
                                             selected='col_dec_selected',
                                             manual_options=self._guess_coord_cols('dec'))

        self.col_ra_unit = SelectPluginComponent(self,
                                                 items='col_ra_unit_items',
                                                 selected='col_ra_unit_selected',
                                                 manual_options=self._valid_coord_units('ra'))
        self.col_dec_unit = SelectPluginComponent(self,
                                                  items='col_dec_unit_items',
                                                  selected='col_dec_unit_selected',
                                                  manual_options=self._valid_coord_units('dec'))

        # dropdowns for tables with pixel source positions
        self.col_x = SelectPluginComponent(self,
                                           items='col_x_items',
                                           selected='col_x_selected',
                                           manual_options=self._guess_coord_cols('x'))
        self.col_x = SelectPluginComponent(self,
                                           items='col_y_items',
                                           selected='col_y_selected',
                                           manual_options=self._guess_coord_cols('y'))

        # dropdowns for (optional) additional columns
        self.col_other = SelectPluginComponent(self,
                                               items='col_other_items',
                                               selected='col_other_selected',
                                               manual_options=self.input.colnames,
                                               multiselect='col_other_multiselect')

    def _guess_coord_cols(self, col):
        """
        Rough guess at detecting RA/Dec/X/Y columns from input table to determine
        the initial selections for the column select dropdown. This starts
        by checking for the presence of a SkyCoord (if col is 'ra' or 'dec') or
        PixCoord column (if col is 'x' or 'y'), and next checking
        against some common source catalog column names. If no good candidate
        column is found, the initial selection in the drop down for RA/x, dec/y
        columns will be '---' (no selection)
        """

        tab = self.input
        colnames = self.input.colnames

        if colnames is None:
            return

        col_is_sc = [isinstance(tab[colnames[i]], SkyCoord) for i in range(len(colnames))]

        if np.any(col_is_sc):
            idx = np.where(col_is_sc)[0][0]

        else:
            all_column_names = np.array([x.lower() for x in colnames])
            get_idx = lambda x, s, d: np.where(np.isin(x, s))[0][0] if np.any(np.isin(x, s)) else d  # noqa

            if col == 'ra':
                col_possibilities = ['right ascension', 'ra', 'ra_deg', 'radeg',
                                     'radegrees', 'right ascension (degrees)',
                                     'ra_obj', 'raj2000', 'ra2000']
                idx = get_idx(all_column_names, col_possibilities, None)
            elif col == 'dec':
                col_possibilities = ['declination', 'dec', 'dec_deg', 'decdeg',
                                     'decdegrees', 'declination (degrees)',
                                     'dec_obj', 'obj_dec', 'decj2000', 'dec2000']
                idx = get_idx(all_column_names, col_possibilities, None)
            elif col == 'x':
                col_possibilities = ["x", "xpos", "xcentroid", "xcenter",
                                     "xpixel", "xpix", "ximage", "ximg"
                                     "xcoord", "xcoordinate", "sourcex", "xsource"]
                idx = get_idx(all_column_names, col_possibilities, None)
            elif col == 'y':
                col_possibilities = ["y", "ypos", "ycentroid", "ycenter",
                                     "ypixel", "ypix", "yimage", "yimg"
                                     "ycoord", "ycoordinate", "sourcey", "ysource"]
                idx = get_idx(all_column_names, col_possibilities, None)

        # if no good candidate found, default to '---' (no selection) for
        # the default selection.
        if idx is None:
            return ['---'] + colnames
        return colnames if idx == 0 else (colnames[idx:] + colnames[:idx]) + ['---']

    def _valid_coord_units(self, coord):
        """Valid choices for Ra, Dec units."""

        choices = ['deg', 'rad', 'arcmin', 'arcsec']

        if coord == 'ra':
            choices += ['hour minute second']
        elif coord == 'dec':
            choices += ['degree arcmin arcsec']

        return choices

    @observe('col_ra_selected', 'col_dec_selected')
    def _on_ra_or_dec_col_selected(self, msg):
        """
        - Check if the newly selected 'ra' or 'dec' column has units assigned
        already, to set the col_ra_has_unit and col_dec_has_unit traitlets.
        -  Make sure that ra and dec columns are not the same (unless SkyCoord) and
        disable the import button if they are the same.
        - Check if only RA or Dec is selected without the other, and disable import
        in that case.
        """

        ra = self.col_ra_selected
        dec = self.col_dec_selected

        axis = ra if msg['name'] == 'col_ra_selected' else dec

        if axis == '---':
            # no selection, assume 'has units' to disable unit selection dropdown
            if msg['name'] == 'col_ra_selected':
                self.col_ra_has_unit = True
            elif msg['name'] == 'col_dec_selected':
                self.col_dec_has_unit = True
            # disable import if RA is selected but Dec is not (or vice versa)
            if (ra in ['---', ''] or ra is None) != (dec in ['---', ''] or dec is None):
                self.import_disabled = True
            return

        has_units = False

        if isinstance(self.input[axis], SkyCoord):
            has_units = True

        elif hasattr(self.input[axis], 'unit'):
            if self.input[axis].unit is not None:
                has_units = True
                # unit must be an angle unit
                if self.input[axis].unit.physical_type != 'angle':
                    has_units = False

        # set the 'has units' traitlets for ra/dec, which determine if the unit
        # selection dropdowns should be exposed
        if msg['name'] == 'col_ra_selected':
            self.col_ra_has_unit = has_units
        elif msg['name'] == 'col_dec_selected':
            self.col_dec_has_unit = has_units

        # disable import if the same ra and dec columns are selected
        # and they are NOT a SkyCoord column (which contains both RA and Dec),
        if ra == dec and not isinstance(self.input[axis], SkyCoord):
            self.import_disabled = True
        else:
            self.import_disabled = False

        # disable import if RA is selected but Dec is not (or vice versa)
        if (ra in ['---', ''] or ra is None) != (dec in ['---', ''] or dec is None):
            self.import_disabled = True

    @staticmethod
    def _get_supported_viewers():
        return [{'label': 'Image', 'reference': 'imviz-image-viewer'},
                {'label': 'Scatter', 'reference': 'scatter-viewer'},
                {'label': 'Histogram', 'reference': 'histogram-viewer'}]

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
