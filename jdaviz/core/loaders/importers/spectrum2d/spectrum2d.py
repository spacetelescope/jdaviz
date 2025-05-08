from traitlets import Bool, List, Unicode, observe
from astropy.io import fits
from astropy import units as u
from astropy.wcs import WCS
from specutils import Spectrum1D

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import AutoTextField, SelectFileExtensionComponent
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.utils import standardize_metadata, PRIHDR_KEY


__all__ = ['Spectrum2DImporter']


def hdu_is_valid(hdu):
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

    # HDUList-specific options
    input_hdulist = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.app.config == 'specviz2d':
            self.data_label_default = '2D Spectrum'

        self.ext_data_label = AutoTextField(self,
                                            'ext_data_label_value',
                                            'ext_data_label_default',
                                            'ext_data_label_auto',
                                            'ext_data_label_invalid_msg')

        self.input_hdulist = isinstance(self.input, fits.HDUList)
        if self.input_hdulist:
            self.extension = SelectFileExtensionComponent(self,
                                                          items='extension_items',
                                                          selected='extension_selected',
                                                          manual_options=self.input,
                                                          filters=[hdu_is_valid])

    @property
    def user_api(self):
        expose = ['auto_extract', 'ext_data_label']
        if self.input_hdulist:
            expose += ['extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        if not ((isinstance(self.input, Spectrum1D)
                 and self.input.flux.ndim == 2) or
                (isinstance(self.input, fits.HDUList)
                 and len([hdu for hdu in self.input if hdu_is_valid(hdu)]))):  # noqa
            return False
        try:
            self.output
        except Exception:
            return False
        return True

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
        hdu = self.extension.selected_hdu
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
