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


def _add_to_table(app, data, comp_label):
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

        viewer = app.get_viewer("table-viewer")
        viewer.add_data(table_data)
    else:
        mos_table = app.data_collection['MOS Table']
        if comp_label not in mos_table.component_ids():
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
    def _parse_as_spectrum1d(path):
        # Parse as a FITS file and assume the WCS is correct
        with fits.open(path) as hdulist:
            data = hdulist[1].data
            header = hdulist[1].header
            wcs = WCS(header)
            metadata = standardize_metadata(header)
            metadata[PRIHDR_KEY] = standardize_metadata(hdulist[0].header)
        return Spectrum1D(data, wcs=wcs, meta=metadata)

    # Coerce into list-like object
    if not isinstance(data_obj, (list, tuple, SpectrumCollection)):
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
                    data = Spectrum1D.read(data)
                except IORegistryError:
                    data = _parse_as_spectrum1d(data)

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
            _add_to_table(app, data_labels, '2D Spectra')

    if show_in_viewer:
        if len(data_labels) > 1:
            raise ValueError("More than one data label provided, unclear " +
                             "which to show in viewer")
        app.add_data_to_viewer("spectrum-2d-viewer", data_labels[0])


def _load_fits_image_from_filename(filename, app):
    with fits.open(filename) as hdulist:
        # We do not use the generated labels
        data_list = [d for d, _ in get_image_data_iterator(app, hdulist, "Image", ext=None)]
    return data_list


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
            app.add_data_to_viewer("image-viewer", data_labels[0])

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


def _get_source_identifiers_by_hdu(hdus, filepaths=None, header_keys=['SOURCEID', 'OBJECT']):
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
    if not(isinstance(header_keys, Iterable) and not isinstance(header_keys, (str, dict))):
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


@data_parser_registry("mosviz-niriss-parser")
def mos_niriss_parser(app, data_dir, obs_label=""):
    """
    Attempts to parse all data for a NIRISS dataset in the specified
    directory, which should include:
    - *_direct_*_cal.fits : Direct 2D image
    - *_direct_*_cat.ecsv : Source catalog
    - *_WFSSR_*_cal.fits : 2D spectra in first orientation
    - *_WFSSC_*_cal.fits : 2D spectra in second orientation
    - *_WFSSR_*_x1d.fits : 1D spectra in first orientation
    - *_WFSSC_*_x1d.fits : 1D spectra in second orientation
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

        with fits.open(image_file) as file_obj:
            data_iter = get_image_data_iterator(app, file_obj, "Image", ext=None)
            data_obj = [d[0] for d in data_iter]  # We do not use the generated labels
            image_data = data_obj[0]  # Grab the first one. TODO: Error if multiple found?

        with fits.open(image_file) as temp:
            filter_wcs[pupil] = temp[1].header

        image_data.label = image_label
        add_to_glue[image_label] = image_data

        image_dict[pupil] = image_label

    # Parse 2D spectra
    spec_labels_2d = []
    filters = []
    for f in ["2D Spectra C", "2D Spectra R"]:

        for fname in file_lists[f]:
            print(f"Loading: {f} sources")

            orientation = f[-1]
            filter_name = [x
                           for x in fname.split("/")[-1].split("_")
                           if x[0] == "F" or x[0] == "f"][0]

            with fits.open(fname, memmap=False) as temp:
                sci_hdus = []
                wav_hdus = {}
                for i in range(len(temp)):

                    if i == 0:
                        filter = temp[0].header["FILTER"]

                    if "EXTNAME" in temp[i].header:
                        if temp[i].header["EXTNAME"] == "SCI":
                            sci_hdus.append(i)
                            wav_hdus[i] = ('WAVELENGTH', temp[i].header['EXTVER'])

                # Now get a Spectrum1D object for each SCI HDU
                source_ids.extend(_get_source_identifiers_by_hdu([temp[sci] for sci in sci_hdus]))

                for sci in sci_hdus:

                    if temp[sci].header["SPORDER"] == 1:

                        data = temp[sci].data
                        meta = standardize_metadata(temp[sci].header)
                        meta[PRIHDR_KEY] = standardize_metadata(temp[0].header)

                        # The wavelength is stored in a WAVELENGTH HDU. This is
                        # a 2D array, but in order to be able to use Spectrum1D
                        # we use the average wavelength for all image rows
                        wav = temp[wav_hdus[sci]].data.mean(axis=0) * u.micron

                        spec2d = Spectrum1D(data * u.one, spectral_axis=wav, meta=meta)

                        spec2d.meta['INSTRUME'] = 'NIRISS'
                        spec2d.meta['mosviz_row'] = len(spec_labels_2d)

                        label = f"{filter_name} Source {temp[sci].header['SOURCEID']} spec2d {orientation}"  # noqa
                        ra, dec = pupil_id_dict[filter_name][temp[sci].header["SOURCEID"]]
                        ras.append(ra)
                        decs.append(dec)
                        image_add.append(image_dict[filter_name])
                        spec_labels_2d.append(label)

                        add_to_glue[label] = spec2d

                        filters.append(filter)

    spec_labels_1d = []
    for f in ["1D Spectra C", "1D Spectra R"]:

        for fname in file_lists[f]:
            print(f"Loading: {f} sources")

            with fits.open(fname, memmap=False) as temp:
                # TODO: Remove this once valid SRCTYPE values are present in all headers
                for hdu in temp:
                    if ("SRCTYPE" in hdu.header and
                            (hdu.header["SRCTYPE"] in ("POINT", "EXTENDED"))):
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
                    # Make metadata layout conform with other viz.
                    spec.meta = standardize_metadata(spec.meta)
                    spec.meta['mosviz_row'] = len(spec_labels_1d)

                    if spec.meta['SPORDER'] == 1 and spec.meta['EXTNAME'] == "EXTRACT1D":
                        label = f"{filter_name} Source {spec.meta['SOURCEID']} spec1d {orientation}"
                        spec_labels_1d.append(label)
                        add_to_glue[label] = spec

    # Add the datasets to glue - we do this in one step so that we can easily
    # optimize by avoiding recomputing the full link graph at every add

    with app.data_collection.delay_link_manager_update():

        for label, data in add_to_glue.items():
            app.add_data(data, label, notify_done=False)

        # We then populate the table inside this context manager as _add_to_table
        # does operations that also trigger link manager updates.
        _add_to_table(app, source_ids, "Identifier")
        _add_to_table(app, ras, "R.A.")
        _add_to_table(app, decs, "Dec.")
        _add_to_table(app, image_add, "Images")
        _add_to_table(app, spec_labels_1d, "1D Spectra")
        _add_to_table(app, spec_labels_2d, "2D Spectra")
        _add_to_table(app, filters, "Filter/Grating")

    app.get_viewer('table-viewer')._shared_image = True
