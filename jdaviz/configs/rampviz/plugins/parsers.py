import os
import numpy as np
from astropy.io import fits

from jdaviz.utils import download_uri_to_path
from jdaviz.configs.cubeviz.plugins.parsers import (
    _parse_ndarray, _parse_hdulist, _parse_gif
)
from jdaviz.core.registries import data_parser_registry

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True


@data_parser_registry("rampviz-data-parser")
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

    flux_viewer_reference_name = app._jdaviz_helper._default_group_viewer_reference_name
    uncert_viewer_reference_name = app._jdaviz_helper._default_diff_viewer_reference_name
    spectrum_viewer_reference_name = app._jdaviz_helper._default_profile_viewer_reference_name

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
            uncert_viewer_reference_name=uncert_viewer_reference_name
        )
    elif isinstance(file_obj, str):
        if file_obj.lower().endswith('.gif'):  # pragma: no cover
            _parse_gif(app, file_obj, data_label,
                       flux_viewer_reference_name=flux_viewer_reference_name)
            return
        elif file_obj.lower().endswith('.asdf'):
            if not HAS_ROMAN_DATAMODELS:
                raise ImportError(
                    "ASDF detected but roman-datamodels is not installed."
                )
            with rdd.open(file_obj) as pf:
                _roman_3d_to_glue_data(
                    app, pf, data_label,
                    flux_viewer_reference_name=flux_viewer_reference_name,
                    spectrum_viewer_reference_name=spectrum_viewer_reference_name,
                    uncert_viewer_reference_name=uncert_viewer_reference_name
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
                flux_viewer_reference_name=flux_viewer_reference_name,
                uncert_viewer_reference_name=uncert_viewer_reference_name
            )

    elif isinstance(file_obj, np.ndarray) and file_obj.ndim == 3:
        _parse_ndarray(app, file_obj, data_label=data_label, data_type=data_type,
                       flux_viewer_reference_name=flux_viewer_reference_name,
                       uncert_viewer_reference_name=uncert_viewer_reference_name)

        app.get_tray_item_from_name("Spectral Extraction").disabled_msg = ""

    elif HAS_ROMAN_DATAMODELS and isinstance(file_obj, rdd.DataModel):
        with rdd.open(file_obj) as pf:
            _roman_3d_to_glue_data(
                app, pf, data_label,
                flux_viewer_reference_name=flux_viewer_reference_name,
                spectrum_viewer_reference_name=spectrum_viewer_reference_name,
                uncert_viewer_reference_name=uncert_viewer_reference_name
            )

    else:
        raise NotImplementedError(f'Unsupported data format: {file_obj}')


def _roman_3d_to_glue_data(
    app, file_obj, data_label,
    flux_viewer_reference_name=None,
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

    # load the `data` cube into what's usually the "flux-viewer"
    _parse_ndarray(
        app,
        file_obj=_swap_axes(data),
        data_label=f"{data_label}[DATA]",
        data_type="flux",
        flux_viewer_reference_name=flux_viewer_reference_name,
    )

    # load the diff of the data cube
    # into what's usually the "uncert-viewer"
    _parse_ndarray(
        app,
        file_obj=_swap_axes(diff_data),
        data_type="uncert",
        data_label=f"{data_label}[DIFF]",
        uncert_viewer_reference_name=diff_viewer_reference_name,
    )

    # the default collapse function in the profile viewer is "sum",
    # but for ramp files, "median" is more useful:
    viewer = app.get_viewer('integration-viewer')
    viewer.state.function = 'median'
