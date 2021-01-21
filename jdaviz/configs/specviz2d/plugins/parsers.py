from glue.core.data import Data

from jdaviz.core.registries import data_parser_registry

from spectral_cube import SpectralCube
from astropy.nddata import CCDData
from specutils import Spectrum1D
from astropy.io import fits
import numpy as np
import logging
from astropy.wcs import WCS
from pathlib import Path

__all__ = ['mos_spec1d_parser', 'mos_spec2d_parser']

def _check_is_file(path):
    return isinstance(path, str) and Path(path).is_file()


@data_parser_registry("spec1d-parser")
def mos_spec1d_parser(app, data_obj, data_labels=None):
    """
    Attempts to parse a 1D spectrum object.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or spectrum-like
        File path, list, or spectrum-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    """
    # If providing a file path, parse it using the specutils io tooling
    if _check_is_file(data_obj):
        data_obj = [Spectrum1D.read(data_obj)]

    if isinstance(data_labels, str):
        data_labels = [data_labels]

    # Coerce into list-like object. This works because `Spectrum1D` objects
    #  don't have a length dunder method.
    if not hasattr(data_obj, '__len__'):
        data_obj = [data_obj]
    else:
        data_obj = [Spectrum1D.read(x)
                    if _check_is_file(x) else x
                    for x in data_obj]

    if data_labels is None:
        data_labels = [f"1D Spectrum {i}" for i in range(len(data_obj))]
    elif len(data_obj) != len(data_labels):
        data_labels = [f"{data_labels[0]} {i}" for i in range(len(data_obj))]

    # Handle the case where the 1d spectrum is a collection of spectra
    for i in range(len(data_obj)):
        app.data_collection[data_labels[i]] = data_obj[i]


@data_parser_registry("spec2d-parser")
def mos_spec2d_parser(app, data_obj, data_labels=None):
    """
    Attempts to parse a 2D spectrum object.

    Notes
    -----
    This currently only works with JWST-type data in which the data is in the
    second hdu of the fits file.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or spectrum-like
        File path, list, or spectrum-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    """
    # In the case where the data object is a string, attempt to parse it as
    #  a fits file.
    # TODO: this current does not handle the case where the file in the path is
    #  anything but a fits file whose wcs can be extracted.
    def _parse_as_cube(path):
        with fits.open(path) as hdulist:
            data = hdulist[1].data
            header = hdulist[1].header
            if header['NAXIS'] == 2:
                new_data = np.expand_dims(data, axis=1)
                header['NAXIS'] = 3

            header['NAXIS3'] = 1
            header['BUNIT'] = 'dN/s'
            header['CUNIT3'] = 'um'
            wcs = WCS(header)

            meta = {'S_REGION': header['S_REGION']}


        return SpectralCube(new_data, wcs=wcs, meta=meta)

    if _check_is_file(data_obj):
        data_obj = [_parse_as_cube(data_obj)]

    if isinstance(data_labels, str):
        data_labels = [data_labels]

    # Coerce into list-like object
    if not isinstance(data_obj, (list, set)):
        data_obj = [data_obj]
    else:
        data_obj = [_parse_as_cube(x)
                    if _check_is_file(x) else x
                    for x in data_obj]

    if data_labels is None:
        data_labels = [f"2D Spectrum {i}" for i in range(len(data_obj))]
    elif len(data_obj) != len(data_labels):
        data_labels = [f"{data_labels} {i}" for i in range(len(data_obj))]

    for i in range(len(data_obj)):
        app.data_collection[data_labels[i]] = data_obj[i]

