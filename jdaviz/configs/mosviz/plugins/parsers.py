from glue.core.data import Data

from jdaviz.core.registries import data_parser_registry

from spectral_cube import SpectralCube
from astropy.nddata import CCDData
from specutils import Spectrum1D
from astropy.io import fits
import numpy as np
import logging

__all__ = ['mos_spec1d_parser', 'mos_spec2d_parser', 'mos_image_parser']


def _add_to_table(app, data, comp_label):
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
        The label applied to the glue data component.
    """
    # If providing a file path, parse it using the specutils io tooling
    if isinstance(data_obj, str):
        data_obj = Spectrum1D.read(data_obj)

    if data_labels is None or len(data_obj) != len(data_labels):
        data_labels = [f"1D Spectrum {i}" for i in range(len(data_obj))]

    # Handle the case where the 1d spectrum is a collection of spectra
    if hasattr(data_obj, '__len__'):
        for i in range(len(data_obj)):
            app.data_collection[data_labels[i]] = data_obj[i]

    _add_to_table(app, data_labels, '1D Spectra')


@data_parser_registry("mosviz-spec2d-parser")
def mos_spec2d_parser(app, data_obj, data_labels=None, header_kwargs=None):
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
        The label applied to the glue data component.
    """
    # In the case where the data object is a string, attempt to parse it as
    #  a fits file.
    # TODO: this current does not handle the case where the file in the path is
    #  anything but a fits file whose wcs can be extracted.
    if isinstance(data_obj, str):
        with fits.open(data_obj) as hdulist:
            data = hdulist[1].data
            new_data = np.expand_dims(data, axis=1)
            hdulist[1].header['NAXIS'] = 3
            hdulist[1].header['NAXIS3'] = 1
            hdulist[1].header['BUNIT'] = 'dN/s'
            hdulist[1].header['CUNIT3'] = 'um'
            wcs = WCS(hdulist[1].header)

        data_obj = SpectralCube(new_data, wcs=wcs)

    if data_labels is None or len(data_obj) != len(data_labels):
        data_labels = [f"2D Spectrum {i}" for i in range(len(data_obj))]

    if hasattr(data_obj, '__len__'):
        for i in range(len(data_obj)):
            app.data_collection[data_labels[i]] = data_obj[i]

    _add_to_table(app, data_labels, '2D Spectra')


@data_parser_registry("mosviz-image-parser")
def mos_image_parser(app, data_obj, data_labels=None):
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

    if data_labels is None or len(data_obj) != len(data_labels):
        data_labels = [f"Image {i}" for i in range(len(data_obj))]

    if hasattr(data_obj, '__len__'):
        for i in range(len(data_obj)):
            app.data_collection[data_labels[i]] = data_obj[i]

    _add_to_table(app, data_labels, 'Images')
