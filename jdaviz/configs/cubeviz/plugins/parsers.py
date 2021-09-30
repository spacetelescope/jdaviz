import logging
import os

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from specutils import Spectrum1D

from jdaviz.core.registries import data_parser_registry

__all__ = ['parse_data']

EXT_TYPES = dict(flux=['flux', 'sci'],
                 uncert=['ivar', 'err', 'var', 'uncert'],
                 mask=['mask', 'dq'])


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
        _parse_hdu(app, file_obj, file_name=data_label)
    elif isinstance(file_obj, str) and os.path.exists(file_obj):
        file_name = os.path.basename(file_obj)

        with fits.open(file_obj) as hdulist:
            prihdr = hdulist[0].header
            telescop = prihdr.get('TELESCOP', '').lower()
            filetype = prihdr.get('FILETYPE', '').lower()
            if telescop == 'jwst' and filetype == '3d ifu cube':
                # TODO: What about ERR, DQ, and WMAP?
                data_label = f'{file_name}[SCI]'
                _parse_jwst_s3d(app, hdulist, data_label)
            else:
                _parse_hdu(app, hdulist, file_name=data_label or file_name)

    # If the data types are custom data objects, use explicit parsers. Note
    #  that this relies on the glue-astronomy machinery to turn the data object
    #  into something glue can understand.
    elif isinstance(file_obj, Spectrum1D):
        if file_obj.flux.ndim == 3:
            _parse_spectrum1d_3d(app, file_obj)
        else:
            _parse_spectrum1d(app, file_obj)
    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def _parse_hdu(app, hdulist, file_name=None):
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

        try:
            sc = Spectrum1D(flux=flux, wcs=wcs)
        except Exception as e:
            logging.warning(e)
            continue

        app.add_data(sc, data_label)

        # If the data type is some kind of integer, assume it's the mask/dq
        if hdu.data.dtype in (int, np.uint, np.uint32) or \
                any(x in hdu.name.lower() for x in EXT_TYPES['mask']):
            app.add_data_to_viewer('mask-viewer', data_label)

        if 'errtype' in [x.lower() for x in hdu.header.keys()] or \
                any(x in hdu.name.lower() for x in EXT_TYPES['uncert']):
            app.add_data_to_viewer('uncert-viewer', data_label)

        if any(x in hdu.name.lower() for x in EXT_TYPES['flux']):
            app.add_data_to_viewer('flux-viewer', data_label)
            app.add_data_to_viewer('spectrum-viewer', data_label)


def _parse_jwst_s3d(app, hdulist, data_label):
    from specutils import Spectrum1D

    unit = u.Unit(hdulist[1].header.get('BUNIT', 'count'))
    flux = hdulist[1].data << unit
    wcs = WCS(hdulist[1].header, hdulist)
    data = Spectrum1D(flux, wcs=wcs)

    # NOTE: Tried to only pass in sliced WCS but got error in Glue.
    # sliced_wcs = wcs[:, 0, 0]  # Only want wavelengths
    # data = Spectrum1D(flux, wcs=sliced_wcs)

    app.add_data(data, data_label)
    app.add_data_to_viewer('flux-viewer', data_label)
    app.add_data_to_viewer('spectrum-viewer', data_label)


def _parse_spectrum1d_3d(app, file_obj):
    # Load spectrum1d as a cube

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

        s1d = Spectrum1D(flux=flux, wcs=file_obj.wcs)

        data_label = f"Unknown spectrum object[{attr.upper()}]"
        app.add_data(s1d, data_label)

        if attr == 'flux':
            app.add_data_to_viewer('flux-viewer', data_label)
            app.add_data_to_viewer('spectrum-viewer', data_label)
        elif attr == 'mask':
            app.add_data_to_viewer('mask-viewer', data_label)
        else:  # 'uncertainty'
            app.add_data_to_viewer('uncert-viewer', data_label)


def _parse_spectrum1d(app, file_obj):
    data_label = "Unknown spectrum object"

    # TODO: glue-astronomy translators only look at the flux property of
    #  specutils Spectrum1D objects. Fix to support uncertainties and masks.

    app.add_data(file_obj, f"{data_label}[FLUX]")
    app.add_data_to_viewer('spectrum-viewer', f"{data_label}[FLUX]")
