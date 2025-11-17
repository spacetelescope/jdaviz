import numpy as np

from asdf import AsdfFile
from astropy import units as u
from astropy.io import fits
from astropy.nddata import StdDevUncertainty
from astropy.wcs import WCS
from functools import cached_property
from glue.core import HubListener
from ipyvuetify import VuetifyTemplate
from specutils import Spectrum
from traitlets import List, Unicode, observe

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
    if not len(units) and comp_id == 'flux':
        units = 'ct'
    if units in ('ct', 'pixel'):
        physical_type = units

    if physical_type is None:
        return None
    if comp_id in SPECTRAL_AXIS_COMP_LABELS:
        if physical_type in ('frequency', 'length', 'pixel'):
            # link frequency to wavelength
            return 'spectral_axis'
        return f'spectral_axis:{physical_type}'
    if comp_id == 'uncertainty':
        # don't link with flux columns
        return f'uncertainty:{physical_type}'
    return physical_type


class SpectrumInputExtensionsMixin(VuetifyTemplate, HubListener):
    input_type = Unicode().tag(sync=True)

    extension_items = List().tag(sync=True)
    extension_selected = Unicode().tag(sync=True)

    unc_extension_items = List().tag(sync=True)
    unc_extension_selected = Unicode().tag(sync=True)

    mask_extension_items = List().tag(sync=True)
    mask_extension_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.input, fits.HDUList):
            self.input_type = 'fits:hdulist'
            ext_options = [{'label': f"{index}: {hdu.name}",
                            'name': hdu.name,
                            'ver': hdu.ver,
                            'name_ver': f"{hdu.name},{hdu.ver}",
                            'index': index,
                            'obj': hdu}
                           for index, hdu in enumerate(self.input)
                           ]

        elif isinstance(self.input, AsdfFile) and 'roman' in self.input:
            self.input_type = 'asdf:roman'
            ext_options = [{'label': f"{ind}: {k}",
                            'name': k,
                            'name_ver': k,
                            'index': ind,
                            'obj': ext}
                           for ind, (k, ext) in enumerate(self.input['roman']['data'].items())
                           ]

        elif isinstance(self.input, Spectrum):
            self.input_type = 'specutils:spectrum'
            ext_options = [{'label': f'spectrum.{attr}',
                            'name': attr,
                            'name_ver': None,
                            'index': ind+1,  # to match indexing of HDUList for load_data defaults
                            'obj': self.input}
                           for ind, attr in enumerate(('flux', 'uncertainty', 'mask'))
                           if getattr(self.input, attr, None) is not None
                           ]
        else:
            raise TypeError("Input type not supported for SpectrumInputExtensionsMixin")

        ext_options += [{'label': 'None',
                         'name': '',
                         'name_ver': '',
                         'index': len(ext_options),
                         'obj': None}]

        self.extension = SelectFileExtensionComponent(self,
                                                      items='extension_items',
                                                      selected='extension_selected',
                                                      manual_options=ext_options,
                                                      filters=[self.is_valid_flux])
        self.unc_extension = SelectFileExtensionComponent(self,
                                                          items='unc_extension_items',
                                                          selected='unc_extension_selected',
                                                          manual_options=ext_options,
                                                          filters=[self.is_valid_unc])
        self.mask_extension = SelectFileExtensionComponent(self,
                                                           items='mask_extension_items',
                                                           selected='mask_extension_selected',
                                                           manual_options=ext_options,
                                                           filters=[self.is_valid_mask])

    def _cleanup(self):
        for attr in ('extension', 'unc_extension', 'mask_extension'):
            if not hasattr(self, attr):
                continue

            for ext in getattr(self, attr).manual_options:
                try:
                    del ext['obj'].data
                except Exception:  # nosec
                    pass

        if self.input_type == 'fits:hdulist':
            for hdu in self.input:
                try:
                    del hdu.data
                except Exception:  # nosec
                    pass

        self._clear_cache('spectrum')

    @property
    def supported_flux_ndim(self):
        return 2

    @property
    def default_spectral_axis_index(self):
        return 1

    def is_valid_flux(self, item):
        if self.input_type == 'fits:hdulist':
            return self.hdu_is_valid_flux(item)
        if self.input_type == 'asdf:roman':
            return self.asdf_roman_is_valid_flux(item)
        if self.input_type == 'specutils:spectrum':
            return item.get('name') == 'flux'
        raise NotImplementedError("Unknown input type")

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
        if item.get('label') == 'None':
            # require selection for flux
            return False
        hdu = item.get('obj')
        return (len(getattr(hdu, 'shape', [])) == self.supported_flux_ndim
                and ('DISPAXIS' in hdu.header
                     or hdu.header.get('CTYPE1', '') == 'WAVE'
                     or hdu.header.get('EXTNAME', '') == 'FLUX'))

    def asdf_roman_is_valid_flux(self, item):
        if item.get('label') == 'None':
            # require selection for flux
            return False
        if self.supported_flux_ndim == 1:
            return all(k in item.get('obj').keys() for k in ["wl", "flux"])
        elif self.supported_flux_ndim == 2:
            return all(k in item.get('obj').keys() for k in ["spectrum", "wavelength"])
        else:
            raise NotImplementedError("Only 1D and 2D spectra are supported for ASDF Roman data")

    def is_valid_unc(self, item):
        if item.get('label') == 'None':
            return True
        if self.input_type == 'fits:hdulist':
            return self.hdu_is_valid_unc(item)
        if self.input_type == 'asdf:roman':
            return self.asdf_roman_is_valid_unc(item)
        if self.input_type == 'specutils:spectrum':
            return item.get('name') == 'uncertainty'
        raise NotImplementedError("Unknown input type")

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

    def asdf_roman_is_valid_unc(self, item):
        # TODO: should this instead have options just to include or not
        # include and pull from the flux extension?
        return all(k in item.get('obj').keys() for k in ["flux", "flux_err"])

    def is_valid_mask(self, item):
        if item.get('label') == 'None':
            return True
        if self.input_type == 'fits:hdulist':
            return self.hdu_is_valid_mask(item)
        if self.input_type == 'asdf:roman':
            return self.asdf_roman_is_valid_mask(item)
        if self.input_type == 'specutils:spectrum':
            return item.get('name') == 'mask'
        raise NotImplementedError("Unknown input type")

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

    def asdf_roman_is_valid_mask(self, item):
        # TODO: should this instead have options just to include or not
        # include and pull from the flux extension?
        return False

    @observe('extension_selected',
             'unc_extension_selected',
             'mask_extension_selected')
    def _on_extension_change(self, change):
        self._clear_cache('spectrum')

    @cached_property
    def spectrum(self):
        if self.input_type == 'fits:hdulist':
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

            if self.unc_extension.selected not in ('', 'None'):
                unc_hdu = self.unc_extension.selected_obj
                unc_data = unc_hdu.data
            else:
                unc_data = None
            if self.mask_extension.selected not in ('', 'None'):
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
        elif self.input_type == 'asdf:roman':
            def _to_unit(x):
                """Coerce str/bytes/Unit to astropy.units.Unit."""
                if isinstance(x, bytes):
                    x = x.decode()
                return u.Unit(x)

            roman = self.input["roman"]
            meta = roman["meta"]
            data = roman["data"]
            extension = self.extension.selected_obj
            if self.supported_flux_ndim == 1:
                wavelength = np.asarray(extension["wl"])
                flux = np.asarray(extension["flux"])
                wl_unit = _to_unit(meta["unit_wl"])
                flux_unit = _to_unit(meta["unit_flux"])

                # TODO: expose option in unc_extension that defaults to pulling
                # from flux extension, but also allowing user to set to "None"
                # to skip loading uncertainty
                flux_error = extension.get("flux_error", None)
                variance = extension.get("var", None)
                uncertainty = None
            elif self.supported_flux_ndim == 2:
                # TODO: handle detecting/selecting spectral axis?
                flux = np.asarray(extension["spectrum"]).transpose()
                flux_unit = _to_unit(meta["unit_flux"])
                if extension['wavelength'] is not None:
                    wavelength = np.asarray(extension["wavelength"])
                    wl_unit = _to_unit(meta["unit_wl"])
                else:
                    wavelength = np.arange(flux.shape[1])
                    wl_unit = u.pix

                flux_error = None
                variance = extension.get("variance", None)
                if variance is not None:
                    variance = np.asarray(variance).transpose()
                uncertainty = None
            else:
                raise NotImplementedError("Only 1D and 2D spectra are supported for ASDF Roman data")  # noqa

            if flux_error is not None:
                uncertainty = StdDevUncertainty(np.asarray(flux_error) * flux_unit)
            elif variance is not None:
                var = np.asarray(variance) * (flux_unit ** 2)
                var = np.where(np.asarray(var.value) < 0, np.nan, var.value) * var.unit
                uncertainty = StdDevUncertainty(np.sqrt(var))
            else:
                uncertainty = None

            spectrum = Spectrum(
                flux=flux * flux_unit,
                spectral_axis=wavelength * wl_unit,
                uncertainty=uncertainty
            )
            return spectrum
        elif self.input_type == 'specutils:spectrum':
            spectrum = self.input
            # TODO: remove uncertainty or mask if requested
            return spectrum
