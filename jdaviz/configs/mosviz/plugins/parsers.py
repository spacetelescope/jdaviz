import os

from glue.core.data import Data
from jdaviz.core.registries import data_parser_registry
from jdaviz.core.events import SnackbarMessage
import csv

from spectral_cube import SpectralCube
from astropy.nddata import CCDData
from specutils import Spectrum1D, SpectrumList
from astropy.io import fits
import numpy as np
import logging
from astropy.wcs import WCS
from asdf.fits_embed import AsdfInFits
from pathlib import Path
import glob

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
        raise ValueError("No valid files found in specified directory")
    if len(not_found) > 0:
        warn_msg = "Some files not found: {}".format(", ".join(not_found))
        print(warn_msg)
        warn_msg = SnackbarMessage(warn_msg, color="warning", sender=app)
        app.hub.broadcast(warn_msg)

    return found


def _parse_as_image(path):
    """
    Parse and load a 2D image. ``CCDData`` objects require a unit be defined
    in the fits header - if none is provided, use a fallback and
    raise an error.
    """
    with fits.open(path) as hdulist:

        header = hdulist[0].header.copy()
        meta = dict(header)

        wcs = WCS(header)

        try:
            image_ccd = CCDData.read(path, wcs=wcs)
        except ValueError as e:
            if str(e) == "a unit for CCDData must be specified.":
                logging.warning("No 'BUNIT' defined in the header, using 'Jy'.")
                image_ccd = CCDData.read(path, unit='Jy', wcs=wcs)
            else:
                raise

        image_ccd.meta = meta

    return image_ccd


def _fields_from_ecsv(fname, fields, delimiter=","):
    parsed_fields = []
    with open(fname, "r") as f:
        reader = csv.DictReader(filter(lambda r: r[0] != "#", f),
                                delimiter=delimiter)
        for row in reader:
            temp_list = []
            for field in fields:
                temp_list.append(row[field])
            parsed_fields.append(temp_list)
    return parsed_fields


@data_parser_registry("mosviz-nirspec-directory-parser")
def mos_nirspec_directory_parser(app, data_obj, data_labels=None):

    spectra_1d = []
    spectra_2d = []

    # Load spectra
    level3_path = Path(data_obj)
    for file_path in glob.iglob(str(level3_path / '*')):
        if 'x1d' in file_path or 'c1d' in file_path:
            spectra_1d.append(file_path)
        elif 's2d' in file_path:
            spectra_2d.append(file_path)

    # Load images, if present
    image_path = None

    # Potential names of subdirectories where images are stored
    for image_dir_name in ["cutouts", "mosviz_cutouts", "images"]:
        if os.path.isdir(Path(str(level3_path / image_dir_name))):
            image_path = Path(str(level3_path / image_dir_name))
            break
    if image_path is not None:
        images = sorted([file_path for file_path in glob.iglob(str(image_path / '*'))])

        # The amount of images needs to be equal to the amount of rows
        # of the other columns in the table
        if len(images) == len(spectra_1d):
            mos_meta_parser(app, images)
            mos_image_parser(app, images)
        else:
            msg = "The number of images in this directory does not match the" \
                  " number of spectra 1d and 2d files, please make the " \
                  "amounts equal or load images separately."
            logging.warning(msg)
            msg = SnackbarMessage(msg, color='warning', sender=app)
            app.hub.broadcast(msg)

    spectra_1d.sort()
    spectra_2d.sort()
    mos_spec1d_parser(app, spectra_1d)
    mos_spec2d_parser(app, spectra_2d)


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

    with app.data_collection.delay_link_manager_update():

        for i in range(len(data_obj)):
            app.data_collection[data_labels[i]] = data_obj[i]

        _add_to_table(app, data_labels, '1D Spectra')


@data_parser_registry("mosviz-spec2d-parser")
def mos_spec2d_parser(app, data_obj, data_labels=None, add_to_table=True,
                      show_in_viewer=False):
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
            header['CTYPE3'] = 'WAVE'

            # Information not present in the SCI header has to be put there
            # so spectral_cube won't choke. We cook up a simple linear wcs
            # with the only intention of making the code run beyond the
            # spectral_cube processing. There is no guarantee that this will
            # result in the correct axis label values being displayed.
            #
            # This is a stopgap solution that will be replaced when specutils
            # absorbs the functionality provided by spectral_cube.

            fa = AsdfInFits.open(path)
            gwcs = fa.tree['meta']['wcs']

            header['CTYPE1'] = 'RA---TAN'
            header['CTYPE2'] = 'DEC--TAN'
            header['CUNIT1'] = 'deg'
            header['CUNIT2'] = 'deg'

            header['CRVAL1'] = gwcs.forward_transform.lon_4.value
            header['CRVAL2'] = gwcs.forward_transform.lat_4.value
            header['CRPIX1'] = gwcs.forward_transform.intercept_1.value
            header['CRPIX2'] = gwcs.forward_transform.intercept_2.value
            header['CDELT1'] = gwcs.forward_transform.slope_1.value
            header['CDELT2'] = gwcs.forward_transform.slope_2.value
            header['PC1_1'] = -1.
            header['PC1_2'] = 0.
            header['PC2_1'] = 0.
            header['PC2_2'] = 1.
            header['PC3_1'] = 1.
            header['PC3_2'] = 0.

            wcs = WCS(header)

            meta = {'S_REGION': header['S_REGION'], 'INSTRUME': 'nirspec'}

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

    with app.data_collection.delay_link_manager_update():

        for i in range(len(data_obj)):
            app.data_collection[data_labels[i]] = data_obj[i]

        if add_to_table:
            _add_to_table(app, data_labels, '2D Spectra')

    if show_in_viewer:
        if len(data_labels) > 1:
            raise ValueError("More than one data label provided, unclear " +
                             "which to show in viewer")
        app.add_data_to_viewer("spectrum-2d-viewer", data_labels[0])


@data_parser_registry("mosviz-image-parser")
def mos_image_parser(app, data_obj, data_labels=None, share_image=0):
    """
    Attempts to parse an image-like object or list of images.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or image-like
        File path, list, or image-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    share_image : int, optional
        If 0, images are treated as applying to individual spectra. If non-zero,
        a single image will be shared by multiple spectra so that clicking a
        different row in the table does not reload the displayed image.
        Currently, if non-zero, the provided number must match the number of
        spectra.
    """

    if data_obj is None:
        return

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
        if share_image:
            data_labels = ["Shared Image"]
        else:
            data_labels = [f"Image {i}" for i in range(len(data_obj))]

    elif isinstance(data_labels, str):
        if share_image:
            data_labels = [data_labels]
        else:
            data_labels = [f"{data_labels} {i}" for i in range(len(data_obj))]

    with app.data_collection.delay_link_manager_update():

        for i in range(len(data_obj)):
            app.data_collection[data_labels[i]] = data_obj[i]

        if share_image:
            # Associate this image with multiple spectra
            data_labels *= share_image

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

    if data_obj is None:
        return

    # Coerce into list-like object
    if not hasattr(data_obj, '__len__'):
        data_obj = [data_obj]
    elif isinstance(data_obj, str):
        data_obj = [fits.open(data_obj)]
    else:
        data_obj = [fits.open(x) if _check_is_file(x)
                    else x for x in data_obj]

    if np.all([isinstance(x, fits.HDUList) for x in data_obj]):
        ra = [x[0].header.get("OBJ_RA", float("nan")) for x in data_obj]
        dec = [x[0].header.get("OBJ_DEC", float("nan")) for x in data_obj]
        names = [x[0].header.get("OBJECT", "Unspecified Target") for x in data_obj]

        [x.close() for x in data_obj]

    else:
        # TODO: Come up with more robust metadata parsing, perhaps from
        # the spectra files.
        logging.warn("Could not parse metadata from input images.")
        return

    with app.data_collection.delay_link_manager_update():

        _add_to_table(app, names, "Source Names")
        _add_to_table(app, ra, "Right Ascension")
        _add_to_table(app, dec, "Declination")


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
    source_cat = sorted(list(p.glob("{}*_direct_*_cat.ecsv".format(obs_label))))
    direct_image = sorted(list(p.glob("{}*_direct_dit1*_i2d.fits".format(obs_label))))
    spec2d_r = sorted(list(p.glob("{}*_WFSSR_*_cal.fits".format(obs_label))))
    spec2d_c = sorted(list(p.glob("{}*_WFSSC_*_cal.fits".format(obs_label))))
    spec1d_r = sorted(list(p.glob("{}*_WFSSR_*_x1d.fits".format(obs_label))))
    spec1d_c = sorted(list(p.glob("{}*_WFSSC_*_x1d.fits".format(obs_label))))

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
    _warn_if_not_found(app, file_lists)

    # Parse relevant information from source catalog
    cat_fields = ["id", "sky_centroid.ra", "sky_centroid.dec"]
    source_ids = []
    ras = []
    decs = []
    image_add = []

    pupil_id_dict = {}

    # Retrieve source information
    for source_catalog_num in range(0, len(file_lists["Source Catalog"])):
        cat_file = file_lists["Source Catalog"][source_catalog_num]
        parsed_cat_fields = _fields_from_ecsv(cat_file, cat_fields, delimiter=" ")
        pupil = [x
                 for x in cat_file.split("/")[-1].split("_")
                 if x[0] == "F" or x[0] == "f"][0]

        pupil_id_dict[pupil] = {}

        for row in parsed_cat_fields:
            pupil_id_dict[pupil][int(row[0])] = (row[1], row[2])

    # Read in direct image filters
    image_dict = {}
    filter_wcs = {}

    # Set up a dictionary of datasets to add to glue
    add_to_glue = {}

    print("Loading: Images")

    for image_file in file_lists["Direct Image"]:
        im_split = image_file.split("/")[-1].split("_")
        pupil = [x
                 for x in image_file.split("/")[-1].split("_")
                 if x[0] == "F" or x[0] == "f"][0]

        image_label = "Image {} {}".format(im_split[0], pupil)

        image_data = _parse_as_image(image_file)

        with fits.open(image_file) as temp:
            filter_wcs[pupil] = temp[1].header

        add_to_glue[image_label] = image_data

        image_dict[pupil] = image_label

    # Parse 2D spectra
    spec_labels_2d = []
    for f in ["2D Spectra C", "2D Spectra R"]:

        for fname in file_lists[f]:
            print(f"Loading: {f} sources")

            orientation = f[-1]
            filter_name = [x
                           for x in fname.split("/")[-1].split("_")
                           if x[0] == "F" or x[0] == "f"][0]

            with fits.open(fname, memmap=False) as temp:
                sci_hdus = []
                for i in range(len(temp)):
                    if "EXTNAME" in temp[i].header:
                        if temp[i].header["EXTNAME"] == "SCI":
                            sci_hdus.append(i)

                # Now get a SpectralCube object for each SCI HDU
                for sci in sci_hdus:

                    if temp[sci].header["SPORDER"] == 1:

                        data = temp[sci].data
                        meta = temp[sci].header
                        header = filter_wcs[filter_name]

                        # Information that needs to be added to the header in order to load
                        # WCS information into SpectralCube.
                        # TODO: Use gwcs instead to avoid hardcoding information for 3rd wcs axis
                        new_data = np.expand_dims(data, axis=1)
                        header['NAXIS'] = 3

                        header['NAXIS3'] = 1
                        header['BUNIT'] = 'dN/s'
                        header['CUNIT3'] = 'um'
                        header['WCSAXES'] = 3
                        header['CRPIX3'] = 0.0
                        header['CDELT3'] = 1E-06
                        header['CUNIT3'] = 'm'
                        header['CTYPE3'] = 'WAVE'
                        header['CRVAL3'] = 0.0

                        wcs = WCS(header)

                        spec2d = SpectralCube(new_data, wcs=wcs, meta=meta)

                        spec2d.meta['INSTRUME'] = 'NIRISS'

                        label = "{} Source {} spec2d {}".format(filter_name,
                                                                temp[sci].header["SOURCEID"],
                                                                orientation
                                                                )
                        ra, dec = pupil_id_dict[filter_name][temp[sci].header["SOURCEID"]]
                        source_ids.append("Source Catalog: {} Source ID: {}".
                                          format(filter_name, temp[sci].header["SOURCEID"]))
                        ras.append(ra)
                        decs.append(dec)
                        image_add.append(image_dict[filter_name])
                        spec_labels_2d.append(label)

                        add_to_glue[label] = spec2d

    spec_labels_1d = []
    for f in ["1D Spectra C", "1D Spectra R"]:

        for fname in file_lists[f]:
            print(f"Loading: {f} sources")

            with fits.open(fname, memmap=False) as temp:
                # TODO: Remove this once valid SRCTYPE values are present in all headers
                for hdu in temp:
                    if "SRCTYPE" in hdu.header and\
                            (hdu.header["SRCTYPE"] in ["POINT", "EXTENDED"]):
                        pass
                    else:
                        hdu.header["SRCTYPE"] = "EXTENDED"

                specs = SpectrumList.read(temp, format="JWST x1d multi")
                filter_name = [x
                               for x in fname.split("/")[-1].split("_")
                               if x[0] == "F" or x[0] == "f"][0]

                # Orientation denoted by "C" or "R"
                orientation = f[-1]

                for spec in specs:
                    if spec.meta['header']['SPORDER'] == 1 and\
                            spec.meta['header']['EXTNAME'] == "EXTRACT1D":

                        label = "{} Source {} spec1d {}".format(filter_name,
                                                                spec.meta['header']['SOURCEID'],
                                                                orientation
                                                                )
                        spec_labels_1d.append(label)
                        add_to_glue[label] = spec

    # Add the datasets to glue - we do this in one step so that we can easily
    # optimize by avoiding recomputing the full link graph at every add

    with app.data_collection.delay_link_manager_update():

        for label, data in add_to_glue.items():
            app.data_collection[label] = data

        # We then populate the table inside this context manager as _add_to_table
        # does operations that also trigger link manager updates.

        print("Populating table")

        _add_to_table(app, source_ids, "Source ID")
        _add_to_table(app, ras, "Right Ascension")
        _add_to_table(app, decs, "Declination")
        _add_to_table(app, image_add, "Images")
        _add_to_table(app, spec_labels_1d, "1D Spectra")
        _add_to_table(app, spec_labels_2d, "2D Spectra")

    print("Done")
