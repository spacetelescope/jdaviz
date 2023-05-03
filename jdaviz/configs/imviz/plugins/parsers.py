import os

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData
from astropy.wcs import WCS
from astropy.utils.data import cache_contents

from glue.core.data import Component, Data
from gwcs.wcs import WCS as GWCS
from stdatamodels import asdf_in_fits

from jdaviz.core.registries import data_parser_registry
from jdaviz.core.events import SnackbarMessage
from jdaviz.utils import standardize_metadata, PRIHDR_KEY

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True

__all__ = ['parse_data']

INFO_MSG = ("The file contains more viewable extensions. Add the '[*]' suffix"
            " to the file name to load all of them.")


@data_parser_registry("imviz-data-parser")
def parse_data(app, file_obj, ext=None, data_label=None):
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

    """
    if isinstance(file_obj, str):
        if data_label is None:
            data_label = os.path.splitext(os.path.basename(file_obj))[0]

        # If file_obj is a path to a cached file from
        # astropy.utils.data.download_file, the path has no file extension.
        # Here we check if the file is in the download cache, and if it is,
        # we look up the file extension from the source URL:
        if file_obj.endswith('contents'):
            path_to_url_mapping = {v: k for k, v in cache_contents().items() if file_obj}
            source_url = path_to_url_mapping[file_obj]
            # file_obj_lower is only used for checking extensions,
            # file_obj is passed for parsing and is not modified here:
            file_obj_lower = source_url.split('/')[-1].lower()
        else:
            file_obj_lower = file_obj.lower()

        if file_obj_lower.endswith(('.jpg', '.jpeg', '.png')):
            from skimage.io import imread
            from skimage.color import rgb2gray, rgba2rgb
            im = imread(file_obj)
            if im.shape[2] == 4:
                pf = rgb2gray(rgba2rgb(im))
            else:  # Assume RGB
                pf = rgb2gray(im)
            pf = pf[::-1, :]  # Flip it
            _parse_image(app, pf, data_label, ext=ext)

        elif file_obj_lower.endswith('.asdf'):
            if not HAS_ROMAN_DATAMODELS:
                raise ImportError(
                    "ASDF detected but roman-datamodels is not installed."
                )
            with rdd.open(file_obj) as pf:
                _parse_image(app, pf, data_label, ext=ext)
        else:  # Assume FITS
            with fits.open(file_obj) as pf:
                _parse_image(app, pf, data_label, ext=ext)
    else:
        _parse_image(app, file_obj, data_label, ext=ext)


def get_image_data_iterator(app, file_obj, data_label, ext=None):
    """This function is for internal use, so other viz can also extract image data
    like Imviz does.
    """

    if isinstance(file_obj, fits.HDUList):
        if 'ASDF' in file_obj:  # JWST ASDF-in-FITS
            # Load all extensions
            if ext == '*':
                data_iter = _jwst_all_to_glue_data(file_obj, data_label)

            # Load only specified extension
            else:
                data_iter = _jwst_to_glue_data(file_obj, ext, data_label)

                # if more than one viewable extension is found in the file,
                # issue info message.
                _info_nextensions(app, file_obj)

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

    # Roman 2D datamodels
    elif HAS_ROMAN_DATAMODELS and isinstance(file_obj, rdd.DataModel):
        data_iter = _roman_2d_to_glue_data(file_obj, data_label, ext=ext)

    else:
        raise NotImplementedError(f'Imviz does not support {file_obj}')

    return data_iter


def _parse_image(app, file_obj, data_label, ext=None):
    if app is None:
        raise ValueError("app is None, cannot proceed")
    if data_label is None:
        data_label = app.return_data_label(file_obj, ext, alt_name="image_data")
    data_iter = get_image_data_iterator(app, file_obj, data_label, ext=ext)

    for data, data_label in data_iter:
        if isinstance(data.coords, GWCS) and (data.coords.bounding_box is not None):
            # keep a copy of the original bounding box so we can detect
            # when extrapolating beyond, but then remove the bounding box
            # so that image layers are not cropped.
            # NOTE: if extending this beyond GWCS, the mouseover logic
            # for outside_*_bounding_box should also be updated.
            data.coords._orig_bounding_box = data.coords.bounding_box
            data.coords.bounding_box = None
        data_label = app.return_data_label(data_label, alt_name="image_data")
        app.add_data(data, data_label)

    # Do not run link_image_data here. We do it at the end in Imviz.load_data()


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
        if hdu.data is not None and hdu.is_image:
            ndim = hdu.data.ndim
        else:
            ndim = None
        raise ValueError(
            f'Imviz cannot load this HDU ({hdu}): '
            f'has_data={hdu.data is not None}, is_image={hdu.is_image}, '
            f'name={hdu.name}, ver={hdu.ver}, ndim={ndim}')
    return valid


def _validate_bunit(bunit, raise_error=True):
    # TODO: Handle weird FITS BUNIT values here, as needed.
    if bunit == 'ELECTRONS/S':
        valid = 'electron/s'
    elif bunit == 'ELECTRONS':
        valid = 'electron'
    else:
        try:
            u.Unit(bunit)
        except Exception:
            if raise_error:
                raise
            valid = ''
        else:
            valid = bunit
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
        fits_ext = 'sci'
    else:
        if isinstance(ext, tuple):
            ext = ext[0]  # EXTVER means nothing in ASDF
        ext = ext.lower()
        if ext in ('sci', 'asdf'):
            ext = 'data'
            fits_ext = 'sci'
        else:
            fits_ext = ext

    _validate_fits_image2d(file_obj[fits_ext])
    data, new_data_label = _jwst2data(file_obj, ext, data_label)

    yield data, new_data_label


def _jwst2data(file_obj, ext, data_label):
    comp_label = ext.upper()
    new_data_label = f'{data_label}[{comp_label}]'
    data = Data(label=new_data_label)
    unit_attr = f'bunit_{ext}'

    try:
        # This is very specific to JWST pipeline image output.
        with asdf_in_fits.open(file_obj) as af:
            dm = af.tree
            dm_meta = af.tree["meta"]
            data.meta.update(standardize_metadata(dm_meta))

            if unit_attr in dm_meta:
                bunit = _validate_bunit(dm_meta[unit_attr], raise_error=False)
            else:
                bunit = ''

            # This is instance of gwcs.WCS, not astropy.wcs.WCS
            if 'wcs' in dm_meta:
                data.coords = dm_meta['wcs']

            imdata = dm[ext]
            component = Component.autotyped(imdata, units=bunit)

            # Might have bad GWCS. If so, we exclude it.
            try:
                data.add_component(component=component, label=comp_label)
            except Exception:  # pragma: no cover
                data.coords = None
                data.add_component(component=component, label=comp_label)

    # TODO: Do not need this when jwst.datamodels finally its own package.
    # This might happen for grism image; fall back to FITS loader without WCS.
    except Exception:
        if ext == 'data':
            ext = 'sci'
        hdu = file_obj[ext]
        return _hdu2data(hdu, data_label, file_obj, include_wcs=False)

    return data, new_data_label


# ---- Functions that handle input from Roman ASDF files -----

def _roman_2d_to_glue_data(file_obj, data_label, ext=None):

    if ext == '*' or ext is None:
        # NOTE: Update as needed. Should cover all the image extensions available.
        ext_list = ('data', 'dq', 'err', 'var_poisson', 'var_rnoise')
    elif isinstance(ext, (list, tuple)):
        ext_list = ext
    else:
        ext_list = (ext, )

    meta = getattr(file_obj, 'meta', {})
    coords = getattr(meta, 'wcs', None)

    for cur_ext in ext_list:
        comp_label = cur_ext.upper()
        new_data_label = f'{data_label}[{comp_label}]'
        data = Data(coords=coords, label=new_data_label)

        # This could be a quantity or a ndarray:
        ext_values = getattr(file_obj, cur_ext)
        bunit = getattr(ext_values, 'unit', '')
        component = Component.autotyped(np.array(ext_values), units=bunit)
        data.add_component(component=component, label=comp_label)
        data.meta.update(standardize_metadata(dict(meta)))

        yield data, new_data_label


# ---- Functions that handle input from non-JWST, non-Roman FITS files -----

def _hdu_to_glue_data(hdu, data_label, hdulist=None):
    data, data_label = _hdu2data(hdu, data_label, hdulist)
    yield data, data_label


def _hdus_to_glue_data(file_obj, data_label):
    for hdu in file_obj:
        if _validate_fits_image2d(hdu, raise_error=False):
            data, new_data_label = _hdu2data(hdu, data_label, file_obj)
            yield data, new_data_label


def _hdu2data(hdu, data_label, hdulist, include_wcs=True):
    if 'BUNIT' in hdu.header:
        bunit = _validate_bunit(hdu.header['BUNIT'], raise_error=False)
    else:
        bunit = ''

    comp_label = f'{hdu.name.upper()},{hdu.ver}'
    new_data_label = f'{data_label}[{comp_label}]'

    data = Data(label=new_data_label)
    if hdulist is not None and hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
        data.meta[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)
    data.meta.update(standardize_metadata(hdu.header))
    if include_wcs:
        data.coords = WCS(hdu.header, hdulist)
    component = Component.autotyped(hdu.data, units=bunit)
    data.add_component(component=component, label=comp_label)

    return data, new_data_label


# ---- Functions that handle input from arrays -----

def _nddata_to_glue_data(ndd, data_label):
    if ndd.data.ndim != 2:
        raise ValueError(f'Imviz cannot load this NDData with ndim={ndd.data.ndim}')

    for attrib, sub_attrib in zip(
            ['data', 'mask', 'uncertainty'],
            ['data', None, 'array']
    ):
        arr = getattr(ndd, attrib)
        if arr is None:
            continue
        cur_data = Data()
        cur_data.meta.update(standardize_metadata(ndd.meta))
        if ndd.wcs is not None:
            cur_data.coords = ndd.wcs
        raw_arr = arr

        if sub_attrib is not None:
            base_arr = getattr(raw_arr, sub_attrib)
        else:
            base_arr = raw_arr
        wcs_only = np.all(np.isnan(base_arr))
        cur_data.meta.update({'WCS-ONLY': wcs_only})

        cur_label = f'{data_label}'
        comp_label = attrib.upper()
        if not wcs_only:
            cur_label += f'[{comp_label}]'
        cur_data.label = cur_label

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
    yield (data, data_label)
