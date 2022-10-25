from collections.abc import Iterable
import csv
import glob
import os
from pathlib import Path
import warnings

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.io.registry import IORegistryError
from astropy.wcs import WCS
from glue.core.data import Data
from glue.core.link_helpers import LinkSame
from specutils import Spectrum1D, SpectrumList, SpectrumCollection

from jdaviz.configs.imviz.plugins.parsers import get_image_data_iterator
from jdaviz.core.registries import data_parser_registry
from jdaviz.core.events import SnackbarMessage
from jdaviz.utils import standardize_metadata, PRIHDR_KEY

__all__ = ['mos_spec1d_parser', 'mos_spec2d_parser', 'mos_image_parser']

FALLBACK_NAME = "Unspecified"


def _add_to_table(app, data, comp_label, table_viewer_reference_name='table-viewer'):
    """
    Creates a mos table instance in the application data collection is none
    currently exists.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The Jdaviz application instance.
    data : array-list
        The set of data to added as a table (i.g. column) component.
    comp_label : str
        The label used to describe the data. Also used as the column header.
    """
    # Add data to the mos viz table object
    if 'MOS Table' not in app.data_collection:
        table_data = Data(label='MOS Table')
        app.add_data(table_data, notify_done=False)

        mos_table = app.data_collection['MOS Table']
        mos_table.add_component(data, comp_label)

        viewer = app.get_viewer(table_viewer_reference_name)
        viewer.add_data(table_data)
    else:
        mos_table = app.data_collection['MOS Table']
        if comp_label not in mos_table.component_ids():
            mos_table.add_component(data, comp_label)


def _check_is_file(path):
    return isinstance(path, str) and Path(path).is_file()


def _warn_if_not_found(app, files_by_labels):
    """
    Take a list of labels and associated file lists/strings and send a
    snackbar message if any are empty.
    """
    found = []
    not_found = []
    for key in files_by_labels:
        if files_by_labels[key]:
            found.append(key)
        else:
            not_found.append(key)

    if len(found) == 0:
        raise ValueError("No valid files found in specified directory")
    if len(not_found) > 0:
        warn_msg = f"Some files not found: {', '.join(not_found)}"
        warn_msg = SnackbarMessage(warn_msg, color="warning", sender=app)
        app.hub.broadcast(warn_msg)

    return found


def _fields_from_ecsv(fname, fields, delimiter=","):
    """
    Save specified field(s) from an ecsv file as a row-by-row list of
    lists.
    """
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


@data_parser_registry("mosviz-link-data")
def link_data_in_table(app, data_obj=None):
    """
    Batch links data in the mosviz table viewer.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : None
        Passed in in order to use the data_parser_registry, otherwise
        not used.
    """
    mos_data = app.session.data_collection['MOS Table']
    wc_spec_ids = []

    # Optimize linking speed through a) delaying link manager updates with a
    # context manager, b) handling intra-row linkage of 1D and 2D spectra in a
    # loop, and c) handling inter-row linkage after that in one fell swoop.
    with app.data_collection.delay_link_manager_update():

        spectra_1d = mos_data.get_component('1D Spectra').data
        spectra_2d = mos_data.get_component('2D Spectra').data

        # Link each 1D spectrum with its corresponding 2D spectrum
        for index in range(len(spectra_1d)):

            spec_1d = spectra_1d[index]
            spec_2d = spectra_2d[index]

            wc_spec_1d = app.session.data_collection[spec_1d].world_component_ids
            wc_spec_2d = app.session.data_collection[spec_2d].world_component_ids

            wc_spec_ids.append(LinkSame(wc_spec_1d[0], wc_spec_2d[1]))

        # Link each 1D spectrum to all other 1D spectra
        first_spec_1d = spectra_1d[0]
        wc_first_spec_1d = app.session.data_collection[first_spec_1d].world_component_ids

        for index in range(1, len(spectra_1d)):
            spec_1d = spectra_1d[index]
            wc_spec_1d = app.session.data_collection[spec_1d].world_component_ids
            wc_spec_ids.append(LinkSame(wc_spec_1d[0], wc_first_spec_1d[0]))

    app.session.data_collection.add_link(wc_spec_ids)


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
            mos_meta_parser(app, images, ids=images)
            mos_image_parser(app, images)
        else:
            msg = ("The number of images in this directory does not match the"
                   " number of spectra 1d and 2d files, please make the "
                   "amounts equal or load images separately.")
            msg = SnackbarMessage(msg, color='warning', sender=app)
            app.hub.broadcast(msg)

    spectra_1d.sort()
    spectra_2d.sort()
    mos_spec1d_parser(app, spectra_1d)
    mos_spec2d_parser(app, spectra_2d)
    mos_meta_parser(app, spectra_2d, spectra=True)
    mos_meta_parser(app, spectra_1d, spectra=True, sp1d=True)


@data_parser_registry("mosviz-spec1d-parser")
def mos_spec1d_parser(app, data_obj, data_labels=None,
                      table_viewer_reference_name='table-viewer'):
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

    if isinstance(data_labels, str):
        data_labels = [data_labels]

    # Coerce into list if needed
    if not isinstance(data_obj, (list, tuple, SpectrumCollection)):
        data_obj = [data_obj]

    data_obj = [Spectrum1D.read(x) if _check_is_file(x) else x for x in data_obj]

    if data_labels is None:
        data_labels = [f"1D Spectrum {i}" for i in range(len(data_obj))]
    elif len(data_obj) != len(data_labels):
        data_labels = [f"{data_labels[0]} {i}" for i in range(len(data_obj))]

    # Handle the case where the 1d spectrum is a collection of spectra

    with app.data_collection.delay_link_manager_update():

        for i, (cur_data, cur_label) in enumerate(zip(data_obj, data_labels)):
            # Make metadata layout conform with other viz.
            cur_data.meta = standardize_metadata(cur_data.meta)
            cur_data.meta['mosviz_row'] = i

            app.add_data(cur_data, cur_label, notify_done=False)

        _add_to_table(app, data_labels, '1D Spectra',
                      table_viewer_reference_name=table_viewer_reference_name)


@data_parser_registry("mosviz-spec2d-parser")
def mos_spec2d_parser(app, data_obj, data_labels=None, add_to_table=True,
                      show_in_viewer=False, ext=1, transpose=False):
    """
    Attempts to parse a 2D spectrum object.

    Notes
    -----
    Default arguments assume that the data is in the second HDU of the FITS file unless
    otherwise specified with the ``ext`` parameter.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or spectrum-like
        File path, list, or spectrum-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    ext : int, optional
        The extension in the FITS file that contains the data to be loaded.
    transpose : bool, optional
        Flag to transpose the data array before loading.
    """
    spectrum_2d_viewer_reference_name = (
        app._jdaviz_helper._default_spectrum_2d_viewer_reference_name
    )
    table_viewer_reference_name = (
        app._jdaviz_helper._default_table_viewer_reference_name
    )

    # Note: This is also used by Specviz2D
    def _parse_as_spectrum1d(hdulist, ext, transpose):
        # Parse as a FITS file and assume the WCS is correct
        data = hdulist[ext].data
        header = hdulist[ext].header
        metadata = standardize_metadata(header)
        metadata[PRIHDR_KEY] = standardize_metadata(hdulist[0].header)
        wcs = WCS(header, hdulist)
        if transpose:
            data = data.T
            wcs = wcs.swapaxes(0, 1)

        try:
            data_unit = u.Unit(header['BUNIT'])
        except Exception:
            data_unit = u.count

        # FITS WCS is invalid, so ignore it.
        if wcs.spectral.naxis == 0:
            kw = {}
        else:
            kw = {'wcs': wcs}

        return Spectrum1D(flux=data * data_unit, meta=metadata, **kw)

    # Coerce into list-like object
    if (not isinstance(data_obj, (list, tuple, SpectrumCollection)) or
            isinstance(data_obj, fits.HDUList)):
        data_obj = [data_obj]

    # If we're given a string, repeat it for each object
    if isinstance(data_labels, str):
        if len(data_obj) > 1:
            data_labels = [f"{data_labels} {i}" for i in range(len(data_obj))]
        else:
            data_labels = [data_labels]
    elif data_labels is None:
        if len(data_obj) > 1:
            data_labels = [f"2D Spectrum {i}" for i in range(len(data_obj))]
        else:
            data_labels = ['2D Spectrum']

    with app.data_collection.delay_link_manager_update():
        for index, data in enumerate(data_obj):
            # If we got a filepath, first try and parse using the Spectrum1D and
            # SpectrumList parsers, and then fall back to parsing it as a generic
            # FITS file.
            if _check_is_file(data):
                try:
                    if ext != 1 or transpose:
                        with fits.open(data) as hdulist:
                            data = _parse_as_spectrum1d(hdulist, ext, transpose)
                    else:
                        data = Spectrum1D.read(data)
                except IORegistryError:
                    with fits.open(data) as hdulist:
                        data = _parse_as_spectrum1d(hdulist, ext, transpose)
            elif isinstance(data, fits.HDUList):
                data = _parse_as_spectrum1d(data, ext, transpose)

            # Make metadata layout conform with other viz.
            data.meta = standardize_metadata(data.meta)

            # Set the instrument
            # TODO: this should not be set to nirspec for all datasets
            data.meta['INSTRUME'] = 'nirspec'

            data.meta['mosviz_row'] = index
            # Get the corresponding label for this data product
            label = data_labels[index]
            app.data_collection[label] = data

        if add_to_table:
            _add_to_table(
                app, data_labels, '2D Spectra',
                table_viewer_reference_name=table_viewer_reference_name
            )

    if show_in_viewer:
        if len(data_labels) > 1:
            raise ValueError("More than one data label provided, unclear " +
                             "which to show in viewer")
        app.add_data_to_viewer(spectrum_2d_viewer_reference_name, data_labels[0])


def _load_fits_image_from_filename(filename, app):
    with fits.open(filename) as hdulist:
        # We do not use the generated labels
        data_list = [d for d, _ in get_image_data_iterator(app, hdulist, "Image", ext=None)]
    return data_list


@data_parser_registry("mosviz-image-parser")
def mos_image_parser(app, data_obj, data_labels=None, share_image=0,
                     image_viewer_reference_name="image-viewer"):
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

    # The label does not matter here. We overwrite later.
    if isinstance(data_obj, str):
        data_obj = _load_fits_image_from_filename(data_obj, app)
    elif isinstance(data_obj, (list, tuple)) and share_image == 0:
        temp_data = []
        for cur_data_obj in data_obj:
            if isinstance(cur_data_obj, str):
                temp_data += _load_fits_image_from_filename(cur_data_obj, app)
            else:
                data_iter = get_image_data_iterator(app, cur_data_obj, "Image", ext=None)
                temp_data += [d[0] for d in data_iter]
        data_obj = temp_data
    else:
        data_iter = get_image_data_iterator(app, data_obj, "Image", ext=None)
        data_obj = [d[0] for d in data_iter]

    n_data = len(data_obj)
    n_data_range = range(n_data)

    # TODO: Maybe should raise exception?
    if share_image and n_data > 1:  # Just use the first one
        data_obj = [data_obj[0]]

    if data_labels is None:
        if share_image:
            data_labels = ["Shared Image"]
        else:
            data_labels = [f"Image {i}" for i in n_data_range]

    elif isinstance(data_labels, str):
        if share_image:
            data_labels = [data_labels]
        else:
            data_labels = [f"{data_labels} {i}" for i in n_data_range]

    with app.data_collection.delay_link_manager_update():

        for i in n_data_range:
            data_obj[i].label = data_labels[i]
            data_obj[i].meta['mosviz_row'] = i
            app.add_data(data_obj[i], data_labels[i], notify_done=False)

        if share_image:
            # Associate this image with multiple spectra
            data_labels *= share_image
            # Show it on viewer
            app.add_data_to_viewer(image_viewer_reference_name, data_labels[0])

        _add_to_table(app, data_labels, 'Images')


@data_parser_registry("mosviz-metadata-parser")
def mos_meta_parser(app, data_obj, ids=None, spectra=False, sp1d=False):
    """
    Attempts to parse MOS FITS header metadata.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or HDUList
        File path, list, or an HDUList to extract metadata from.
    ids : list of str
        A list with identification strings to be used to label mosviz
        table rows. Typically, a list with file names.
    spectra : Boolean
        In case the FITS objects are related to spectral data.
    """

    if data_obj is None:
        return

    # Coerce into list if needed
    if not isinstance(data_obj, (list, tuple, SpectrumCollection)):
        data_obj = [data_obj]

    data_obj = [fits.open(x) if _check_is_file(x) else x for x in data_obj]

    if np.all([isinstance(x, fits.HDUList) for x in data_obj]):

        # metadata taken from 2d spectra
        if spectra and not sp1d:
            filters = [x[0].header.get("FILTER", FALLBACK_NAME) for x in data_obj]
            gratings = [x[0].header.get("GRATING", FALLBACK_NAME) for x in data_obj]

            filters_gratings = [(f+'/'+g) for f, g in zip(filters, gratings)]

            [x.close() for x in data_obj]

        # source name can be taken from 1d spectra
        elif spectra and sp1d:
            names = _get_source_identifiers_by_hdu([x[0] for x in data_obj], ids)

        # source name and coordinates are taken from image headers, if present
        else:
            ra = [x[0].header.get("OBJ_RA", float("nan")) for x in data_obj]
            dec = [x[0].header.get("OBJ_DEC", float("nan")) for x in data_obj]
            names = _get_source_identifiers_by_hdu([x[0] for x in data_obj], ids)

        [x.close() for x in data_obj]

    else:
        # TODO: Come up with more robust metadata parsing, perhaps from
        # the spectra files.
        warnings.warn("Could not parse metadata from input images.")
        return

    with app.data_collection.delay_link_manager_update():

        # this conditional must mirror the one above
        if spectra and not sp1d:
            _add_to_table(app, filters_gratings, "Filter/Grating")
        elif spectra and sp1d:
            _add_to_table(app, names, "Identifier")
        else:
            _add_to_table(app, names, "Identifier")
            _add_to_table(app, ra, "R.A.")
            _add_to_table(app, dec, "Dec.")


def _get_source_identifiers_by_hdu(hdus, filepaths=None,
                                   header_keys=['SOURCEID', 'OBJECT']):
    """
    Attempts to extract a list of source identifiers via different header values.

    Parameters
    ----------
    hdus : list of HDU
        A list of HDUs (NOT an HDUList!) to check the header of. Filtering should
        be done in advance to decide which HDUs to check against (e.g., SCI only).
    filepaths : list of str, optional
        A list of filepaths to fallback on if no header values are identified.
    header_keys: str or list of str, optional
        The header value (or values) to search an HDU for to extract the source id.
        List order is assumed to be priority order (i.e. will return first successful
        lookup)
    """
    src_names = list()
    # If the user only provided a key that's not already in a container or list, put it in
    # one for the upcoming loop
    if not (isinstance(header_keys, Iterable) and not isinstance(header_keys, (str, dict))):
        header_keys = [header_keys]
    for indx, hdu in enumerate(hdus):
        try:
            src_name = None
            # Search all given keys to see if they exist. Return the first hit
            for key in header_keys:
                if key in hdu.header:
                    src_name = hdu.header.get(key)
                    break
            # If none exist, default to fallback
            if not src_name:
                # Fallback 1: filepath if only one is given
                # Fallback 2: filepath at indx, if list of files given
                # Fallback 3: If nothing else, just our fallback value
                src_name = (
                    os.path.basename(filepaths) if type(filepaths) is str
                    else os.path.basename(filepaths[indx]) if type(filepaths) is list
                    else FALLBACK_NAME)
            src_names.append(src_name)
        except Exception:
            # Source ID lookup shouldn't ever prevent target from loading. Downgrade all errors to
            # warnings and use fallback
            warnings.warn("Source name lookup failed for Target " + str(indx) +
                          ". Using fallback ID", RuntimeWarning)
            src_names.append(FALLBACK_NAME)
    return src_names


def _id_files_by_datamodl(label_dict, filepaths, catalog_key=None):
    '''
    Given a dictionary of expected file labels, sort a directory of files into
    their matching categories using their DATAMODL values. The key corresponding
    with the source catalog file must be provided as well.

    Specific to JWST generally (through datamodels) and NIRISS specifically for
    the time, though the eventual plan is to add support for the NIRSpec parser.
    '''
    if catalog_key is None:
        raise ValueError("cat_key must be identified before parsing directory")

    for fp in filepaths:
        if fp.is_dir():
            continue

        if fp.suffix in ('.fits', '.fits.gz', '.fit', '.fit.gz'):
            # eligible files will have a DATAMODL value in their primary headers
            header = fits.getheader(fp, ext=0)
            datamodl = header.get('DATAMODL')

            # infer the dispersion direction of 1D and 2D spectra by the last
            # letter of their filter values (e.g., "C" from "GR150C")
            try:
                dispersion = header.get('FILTER')[-1]
            except TypeError:
                dispersion = None

            # distinguish image files from counts files -- only the former go
            # through the "Assign World Coordinate System" calibration step
            s_wcs = header.get('S_WCS')

            if datamodl is None:
                continue
            if datamodl == 'MultiSpecModel' and dispersion == 'C':
                label_dict['1D Spectra C'].append(fp)
            elif datamodl == 'MultiSpecModel' and dispersion == 'R':
                label_dict['1D Spectra R'].append(fp)
            elif datamodl == 'MultiSlitModel' and dispersion == 'C':
                label_dict['2D Spectra C'].append(fp)
            elif datamodl == 'MultiSlitModel' and dispersion == 'R':
                label_dict['2D Spectra R'].append(fp)
            elif datamodl == 'ImageModel' and s_wcs is not None:
                label_dict['Direct Image'].append(fp)
            else:
                continue

        elif fp.suffix == '.ecsv':
            if label_dict[catalog_key]:
                raise ValueError("source directory has more "
                                 "than one source catalog")
            else:
                label_dict[catalog_key] = fp

        else:
            continue

    return label_dict


@data_parser_registry("mosviz-niriss-parser")
def mos_niriss_parser(app, data_dir, table_viewer_reference_name='table-viewer'):
    """
    Attempts to parse all data for a NIRISS dataset in a single
    directory, which should include:

    - *_i2d.fits : Direct 2D images
    - *_cat.ecsv : Source catalog
    - *_cal.fits : 2D spectra in vertical (R) and horizontal (C)
        orientations. C spectra are shown first in viewers by default
    - *_x1d.fits : 1D spectra in vertical (R) and horizontal (C)
        orientations. C spectra are shown first in viewers by default

    NOTE: For best performance, it's recommended that your directory
    only contain one source catalog and its associated images/spectra.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_dir : str
        The path to a directory containing NIRISS data products.
    """
    path = Path(data_dir)
    if not path.is_dir():
        raise ValueError(f"{data_dir} is not a valid directory path")

    # create dict for mapping expected file types to their DATAMODL identifiers
    expected_labels = ['1D Spectra C', '1D Spectra R',
                       '2D Spectra C', '2D Spectra R', 'Direct Image']
    files_by_labels = {k: [] for k in expected_labels}

    # there should only be one source catalog, so that key gets a string
    cat_key = 'Source Catalog'
    expected_labels += [cat_key]
    files_by_labels[cat_key] = ''

    # use FITS header keywords to sort the directory's files
    files_by_labels = _id_files_by_datamodl(files_by_labels, path.glob('*'),
                                            catalog_key=cat_key)

    # validate that all expected files are present in proper amounts
    _warn_if_not_found(app, files_by_labels)

    # parse relevant information from source catalog
    cat_id_dict = {}
    cat_file = files_by_labels[cat_key]
    try:
        cat_fields = ['label', 'sky_centroid.ra', 'sky_centroid.dec']
        parsed_cat_fields = _fields_from_ecsv(cat_file, cat_fields,
                                              delimiter=" ")
    except KeyError:
        # Older pipeline builds use different colname to distinguish sources
        cat_fields[0] = 'id'
        parsed_cat_fields = _fields_from_ecsv(cat_file, cat_fields,
                                              delimiter=" ")
    for row in parsed_cat_fields:
        cat_id_dict[int(row[0])] = (row[1], row[2])

    # set up a dictionary of datasets to add to glue
    add_to_glue = {}

    # Parse images
    image_dict = {}

    print("Loading: Images")
    for image_file in files_by_labels["Direct Image"]:
        # save label for table viewer
        im_split = image_file.stem.split("_")[0]
        pupil = fits.getheader(image_file, ext=0).get('PUPIL')

        image_label = f"Image {im_split} {pupil}"
        image_dict[pupil] = image_label

        # save information from data file
        with fits.open(image_file) as temp:
            data_iter = get_image_data_iterator(app, temp, "Image", ext=None)
            data_obj = [d[0] for d in data_iter]  # We do not use the generated labels
            image_data = data_obj[0]  # Grab the first one.
            # TODO: Error if multiple found?

        image_data.label = image_label
        add_to_glue[image_label] = image_data

    # initialize lists of data to be shown in table viewer
    source_ids = []
    ras = []
    decs = []
    image_add = []
    spec_labels_1d = []
    spec_labels_2d = []
    filters = []

    # Parse 2D spectra
    file_labels_2d = [k for k in files_by_labels.keys() if k.startswith("2D")]

    for flabel in file_labels_2d:
        for fname in files_by_labels[flabel]:
            print(f"Loading: {flabel} sources")
            filter_name = fits.getheader(fname, ext=0).get('PUPIL')

            # Orientation denoted by "C", "R", or "C+R" for combined spectra
            orientation = flabel.split()[-1]

            # save HDUs in file that correspond with sources in catalog
            with fits.open(fname, memmap=False) as temp:
                sci_hdus = []
                wav_hdus = {}
                for i in range(len(temp)):
                    if i == 0:
                        filter = temp[0].header["FILTER"]
                    if "EXTNAME" in temp[i].header:
                        if (temp[i].header["EXTNAME"] == "SCI"
                                and (temp[i].header["SOURCEID"]
                                     in cat_id_dict.keys())):
                            sci_hdus.append(i)
                            wav_hdus[i] = ('WAVELENGTH',
                                           temp[i].header['EXTVER'])

                # Now get a Spectrum1D object for each matching SCI HDU
                source_ids.extend(_get_source_identifiers_by_hdu([temp[sci] for sci in sci_hdus]))

                for sci in sci_hdus:
                    if temp[sci].header["SPORDER"] == 1:
                        data = temp[sci].data
                        meta = standardize_metadata(temp[sci].header)
                        meta[PRIHDR_KEY] = standardize_metadata(temp[0].header)

                        # The wavelength is stored in a WAVELENGTH HDU. This is
                        # a 2D array, but in order to be able to use Spectrum1D
                        # we use the average wavelength for all image rows

                        if data.shape[0] > data.shape[1]:
                            # then the input data needs to be transposed, and wavelength
                            # needs to be averaged over axis=1 instead of axis=0
                            data = data.T
                            wav = temp[wav_hdus[sci]].data.mean(axis=1) * u.micron
                        else:
                            wav = temp[wav_hdus[sci]].data.mean(axis=0) * u.micron

                        spec2d = Spectrum1D(data * u.one, spectral_axis=wav, meta=meta)
                        spec2d.meta['INSTRUME'] = 'NIRISS'
                        spec2d.meta['mosviz_row'] = len(spec_labels_2d)

                        label = (f"{filter_name} Source "
                                 f"{temp[sci].header['SOURCEID']} spec2d "
                                 f"{orientation}")  # noqa
                        add_to_glue[label] = spec2d

                        # update labels for table viewer
                        ra, dec = cat_id_dict[temp[sci].header["SOURCEID"]]
                        ras.append(ra)
                        decs.append(dec)
                        image_add.append(image_dict[filter_name])
                        spec_labels_2d.append(label)
                        filters.append(filter)

    # Parse 1D spectra
    file_labels_1d = [k for k in files_by_labels.keys() if k.startswith("1D")]

    for flabel in file_labels_1d:
        for fname in files_by_labels[flabel]:
            print(f"Loading: {flabel} sources")

            with fits.open(fname, memmap=False) as temp:
                # Filter out HDUs we care about
                source_ids_to_filter = cat_id_dict.keys()
                filtered_hdul = fits.HDUList([hdu for hdu in temp if (
                    (hdu.name in ('PRIMARY', 'ASDF')) or
                    (hdu.header.get('SOURCEID', None) in source_ids_to_filter))])

                # SRCTYPE is required for the specutils JWST x1d reader. The reader will
                # force this to POINT if not set. Under known cases, this field will be set
                # for NIRISS programs; if it's not, something's gone wrong. Catch this
                # warning and reraise as an error to warn users.
                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("error",
                                                category=UserWarning,
                                                message=".*SRCTYPE is missing or UNKNOWN*")
                        specs = SpectrumList.read(filtered_hdul, format="JWST x1d multi")
                except UserWarning as e:
                    raise KeyError(f"The SRCTYPE keyword in the header of file {fname} "
                                   "is not populated (expected values: EXTENDED or POINT)") from e

                filter_name = fits.getheader(fname, ext=0).get('PUPIL')

                # Orientation denoted by "C", "R", or "C+R" for combined spectra
                orientation = flabel.split()[-1]

                # update 1D labels and standardize metadata for table viewer
                for sp in specs:
                    if (
                        sp.meta['header']['SPORDER'] == 1
                        and sp.meta['header']['EXTNAME'] == 'EXTRACT1D'
                    ):
                        sp.meta = standardize_metadata(sp.meta)
                        label = (f"{filter_name} Source "
                                 f"{sp.meta['SOURCEID']} spec1d "
                                 f"{orientation}")

                        spec_labels_1d.append(label)
                        add_to_glue[label] = sp

    # Add the datasets to glue - we do this in one step so that we can easily
    # optimize by avoiding recomputing the full link graph at every add
    with app.data_collection.delay_link_manager_update():
        for label, data in add_to_glue.items():
            app.add_data(data, label, notify_done=False)

        # We then populate the table inside this context manager as
        # _add_to_table does operations that also trigger link manager updates.
        _add_to_table(app, source_ids, "Identifier")
        _add_to_table(app, ras, "R.A.")
        _add_to_table(app, decs, "Dec.")
        _add_to_table(app, image_add, "Images")
        _add_to_table(app, spec_labels_1d, "1D Spectra")
        _add_to_table(app, spec_labels_2d, "2D Spectra")
        _add_to_table(app, filters, "Filter/Grating")

    app.get_viewer(table_viewer_reference_name)._shared_image = True
