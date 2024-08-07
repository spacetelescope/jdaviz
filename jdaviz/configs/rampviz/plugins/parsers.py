import logging
import os
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.nddata import NDData, NDDataArray
from astropy.time import Time

from jdaviz.core.registries import data_parser_registry
from jdaviz.configs.cubeviz.plugins.parsers import _get_data_type_by_hdu
from jdaviz.utils import standardize_metadata, download_uri_to_path, PRIHDR_KEY

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True

__all__ = ['parse_data']


@data_parser_registry("ramp-data-parser")
def parse_data(app, file_obj, data_type=None, data_label=None,
               parent=None, cache=None, local_path=None, timeout=None):
    """
    Attempts to parse a data file and auto-populate available viewers in
    rampviz.

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

    group_viewer_reference_name = app._jdaviz_helper._default_group_viewer_reference_name
    diff_viewer_reference_name = app._jdaviz_helper._default_diff_viewer_reference_name
    integration_viewer_reference_name = (
        app._jdaviz_helper._default_integration_viewer_reference_name
    )

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
            group_viewer_reference_name=group_viewer_reference_name,
            diff_viewer_reference_name=diff_viewer_reference_name,
            integration_viewer_reference_name=integration_viewer_reference_name
        )
    elif isinstance(file_obj, str):
        if file_obj.lower().endswith('.asdf'):
            if not HAS_ROMAN_DATAMODELS:
                raise ImportError(
                    "ASDF detected but roman-datamodels is not installed."
                )
            with rdd.open(file_obj) as pf:
                _roman_3d_to_glue_data(
                    app, pf, data_label, parent=parent,
                    group_viewer_reference_name=group_viewer_reference_name,
                    diff_viewer_reference_name=diff_viewer_reference_name,
                    integration_viewer_reference_name=integration_viewer_reference_name
                )
            return

        # try parsing file_obj as a URI/URL:
        file_obj = download_uri_to_path(
            file_obj, cache=cache, local_path=local_path, timeout=timeout
        )

        file_name = os.path.basename(file_obj)

        with fits.open(file_obj) as hdulist:
            _parse_hdulist(
                app, hdulist, file_name=data_label or file_name,
                group_viewer_reference_name=group_viewer_reference_name,
                diff_viewer_reference_name=diff_viewer_reference_name,
                integration_viewer_reference_name=integration_viewer_reference_name
            )

    elif isinstance(file_obj, np.ndarray) and file_obj.ndim == 3:
        # load 3D cube to group viewer
        _parse_ndarray(
            app, file_obj, data_label=data_label, data_type=data_type,
            viewer_reference_name=group_viewer_reference_name,
        )

    elif isinstance(file_obj, (np.ndarray, NDData)) and file_obj.ndim in (1, 2):
        # load 1D profile(s) to integration_viewer
        _parse_ndarray(
            app, file_obj, data_label=data_label,
            viewer_reference_name=integration_viewer_reference_name
        )

    elif HAS_ROMAN_DATAMODELS and isinstance(file_obj, rdd.DataModel):
        with rdd.open(file_obj) as pf:
            _roman_3d_to_glue_data(
                app, pf, data_label,
                group_viewer_reference_name=group_viewer_reference_name,
                diff_viewer_reference_name=diff_viewer_reference_name,
                integration_viewer_reference_name=integration_viewer_reference_name
            )

    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def _roman_3d_to_glue_data(
    app, file_obj, data_label, parent=None,
    group_viewer_reference_name=None,
    diff_viewer_reference_name=None,
    integration_viewer_reference_name=None,
):
    """
    Parse a Roman 3D ramp cube file (Level 1),
    usually with suffix '_uncal.asdf'.
    """
    def _swap_axes(x):
        # swap axes per the conventions of Roman cubes
        # (group axis comes first) and the default in
        # Cubeviz (wavelength axis expected last)
        return np.swapaxes(x, 0, -1)

    # update viewer reference names for Roman ramp cubes:
    # app._update_viewer_reference_name()

    data = file_obj.data

    if data_label is None:
        data_label = app.return_data_label(file_obj)

    # last axis is the group axis, first two are spatial axes:
    diff_data = np.vstack([
        # begin with a group of zeros, so
        # that `diff_data.ndim == data.ndim`
        np.zeros((1, *data[0].shape)),
        np.diff(data, axis=0)
    ])

    ramp_cube_data_label = f"{data_label}[DATA]"
    ramp_diff_data_label = f"{data_label}[DIFF]"

    # load these cubes into the cache:
    app._jdaviz_helper.cube_cache[ramp_cube_data_label] = NDDataArray(_swap_axes(data))
    app._jdaviz_helper.cube_cache[ramp_diff_data_label] = NDDataArray(_swap_axes(diff_data))

    # load these cubes into the app:
    _parse_ndarray(
        app,
        file_obj=_swap_axes(data),
        data_label=ramp_cube_data_label,
        viewer_reference_name=group_viewer_reference_name,
    )
    _parse_ndarray(
        app,
        file_obj=_swap_axes(diff_data),
        data_label=ramp_diff_data_label,
        viewer_reference_name=diff_viewer_reference_name,
    )

    # the default collapse function in the profile viewer is "sum",
    # but for ramp files, "median" is more useful:
    viewer = app.get_viewer('integration-viewer')
    viewer.state.function = 'median'


def _parse_hdulist(
    app, hdulist, file_name=None,
    viewer_reference_name=None
):
    if file_name is None and hasattr(hdulist, 'file_name'):
        file_name = hdulist.file_name
    else:
        file_name = file_name or "Unknown HDU object"

    is_loaded = []

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

        if 'BUNIT' in hdu.header:
            try:
                flux_unit = u.Unit(hdu.header['BUNIT'])
            except Exception:
                logging.warning("Invalid BUNIT, using DN as data unit")
                flux_unit = u.DN
        else:
            logging.warning("Invalid BUNIT, using DN as data unit")
            flux_unit = u.DN

        flux = hdu.data << flux_unit
        metadata = standardize_metadata(hdu.header)
        if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
            metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

        app.add_data(flux, data_label)
        app.data_collection[data_label].get_component("data").units = flux_unit
        app.add_data_to_viewer(viewer_reference_name, data_label)
        app._jdaviz_helper._loaded_flux_cube = app.data_collection[data_label]


def _parse_jwst_level1(
    app, hdulist, data_label, ext='SCI',
    viewer_name=None,
):
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

    unit = u.Unit(hdu.header.get('BUNIT', 'count'))
    flux = hdu.data << unit

    metadata = standardize_metadata(hdu.header)
    app.data_collection[data_label] = NDData(data=flux, meta=metadata)

    if data_type == 'flux':
        app.data_collection[-1].get_component("data").units = flux.unit

    if viewer_name is not None:
        app.add_data_to_viewer(viewer_name, data_label)

    if data_type == 'flux':
        app._jdaviz_helper._loaded_flux_cube = app.data_collection[data_label]


def _parse_ndarray(
    app, file_obj, data_label=None,
    viewer_reference_name=None,
    meta=None
):
    if data_label is None:
        data_label = app.return_data_label(file_obj)

    # Cannot change axis to ensure roundtripping within Rampviz.
    # Axes must already be (x, y, z) at this point.

    if isinstance(file_obj, NDData):
        ndd = file_obj
    else:
        ndd = NDDataArray(data=file_obj, meta=meta)
    app.add_data(ndd, data_label)

    app.add_data_to_viewer(viewer_reference_name, data_label)
    app._jdaviz_helper._loaded_flux_cube = app.data_collection[data_label]
