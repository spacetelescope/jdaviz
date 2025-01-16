import os
import warnings

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import StdDevUncertainty
from astropy.time import Time
from astropy.wcs import WCS
from specutils import Spectrum1D

from jdaviz.core.custom_units_and_equivs import PIX2, _eqv_flux_to_sb_pixel
from jdaviz.core.registries import data_parser_registry
from jdaviz.core.unit_conversion_utils import check_if_unit_is_per_solid_angle
from jdaviz.utils import standardize_metadata, PRIHDR_KEY, download_uri_to_path

__all__ = ['parse_data']

EXT_TYPES = dict(flux=['flux', 'sci', 'data'],
                 uncert=['ivar', 'err', 'error', 'var', 'uncert'],
                 mask=['mask', 'dq', 'quality', 'data_quality'])


@data_parser_registry("cubeviz-data-parser")
def parse_data(app, file_obj, data_type=None, data_label=None,
               parent=None, cache=None, local_path=None, timeout=None):
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
    parent : str, optional
        Data label for "parent" data to associate with the loaded data as "child".
    cache : None, bool, or str
        Cache the downloaded file if the data are retrieved by a query
        to a URL or URI.
    local_path : str, optional
        Cache remote files to this path. This is only used if data is
        requested from `astroquery.mast`.
    timeout : float, optional
        If downloading from a remote URI, set the timeout limit for
        remote requests in seconds (passed to
        `~astropy.utils.data.download_file` or
        `~astroquery.mast.Conf.timeout`).
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
        try:
            _parse_spectrum1d_3d(
                app, Spectrum1D.read(file_obj), data_label=data_label,
                flux_viewer_reference_name=flux_viewer_reference_name,
                uncert_viewer_reference_name=uncert_viewer_reference_name
            )
        except Exception:  # nosec
            _parse_hdulist(
                app, file_obj, file_name=data_label,
                flux_viewer_reference_name=flux_viewer_reference_name,
                uncert_viewer_reference_name=uncert_viewer_reference_name
            )
    elif isinstance(file_obj, str):
        if file_obj.lower().endswith('.gif'):  # pragma: no cover
            _parse_gif(app, file_obj, data_label,
                       flux_viewer_reference_name=flux_viewer_reference_name)
            return

        # try parsing file_obj as a URI/URL:
        file_obj = download_uri_to_path(
            file_obj, cache=cache, local_path=local_path, timeout=timeout
        )

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

                    if ext == 'SCI':
                        sci_ext = data_label

                    # TODO: generalize/centralize this for use in other configs too

                    if parent is not None:
                        parent_data_label = parent
                    elif ext == 'DQ':
                        parent_data_label = sci_ext
                    else:
                        parent_data_label = None

                    _parse_jwst_s3d(
                        app, hdulist, data_label, ext=ext, viewer_name=viewer_name,
                        flux_viewer_reference_name=flux_viewer_reference_name,
                        parent=parent_data_label
                    )
            elif telescop == 'jwst' and filetype == 'r3d' and system == 'esa-pipeline':
                for ext, viewer_name in (('DATA', flux_viewer_reference_name),
                                         ('ERR', uncert_viewer_reference_name),
                                         ('QUALITY', None)):
                    data_label = app.return_data_label(file_name, ext)
                    _parse_esa_s3d(
                        app, hdulist, data_label, ext=ext, viewer_name=viewer_name,
                        flux_viewer_reference_name=flux_viewer_reference_name,
                    )
            else:
                try:
                    _parse_spectrum1d_3d(
                        app, Spectrum1D.read(hdulist), data_label=data_label or file_name,
                        flux_viewer_reference_name=flux_viewer_reference_name,
                        uncert_viewer_reference_name=uncert_viewer_reference_name
                    )
                except Exception:  # nosec
                    _parse_hdulist(
                        app, hdulist, file_name=data_label or file_name,
                        flux_viewer_reference_name=flux_viewer_reference_name,
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
                       uncert_viewer_reference_name=uncert_viewer_reference_name)
    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def _get_celestial_wcs(wcs):
    """ If `wcs` has a celestial component return that, otherwise return None """
    return wcs.celestial if hasattr(wcs, 'celestial') else None


def _return_spectrum_with_correct_units(flux, wcs, metadata, data_type=None,
                                        target_wave_unit=None, hdulist=None,
                                        uncertainty=None, mask=None, apply_pix2=False):
    """Upstream issue of WCS not using the correct units for data must be fixed here.
    Issue: https://github.com/astropy/astropy/issues/3658.

    Also converts flux units to flux/pix2 solid angle units, if `flux` is not a surface
    brightness and `apply_pix2` is True.
    """
    # handle scale factors when they are included in the unit
    # (has to be done before Spectrum1D creation)
    if not np.isclose(flux.unit.scale, 1, rtol=1e-5):
        flux = flux.to(flux.unit / flux.unit.scale)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', message='Input WCS indicates that the spectral axis is not last',
            category=UserWarning)
        sc = Spectrum1D(flux=flux, wcs=wcs, meta=metadata, uncertainty=uncertainty, mask=mask)

    # convert flux and uncertainty to per-pix2 if input is not a surface brightness
    target_flux_unit = None
    if (apply_pix2 and (data_type != "mask") and
            (not check_if_unit_is_per_solid_angle(flux.unit))):
        target_flux_unit = flux.unit / PIX2
    elif check_if_unit_is_per_solid_angle(flux.unit, return_unit=True) == "spaxel":
        # We need to convert spaxel to pixel squared, since spaxel isn't fully supported by astropy
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
        new_sc.meta['_orig_spec'] = sc  # Need this for later

    return new_sc


def _parse_hdulist(app, hdulist, file_name=None,
                   flux_viewer_reference_name=None,
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
                warnings.warn("Invalid BUNIT, using count as data unit", UserWarning)
                flux_unit = u.count
        elif data_type == 'mask':  # DQ flags have no unit
            flux_unit = u.dimensionless_unscaled
        else:
            warnings.warn("Invalid BUNIT, using count as data unit", UserWarning)
            flux_unit = u.count

        flux = hdu.data << flux_unit

        metadata = standardize_metadata(hdu.header)
        if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
            metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

        # store original WCS in metadata. this is a hacky workaround for converting subsets
        # to sky regions, where the parent data of the subset might have dropped spatial WCS info
        metadata['_orig_spatial_wcs'] = _get_celestial_wcs(wcs)

        apply_pix2 = data_type in ['flux', 'uncert']
        sc = _return_spectrum_with_correct_units(flux, wcs, metadata, data_type=data_type,
                                                 hdulist=hdulist, apply_pix2=apply_pix2)

        app.add_data(sc, data_label)

        if data_type == 'mask':
            # We no longer auto-populate the mask cube into a viewer, but we still want
            # to keep track of this cube for use in, e.g., spectral extraction.
            app._jdaviz_helper._loaded_mask_cube = app.data_collection[data_label]

        elif data_type == 'uncert':
            app.add_data_to_viewer(uncert_viewer_reference_name, data_label)
            app._jdaviz_helper._loaded_uncert_cube = app.data_collection[data_label]

        else:  # flux
            # Forced wave unit conversion made it lose stuff, so re-add
            # also re-get unit from sc in case a factor of pix2 was applied
            app.data_collection[data_label].get_component("flux").units = sc.unit
            # Add flux to top left image viewer
            app.add_data_to_viewer(flux_viewer_reference_name, data_label)
            app._jdaviz_helper._loaded_flux_cube = app.data_collection[data_label]


def _parse_jwst_s3d(app, hdulist, data_label, ext='SCI',
                    viewer_name=None, flux_viewer_reference_name=None,
                    parent=None):
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

    # store original WCS in metadata. this is a hacky workaround for converting subsets
    # to sky regions, where the parent data of the subset might have dropped spatial WCS info
    metadata['_orig_spatial_wcs'] = _get_celestial_wcs(wcs)

    if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

    data = _return_spectrum_with_correct_units(
        flux, wcs, metadata, data_type=data_type, hdulist=hdulist)
    app.add_data(data, data_label, parent=parent)

    # get glue data and update if DQ:
    if ext == 'DQ':
        # prevent circular import:
        from jdaviz.configs.imviz.plugins.parsers import prep_data_layer_as_dq

        data = app.data_collection[-1]
        prep_data_layer_as_dq(data)

    if data_type == 'flux':  # Forced wave unit conversion made it lose stuff, so re-add
        app.data_collection[-1].get_component("flux").units = flux.unit

    if viewer_name is not None:
        app.add_data_to_viewer(viewer_name, data_label)

    if ext == 'DQ':
        app.add_data_to_viewer(flux_viewer_reference_name, data_label, visible=False)

    if data_type == 'flux':
        app._jdaviz_helper._loaded_flux_cube = app.data_collection[data_label]
    elif data_type == 'uncert':
        app._jdaviz_helper._loaded_uncert_cube = app.data_collection[data_label]


def _parse_esa_s3d(app, hdulist, data_label, ext='DATA', flux_viewer_reference_name=None):
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

    # store original WCS in metadata. this is a hacky workaround for converting subsets
    # to sky regions, where the parent data of the subset might have dropped spatial WCS info
    metadata['_orig_spatial_wcs'] = _get_celestial_wcs(wcs)

    data = _return_spectrum_with_correct_units(
        flux, wcs, metadata, data_type=data_type, hdulist=hdulist)

    app.add_data(data, data_label)

    if data_type == 'flux':  # Forced wave unit conversion made it lose stuff, so re-add
        app.data_collection[-1].get_component("flux").units = flux.unit

    app.add_data_to_viewer(flux_viewer_reference_name, data_label)

    if data_type == 'flux':
        app._jdaviz_helper._loaded_flux_cube = app.data_collection[data_label]
    elif data_type == 'uncert':
        app._jdaviz_helper._loaded_uncert_cube = app.data_collection[data_label]
    elif data_type == 'mask':
        app._jdaviz_helper._loaded_mask_cube = app.data_collection[data_label]


def _parse_spectrum1d_3d(app, file_obj, data_label=None,
                         flux_viewer_reference_name=None,
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
            flux = val.represent_as(StdDevUncertainty).quantity
            flux[np.isinf(flux)] = np.nan  # Avoid INF from IVAR conversion
        else:
            flux = val

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore', message='Input WCS indicates that the spectral axis is not last',
                category=UserWarning)
            meta = standardize_metadata(file_obj.meta)

            # store original WCS in metadata. this is a hacky workaround for
            # converting subsets to sky regions, where the parent data of the
            # subset might have dropped spatial WCS info
            meta['_orig_spatial_wcs'] = None
            if hasattr(file_obj, 'wcs'):
                meta['_orig_spatial_wcs'] = _get_celestial_wcs(file_obj.wcs)

            # Also convert data loaded in flux units to a per-square-pixel surface
            # brightness unit (e.g Jy to Jy/pix**2)
            s1d = _return_spectrum_with_correct_units(
                flux, file_obj.wcs, meta, data_type=attr, apply_pix2=True)

        cur_data_label = app.return_data_label(data_label, attr.upper())
        app.add_data(s1d, cur_data_label)

        if attr == 'flux':
            app.add_data_to_viewer(flux_viewer_reference_name, cur_data_label)
            app._jdaviz_helper._loaded_flux_cube = app.data_collection[cur_data_label]
        elif attr == 'uncertainty':
            app.add_data_to_viewer(uncert_viewer_reference_name, cur_data_label)
            app._jdaviz_helper._loaded_uncert_cube = app.data_collection[cur_data_label]
        elif attr == 'mask':
            app._jdaviz_helper._loaded_mask_cube = app.data_collection[cur_data_label]


def _parse_spectrum1d(app, file_obj, data_label=None, spectrum_viewer_reference_name=None):

    # Here 'file_obj' is a Spectrum1D

    if data_label is None:
        data_label = app.return_data_label(file_obj)

    # store original WCS in metadata. this is a hacky workaround for converting subsets
    # to sky regions, where the parent data of the subset might have dropped spatial WCS info
    file_obj.meta['_orig_spatial_wcs'] = _get_celestial_wcs(file_obj.wcs) if hasattr(file_obj, 'wcs') else None  # noqa: E501

    # TODO: glue-astronomy translators only look at the flux property of
    #  specutils Spectrum1D objects. Fix to support uncertainties and masks.

    # convert data loaded in flux units to a per-square-pixel surface
    # brightness unit (e.g Jy to Jy/pix**2)
    if not check_if_unit_is_per_solid_angle(file_obj.flux.unit):
        file_obj = file_obj.with_flux_unit(
            file_obj.flux.unit / PIX2, equivalencies=_eqv_flux_to_sb_pixel())

    app.add_data(file_obj, data_label)
    app.add_data_to_viewer(spectrum_viewer_reference_name, data_label)


def _parse_ndarray(app, file_obj, data_label=None, data_type=None,
                   flux_viewer_reference_name=None,
                   uncert_viewer_reference_name=None):
    if data_label is None:
        data_label = app.return_data_label(file_obj)

    if data_type is None:
        data_type = 'flux'

    # Cannot change axis to ensure roundtripping within Cubeviz.
    # Axes must already be (x, y, z) at this point.
    flux = file_obj

    if not hasattr(flux, 'unit'):
        flux = flux << (u.count / PIX2)

    meta = standardize_metadata({'_orig_spatial_wcs': None})
    s3d = Spectrum1D(flux=flux, meta=meta)

    # convert data loaded in flux units to a per-square-pixel surface
    # brightness unit (e.g Jy to Jy/pix**2)
    if not check_if_unit_is_per_solid_angle(s3d.flux.unit):
        s3d = s3d.with_flux_unit(s3d.flux.unit / PIX2, equivalencies=_eqv_flux_to_sb_pixel())

    app.add_data(s3d, data_label)

    if data_type == 'flux':
        app.add_data_to_viewer(flux_viewer_reference_name, data_label)
        app._jdaviz_helper._loaded_flux_cube = app.data_collection[data_label]
    elif data_type == 'uncert':
        app.add_data_to_viewer(uncert_viewer_reference_name, data_label)
        app._jdaviz_helper._loaded_uncert_cube = app.data_collection[data_label]
    elif data_type == 'mask':
        app._jdaviz_helper._loaded_mask_cube = app.data_collection[data_label]


def _parse_gif(app, file_obj, data_label=None, flux_viewer_reference_name=None):  # pragma: no cover
    # NOTE: Parsing GIF needs imageio and Pillow, both are which undeclared
    # in setup.cfg but might or might not be installed by declared ones.
    import imageio

    file_name = os.path.basename(file_obj)

    if data_label is None:
        data_label = app.return_data_label(file_obj)

    flux = imageio.v3.imread(file_obj, mode='P')  # All frames as gray scale
    flux = np.rot90(np.moveaxis(flux, 0, 2), k=-1, axes=(0, 1))

    meta = {'filename': file_name, '_orig_spatial_wcs': None}
    s3d = Spectrum1D(flux=flux * (u.count / PIX2), meta=standardize_metadata(meta))

    app.add_data(s3d, data_label)
    app.add_data_to_viewer(flux_viewer_reference_name, data_label)


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
