import logging
import os
import warnings

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from specutils import Spectrum1D

from jdaviz.core.registries import data_parser_registry
from jdaviz.utils import standardize_metadata, PRIHDR_KEY

__all__ = ['parse_data']

EXT_TYPES = dict(flux=['flux', 'sci', 'data'],
                 uncert=['ivar', 'err', 'var', 'uncert'],
                 mask=['mask', 'dq', 'quality'])


@data_parser_registry("cubeviz-data-parser")
def parse_data(app, file_obj, data_type=None, data_label=None):
    """
    Attempts to parse a data file and auto-populate available viewers in
    cubeviz.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    file_obj : str
        The path to a cube-like data file.
    data_type : str, {'flux', 'mask', 'uncert'}
        The data type used to explicitly differentiate parsed data.
    data_label : str, optional
        The label to be applied to the Glue data component.
    """

    flux_viewer_reference_name = app._jdaviz_helper._default_flux_viewer_reference_name
    uncert_viewer_reference_name = app._jdaviz_helper._default_uncert_viewer_reference_name
    spectrum_viewer_reference_name = app._jdaviz_helper._default_spectrum_viewer_reference_name

    if data_type is not None and data_type.lower() not in ('flux', 'mask', 'uncert'):
        raise TypeError("Data type must be one of 'flux', 'mask', or 'uncert' "
                        f"but got '{data_type}'")

    # If the file object is an hdulist or a string, use the generic parser for
    #  fits files.
    # TODO: this currently only supports fits files. We will want to make this
    #  generic enough to work with other file types (e.g. ASDF). For now, this
    #  supports MaNGA and JWST data.
    if isinstance(file_obj, fits.hdu.hdulist.HDUList):
        _parse_hdulist(
            app, file_obj, file_name=data_label,
            flux_viewer_reference_name=flux_viewer_reference_name,
            spectrum_viewer_reference_name=spectrum_viewer_reference_name,
            uncert_viewer_reference_name=uncert_viewer_reference_name
        )
    elif isinstance(file_obj, str):
        if file_obj.lower().endswith('.gif'):  # pragma: no cover
            _parse_gif(app, file_obj, data_label,
                       flux_viewer_reference_name=flux_viewer_reference_name,
                       spectrum_viewer_reference_name=spectrum_viewer_reference_name)
            return

        file_name = os.path.basename(file_obj)

        with fits.open(file_obj) as hdulist:
            prihdr = hdulist[0].header
            telescop = prihdr.get('TELESCOP', '').lower()
            exptype = prihdr.get('EXP_TYPE', '').lower()
            # NOTE: Alerted to deprecation of FILETYPE keyword from pipeline on 2022-07-08
            # Kept for posterity in for data processed prior to this date. Use EXP_TYPE instead
            filetype = prihdr.get('FILETYPE', '').lower()
            system = prihdr.get('SYSTEM', '').lower()
            if telescop == 'jwst' and ('ifu' in exptype or
                                       'mrs' in exptype or
                                       filetype == '3d ifu cube'):
                for ext, viewer_name in (('SCI', flux_viewer_reference_name),
                                         ('ERR', uncert_viewer_reference_name),
                                         ('DQ', None)):
                    data_label = app.return_data_label(file_name, ext)
                    _parse_jwst_s3d(
                        app, hdulist, data_label, ext=ext, viewer_name=viewer_name,
                        flux_viewer_reference_name=flux_viewer_reference_name,
                        spectrum_viewer_reference_name=spectrum_viewer_reference_name
                    )
            elif telescop == 'jwst' and filetype == 'r3d' and system == 'esa-pipeline':
                for ext, viewer_name in (('DATA', flux_viewer_reference_name),
                                         ('ERR', uncert_viewer_reference_name),
                                         ('QUALITY', None)):
                    data_label = app.return_data_label(file_name, ext)
                    _parse_esa_s3d(
                        app, hdulist, data_label, ext=ext, viewer_name=viewer_name,
                        flux_viewer_reference_name=flux_viewer_reference_name,
                        spectrum_viewer_reference_name=spectrum_viewer_reference_name
                    )
            else:
                _parse_hdulist(
                    app, hdulist, file_name=data_label or file_name,
                    flux_viewer_reference_name=flux_viewer_reference_name,
                    spectrum_viewer_reference_name=spectrum_viewer_reference_name,
                    uncert_viewer_reference_name=uncert_viewer_reference_name
                )

    # If the data types are custom data objects, use explicit parsers. Note
    #  that this relies on the glue-astronomy machinery to turn the data object
    #  into something glue can understand.
    elif isinstance(file_obj, Spectrum1D) and file_obj.flux.ndim in (1, 3):
        if file_obj.flux.ndim == 3:
            _parse_spectrum1d_3d(
                app, file_obj, data_label=data_label,
                flux_viewer_reference_name=flux_viewer_reference_name,
                spectrum_viewer_reference_name=spectrum_viewer_reference_name,
                uncert_viewer_reference_name=uncert_viewer_reference_name
            )
        else:
            _parse_spectrum1d(
                app, file_obj, data_label=data_label,
                spectrum_viewer_reference_name=spectrum_viewer_reference_name
            )
    elif isinstance(file_obj, np.ndarray) and file_obj.ndim == 3:
        _parse_ndarray(app, file_obj, data_label=data_label, data_type=data_type,
                       flux_viewer_reference_name=flux_viewer_reference_name,
                       spectrum_viewer_reference_name=spectrum_viewer_reference_name,
                       uncert_viewer_reference_name=uncert_viewer_reference_name)
    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def _return_spectrum_with_correct_units(flux, wcs, metadata, data_type, target_wave_unit=None,
                                        hdulist=None):
    """Upstream issue of WCS not using the correct units for data must be fixed here.
    Issue: https://github.com/astropy/astropy/issues/3658
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', message='Input WCS indicates that the spectral axis is not last',
            category=UserWarning)
        sc = Spectrum1D(flux=flux, wcs=wcs)

    if target_wave_unit is None and hdulist is not None:
        found_target = False
        for ext in ('SCI', 'FLUX', 'PRIMARY'):  # In priority order
            if found_target:
                break
            if ext not in hdulist:
                continue
            hdr = hdulist[ext].header
            # The WCS could be swapped or unswapped.
            for cunit_num in (3, 1):
                cunit_key = f"CUNIT{cunit_num}"
                ctype_key = f"CTYPE{cunit_num}"
                if cunit_key in hdr and 'WAVE' in hdr[ctype_key]:
                    target_wave_unit = u.Unit(hdr[cunit_key])
                    found_target = True
                    break

    if (data_type == 'flux' and target_wave_unit is not None
            and target_wave_unit != sc.spectral_axis.unit):
        metadata['_orig_spec'] = sc
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore', message='Input WCS indicates that the spectral axis is not last',
                category=UserWarning)
            new_sc = Spectrum1D(
                flux=sc.flux,
                spectral_axis=sc.spectral_axis.to(target_wave_unit, u.spectral()),
                meta=metadata)
    else:
        sc.meta = metadata
        new_sc = sc
    return new_sc


def _parse_hdulist(app, hdulist, file_name=None,
                   flux_viewer_reference_name=None,
                   spectrum_viewer_reference_name=None,
                   uncert_viewer_reference_name=None):
    if file_name is None and hasattr(hdulist, 'file_name'):
        file_name = hdulist.file_name
    else:
        file_name = file_name or "Unknown HDU object"

    is_loaded = []
    wcs_sci = None

    # TODO: This needs refactoring to be more robust.
    # Current logic fails if there are multiple EXTVER.
    for hdu in hdulist:
        if hdu.data is None or not hdu.is_image or hdu.data.ndim != 3:
            continue

        data_type = _get_data_type_by_hdu(hdu)
        if not data_type:
            continue

        # Only load each type once.
        if data_type in is_loaded:
            continue

        is_loaded.append(data_type)
        data_label = app.return_data_label(file_name, hdu.name)

        if data_type == 'flux':
            wcs = WCS(hdu.header, hdulist)
            wcs_sci = wcs
        else:
            wcs = wcs_sci

        if 'BUNIT' in hdu.header:
            try:
                flux_unit = u.Unit(hdu.header['BUNIT'])
            except Exception:
                logging.warning("Invalid BUNIT, using count as data unit")
                flux_unit = u.count
        elif data_type == 'mask':  # DQ flags have no unit
            flux_unit = u.dimensionless_unscaled
        else:
            logging.warning("Invalid BUNIT, using count as data unit")
            flux_unit = u.count

        flux = hdu.data << flux_unit

        metadata = standardize_metadata(hdu.header)
        if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
            metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

        sc = _return_spectrum_with_correct_units(flux, wcs, metadata, data_type, hdulist=hdulist)
        app.add_data(sc, data_label)
        if data_type == 'flux':  # Forced wave unit conversion made it lose stuff, so re-add
            app.data_collection[-1].get_component("flux").units = flux_unit

        if data_type == 'mask':
            # We no longer auto-populate the mask cube into a viewer
            pass

        elif data_type == 'uncert':
            app.add_data_to_viewer(uncert_viewer_reference_name, data_label)

        else:  # flux
            # Add flux to top left image viewer
            app.add_data_to_viewer(flux_viewer_reference_name, data_label)
            # Add flux to spectrum viewer
            app.add_data_to_viewer(spectrum_viewer_reference_name, data_label)


def _parse_jwst_s3d(app, hdulist, data_label, ext='SCI',
                    viewer_name=None, flux_viewer_reference_name=None,
                    spectrum_viewer_reference_name=None):
    hdu = hdulist[ext]
    data_type = _get_data_type_by_hdu(hdu)

    # Manually inject MJD-OBS until we can support GWCS, see
    # https://github.com/spacetelescope/jdaviz/issues/690 and
    # https://github.com/glue-viz/glue-astronomy/issues/59
    if ext == 'SCI' and 'MJD-OBS' not in hdu.header:
        for key in ('MJD-BEG', 'DATE-OBS'):  # Possible alternatives
            if key in hdu.header:
                if key.startswith('MJD'):
                    hdu.header['MJD-OBS'] = hdu.header[key]
                    break
                else:
                    t = Time(hdu.header[key])
                    hdu.header['MJD-OBS'] = t.mjd
                    break

    if ext == 'DQ':  # DQ flags have no unit
        flux = hdu.data << u.dimensionless_unscaled
    else:
        unit = u.Unit(hdu.header.get('BUNIT', 'count'))
        flux = hdu.data << unit
    wcs = WCS(hdulist['SCI'].header, hdulist)  # Everything uses SCI WCS

    metadata = standardize_metadata(hdu.header)
    if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

    data = _return_spectrum_with_correct_units(flux, wcs, metadata, data_type, hdulist=hdulist)
    app.add_data(data, data_label)
    if data_type == 'flux':  # Forced wave unit conversion made it lose stuff, so re-add
        app.data_collection[-1].get_component("flux").units = flux.unit

    if viewer_name is not None:
        app.add_data_to_viewer(viewer_name, data_label)
    # Also add the collapsed flux to the spectrum viewer
    if viewer_name == flux_viewer_reference_name:
        app.add_data_to_viewer(spectrum_viewer_reference_name, data_label)


def _parse_esa_s3d(app, hdulist, data_label, ext='DATA', viewer_name='flux-viewer',
                   flux_viewer_reference_name=None, spectrum_viewer_reference_name=None):
    hdu = hdulist[ext]
    data_type = _get_data_type_by_hdu(hdu)

    if ext == 'QUALITY':  # QUALITY flags have no unit
        flux = hdu.data << u.dimensionless_unscaled
    else:
        unit = u.Unit(hdu.header.get('BUNIT', 'count'))
        flux = hdu.data << unit

    hdr = hdulist[1].header

    wcs_dict = {
        'CTYPE1': 'WAVE    ', 'CUNIT1': 'um', 'CDELT1': hdr['CDELT3'] * 1E6,
        'CRPIX1': hdr['CRPIX3'],
        'CRVAL1': hdr['CRVAL3'] * 1E6, 'NAXIS1': hdr['NAXIS3'],
        'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg', 'CDELT2': hdr['CDELT1'], 'CRPIX2': hdr['CRPIX1'],
        'CRVAL2': hdr['CRVAL1'], 'NAXIS2': hdr['NAXIS1'],
        'CTYPE3': 'RA---TAN', 'CUNIT3': 'deg', 'CDELT3': hdr['CDELT2'], 'CRPIX3': hdr['CRPIX2'],
        'CRVAL3': hdr['CRVAL2'], 'NAXIS3': hdr['NAXIS2']}

    wcs = WCS(wcs_dict)
    flux = np.moveaxis(flux, 0, -1)
    flux = np.swapaxes(flux, 0, 1)

    metadata = standardize_metadata(hdu.header)
    metadata.update(wcs_dict)  # To be internally consistent
    if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

    data = _return_spectrum_with_correct_units(flux, wcs, metadata, data_type, hdulist=hdulist)

    app.add_data(data, data_label)

    if data_type == 'flux':  # Forced wave unit conversion made it lose stuff, so re-add
        app.data_collection[-1].get_component("flux").units = flux.unit

    app.add_data_to_viewer(viewer_name, data_label)
    if viewer_name == flux_viewer_reference_name:
        app.add_data_to_viewer(spectrum_viewer_reference_name, data_label)


def _parse_spectrum1d_3d(app, file_obj, data_label=None,
                         flux_viewer_reference_name=None, spectrum_viewer_reference_name=None,
                         uncert_viewer_reference_name=None):
    """Load spectrum1d as a cube."""

    if data_label is None:
        data_label = "Unknown spectrum object"

    for attr in ("flux", "mask", "uncertainty"):
        val = getattr(file_obj, attr)
        if val is None:
            continue

        if attr == "mask":
            flux = val << u.dimensionless_unscaled  # DQ flags have no unit
        elif attr == "uncertainty":
            if hasattr(val, "array"):
                flux = u.Quantity(val.array, file_obj.flux.unit)
            else:
                continue
        else:
            flux = val

        flux = np.moveaxis(flux, 1, 0)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore', message='Input WCS indicates that the spectral axis is not last',
                category=UserWarning)
            s1d = Spectrum1D(flux=flux, wcs=file_obj.wcs,
                             meta=standardize_metadata(file_obj.meta))

        cur_data_label = app.return_data_label(data_label, attr.upper())
        app.add_data(s1d, cur_data_label)

        if attr == 'flux':
            app.add_data_to_viewer(flux_viewer_reference_name, cur_data_label)
            app.add_data_to_viewer(spectrum_viewer_reference_name, cur_data_label)
        elif attr == 'uncertainty':
            app.add_data_to_viewer(uncert_viewer_reference_name, cur_data_label)
        # We no longer auto-populate the mask cube into a viewer


def _parse_spectrum1d(app, file_obj, data_label=None, spectrum_viewer_reference_name=None):
    if data_label is None:
        data_label = app.return_data_label(file_obj)

    # TODO: glue-astronomy translators only look at the flux property of
    #  specutils Spectrum1D objects. Fix to support uncertainties and masks.

    app.add_data(file_obj, data_label)
    app.add_data_to_viewer(spectrum_viewer_reference_name, data_label)


def _parse_ndarray(app, file_obj, data_label=None, data_type=None,
                   flux_viewer_reference_name=None, spectrum_viewer_reference_name=None,
                   uncert_viewer_reference_name=None):
    if data_label is None:
        data_label = app.return_data_label(file_obj)

    if data_type is None:
        data_type = 'flux'

    # Cannot change axis to ensure roundtripping within Cubeviz.
    # Axes must already be (x, y, z) at this point.
    flux = file_obj

    if not hasattr(flux, 'unit'):
        flux = flux << u.count
    s3d = Spectrum1D(flux=flux)
    app.add_data(s3d, data_label)

    if data_type == 'flux':
        app.add_data_to_viewer(flux_viewer_reference_name, data_label)
        app.add_data_to_viewer(spectrum_viewer_reference_name, data_label)
    elif data_type == 'uncert':
        app.add_data_to_viewer(uncert_viewer_reference_name, data_label)


def _parse_gif(app, file_obj, data_label=None, flux_viewer_reference_name=None,
               spectrum_viewer_reference_name=None):  # pragma: no cover
    # NOTE: Parsing GIF needs imageio and Pillow, both are which undeclared
    # in setup.cfg but might or might not be installed by declared ones.
    import imageio

    file_name = os.path.basename(file_obj)

    if data_label is None:
        data_label = app.return_data_label(file_obj)

    flux = imageio.v3.imread(file_obj, mode='P')  # All frames as gray scale
    flux = np.rot90(np.moveaxis(flux, 0, 2), k=-1, axes=(0, 1))
    s3d = Spectrum1D(flux=flux * u.count, meta={'filename': file_name})

    app.add_data(s3d, data_label)
    app.add_data_to_viewer(flux_viewer_reference_name, data_label)
    app.add_data_to_viewer(spectrum_viewer_reference_name, data_label)


def _get_data_type_by_hdu(hdu):
    # If the data type is some kind of integer, assume it's the mask/dq
    if (hdu.data.dtype in (int, np.uint, np.uint8, np.uint16, np.uint32) or
            any(x in hdu.name.lower() for x in EXT_TYPES['mask'])):
        data_type = 'mask'
    elif ('errtype' in [x.lower() for x in hdu.header.keys()] or
            any(x in hdu.name.lower() for x in EXT_TYPES['uncert'])):
        data_type = 'uncert'
    elif any(x in hdu.name.lower() for x in EXT_TYPES['flux']):
        data_type = 'flux'
    else:
        data_type = ''
    return data_type
