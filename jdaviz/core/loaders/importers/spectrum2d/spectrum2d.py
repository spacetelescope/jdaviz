from traitlets import Any, Bool, List, Unicode, observe
from astropy.io import fits
from astropy import units as u
from astropy.wcs import WCS
from specutils import Spectrum

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry, viewer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           _spectrum_assign_component_type)
from jdaviz.core.template_mixin import (AutoTextField,
                                        SelectFileExtensionComponent,
                                        ViewerSelectCreateNew)
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.utils import standardize_metadata, PRIHDR_KEY


__all__ = ['Spectrum2DImporter']


def hdu_is_valid(item):
    """
    Check if the HDU is valid to be imported as a 2D Spectrum.

    Parameters
    ----------
    hdu : `astropy.io.fits.hdu.base.HDUBase`
        The HDU to check.

    Returns
    -------
    bool
        True if the HDU is a valid light curve HDU, False otherwise.
    """
    hdu = item.get('obj')
    return (len(getattr(hdu, 'shape', [])) == 2
            and ('DISPAXIS' in hdu.header
                 or hdu.header.get('CTYPE1', '') == 'WAVE'
                 or hdu.header.get('EXTNAME', '') == 'FLUX'))


@loader_importer_registry('2D Spectrum')
class Spectrum2DImporter(BaseImporterToDataCollection):
    template_file = __file__, "./spectrum2d.vue"
    parser_preference = ['fits', 'specutils.Spectrum']

    auto_extract = Bool(True).tag(sync=True)

    ext_data_label_value = Unicode().tag(sync=True)
    ext_data_label_default = Unicode().tag(sync=True)
    ext_data_label_auto = Bool(True).tag(sync=True)
    ext_data_label_invalid_msg = Unicode().tag(sync=True)

    ext_viewer_create_new_items = List([]).tag(sync=True)
    ext_viewer_create_new_selected = Unicode().tag(sync=True)

    ext_viewer_items = List([]).tag(sync=True)
    ext_viewer_selected = Any([]).tag(sync=True)
    ext_viewer_multiselect = Bool(True).tag(sync=True)

    ext_viewer_label_value = Unicode().tag(sync=True)
    ext_viewer_label_default = Unicode().tag(sync=True)
    ext_viewer_label_auto = Bool(True).tag(sync=True)
    ext_viewer_label_invalid_msg = Unicode().tag(sync=True)

    # HDUList-specific options
    input_hdulist = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz2d':
            self.data_label_default = '2D Spectrum'

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
                                                multiselect='ext_viewer_multiselect',
                                                default_mode='empty')
        supported_viewers = [{'label': '1D Spectrum',
                              'reference': 'spectrum-1d-viewer'}]
        if self.app.config == 'deconfigged':
            self.ext_viewer_create_new_items = supported_viewers

        def viewer_in_registry_names(viewer):
            classes = [viewer_registry.members.get(item.get('reference')).get('cls')
                       for item in supported_viewers]
            return isinstance(viewer, tuple(classes))
        self.ext_viewer.add_filter(viewer_in_registry_names)
        self.ext_viewer.select_default()

        self.input_hdulist = isinstance(self.input, fits.HDUList)
        if self.input_hdulist:
            ext_options = [{'label': f"{index}: {hdu.name}",
                            'name': hdu.name,
                            'ver': hdu.ver,
                            'name_ver': f"{hdu.name},{hdu.ver}",
                            'index': index,
                            'obj': hdu}
                           for index, hdu in enumerate(self.input)]
            self.extension = SelectFileExtensionComponent(self,
                                                          items='extension_items',
                                                          selected='extension_selected',
                                                          manual_options=ext_options,
                                                          filters=[hdu_is_valid])

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '2D Spectrum', 'reference': 'spectrum-2d-viewer'}]

    @property
    def user_api(self):
        expose = ['auto_extract', 'ext_data_label', 'ext_viewer']
        if self.input_hdulist:
            expose += ['extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        if not ((isinstance(self.input, Spectrum)
                 and self.input.flux.ndim == 2) or
                (isinstance(self.input, fits.HDUList)
                 and len([hdu for hdu in self.input if hdu_is_valid({'obj': hdu})]))):  # noqa
            return False
        try:
            self.output
        except Exception:
            return False
        return True

    @observe('data_label_value')
    def _data_label_changed(self, msg={}):
        self.ext_data_label_default = f"{self.data_label_value} (auto-ext)"

    @property
    def output(self):
        if not self.input_hdulist:
            return self.input

        hdulist = self.input
        hdu = self.extension.selected_obj
        data = hdu.data
        header = hdu.header
        metadata = standardize_metadata(header)
        if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
            metadata[PRIHDR_KEY] = standardize_metadata(hdulist[0].header)
        wcs = WCS(header, hdulist)
        if data.shape[0] > data.shape[1]:
            data = data.T
            self.app.hub.broadcast(SnackbarMessage(
                f"Transposed input data to {data.shape}",
                sender=self, color="warning"))
        if wcs.array_shape[0] > wcs.array_shape[1]:
            wcs = wcs.swapaxes(0, 1)

        try:
            data_unit = u.Unit(header['BUNIT'])
        except Exception:
            data_unit = u.count

        try:
            if wcs.world_axis_physical_types == [None, None]:
                # This may be a JWST file with WCS stored in ASDF
                if 'ASDF' in hdulist:
                    try:
                        from stdatamodels import asdf_in_fits
                        tree = asdf_in_fits.open(hdulist).tree
                        if 'meta' in tree and 'wcs' in tree['meta']:
                            wcs = tree["meta"]["wcs"][0]
                        else:
                            wcs = None
                    except ValueError:
                        wcs = None
                else:
                    wcs = None
            return Spectrum(flux=data * data_unit, meta=metadata, wcs=wcs, spectral_axis_index=1)
        except ValueError:
            # In some cases, the above call to Spectrum will fail if no
            # spectral axis is found in the WCS. Even without a spectral axis,
            # the Spectrum.read parser may work, so we try that next.
            # If that also fails, then drop the WCS.
            try:
                Spectrum.read(self._resolver())
            except Exception:
                # specutils.Spectrum > Spectrum2D would fail, so use no WCS
                return Spectrum(flux=data * data_unit, meta=metadata)
            else:
                # raising an error here will allow using specutils.Spectrum > Spectrum2D
                raise

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return _spectrum_assign_component_type(comp_id, comp, units, physical_type)

    def __call__(self):
        # get a copy of both of these before additional data entries changes defaults
        data_label = self.data_label_value
        ext_data_label = self.ext_data_label_value

        super().__call__()

        if not self.auto_extract:
            return

        try:
            spext = self.app.get_tray_item_from_name('spectral-extraction-2d')
            ext = spext._extract_in_new_instance(dataset=data_label,
                                                 add_data=False)
        except Exception as e:
            ext = None
            msg = SnackbarMessage(
                "Automatic spectrum extraction failed. See the spectral extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000, traceback=e)
        else:
            msg = SnackbarMessage(
                "The extracted 1D spectrum was generated automatically."
                " See the spectral extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            self.add_to_data_collection(ext, ext_data_label, viewer_select=self.ext_viewer)
