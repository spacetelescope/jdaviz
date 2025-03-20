from traitlets import Bool, List, Unicode, observe
from astropy.io import fits
from astropy import units as u
from astropy.wcs import WCS
from specutils import Spectrum1D

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import AutoTextField, SelectPluginComponent
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.utils import standardize_metadata, PRIHDR_KEY


__all__ = ['Spectrum2DImporter']


class SelectExtensionComponent(SelectPluginComponent):
    @property
    def selected_index(self):
        return self.choices.index(self.selected)


@loader_importer_registry('2D Spectrum')
class Spectrum2DImporter(BaseImporterToDataCollection):
    template_file = __file__, "./spectrum2d.vue"

    auto_extract = Bool(True).tag(sync=True)

    ext_data_label_value = Unicode().tag(sync=True)
    ext_data_label_default = Unicode().tag(sync=True)
    ext_data_label_auto = Bool(True).tag(sync=True)
    ext_data_label_invalid_msg = Unicode().tag(sync=True)

    # HDUList-specific options
    input_hdulist = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Unicode().tag(sync=True)
    transpose = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.app.config == 'specviz2d':
            self.data_label_default = '2D Spectrum'

        self.ext_data_label = AutoTextField(self,
                                            'ext_data_label_value',
                                            'ext_data_label_default',
                                            'ext_data_label_auto',
                                            'ext_data_label_invalid_msg')

        self.input_hdulist = not isinstance(self.input, Spectrum1D)
        if self.is_valid and self.input_hdulist:
            extension_options = [f"{i}: {hdu.name} {hdu.shape}"
                                 for i, hdu in enumerate(self.input)
                                 if len(getattr(hdu, 'shape', [])) == 2]
            self.extension = SelectExtensionComponent(self,
                                                      items='extension_items',
                                                      selected='extension_selected',
                                                      manual_options=extension_options)

    @property
    def user_api(self):
        expose = ['auto_extract', 'ext_data_label']
        if isinstance(self.input, fits.HDUList):
            expose += ['extension', 'transpose']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        return ((isinstance(self.input, Spectrum1D)
                 and self.input.flux.ndim == 2) or
                (isinstance(self.input, fits.HDUList)
                 and len([hdu for hdu in self.input if len(getattr(hdu, 'shape', [])) == 2])))  # noqa

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'spectrum-2d-viewer'

    @observe('data_label_value')
    def _data_label_changed(self, msg={}):
        self.ext_data_label_default = f"{self.data_label_value} (auto-ext)"

    @property
    def output(self):
        if not self.input_hdulist:
            return self.input

        hdulist = self.input
        ext = self.extension.selected_index
        data = hdulist[ext].data
        header = hdulist[ext].header
        metadata = standardize_metadata(header)
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist[0].header)
        wcs = WCS(header, hdulist)
        if self.transpose:
            data = data.T
            wcs = wcs.swapaxes(0, 1)

        try:
            data_unit = u.Unit(header['BUNIT'])
        except Exception:
            data_unit = u.count

        # FITS WCS is invalid, so ignore it.
        if wcs.spectral.naxis == 0:
            kw = {}
        else:
            kw = {'wcs': wcs}

        return Spectrum1D(flux=data * data_unit, meta=metadata, **kw)

    def __call__(self):
        # get a copy of both of these before additional data entries changes defaults
        data_label = self.data_label_value
        ext_data_label = self.ext_data_label_value

        super().__call__()

        if not self.auto_extract:
            return

        try:
            spext = self.app.get_tray_item_from_name('spectral-extraction')
            ext = spext._extract_in_new_instance(dataset=data_label,
                                                 add_data=False)
        except Exception:
            raise
            ext = None
            msg = SnackbarMessage(
                "Automatic spectrum extraction failed. See the spectral extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000)
        else:
            msg = SnackbarMessage(
                "The extracted 1D spectrum was generated automatically."
                " See the spectral extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            self.add_to_data_collection(ext, ext_data_label, show_in_viewer=False)
            self.load_into_viewer(ext_data_label, "spectrum-1d-viewer")
