import numpy as np
import warnings
from traitlets import Any, Bool, List, Unicode, observe
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDDataArray

try:
    from stdatamodels.jwst.datamodels import Level1bModel
except ImportError:
    Level1bModel = None

try:
    from roman_datamodels.datamodels import RampModel, ScienceRawModel
except ImportError:
    RampModel = None
    ScienceRawModel = None

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry, viewer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import (AutoTextField,
                                        SelectPluginComponent,
                                        ViewerSelectCreateNew)
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.utils import (standardize_metadata,
                          standardize_roman_metadata,
                          PRIHDR_KEY)


__all__ = ['RampImporter']


def move_group_axis_last(x):
    # swap axes per the conventions of ramp cubes
    # (group axis comes first) and the default in
    # rampviz (group axis expected last)
    return np.transpose(x, (1, 2, 0))


@loader_importer_registry('Ramp')
class RampImporter(BaseImporterToDataCollection):
    template_file = __file__, "./ramp.vue"

    # INTEGRATION SELECT
    integration_items = List().tag(sync=True)
    integration_selected = Unicode().tag(sync=True)

    # DIFF CUBE
    diff_data_label_value = Unicode().tag(sync=True)
    diff_data_label_default = Unicode().tag(sync=True)
    diff_data_label_auto = Bool(True).tag(sync=True)
    diff_data_label_invalid_msg = Unicode().tag(sync=True)

    # DIFF VIEWER
    diff_viewer_create_new_items = List([]).tag(sync=True)
    diff_viewer_create_new_selected = Unicode().tag(sync=True)
    diff_viewer_items = List([]).tag(sync=True)
    diff_viewer_selected = Any([]).tag(sync=True)
    diff_viewer_multiselect = Bool(True).tag(sync=True)

    diff_viewer_label_value = Unicode().tag(sync=True)
    diff_viewer_label_default = Unicode().tag(sync=True)
    diff_viewer_label_auto = Bool(True).tag(sync=True)
    diff_viewer_label_invalid_msg = Unicode().tag(sync=True)

    # EXTRACTED INTEGRATION
    auto_extract = Bool(True).tag(sync=True)
    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)

    ext_data_label_value = Unicode().tag(sync=True)
    ext_data_label_default = Unicode().tag(sync=True)
    ext_data_label_auto = Bool(True).tag(sync=True)
    ext_data_label_invalid_msg = Unicode().tag(sync=True)

    # INTEGRATION VIEWER
    ext_viewer_create_new_items = List([]).tag(sync=True)
    ext_viewer_create_new_selected = Unicode().tag(sync=True)
    ext_viewer_items = List([]).tag(sync=True)
    ext_viewer_selected = Any([]).tag(sync=True)
    ext_viewer_multiselect = Bool(True).tag(sync=True)

    ext_viewer_label_value = Unicode().tag(sync=True)
    ext_viewer_label_default = Unicode().tag(sync=True)
    ext_viewer_label_auto = Bool(True).tag(sync=True)
    ext_viewer_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def viewer_in_registry_names(supported_viewers):
            def viewer_filter(viewer):
                classes = [viewer_registry.members.get(item.get('reference')).get('cls')
                           for item in supported_viewers]
                return isinstance(viewer, tuple(classes))
            return viewer_filter

        if Level1bModel is not None and isinstance(self.input, Level1bModel):
            integration_options = [str(i) for i in range(len(self.input.data))]
        elif isinstance(self.input, fits.HDUList):
            # TODO: this will need to be adjusted if adding extension selection
            integration_options = [str(i) for i in range(len(self.input[1].data))]
        else:
            integration_options = []
        self.integration = SelectPluginComponent(self,
                                                 items='integration_items',
                                                 selected='integration_selected',
                                                 manual_options=integration_options)

        # RAMP GROUP CUBE
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver + '[DATA]'
        elif self.config == 'rampviz':
            # TODO: backwards compaibility for other inputs
            self.data_label_default = self.input.__class__.__name__ + '[DATA]'
        else:
            self.data_label_default = 'Ramp[DATA]'

        if self.config == 'rampviz':
            self.viewer.selected = ['group-viewer']

        # DIFF CUBE
        self.diff_data_label = AutoTextField(self,
                                             'diff_data_label_value',
                                             'diff_data_label_default',
                                             'diff_data_label_auto',
                                             'diff_data_label_invalid_msg')

        self.diff_viewer = ViewerSelectCreateNew(self,
                                                 'diff_viewer_items',
                                                 'diff_viewer_selected',
                                                 'diff_viewer_create_new_items',
                                                 'diff_viewer_create_new_selected',
                                                 'diff_viewer_label_value',
                                                 'diff_viewer_label_default',
                                                 'diff_viewer_label_auto',
                                                 'diff_viewer_label_invalid_msg',
                                                 multiselect='diff_viewer_multiselect',
                                                 default_mode='empty')
        supported_viewers = [{'label': '3D Ramp Diff',
                              'reference': 'rampviz-image-viewer'}]
        if self.app.config == 'deconfigged':
            self.diff_viewer_create_new_items = supported_viewers
        self.diff_viewer.add_filter(viewer_in_registry_names(supported_viewers))
        if self.config == 'rampviz':
            self.diff_viewer.selected = ['diff-viewer']
        else:
            self.diff_viewer.select_default()

        # RAMP INTEGRATION EXTRACTION
        self.function = SelectPluginComponent(
            self,
            items='function_items',
            selected='function_selected',
            manual_options=['Mean', 'Median', 'Min', 'Max', 'Sum']
        )
        # the default collapse function in the profile viewer is "sum",
        # but for ramp files, "median" is more useful:
        self.function.selected = 'Median'

        self.ext_data_label = AutoTextField(self,
                                            'ext_data_label_value',
                                            'ext_data_label_default',
                                            'ext_data_label_auto',
                                            'ext_data_label_invalid_msg')

        self.ext_viewer = ViewerSelectCreateNew(self,
                                                'ext_viewer_items',
                                                'ext_viewer_selected',
                                                'ext_viewer_create_new_items',
                                                'ext_viewer_create_new_selected',
                                                'ext_viewer_label_value',
                                                'ext_viewer_label_default',
                                                'ext_viewer_label_auto',
                                                'ext_viewer_label_invalid_msg',
                                                multiselect='ext_viewer_multiselect',  # noqa
                                                default_mode='empty')
        supported_viewers = [{'label': 'Ramp Integration',
                              'reference': 'rampviz-profile-viewer'}]
        if self.app.config == 'deconfigged':
            self.ext_viewer_create_new_items = supported_viewers
        self.ext_viewer.add_filter(viewer_in_registry_names(supported_viewers))
        if self.config == 'rampviz':
            self.ext_viewer.selected = ['integration-viewer']
        else:
            self.ext_viewer.select_default()

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '3D Ramp', 'reference': 'rampviz-image-viewer'}]

    @property
    def user_api(self):
        expose = ['diff_data_label', 'diff_viewer',
                  'auto_extract', 'function', 'ext_data_label', 'ext_viewer']
        if len(self.integration_items) > 0:
            expose += ['integration']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'rampviz'):
            # NOTE: temporary during deconfig process
            return False

        # Filter out None types from isinstance check (optional dependencies)
        valid_types = tuple(
            t for t in (Level1bModel,
                        RampModel, ScienceRawModel,
                        fits.HDUList,
                        np.ndarray)
            if t is not None
        )
        if not isinstance(self.input, valid_types):
            return False

        if isinstance(self.input, fits.HDUList) and self.input[1].header['NAXIS'] != 4:
            return False

        try:
            self.output
        except Exception:
            return False
        return True

    @observe('data_label_value', 'function_selected')
    def _data_label_changed(self, msg={}):
        base = self.data_label_value.strip('[DATA]').strip()
        self.diff_data_label_default = f"{base}[DIFF]"
        self.ext_data_label_default = f"{base} ({self.function_selected.lower()})"

    @property
    def output(self):
        integration = 0  # TODO: integration/extension select

        # NOTE: each if-statement should provide meta and ramp_data
        # if there is specific handling for flux_unit, ramp_data should
        # be a quantity with the unit attached
        if Level1bModel is not None and isinstance(self.input, Level1bModel):
            meta = standardize_metadata({
                key: value for key, value in self.input.to_flat_dict(
                    include_arrays=False)
                .items()
                if key.startswith('meta')
            })

            ramp_data = self.input.data[integration]
        elif (RampModel is not None and ScienceRawModel is not None
              and isinstance(self.input, (RampModel, ScienceRawModel))):
            meta = standardize_roman_metadata(self.input)
            ramp_data = self.input.data
        elif isinstance(self.input, fits.HDUList):
            # TODO: extension selection (didn't exist previously)
            hdulist = self.input
            hdu = hdulist[1]  # extension containing the ramp

            meta = standardize_metadata(hdu.header)
            if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
                meta[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

            if 'BUNIT' in hdu.header:
                try:
                    flux_unit = u.Unit(hdu.header['BUNIT'])
                except Exception:
                    warnings.warn("Invalid BUNIT, using DN as data unit", UserWarning)
                    flux_unit = u.DN
            else:
                warnings.warn("Invalid BUNIT, using DN as data unit", UserWarning)
                flux_unit = u.DN

            # index the ramp array by the integration to load. returns all groups and pixels.
            # cast from uint16 to integers:
            ramp_data = hdu.data[integration].astype(int) * flux_unit
        elif isinstance(self.input, np.ndarray):
            meta = {}
            ramp_data = self.input
        else:
            raise NotImplementedError(f"Unsupported input for RampImporter: {type(self.input)}")

        # last axis is the group axis, first two are spatial axes:
        diff_data = np.vstack([
            # begin with a group of zeros, so
            # that `diff_data.ndim == data.ndim`
            np.zeros((1, *ramp_data[0].shape)),
            np.diff(ramp_data, axis=0)
        ])

        # if the ramp cube has no units, assume DN:
        flux_unit = getattr(ramp_data, 'unit', u.DN)

        ramp_cube = NDDataArray(move_group_axis_last(ramp_data),
                                unit=flux_unit,
                                meta=meta)
        diff_cube = NDDataArray(move_group_axis_last(diff_data),
                                unit=flux_unit,
                                meta=meta)

        return ramp_cube, diff_cube

    def __call__(self):
        # get a copy of all requested data-labels before additional data entries changes defaults
        data_label = self.data_label_value
        diff_data_label = self.diff_data_label_value
        ext_data_label = self.ext_data_label_value

        ramp_cube, diff_cube = self.output

        ramp_cube.meta['_ramp_type'] = 'group'
        self.add_to_data_collection(ramp_cube,
                                    data_label,
                                    viewer_select=self.viewer)
        # TODO: this will need to be removed when removing restriction of a single flux cube
        self.app._jdaviz_helper._loaded_flux_cube = self.app.data_collection[data_label]
        if not hasattr(self.app._jdaviz_helper, 'cube_cache'):
            self.app._jdaviz_helper.cube_cache = {}
        self.app._jdaviz_helper.cube_cache[data_label] = ramp_cube

        diff_cube.meta['_ramp_type'] = 'diff'
        self.add_to_data_collection(diff_cube,
                                    diff_data_label,
                                    viewer_select=self.diff_viewer)
        self.app._jdaviz_helper.cube_cache[diff_data_label] = diff_cube

        if not self.auto_extract:
            return

        try:
            rext = self.app.get_tray_item_from_name('ramp-extraction')
            ext = rext._extract_in_new_instance(dataset=data_label,
                                                function=self.function.selected,
                                                auto_update=False,
                                                add_data=False)
            # we'll add the data manually instead of through add_results_from_plugin
            # but still want to preserve the plugin metadata
            ext.meta['plugin'] = rext._plugin_name
        except Exception:
            ext = None
            msg = SnackbarMessage(
                "Automatic ramp extraction failed. See the ramp extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000)
        else:
            msg = SnackbarMessage(
                "The extracted 1D ramp integration was generated automatically."
                " See the ramp extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            ext_viewer_selected = self.ext_viewer.create_new.selected if self.ext_viewer.create_new.selected != '' else self.ext_viewer.selected  # noqa
            self.app._jdaviz_helper.load(ext, format='Ramp Integration',
                                         data_label=ext_data_label,
                                         viewer=ext_viewer_selected)
