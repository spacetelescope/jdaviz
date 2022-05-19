import logging
import os

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
    file_path : str
        The path to a cube-like data file.
    data_type : str, {'flux', 'mask', 'uncert'}
        The data type used to explicitly differentiate parsed data.
    data_label : str, optional
        The label to be applied to the Glue data component.
    """
    if data_type is not None and data_type.lower() not in ['flux', 'mask', 'uncert']:
        msg = "Data type must be one of 'flux', 'mask', or 'uncertainty'."
        logging.error(msg)
        return msg

    # If the file object is an hdulist or a string, use the generic parser for
    #  fits files.
    # TODO: this currently only supports fits files. We will want to make this
    #  generic enough to work with other file types (e.g. ASDF). For now, this
    #  supports MaNGA and JWST data.
    if isinstance(file_obj, fits.hdu.hdulist.HDUList):
        _parse_hdulist(app, file_obj, file_name=data_label)
    elif isinstance(file_obj, str) and os.path.exists(file_obj):
        file_name = os.path.basename(file_obj)

        with fits.open(file_obj) as hdulist:
            prihdr = hdulist[0].header
            telescop = prihdr.get('TELESCOP', '').lower()
            filetype = prihdr.get('FILETYPE', '').lower()
            system = prihdr.get('SYSTEM', '').lower()
            if telescop == 'jwst' and filetype == '3d ifu cube':
                for ext, viewer_name in (('SCI', 'flux-viewer'),
                                         ('ERR', 'uncert-viewer'),
                                         ('DQ', 'mask-viewer')):
                    data_label = f'{file_name}[{ext}]'
                    _parse_jwst_s3d(app, hdulist, data_label, ext=ext, viewer_name=viewer_name)
            elif telescop == 'jwst' and filetype == 'r3d' and system == 'esa-pipeline':
                for ext, viewer_name in (('DATA', 'flux-viewer'),
                                         ('ERR', 'uncert-viewer'),
                                         ('QUALITY', 'mask-viewer')):
                    data_label = f'{file_name}[{ext}]'
                    _parse_esa_s3d(app, hdulist, data_label, ext=ext, viewer_name=viewer_name)

            else:
                _parse_hdulist(app, hdulist, file_name=data_label or file_name)

    # If the data types are custom data objects, use explicit parsers. Note
    #  that this relies on the glue-astronomy machinery to turn the data object
    #  into something glue can understand.
    elif isinstance(file_obj, Spectrum1D):
        if file_obj.flux.ndim == 3:
            _parse_spectrum1d_3d(app, file_obj, data_label=data_label)
        else:
            _parse_spectrum1d(app, file_obj, data_label=data_label)
    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def _parse_hdulist(app, hdulist, file_name=None):
    if file_name is None:
        if hasattr(hdulist, 'file_name'):
            file_name = hdulist.file_name

    file_name = file_name or "Unknown HDU object"

    # Now loop through and attempt to parse the fits extensions as spectral
    #  cube object. If the wcs fails to parse in any case, use the wcs
    #  information we scraped above.
    for hdu in hdulist:
        data_label = f"{file_name}[{hdu.name}]"

        if hdu.data is None or not hdu.is_image or hdu.data.ndim != 3:
            continue

        try:
            wcs = WCS(hdu.header, hdulist)
        except Exception as e:  # TODO: Do we just want to fail here?
            logging.warning(f"Invalid WCS: {repr(e)}")
            wcs = None

        if 'BUNIT' in hdu.header:
            try:
                flux_unit = u.Unit(hdu.header['BUNIT'])
            except Exception:
                logging.warning("Invalid BUNIT, using count as data unit")
                flux_unit = u.count
        else:
            logging.warning("Missing BUNIT, using count as data unit")
            flux_unit = u.count

        flux = hdu.data << flux_unit

        metadata = standardize_metadata(hdu.header)
        if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
            metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

        try:
            sc = Spectrum1D(flux=flux, wcs=wcs, meta=metadata)
        except Exception as e:
            logging.warning(e)
            continue

        app.add_data(sc, data_label)

        # If the data type is some kind of integer, assume it's the mask/dq
        if (hdu.data.dtype in (int, np.uint, np.uint32) or
                any(x in hdu.name.lower() for x in EXT_TYPES['mask'])):
            app.add_data_to_viewer('mask-viewer', data_label)

        if ('errtype' in [x.lower() for x in hdu.header.keys()] or
                any(x in hdu.name.lower() for x in EXT_TYPES['uncert'])):
            app.add_data_to_viewer('uncert-viewer', data_label)

        if any(x in hdu.name.lower() for x in EXT_TYPES['flux']):
            # Add flux to top left image viewer
            app.add_data_to_viewer('flux-viewer', data_label)
            # Add flux to spectrum viewer
            app.add_data_to_viewer('spectrum-viewer', data_label)


def _parse_jwst_s3d(app, hdulist, data_label, ext='SCI', viewer_name='flux-viewer'):
    # Manually inject MJD-OBS until we can support GWCS, see
    # https://github.com/spacetelescope/jdaviz/issues/690 and
    # https://github.com/glue-viz/glue-astronomy/issues/59
    if ext == 'SCI' and 'MJD-OBS' not in hdulist[ext].header:
        for key in ('MJD-BEG', 'DATE-OBS'):  # Possible alternatives
            if key in hdulist[ext].header:
                if key.startswith('MJD'):
                    hdulist[ext].header['MJD-OBS'] = hdulist[ext].header[key]
                    break
                else:
                    t = Time(hdulist[ext].header[key])
                    hdulist[ext].header['MJD-OBS'] = t.mjd
                    break

    if ext == 'DQ':  # DQ flags have no unit
        flux = hdulist[ext].data << u.dimensionless_unscaled
    else:
        unit = u.Unit(hdulist[ext].header.get('BUNIT', 'count'))
        flux = hdulist[ext].data << unit
    wcs = WCS(hdulist['SCI'].header, hdulist)  # Everything uses SCI WCS

    metadata = standardize_metadata(hdulist[ext].header)
    if hdulist[ext].name != 'PRIMARY' and 'PRIMARY' in hdulist:
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

    data = Spectrum1D(flux, wcs=wcs, meta=metadata)

    # NOTE: Tried to only pass in sliced WCS but got error in Glue.
    # sliced_wcs = wcs[:, 0, 0]  # Only want wavelengths
    # data = Spectrum1D(flux, wcs=sliced_wcs, meta=metadata)

    app.add_data(data, data_label)
    app.add_data_to_viewer(viewer_name, data_label)
    if viewer_name == 'flux-viewer':
        app.add_data_to_viewer('spectrum-viewer', data_label)


def _parse_esa_s3d(app, hdulist, data_label, ext='DATA', viewer_name='flux-viewer'):
    if ext == 'QUALITY':  # QUALITY flags have no unit
        flux = hdulist[ext].data << u.dimensionless_unscaled
    else:
        unit = u.Unit(hdulist[ext].header.get('BUNIT', 'count'))
        flux = hdulist[ext].data << unit

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

    metadata = standardize_metadata(hdulist[ext].header)
    metadata.update(wcs_dict)  # To be internally consistent
    if hdulist[ext].name != 'PRIMARY' and 'PRIMARY' in hdulist:
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

    data = Spectrum1D(flux, wcs=wcs, meta=metadata)

    app.add_data(data, data_label)
    app.add_data_to_viewer(viewer_name, data_label)
    if viewer_name == 'flux-viewer':
        app.add_data_to_viewer('spectrum-viewer', data_label)


def _parse_spectrum1d_3d(app, file_obj, data_label=None):
    """Load spectrum1d as a cube."""

    if data_label is None:
        data_label = "Unknown spectrum object"

    for attr in ["flux", "mask", "uncertainty"]:
        val = getattr(file_obj, attr)
        if val is None:
            continue

        if attr == "mask":
            flux = val << file_obj.flux.unit
        elif attr == "uncertainty":
            if hasattr(val, "array"):
                flux = u.Quantity(val.array, file_obj.flux.unit)
            else:
                continue
        else:
            flux = val

        flux = np.moveaxis(flux, 1, 0)

        s1d = Spectrum1D(flux=flux, wcs=file_obj.wcs, meta=standardize_metadata(file_obj.meta))

        cur_data_label = f"{data_label}[{attr.upper()}]"
        app.add_data(s1d, cur_data_label)

        if attr == 'flux':
            app.add_data_to_viewer('flux-viewer', cur_data_label)
            app.add_data_to_viewer('spectrum-viewer', cur_data_label)
        elif attr == 'mask':
            app.add_data_to_viewer('mask-viewer', cur_data_label)
        else:  # 'uncertainty'
            app.add_data_to_viewer('uncert-viewer', cur_data_label)


def _parse_spectrum1d(app, file_obj, data_label=None):
    if data_label is None:
        data_label = "Unknown spectrum object"

    # TODO: glue-astronomy translators only look at the flux property of
    #  specutils Spectrum1D objects. Fix to support uncertainties and masks.

    app.add_data(file_obj, f"{data_label}[FLUX]")
    app.add_data_to_viewer('spectrum-viewer', f"{data_label}[FLUX]")
