import csv
import logging
import numpy as np
from pathlib import Path

from glue.core.data import Data
from astropy.nddata import CCDData
from astropy.wcs import WCS
from astropy.io import fits
from spectral_cube import SpectralCube
from specutils import Spectrum1D, SpectrumList


from jdaviz.core.registries import data_parser_registry
from jdaviz.core.events import SnackbarMessage

__all__ = ['mos_spec1d_parser', 'mos_spec2d_parser', 'mos_image_parser']


def _add_to_table(app, data, comp_label):
    """
    Creates a mos table instance in the application data collection if none
    currently exists.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The JDAViz application instance.
    data : array-list
        The set of data to added as a table (i.g. column) component.
    comp_label : str
        The label used to describe the data. Also used as the column header.
    """
    # Add data to the mos viz table object
    if 'MOS Table' not in app.data_collection:
        table_data = Data(label='MOS Table')
        app.data_collection.append(table_data)

        mos_table = app.data_collection['MOS Table']
        mos_table.add_component(data, comp_label)

        viewer = app.get_viewer("table-viewer")
        viewer.add_data(table_data)
    else:
        mos_table = app.data_collection['MOS Table']
        mos_table.add_component(data, comp_label)


def _check_is_file(path):
    return isinstance(path, str) and Path(path).is_file()

def _warn_if_not_found(app, file_lists):
    """
    Take a list of labels and associated file lists and send a snackbar
    message if the length of any list is 0.
    """
    found = []
    not_found = []
    for key in file_lists:
        if len(file_lists[key]) == 0:
            not_found.append(key)
        else:
            found.append(key)

    if len(found) == 0:
        raise ValueError("No valid NIRISS files found in specified directory")
    if len(not_found) > 0:
        warn_msg = "Some files not found: {}".format(", ".join(not_found))
        warn_msg = SnackbarMessage(warn_msg, color="warning", sender=app)
        app.hub.broadcast(warn_msg)

    return found

def _fields_from_ecsv(fname, fields, delimiter=","):
    parsed_fields = []
    with open(fname, "r") as f:
        reader = csv.DictReader(filter(lambda row: row[0]!="#", f),
                                delimiter=delimiter)
        for row in reader:
            temp_list = []
            for field in fields:
                temp_list.append(row[field])
            parsed_fields.append(temp_list)
    return parsed_fields

@data_parser_registry("mosviz-niriss-parser")
def mos_niriss_parser(app, data_dir, obs_label=""):
    """
    Attempts to parse all data for a NIRISS dataset in the specified
    directory, which should include:
    - *_direct_*_cal.fits : Direct 2D image
    - *_direct_*_cat.ecsv : Source catalog
    - *_WFSSR_*_cal.fits : 2D spectra in first orientation
    - *_WFSSC_*_cal.fits : 2D spectra in second orientation
    - *_WFSSR_*_x1d.fits : 1D spectra in first orientatiom
    - *_WFSSC_*_x1d.fits : 1D spectra in second orientatiom

    The spectra from the "C" files (horizontal orientation) are showed
    in the viewers by default.
    """
    p = Path(data_dir)
    if not p.is_dir():
        raise ValueError("{} is not a valid directory path".format(data_dir))
    source_cat = list(p.glob("{}*_direct_*_cat.ecsv".format(obs_label)))
    direct_image = list(p.glob("{}*_direct_*_cal.fits".format(obs_label)))
    spec2d_r = list(p.glob("{}*_WFSSR_*_cal.fits".format(obs_label)))
    spec2d_c = list(p.glob("{}*_WFSSC_*_cal.fits".format(obs_label)))
    spec1d_r = list(p.glob("{}*_WFSSR_*_x1d.fits".format(obs_label)))
    spec1d_c = list(p.glob("{}*_WFSSC_*_x1d.fits".format(obs_label)))

    file_lists = {
                  "Source Catalog": source_cat,
                  "Direct Image": direct_image,
                  "2D Spectra C": spec2d_c,
                  "2D Spectra R": spec2d_r,
                  "1D Spectra C": spec1d_c,
                  "1D Spectra R": spec1d_r
                 }

    # Convert from pathlib Paths back to strings
    for key in file_lists:
        file_lists[key] = [str(x) for x in file_lists[key]]

    found_files = _warn_if_not_found(app, file_lists)

    # Read in direct image (NIRISS only has one image containing all sources)
    for image_file in file_lists["Direct Image"]:
        im_split = image_file.split("_")
        image_label = "Image {} {}".format(im_split[0], im_split[1])
        image_data = CCDData.read(direct_image[0])
        app.data_collection[image_label] = image_data

    # Parse relevant information from source catalog
    cat_fields = ["id", "sky_centroid.ra", "sky_centroid.dec"]
    cat_file = file_lists["Source Catalog"][0]
    parsed_cat_fields = _fields_from_ecsv(cat_file, cat_fields, delimiter=" ")

    # Parse 2D spectra

    # Parse 1D spectra using SpectumList reader
    spec1d_C = {}
    spec2d_R = {}
    for f in ["1D Spectra C", "1D Spectra R"]:
        spec_labels = []
        for fname in file_lists[f]:
            specs = SpectrumList.read(fname, format="JWST x1d")
            # Orientation denoted by "C" or "R"
            orientation = fname.split("_")[2][-1]
            for spec in specs:
                label = "Source {} spec1d {}".format(spec.meta["SOURCEID"],
                                              orientation)
                spec_labels.append(label)
                app.data_collection[label] = spec
        # We default to show the "C" spectra, show those in the table for now
        if orientation == "C":
            _add_to_table(app, spec_labels, "1D Spectra")

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
    def _parse_as_cube(path):
        with fits.open(path) as hdulist:
            data = hdulist[1].data

            if hdulist[1].header['NAXIS'] == 2:
                new_data = np.expand_dims(data, axis=1)
                hdulist[1].header['NAXIS'] = 3

            hdulist[1].header['NAXIS3'] = 1
            hdulist[1].header['BUNIT'] = 'dN/s'
            hdulist[1].header['CUNIT3'] = 'um'
            wcs = WCS(hdulist[1].header)

        return SpectralCube(new_data, wcs=wcs)

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
    def _parse_as_image(path):
        with fits.open(path) as hdulist:
            if 'BUNIT' not in hdulist[0].header:
                logging.warning("No 'BUNIT' defined in the header, using 'Jy'.")

            unit = hdulist[0].header.get('BUNIT', 'Jy')

        return CCDData.read(path, unit=unit)

    if isinstance(data_obj, str):
        data_obj = [_parse_as_image(data_obj)]

    # Coerce into list-like object
    if not hasattr(data_obj, '__len__'):
        data_obj = [data_obj]
    else:
        data_obj = [_parse_as_image(x)
                    if _check_is_file(x) else x
                    for x in data_obj]

    if data_labels is None:
        data_labels = [f"Image {i}" for i in range(len(data_obj))]
    elif len(data_obj) != len(data_labels):
        data_labels = [f"{data_labels} {i}" for i in range(len(data_obj))]

    for i in range(len(data_obj)):
        app.data_collection[data_labels[i]] = data_obj[i]

    _add_to_table(app, data_labels, 'Images')


@data_parser_registry("mosviz-metadata-parser")
def mos_meta_parser(app, data_obj):
    """
    Attempts to parse MOS FITS header metadata.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or HDUList
        File path, list, or an HDUList to extract metadata from.
    """

    # Coerce into list-like object
    if not hasattr(data_obj, '__len__'):
        data_obj = [data_obj]
    else:
        data_obj = [fits.open(x) if _check_is_file(x)
                    else x for x in data_obj]

    ra = [x[0].header.get("OBJ_RA", float("nan")) for x in data_obj]
    dec = [x[0].header.get("OBJ_DEC", float("nan")) for x in data_obj]
    names = [x[0].header.get("OBJECT", "Unspecified Target") for x in data_obj]

    [x.close() for x in data_obj]

    _add_to_table(app, names, "Source Names")
    _add_to_table(app, ra, "Right Ascension")
    _add_to_table(app, dec, "Declination")
