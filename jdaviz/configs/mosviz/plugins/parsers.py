from glue.core.data import Data

from jdaviz.core.registries import data_parser_registry

from spectral_cube import SpectralCube
from astropy.nddata import CCDData
from specutils import Spectrum1D
from astropy.io import fits
import numpy as np
import logging
from astropy.wcs import WCS

__all__ = ['mos_spec1d_parser', 'mos_spec2d_parser', 'mos_image_parser']


def _add_to_table(app, data, comp_label):
    """
    Creates a mos table instance in the application data collection is none
    currently exists.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The JDAViz application instance.
    data : array-list
        The set of data to added as a table (i.g. column) component.
    comp_label : str
        The label used to desribe the data. Also used as the column header.
    """
    # Add data to the mos viz table object
    if 'MOS Table' not in app.data_collection:
        table_data = Data(label="MOS Table")
        app.data_collection.append(table_data)

        mos_table = app.data_collection['MOS Table']
        mos_table.add_component(data, comp_label)

        viewer = app.get_viewer("table-viewer")
        viewer.add_data(table_data)
    else:
        mos_table = app.data_collection['MOS Table']
        mos_table.add_component(data, comp_label)


@data_parser_registry("mosviz-spec1d-parser")
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
    if isinstance(data_obj, str):
        data_obj = [Spectrum1D.read(data_obj)]

    if isinstance(data_labels, str):
        data_labels = [data_labels]

    # Coerce into list-like object
    if not hasattr(data_obj, '__len__'):
        data_obj = [data_obj]

    if data_labels is None or len(data_obj) != len(data_labels):
        data_labels = [f"1D Spectrum {i}" for i in range(len(data_obj))]

    # Handle the case where the 1d spectrum is a collection of spectra
    for i in range(len(data_obj)):
        app.data_collection[data_labels[i]] = data_obj[i]

    _add_to_table(app, data_labels, '1D Spectra')


@data_parser_registry("mosviz-spec2d-parser")
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
    if isinstance(data_obj, str):
        with fits.open(data_obj) as hdulist:
            data = hdulist[1].data

            if hdulist[1].header['NAXIS'] == 2:
                new_data = np.expand_dims(data, axis=1)
                hdulist[1].header['NAXIS'] = 3

            hdulist[1].header['NAXIS3'] = 1
            hdulist[1].header['BUNIT'] = 'dN/s'
            hdulist[1].header['CUNIT3'] = 'um'
            wcs = WCS(hdulist[1].header)

        data_obj = [SpectralCube(new_data, wcs=wcs)]

    # Coerce into list-like object
    if not isinstance(data_obj, (list, set)):
        data_obj = [data_obj]

    if isinstance(data_labels, str):
        data_labels = [data_labels]

    if data_labels is None or len(data_obj) != len(data_labels):
        data_labels = [f"2D Spectrum {i}" for i in range(len(data_obj))]

    for i in range(len(data_obj)):
        app.data_collection[data_labels[i]] = data_obj[i]

    _add_to_table(app, data_labels, '2D Spectra')


@data_parser_registry("mosviz-image-parser")
def mos_image_parser(app, data_obj, data_labels=None):
    """
    Attempts to parse an image-like object.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or image-like
        File path, list, or image-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    """
    # Parse and load the 2d images. `CCData` objects require a unit be defined
    #  in the fits header, however, if none is provided, use a fallback and
    #  raise an error.
    if isinstance(data_obj, str):
        with fits.open(data_obj) as hdulist:
            if 'BUNIT' not in hdulist[0].header:
                logging.warning("No 'BUNIT' defined in the header, using 'Jy'.")

            unit = hdulist[0].header.get('BUNIT', 'Jy')

        data_obj = CCDData.read(data_obj, unit=unit)

    # Coerce into list-like object
    if not hasattr(data_obj, '__len__'):
        data_obj = [data_obj]

    if isinstance(data_labels, str):
        data_labels = [data_labels]

    if data_labels is None or len(data_obj) != len(data_labels):
        data_labels = [f"Image {i}" for i in range(len(data_obj))]

    for i in range(len(data_obj)):
        app.data_collection[data_labels[i]] = data_obj[i]

    _add_to_table(app, data_labels, 'Images')
