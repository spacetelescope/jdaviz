import gc

from astropy import units as u
from astropy.io import fits
from astropy.nddata import StdDevUncertainty
from astropy.wcs import WCS
from functools import cached_property
from glue.core import HubListener
from ipyvuetify import VuetifyTemplate
from specutils import Spectrum
from traitlets import Bool, List, Unicode

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.template_mixin import SelectFileExtensionComponent
from jdaviz.core.unit_conversion_utils import check_if_unit_is_per_solid_angle
from jdaviz.core.custom_units_and_equivs import PIX2, _eqv_flux_to_sb_pixel
from jdaviz.utils import (standardize_metadata,
                          PRIHDR_KEY,
                          SPECTRAL_AXIS_COMP_LABELS,
                          _get_celestial_wcs)

__all__ = ['SpectrumInputExtensionsMixin', '_spectrum_assign_component_type']


def _spectrum_assign_component_type(comp_id, comp, units, physical_type):
    if not len(units) and str(comp_id) == 'flux':
        units = 'ct'
    if units in ('ct', 'pixel'):
        physical_type = units

    if physical_type is None:
        return None
    if str(comp_id) in SPECTRAL_AXIS_COMP_LABELS:
        if physical_type in ('frequency', 'length', 'pixel'):
            # link frequency to wavelength
            return 'spectral_axis'
        return f'spectral_axis:{physical_type}'
    if str(comp_id) == 'uncertainty':
        # don't link with flux columns
        return f'uncertainty:{physical_type}'
    return physical_type


class SpectrumInputExtensionsMixin(VuetifyTemplate, HubListener):
    input_has_extensions = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Unicode().tag(sync=True)

    unc_extension_items = List().tag(sync=True)
    unc_extension_selected = Unicode().tag(sync=True)

    mask_extension_items = List().tag(sync=True)
    mask_extension_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_has_extensions = isinstance(self.input, fits.HDUList)
        if not self.input_has_extensions:
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

    def _cleanup(self):
        for attr in ('extension', 'unc_extension', 'mask_extension'):
            if not hasattr(self, attr):
                continue
            for ext in getattr(self, attr).manual_options:
                try:
                    del ext['obj'].data
                except Exception:  # nosec
                    pass

        if self.input_has_extensions:
            for hdu in self.input:
                try:
                    del hdu.data
                except Exception:  # nosec
                    pass

        gc.collect()

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

    @cached_property
    def spectrum(self):
        if not self.input_has_extensions:
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

        spectral_axis_index = None

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

        if unc_data is not None:
            unc = StdDevUncertainty(unc_data * data_unit)
        else:
            unc = None

        if self.supported_flux_ndim == 2:
            spectral_axis_index = 1
            if data.shape[0] > data.shape[1]:
                data = data.T
                if unc_data is not None:
                    unc_data = unc_data.T
                if mask_data is not None:
                    mask_data = mask_data.T
                wcs = wcs.swapaxes(0, 1)
                self.app.hub.broadcast(SnackbarMessage(
                    f"Transposed input data to {data.shape}",
                    sender=self, color="warning"))

        # Check for data types that have a GWCS stored in ASDF
        telescop = metadata[PRIHDR_KEY].get('TELESCOP', '').lower()
        exptype = metadata[PRIHDR_KEY].get('EXP_TYPE', '').lower()
        # NOTE: Alerted to deprecation of FILETYPE keyword from pipeline on 2022-07-08
        # Kept for posterity in for data processed prior to this date. Use EXP_TYPE instead
        filetype = metadata[PRIHDR_KEY].get('FILETYPE', '').lower()

        # Cubes and 2D data need different checks to see if we want WCS from ASDF
        asdf_3d = (telescop == 'jwst' and ('ifu' in exptype or
                                           'mrs' in exptype or
                                           filetype == '3d ifu cube'))
        asdf_2d = (wcs.world_axis_physical_types == [None, None] or
                   (hasattr(wcs, 'spectral') and wcs.spectral.naxis == 0))

        if (data.ndim == 2 and asdf_2d) or (data.ndim == 3 and asdf_3d):
            if 'ASDF' in hdulist:
                try:
                    from stdatamodels import asdf_in_fits
                    tree = asdf_in_fits.open(hdulist).tree
                    if 'meta' in tree and 'wcs' in tree['meta']:
                        wcs = tree["meta"]["wcs"]
                        if isinstance(wcs, (list, tuple)):
                            wcs = wcs[0]
                        # Check needed for BSUB files, which we want to allow without worrying
                        # about the wavelength solution for now
                        if len(wcs.forward_transform.inputs) == 5:
                            wcs = None
                    else:
                        wcs = None
                except ValueError:
                    wcs = None
            else:
                wcs = None

        try:
            sc = Spectrum(flux=data * data_unit, uncertainty=unc,
                          mask=mask_data, meta=metadata, wcs=wcs,
                          spectral_axis_index=spectral_axis_index)
        except ValueError:
            # In some cases, the above call to Spectrum will fail if no
            # spectral axis is found in the WCS. Even without a spectral axis,
            # the Spectrum.read parser may work, so we try that next.
            # If that also fails, then drop the WCS.
            try:
                sc = Spectrum.read(self._parser.input)
            except Exception:
                # specutils.Spectrum reader would fail, so use no WCS
                sc = Spectrum(
                        flux=data * data_unit, uncertainty=unc,
                        meta=metadata, spectral_axis_index=self.default_spectral_axis_index)
            else:
                # raising an error here will consider this parser as non-valid
                # so that specutils.Spectrum parser is preferred
                raise

        # convert flux and uncertainty to per-pix2 if input is not a surface brightness
        target_flux_unit = None
        target_wave_unit = None
        apply_pix2 = 'FLUX' in self.extension.selected or 'ERR' in self.extension.selected
        flux = sc.flux
        if (apply_pix2 and
                (not check_if_unit_is_per_solid_angle(flux.unit))):
            target_flux_unit = flux.unit / PIX2
        elif check_if_unit_is_per_solid_angle(flux.unit, return_unit=True) == "spaxel":
            # We need to convert spaxel to pixel squared, since spaxel isn't fully supported
            # by astropy
            # This is horribly ugly but just multiplying by u.Unit("spaxel") doesn't work
            target_flux_unit = flux.unit * u.Unit('spaxel') / PIX2
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
        if target_wave_unit == sc.spectral_axis.unit:
            target_wave_unit = None
        if (target_wave_unit is None) and (target_flux_unit is None):  # Nothing to convert
            new_sc = sc
        elif target_flux_unit is None:  # Convert wavelength only
            new_sc = sc.with_spectral_axis_unit(target_wave_unit)
        elif target_wave_unit is None:  # Convert flux only and only PIX2 stuff
            new_sc = sc.with_flux_unit(target_flux_unit, equivalencies=_eqv_flux_to_sb_pixel())
        else:  # Convert both
            new_sc = sc.with_spectral_axis_and_flux_units(
                target_wave_unit, target_flux_unit, flux_equivalencies=_eqv_flux_to_sb_pixel())
        if target_wave_unit is not None:
            new_sc.meta['_orig_spec'] = sc
        # Since we create a new Spectrum, we need to copy over any original WCS info
        # since the WCS will be replaced by a SpectralGWCS object instead of the original
        # astropy.wcs.WCS object.
        # This is needed for the subset tools to work properly.
        if new_sc.flux.ndim == 3 and _get_celestial_wcs(sc.wcs) is not None:
            new_sc.meta['_orig_spatial_wcs'] = _get_celestial_wcs(sc.wcs)

        return new_sc
