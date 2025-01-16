import os
import warnings

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.nddata import NDData, NDDataArray
from stdatamodels.jwst.datamodels import Level1bModel

from jdaviz.core.registries import data_parser_registry
from jdaviz.utils import (
    standardize_metadata, download_uri_to_path,
    PRIHDR_KEY, standardize_roman_metadata
)
from jdaviz.configs.imviz.plugins.parsers import _parse_image as _parse_image_imviz

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True

__all__ = ['parse_data']


@data_parser_registry("ramp-data-parser")
def parse_data(app, file_obj, data_type=None, data_label=None,
               ext=None, parent=None, cache=None, local_path=None, timeout=None,
               integration=0):
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
    integration : int, optional
        JWST Level 1b products bundle multiple integrations in a time-series into the
        same ramp file. If this keyword is specified and the observations
        are JWST Level 1b products, this integration in the time series will be selected.
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
        )
    elif isinstance(file_obj, str):
        if file_obj.lower().endswith('.asdf'):
            if not HAS_ROMAN_DATAMODELS:
                raise ImportError(
                    "ASDF detected but roman-datamodels is not installed."
                )
            with rdd.open(file_obj) as pf:
                _roman_3d_to_glue_data(
                    app, pf, data_label,
                    group_viewer_reference_name=group_viewer_reference_name,
                    diff_viewer_reference_name=diff_viewer_reference_name,
                    meta=dict(pf.meta)
                )
            return

        # try parsing file_obj as a URI/URL:
        file_obj = download_uri_to_path(
            file_obj, cache=cache, local_path=local_path, timeout=timeout
        )

        file_name = os.path.basename(file_obj)

        with fits.open(file_obj) as hdulist:
            _parse_hdulist(
                app, hdulist,
                ext=ext, parent=parent,
                file_name=data_label or file_name,
                integration=integration,
                group_viewer_reference_name=group_viewer_reference_name,
                diff_viewer_reference_name=diff_viewer_reference_name,
            )

    elif isinstance(file_obj, np.ndarray) and file_obj.ndim == 3:
        # load 3D cube to group viewer
        _parse_ndarray(
            app, file_obj, data_label=data_label, data_type=data_type,
            viewer_reference_name=group_viewer_reference_name,
            meta=getattr(file_obj, 'meta')
        )

    elif isinstance(file_obj, (np.ndarray, NDData)) and file_obj.ndim in (1, 2):
        # load 1D profile(s) to integration_viewer
        _parse_ndarray(
            app, file_obj, data_label=data_label,
            viewer_reference_name=integration_viewer_reference_name,
            meta=getattr(file_obj, 'meta')
        )

    elif isinstance(file_obj, Level1bModel):
        metadata = standardize_metadata({
            key: value for key, value in file_obj.to_flat_dict(
                include_arrays=False)
            .items()
            if key.startswith('meta')
        })

        _parse_ramp_cube(
            app, file_obj.data[integration], u.DN,
            data_label or file_obj.__class__.__name__,
            group_viewer_reference_name,
            diff_viewer_reference_name,
            meta=metadata
        )

    elif HAS_ROMAN_DATAMODELS and isinstance(file_obj, rdd.DataModel):
        with rdd.open(file_obj) as pf:
            _roman_3d_to_glue_data(
                app, pf, data_label, meta=pf.meta,
                group_viewer_reference_name=group_viewer_reference_name,
                diff_viewer_reference_name=diff_viewer_reference_name,
            )

    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def move_group_axis_last(x):
    # swap axes per the conventions of ramp cubes
    # (group axis comes first) and the default in
    # rampviz (group axis expected last)
    return np.transpose(x, (1, 2, 0))


def _roman_3d_to_glue_data(
    app, file_obj, data_label,
    group_viewer_reference_name=None,
    diff_viewer_reference_name=None,
    meta=None
):
    """
    Parse a Roman 3D ramp cube file (Level 1),
    usually with suffix '_uncal.asdf'.
    """
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

    data_reshaped = move_group_axis_last(data)
    diff_data_reshaped = move_group_axis_last(diff_data)

    # if the ramp cube has no units, assume DN:
    if getattr(data_reshaped, 'unit', None) is None:
        assumed_unit = u.DN
        data_reshaped <<= assumed_unit
        diff_data_reshaped <<= assumed_unit

    # load these cubes into the cache:
    app._jdaviz_helper.cube_cache[ramp_cube_data_label] = NDDataArray(
        data_reshaped
    )
    app._jdaviz_helper.cube_cache[ramp_diff_data_label] = NDDataArray(
        diff_data_reshaped
    )

    if meta is not None:
        meta = standardize_roman_metadata(file_obj)

    # load these cubes into the app:
    _parse_ndarray(
        app,
        file_obj=data_reshaped,
        data_label=ramp_cube_data_label,
        viewer_reference_name=group_viewer_reference_name,
        meta=meta
    )
    _parse_ndarray(
        app,
        file_obj=diff_data_reshaped,
        data_label=ramp_diff_data_label,
        viewer_reference_name=diff_viewer_reference_name,
        meta=meta
    )

    # the default collapse function in the profile viewer is "sum",
    # but for ramp files, "median" is more useful:
    viewer = app.get_viewer('integration-viewer')
    viewer.state.function = 'median'


def _parse_hdulist(
    app, hdulist,
    ext=None, parent=None,
    file_name=None,
    integration=None,
    group_viewer_reference_name=None,
    diff_viewer_reference_name=None,
):
    if file_name is None and hasattr(hdulist, 'file_name'):
        file_name = hdulist.file_name
    else:
        file_name = file_name or "Unknown HDU object"

    hdu = hdulist[1]  # extension containing the ramp

    if hdu.header['NAXIS'] == 2:
        # this may be a calibrated Level 2 image:
        _parse_image_imviz(app, hdulist, data_label=file_name, ext=ext, parent=parent)
        new_viewer_name = 'level-2'

        # create a level-2 viewer if none exists:
        if new_viewer_name not in app.get_viewer_reference_names():
            app._jdaviz_helper.create_image_viewer(viewer_name=new_viewer_name)

        # add the SCI extension to the level-2 viewer:
        if not ext:
            idx = 1
        elif ext and ('SCI' in ext or ext == '*'):
            idx = len(ext) - ext.index('SCI')

        app.add_data_to_viewer(new_viewer_name, app.data_collection[-idx].label)
        return

    elif hdu.header['NAXIS'] != 4:
        raise ValueError(f"Expected a ramp with NAXIS=4 (with dimensions: "
                         f"integrations, groups, x, y), but got "
                         f"NAXIS={hdu.header['NAXIS']}.")

    if 'BUNIT' in hdu.header:
        try:
            flux_unit = u.Unit(hdu.header['BUNIT'])
        except Exception:
            warnings.warn("Invalid BUNIT, using DN as data unit", UserWarning)
            flux_unit = u.DN
    else:
        warnings.warn("Invalid BUNIT, using DN as data unit", UserWarning)
        flux_unit = u.DN

    # index the ramp array by the integration to load. returns all groups and pixels.
    # cast from uint16 to integers:
    ramp_cube = hdu.data[integration].astype(int)

    metadata = standardize_metadata(hdu.header)
    if hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)

    _parse_ramp_cube(
        app, ramp_cube, flux_unit, file_name,
        group_viewer_reference_name,
        diff_viewer_reference_name,
        meta=metadata
    )


def _parse_ramp_cube(app, ramp_cube_data, flux_unit, file_name,
                     group_viewer_reference_name, diff_viewer_reference_name,
                     meta=None):
    # last axis is the group axis, first two are spatial axes:
    diff_data = np.vstack([
        # begin with a group of zeros, so
        # that `diff_data.ndim == data.ndim`
        np.zeros((1, *ramp_cube_data[0].shape)),
        np.diff(ramp_cube_data, axis=0)
    ])

    ramp_cube = NDDataArray(move_group_axis_last(ramp_cube_data), unit=flux_unit, meta=meta)
    diff_cube = NDDataArray(move_group_axis_last(diff_data), unit=flux_unit, meta=meta)

    group_data_label = app.return_data_label(file_name, ext="DATA")
    diff_data_label = app.return_data_label(file_name, ext="DIFF")

    for data_entry, data_label, viewer_ref in zip(
            (ramp_cube, diff_cube),
            (group_data_label, diff_data_label),
            (group_viewer_reference_name, diff_viewer_reference_name)
    ):
        app.add_data(data_entry, data_label)
        app.add_data_to_viewer(viewer_ref, data_label)

        # load these cubes into the cache:
        app._jdaviz_helper.cube_cache[data_label] = data_entry

        # set as reference data in this viewer
        viewer = app.get_viewer(viewer_ref)
        viewer.state.reference_data = app.data_collection[data_label]

    app._jdaviz_helper._loaded_flux_cube = app.data_collection[group_data_label]


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
