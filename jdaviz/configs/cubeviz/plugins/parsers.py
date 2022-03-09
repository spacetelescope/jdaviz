import base64
import os
import uuid

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.io.fits import HDUList, ImageHDU, PrimaryHDU
from astropy.nddata import NDData
from astropy.wcs import WCS
from glue.core.data import Component, Data
from specutils import Spectrum1D

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import data_parser_registry

__all__ = ['parse_data']


@data_parser_registry("cubeviz-data-parser")
def parse_data(app, file_obj, data_type=None, data_label=None):
    """Parse the given data into Cubeviz.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    file_obj : str, `~astropy.io.fits.ImageHDU`, `~astropy.io.fits.PrimaryHDU`, `~astropy.io.fits.HDUList`, `~specutils.Spectrum1D`, `~astropy.nddata.NDData`, or ndarray
        The path to a cube-like data FITS file or the data object to be loaded.
    data_type : {'flux', 'uncert', 'mask', `None`}
        The data type used to explicitly differentiate parsed data.
        This is only used for ndarray and 2D `~astropy.nddata.NDData`.
        If `None` is given, it tries to parse according to software default.
    data_label : str or `None`
        The label to be applied to the Glue data component.
        If `None` is given, it is automatically generated.

    Raises
    ------
    ValueError
        Parsing failed.

    NotImplementedError
        Unsupported data format.

    """  # noqa: E501
    valid_data_types = ('flux', 'uncert', 'mask')
    if data_type is not None:
        data_type = data_type.lower()
        if data_type not in valid_data_types:
            raise ValueError(f"data_type must be one of: {valid_data_types}")

    if isinstance(file_obj, str):  # Assume FITS file
        file_name = os.path.basename(file_obj)
        if data_label is None:
            data_label = file_name

        with fits.open(file_obj) as hdulist:
            prihdr = hdulist[0].header
            telescop = prihdr.get('TELESCOP', '').lower()
            filetype = prihdr.get('FILETYPE', '').lower()
            if telescop == 'jwst' and filetype == '3d ifu cube':  # pragma: no cover
                _fix_jwst_s3d_sci_header(hdulist)
            _parse_hdulist(app, hdulist, data_label)

    elif isinstance(file_obj, HDUList):
        if data_label is None:  # pragma: no cover
            if hasattr(file_obj, 'file_name'):
                data_label = file_obj.file_name
            else:
                data_label = f'HDUList|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'

        _parse_hdulist(app, file_obj, data_label)

    elif isinstance(file_obj, (ImageHDU, PrimaryHDU)):
        if data_label is None:  # pragma: no cover
            data_label = f'{file_obj.__class__.__name__}|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'  # noqa: E501
        _parse_hdu(app, file_obj, data_label)

    # This relies on the glue-astronomy machinery to turn the data object
    # into something glue can understand.
    elif isinstance(file_obj, Spectrum1D):
        if data_label is None:
            data_label = f'Spectrum1D|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'

        if file_obj.flux.ndim == 3:
            _parse_spectrum1d_3d(app, file_obj, data_label)
        elif file_obj.flux.ndim == 1:
            _parse_spectrum1d(app, file_obj, data_label)
        else:
            raise NotImplementedError(f'Unsupported data format: {file_obj}')

    elif isinstance(file_obj, NDData):
        if data_label is None:
            data_label = f'nddata|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'
        if file_obj.data.ndim == 2:  # This is mainly to support Moment plugin.
            if data_type is None:
                data_type = 'flux'
            _parse_nddata_2d(app, file_obj, data_label, data_type)
        elif file_obj.data.ndim == 3:
            _parse_nddata_3d(app, file_obj, data_label)
        else:
            raise NotImplementedError(f'Unsupported data format: {file_obj}')

    elif isinstance(file_obj, np.ndarray):
        if data_label is None:
            data_label = f'ndarray|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'
        if data_type is None:
            data_type = 'flux'

        if file_obj.ndim >= 3:
            arr = file_obj.squeeze()
            if arr.ndim != 3:
                raise NotImplementedError(f'Unsupported data format: {file_obj}')
            _parse_ndarray_3d(app, arr, data_label, data_type)
        else:
            raise NotImplementedError(f'Unsupported data format: {file_obj}')

    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def _parse_hdulist(app, hdulist, base_data_label):
    viewer_cache = {}

    # Now loop through and attempt to parse the FITS extensions as Spectrum1D.
    # Only show first matching extension to each viewer, but attempts to load
    # all valid extensions.
    for hdu in hdulist:
        data_label = f"{base_data_label}[{hdu.name.upper()}]"
        try:
            data_type = _parse_hdu(app, hdu, data_label, hdulist=hdulist, show_in_viewer=False)
        except Exception:  # nosec
            continue
        if data_type and data_type not in viewer_cache:
            _show_data_in_cubeviz_viewer(app, data_label, data_type)
            viewer_cache[data_type] = data_label


def _parse_hdu(app, hdu, data_label, hdulist=None, show_in_viewer=True):
    """Load HDU into Cubeviz and return data type."""
    data_type, sc = _hdu_to_sc(app, hdu, data_label, hdulist=hdulist)
    app.add_data(sc, data_label)
    if show_in_viewer:
        _show_data_in_cubeviz_viewer(app, data_label, data_type)
    return data_type


def _get_flux_unit_from_hdu_header(app, hdr, data_label, strict=False):
    if 'BUNIT' in hdr:
        try:
            flux_unit = u.Unit(hdr['BUNIT'])
        except Exception:
            if strict:
                raise
            else:
                app.hub.broadcast(SnackbarMessage(
                    f"Invalid BUNIT={hdr['BUNIT']} for {data_label}, assume count",
                    color="warning", timeout=8000, sender=app))
                flux_unit = u.count
    elif strict:
        raise KeyError(f'Missing BUNIT for {data_label}')
    else:
        app.hub.broadcast(SnackbarMessage(
            f"Missing BUNIT for {data_label}, assume count",
            color="warning", timeout=8000, sender=app))
        flux_unit = u.count
    return flux_unit


def _get_wcs_from_hdu_header(app, hdr, data_label, hdulist=None):
    is_bad = ''

    try:
        wcs = WCS(hdr, hdulist)
    except Exception as e:
        is_bad = repr(e)
    else:
        if all([x is None for x in wcs.world_axis_physical_types]):
            is_bad = 'All WCS axis is None'

    if is_bad:
        app.hub.broadcast(SnackbarMessage(
            f"Invalid WCS for {data_label}: {is_bad}",
            color="warning", timeout=8000, sender=app))
        wcs = None

    return wcs


def _get_sci_hdr_from_hdulist(hdulist):
    """Guess and grab SCI header from a given HDUList."""
    if hdulist is None:
        return

    hdr = None
    for hdu_name in ('flux', 'sci', 'primary'):  # In order of search priority.
        if hdu_name in hdulist:
            hdr = hdulist[hdu_name].header
            break
    return hdr


def _hdu_to_sc(app, hdu, data_label, hdulist=None):
    """Return HDU as (data type, Spectrum1D) tuple or throw exception."""
    if hdu.data is None or not hdu.is_image or hdu.data.ndim < 3:
        raise ValueError(f'HDU is not supported as data cube: {hdu}')

    if hdu.data.ndim > 3:
        hdu_data = hdu.data.squeeze()
        if hdu_data.ndim != 3:
            raise ValueError(f'HDU is not supported as data cube: {hdu}')
    else:
        hdu_data = hdu.data

    hdu_name = hdu.name.lower()
    hdr = hdu.header
    if hdu_name in ('flux', 'sci', 'primary'):
        data_type = 'flux'
        flux_unit = _get_flux_unit_from_hdu_header(app, hdr, data_label)
        wcs = _get_wcs_from_hdu_header(app, hdr, data_label, hdulist=hdulist)
    elif hdu_name in ('ivar', 'err', 'var', 'uncert') or 'errtype' in hdr:
        data_type = 'uncert'
        sci_hdr = _get_sci_hdr_from_hdulist(hdulist)
        try:
            flux_unit = _get_flux_unit_from_hdu_header(app, hdr, data_label, strict=True)
        except Exception:
            if sci_hdr:  # Inherit from SCI
                flux_unit = _get_flux_unit_from_hdu_header(app, sci_hdr, data_label)
            else:
                flux_unit = _get_flux_unit_from_hdu_header(app, hdr, data_label)
        if sci_hdr:  # Inherit from SCI
            wcs = _get_wcs_from_hdu_header(app, sci_hdr, data_label, hdulist=hdulist)
        else:
            wcs = _get_wcs_from_hdu_header(app, hdr, data_label, hdulist=hdulist)
    # If the data type is some kind of integer, assume it's the mask/DQ
    elif hdu_name in ('mask', 'dq') or hdu_data.dtype in (int, np.uint, np.uint32):
        data_type = 'mask'
        sci_hdr = _get_sci_hdr_from_hdulist(hdulist)
        flux_unit = u.dimensionless_unscaled
        if sci_hdr:  # Inherit from SCI
            wcs = _get_wcs_from_hdu_header(app, sci_hdr, data_label, hdulist=hdulist)
        else:
            wcs = _get_wcs_from_hdu_header(app, hdr, data_label, hdulist=hdulist)
    else:
        raise ValueError(f'Unsupported extname={hdu.name} and/or dtype={hdu_data.dtype}')

    # NOTE: Transpose here because specutils will not reorder the axes when there is no WCS.
    if wcs is None:
        hdu_data = hdu_data.T

    flux = hdu_data << flux_unit
    return data_type, Spectrum1D(flux=flux, wcs=wcs, meta=hdr)


def _show_data_in_cubeviz_viewer(app, data_label, data_type, show_spectrum=True):
    """Display data to Cubeviz viewer depending on given data type.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.

    data_label : str
        The data label associated with ``sc``.

    data_type : {'flux', 'uncert', 'mask'}
        If ``'flux'`` is given, it also adds a collapsed cube as spectrum
        to the spectrum viewer.

    show_spectrum : bool
        Show ``spectrum-viewer`` for flux data type.

    Raises
    ------
    ValueError
        Invalid ``data_type``.

    """
    if data_type == 'flux':
        app.add_data_to_viewer(f'{data_type}-viewer', data_label)
        if show_spectrum:
            app.add_data_to_viewer('spectrum-viewer', data_label)
    elif data_type in ('uncert', 'mask'):
        app.add_data_to_viewer(f'{data_type}-viewer', data_label)
    else:  # pragma: no cover
        raise ValueError(f"Cannot add {data_label} to {data_type} viewer, must be one of: "
                         "flux, uncert, mask")


def _fix_jwst_s3d_sci_header(hdulist):
    """Manually inject MJD-OBS until we can support GWCS.
    ``hdulist`` is modified in-place.
    Also see https://github.com/spacetelescope/jdaviz/issues/690 and
    https://github.com/glue-viz/glue-astronomy/issues/59
    """
    ext = 'SCI'
    if 'MJD-OBS' not in hdulist[ext].header:
        for key in ('MJD-BEG', 'DATE-OBS'):  # Possible alternatives
            if key in hdulist[ext].header:
                if key.startswith('MJD'):
                    hdulist[ext].header['MJD-OBS'] = hdulist[ext].header[key]
                    break
                else:
                    from astropy.time import Time
                    t = Time(hdulist[ext].header[key])
                    hdulist[ext].header['MJD-OBS'] = t.mjd
                    break


def _parse_spectrum1d_3d(app, file_obj, base_data_label):
    """Load Spectrum1D as a cube."""

    for attr in ("flux", "uncertainty", "mask"):
        val = getattr(file_obj, attr)
        if val is None:  # pragma: no cover
            continue

        if attr == "flux":
            data_type = 'flux'
            flux = val
        elif attr == "uncertainty" and hasattr(val, "array"):
            data_type = 'uncert'
            flux = val.array << file_obj.flux.unit
        elif attr == "mask":
            data_type = 'mask'
            flux = val << u.dimensionless_unscaled
        else:  # pragma: no cover
            continue

        # NOTE: Transpose here because specutils will not reorder the axes when there is no WCS.
        if file_obj.spectral_axis.unit == u.pix:
            flux = flux.T

        s1d = Spectrum1D(flux=flux, wcs=file_obj.wcs, meta=file_obj.meta)

        data_label = f"{base_data_label}[{attr.upper()}]"
        app.add_data(s1d, data_label)
        _show_data_in_cubeviz_viewer(app, data_label, data_type)


def _parse_spectrum1d(app, file_obj, data_label, data_type='flux'):
    # TODO: glue-astronomy translators only look at the flux property of
    # specutils Spectrum1D objects. Fix to support uncertainties and masks.
    data_label = f"{data_label}[{data_type.upper()}]"
    app.add_data(file_obj, data_label)
    app.add_data_to_viewer('spectrum-viewer', data_label)


def _parse_nddata_3d(app, file_obj, base_data_label):
    for attrib in ['data', 'uncertainty', 'mask']:
        arr = getattr(file_obj, attrib)
        if arr is None:
            continue

        if attrib == 'data':
            flux = u.Quantity(arr, file_obj.unit)
            data_type = 'flux'
        elif attrib == 'uncertainty':
            flux = u.Quantity(arr.array, arr.unit)
            data_type = 'uncert'
        else:  # mask
            flux = arr << u.dimensionless_unscaled
            data_type = 'mask'

        # NOTE: Transpose here because specutils will not reorder the axes.
        # NDData WCS is not spectral WCS, so safer to ignore it.
        s1d = Spectrum1D(flux=flux.T, meta=file_obj.meta)
        data_label = f"{base_data_label}[{data_type.upper()}]"
        app.add_data(s1d, data_label)
        _show_data_in_cubeviz_viewer(app, data_label, data_type)


def _parse_nddata_2d(app, file_obj, data_label, data_type):
    # This is mainly to support Moment plugin, so we ignore mask and uncertainty.
    # We want to only show main data in the given data_type without any spectrum support.
    data = Data(label=data_label)
    data.meta.update(file_obj.meta)
    if file_obj.wcs is not None:
        data.coords = file_obj.wcs
    bunit = file_obj.unit or ''
    component = Component.autotyped(file_obj.data, units=bunit)
    data.add_component(component=component, label='flux')
    app.add_data(data, data_label)
    _show_data_in_cubeviz_viewer(app, data_label, data_type, show_spectrum=False)


def _parse_ndarray_3d(app, file_obj, data_label, data_type):
    """Load 3D ndarray into Cubeviz."""
    data_label = f"{data_label}[{data_type.upper()}]"
    if data_type == 'mask':
        flux_unit = u.dimensionless_unscaled
    else:
        flux_unit = u.count

    # NOTE: Transpose here because specutils will not reorder the axes when there is no WCS.
    flux = file_obj.T << flux_unit

    sc = Spectrum1D(flux=flux)
    app.add_data(sc, data_label)
    _show_data_in_cubeviz_viewer(app, data_label, data_type)
