import base64
import os
import uuid

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData
from astropy.wcs import WCS
from glue.core.data import Component, Data
try:
    from jwst import datamodels
    HAS_JWST_ASDF = True
except ImportError:
    HAS_JWST_ASDF = False

from jdaviz.core.registries import data_parser_registry
from jdaviz.core.events import SnackbarMessage


__all__ = ['parse_data']

INFO_MSG = ("The file contains more viewable extensions. Add the '[*]' suffix"
            " to the file name to load all of them.")


@data_parser_registry("imviz-data-parser")
def parse_data(app, file_obj, ext=None, data_label=None, show_in_viewer=True):
    """Parse a data file into Imviz.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.

    file_obj : str or obj
        The path to an image data file or FITS HDUList or image object.

    ext : str, tuple, or `None`, optional
        FITS extension, if given. Examples: ``'SCI'`` or ``('SCI', 1)``

    data_label : str, optional
        The label to be applied to the Glue data component.

    show_in_viewer : bool, optional
        Show data in viewer.

    """
    if isinstance(file_obj, str):
        if data_label is None:
            data_label = os.path.splitext(os.path.basename(file_obj))[0]
        if file_obj.lower().endswith(('.jpg', '.jpeg', '.png')):
            from skimage.io import imread
            from skimage.color import rgb2gray, rgba2rgb
            im = imread(file_obj)
            if im.shape[2] == 4:
                pf = rgb2gray(rgba2rgb(im))
            else:  # Assume RGB
                pf = rgb2gray(im)
            pf = pf[::-1, :]  # Flip it
            _parse_image(app, pf, data_label, show_in_viewer, ext=ext)
        else:  # Assume FITS
            with fits.open(file_obj) as pf:
                _parse_image(app, pf, data_label, show_in_viewer, ext=ext)
    else:
        if data_label is None:
            data_label = f'imviz_data|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'
        _parse_image(app, file_obj, data_label, show_in_viewer, ext=ext)


def _parse_image(app, file_obj, data_label, show_in_viewer, ext=None):
    if data_label is None:
        raise NotImplementedError('data_label should be set by now')

    if isinstance(file_obj, fits.HDUList):
        if 'ASDF' in file_obj:  # JWST ASDF-in-FITS
            if HAS_JWST_ASDF:

                # Load all extensions
                if ext == '*':
                    data_iter = _jwst_all_to_glue_data(file_obj, data_label)

                # Load only specified extension
                else:
                    data_iter = _jwst_to_glue_data(file_obj, ext, data_label)

                    # if more than one viewable extension is found in the file,
                    # issue info message.
                    _info_nextensions(app, file_obj)

            else:
                raise ImportError('jwst package is missing')

        elif ext == '*':  # Load all extensions
            data_iter = _hdus_to_glue_data(file_obj, data_label)

        elif ext is not None:  # Load just the EXT user wants
            hdu = file_obj[ext]
            _validate_fits_image2d(hdu)
            data_iter = _hdu_to_glue_data(hdu, data_label, hdulist=file_obj)

        else:  # Load first image extension found
            found = False
            for hdu in file_obj:
                if _validate_fits_image2d(hdu, raise_error=False):
                    data_iter = _hdu_to_glue_data(hdu, data_label, hdulist=file_obj)
                    found = True

                    # if more than one viewable extension is found in the file,
                    # issue info message.
                    _info_nextensions(app, file_obj)

                    break

            if not found:
                raise ValueError(f'{file_obj} does not have any FITS image')

    elif isinstance(file_obj, (fits.ImageHDU, fits.CompImageHDU, fits.PrimaryHDU)):
        # NOTE: ext is not used here. It only means something if HDUList is given.
        _validate_fits_image2d(file_obj)
        data_iter = _hdu_to_glue_data(file_obj, data_label)

    elif isinstance(file_obj, NDData):
        data_iter = _nddata_to_glue_data(file_obj, data_label)

    elif isinstance(file_obj, np.ndarray):
        data_iter = _ndarray_to_glue_data(file_obj, data_label)

    else:
        raise NotImplementedError(f'Imviz does not support {file_obj}')

    for data, data_label in data_iter:

        # avoid duplicate data labels in colection
        if data_label in app.data_collection.labels:
            data_label = data_label + "_2"  # 0th-order solution as proposed in issue #600

        app.add_data(data, data_label)
        if show_in_viewer:
            app.add_data_to_viewer("viewer-1", data_label)


def _info_nextensions(app, file_obj):
    if _count_image2d_extensions(file_obj) > 1:
        info_msg = SnackbarMessage(INFO_MSG, color="info", timeout=8000, sender=app)
        app.hub.broadcast(info_msg)


def _count_image2d_extensions(file_obj):
    count = 0
    for hdu in file_obj:
        if _validate_fits_image2d(hdu, raise_error=False):
            count += 1
    return count


def _validate_fits_image2d(hdu, raise_error=True):
    valid = hdu.data is not None and hdu.is_image and hdu.data.ndim == 2
    if not valid and raise_error:
        raise ValueError(
            f'Imviz cannot load this HDU ({hdu}): '
            f'has_data={hdu.data is not None}, is_image={hdu.is_image}, '
            f'name={hdu.name}, ver={hdu.ver}')
    return valid


def _validate_bunit(bunit, raise_error=True):
    # TODO: Do we want to handle weird FITS BUNIT values here?
    try:
        u.Unit(bunit)
    except Exception:
        if raise_error:
            raise
        valid = False
    else:
        valid = True
    return valid


# ---- Functions that handle input from JWST FITS files -----

def _jwst_all_to_glue_data(file_obj, data_label):
    for hdu in file_obj:
        if _validate_fits_image2d(hdu, raise_error=False):

            ext = hdu.name.lower()
            if ext == 'sci':
                ext = 'data'

            data, new_data_label = _jwst2data(file_obj, ext, data_label)

            yield data, new_data_label


def _jwst_to_glue_data(file_obj, ext, data_label):
    # Translate FITS extension into JWST ASDF convention.
    if ext is None:
        ext = 'data'
    else:
        if isinstance(ext, tuple):
            ext = ext[0]  # EXTVER means nothing in ASDF
        ext = ext.lower()
        if ext in ('sci', 'asdf'):
            ext = 'data'

    data, new_data_label = _jwst2data(file_obj, ext, data_label)

    yield data, new_data_label


def _jwst2data(file_obj, ext, data_label):
    comp_label = ext.upper()
    new_data_label = f'{data_label}[{comp_label}]'
    data = Data(label=new_data_label)
    unit_attr = f'bunit_{ext}'

    # This is very specific to JWST pipeline image output.
    with datamodels.open(file_obj) as dm:
        if (unit_attr in dm.meta and
                _validate_bunit(getattr(dm.meta, unit_attr), raise_error=False)):
            bunit = getattr(dm.meta, unit_attr)
        else:
            bunit = ''

        # This is instance of gwcs.WCS, not astropy.wcs.WCS
        if hasattr(dm.meta, 'wcs'):
            data.coords = dm.meta.wcs

        imdata = getattr(dm, ext)
        component = Component.autotyped(imdata, units=bunit)
        data.add_component(component=component, label=comp_label)

    return data, new_data_label


# ---- Functions that handle input from non-JWST FITS files -----

def _hdu_to_glue_data(hdu, data_label, hdulist=None):
    data, data_label = _hdu2data(hdu, data_label, hdulist)
    yield data, data_label


def _hdus_to_glue_data(file_obj, data_label):
    for hdu in file_obj:
        if _validate_fits_image2d(hdu, raise_error=False):
            data, new_data_label = _hdu2data(hdu, data_label, file_obj)
            yield data, new_data_label


def _hdu2data(hdu, data_label, hdulist):
    if 'BUNIT' in hdu.header and _validate_bunit(hdu.header['BUNIT'], raise_error=False):
        bunit = hdu.header['BUNIT']
    else:
        bunit = ''

    comp_label = f'{hdu.name.upper()},{hdu.ver}'
    new_data_label = f'{data_label}[{comp_label}]'

    data = Data(label=new_data_label)
    data.coords = WCS(hdu.header, hdulist)
    component = Component.autotyped(hdu.data, units=bunit)
    data.add_component(component=component, label=comp_label)

    return data, new_data_label


# ---- Functions that handle input from arrays -----

def _nddata_to_glue_data(ndd, data_label):
    if ndd.data.ndim != 2:
        raise ValueError(f'Imviz cannot load this NDData with ndim={ndd.data.ndim}')

    for attrib in ['data', 'mask', 'uncertainty']:
        arr = getattr(ndd, attrib)
        if arr is None:
            continue
        comp_label = attrib.upper()
        cur_label = f'{data_label}[{comp_label}]'
        cur_data = Data(label=cur_label)
        if ndd.wcs is not None:
            cur_data.coords = ndd.wcs
        raw_arr = arr
        if attrib == 'data':
            bunit = ndd.unit or ''
        elif attrib == 'uncertainty':
            raw_arr = arr.array
            bunit = arr.unit or ''
        else:
            bunit = ''
        component = Component.autotyped(raw_arr, units=bunit)
        cur_data.add_component(component=component, label=comp_label)
        yield cur_data, cur_label


def _ndarray_to_glue_data(arr, data_label):
    if arr.ndim != 2:
        raise ValueError(f'Imviz cannot load this array with ndim={arr.ndim}')

    data = Data(label=data_label)
    component = Component.autotyped(arr)
    data.add_component(component=component, label='DATA')
    yield data, data_label
