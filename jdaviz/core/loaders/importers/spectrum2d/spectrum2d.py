from astropy import units as u
from astropy.io import fits
from astropy.nddata import StdDevUncertainty
from astropy.wcs import WCS
from functools import cached_property
from glue.core import HubListener
from ipyvuetify import VuetifyTemplate
from specutils import Spectrum
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry, viewer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           _spectrum_assign_component_type)
from jdaviz.core.template_mixin import (AutoTextField,
                                        ViewerSelectCreateNew,
                                        SelectFileExtensionComponent)
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.utils import standardize_metadata, PRIHDR_KEY

__all__ = ['Spectrum2DImporter', 'HDUListToSpectrumMixin']


class HDUListToSpectrumMixin(VuetifyTemplate, HubListener):
    input_hdulist = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Unicode().tag(sync=True)

    unc_extension_items = List().tag(sync=True)
    unc_extension_selected = Unicode().tag(sync=True)

    mask_extension_items = List().tag(sync=True)
    mask_extension_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_hdulist = isinstance(self.input, fits.HDUList)
        if not self.input_hdulist:
            return
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
                                                      filters=[self.hdu_is_valid_flux])
        self.unc_extension = SelectFileExtensionComponent(self,
                                                          items='unc_extension_items',
                                                          selected='unc_extension_selected',
                                                          manual_options=ext_options,
                                                          filters=[self.hdu_is_valid_unc])
        self.mask_extension = SelectFileExtensionComponent(self,
                                                           items='mask_extension_items',
                                                           selected='mask_extension_selected',
                                                           manual_options=ext_options,
                                                           filters=[self.hdu_is_valid_mask])

    @property
    def supported_flux_ndim(self):
        return 2

    @property
    def default_spectral_axis_index(self):
        return 1

    def hdu_is_valid_flux(self, item):
        """
        Check if the HDU is valid to be imported for the flux in a Spectrum.

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
        return (len(getattr(hdu, 'shape', [])) == self.supported_flux_ndim
                and ('DISPAXIS' in hdu.header
                     or hdu.header.get('CTYPE1', '') == 'WAVE'
                     or hdu.header.get('EXTNAME', '') == 'FLUX'))

    def hdu_is_valid_unc(self, item):
        """
        Check if the HDU is valid to be imported for the uncertainty in a Spectrum.

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
        return (len(getattr(hdu, 'shape', [])) == self.supported_flux_ndim
                and hdu.header.get('EXTNAME', '') == 'ERR')

    def hdu_is_valid_mask(self, item):
        """
        Check if the HDU is valid to be imported for the mask in a Spectrum.

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
        return (len(getattr(hdu, 'shape', [])) == self.supported_flux_ndim
                and hdu.header.get('EXTNAME', '') == 'MASK')

    def _get_celestial_wcs(self, wcs):
        """ If `wcs` has a celestial component return that, otherwise return None """
        return wcs.celestial if hasattr(wcs, 'celestial') else None

    @cached_property
    def spectrum(self):
        if not self.input_hdulist:
            if not isinstance(self.input, Spectrum):
                raise TypeError("Input must be a specutils.Spectrum if not a FITS HDUList")
            return self.input
        hdulist = self.input
        hdu = self.extension.selected_obj
        data = hdu.data
        header = hdu.header
        metadata = standardize_metadata(header)
        if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
            metadata[PRIHDR_KEY] = standardize_metadata(hdulist[0].header)
        wcs = WCS(header, hdulist)

        # Try to get the spectral axis unit from the FITS header if possible
        target_wave_unit = None
        if target_wave_unit is None and hdulist is not None:
            found_target = False
            for ext in ('SCI', 'FLUX', 'PRIMARY', 'DATA'):  # In priority order
                if found_target:
                    break
                if ext not in hdulist:
                    continue
                hdr = hdulist[ext].header
                # The WCS could be swapped or unswapped.
                for cunit_num in (3, 1):
                    cunit_key = f"CUNIT{cunit_num}"
                    ctype_key = f"CTYPE{cunit_num}"
                    if cunit_key in hdr and 'WAV' in hdr[ctype_key]:
                        target_wave_unit = u.Unit(hdr[cunit_key])
                        found_target = True
                        break

        # Default to meters if no unit found
        if target_wave_unit is None:
            target_wave_unit = u.Unit('m')

        try:
            data_unit = u.Unit(header['BUNIT'])
        except Exception:
            data_unit = u.count

        if self.unc_extension.selected != '':
            unc_hdu = self.unc_extension.selected_obj
            unc_data = unc_hdu.data
        else:
            unc_data = None
        if self.mask_extension.selected != '':
            mask_hdu = self.mask_extension.selected_obj
            mask_data = mask_hdu.data
        else:
            mask_data = None

        if self.supported_flux_ndim == 2 and data.shape[0] > data.shape[1]:
            data = data.T
            if unc_data is not None:
                unc_data = unc_data.T
            if mask_data is not None:
                mask_data = mask_data.T
            self.app.hub.broadcast(SnackbarMessage(
                f"Transposed input data to {data.shape}",
                sender=self, color="warning"))
        if wcs.array_shape[0] > wcs.array_shape[1]:
            wcs = wcs.swapaxes(0, 1)

        if unc_data is not None:
            unc = StdDevUncertainty(unc_data * data_unit)
        else:
            unc = None

        sc = Spectrum(flux=data * data_unit, uncertainty=unc,
                      mask=mask_data, meta=metadata, wcs=wcs,
                      spectral_axis_index=self.default_spectral_axis_index)

        # Keep original spectrum and spatial WCS around for later use
        metadata['_orig_spec'] = sc  # Need this for later
        metadata['_orig_spatial_wcs'] = self._get_celestial_wcs(sc.wcs)

        try:
            if wcs.world_axis_physical_types == [None, None]:
                # This may be a JWST file with WCS stored in ASDF
                if 'ASDF' in hdulist:
                    try:
                        from stdatamodels import asdf_in_fits
                        tree = asdf_in_fits.open(hdulist).tree
                        if 'meta' in tree and 'wcs' in tree['meta']:
                            wcs = tree["meta"]["wcs"]
                            if isinstance(wcs, list):
                                wcs = wcs[0]
                        else:
                            wcs = None
                    except ValueError:
                        wcs = None
                else:
                    wcs = None
            return Spectrum(
                spectral_axis=sc.spectral_axis.to(target_wave_unit, equivalencies=u.spectral()),
                flux=data * data_unit, uncertainty=unc,
                mask=mask_data, meta=metadata,
                spectral_axis_index=self.default_spectral_axis_index)
        except ValueError:
            # In some cases, the above call to Spectrum will fail if no
            # spectral axis is found in the WCS. Even without a spectral axis,
            # the Spectrum.read parser may work, so we try that next.
            # If that also fails, then drop the WCS.
            try:
                Spectrum.read(self._resolver())
            except Exception:
                # specutils.Spectrum reader would fail, so use no WCS
                return Spectrum(
                    spectral_axis=sc.spectral_axis.to(target_wave_unit, equivalencies=u.spectral()),
                    flux=data * data_unit, uncertainty=unc,
                    meta=metadata)
            else:
                # raising an error here will consider this parser as non-valid
                # so that specutils.Spectrum parser is preferred
                raise


@loader_importer_registry('2D Spectrum')
class Spectrum2DImporter(BaseImporterToDataCollection, HDUListToSpectrumMixin):
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

    input_hdulist = Bool(False).tag(sync=True)

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

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '2D Spectrum', 'reference': 'spectrum-2d-viewer'}]

    @property
    def user_api(self):
        expose = ['auto_extract', 'ext_data_label', 'ext_viewer']
        if self.input_hdulist:
            expose += ['extension', 'unc_extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        try:
            sp = self.spectrum
        except Exception:
            return False
        if sp.flux.ndim != 2:
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
        return self.spectrum

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
                "Automatic spectrum extraction failed. See the 2D spectral extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000, traceback=e)
        else:
            msg = SnackbarMessage(
                "The extracted 1D spectrum was generated automatically."
                " See the 2D spectral extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            self.add_to_data_collection(ext, ext_data_label, viewer_select=self.ext_viewer)
