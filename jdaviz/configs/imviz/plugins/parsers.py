import os
import warnings

import asdf
import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData
from astropy.wcs import WCS
from astropy.utils.data import cache_contents

from glue.core.data import Component, Data
from stdatamodels import asdf_in_fits

from jdaviz.core.registries import data_parser_registry
from jdaviz.core.events import SnackbarMessage
from jdaviz.utils import (
    standardize_metadata, standardize_roman_metadata,
    PRIHDR_KEY, _wcs_only_label, download_uri_to_path
)

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True

__all__ = ['parse_data']

INFO_MSG = ("The file contains more viewable extensions. Add the '[*]' suffix"
            " to the file name to load all of them.")


def prep_data_layer_as_dq(data):
    # nans are used to mark "good" flags in the DQ colormap, so
    # convert DQ array to float to support nans:
    for component_id in data.main_components:
        if component_id.label.startswith("DQ"):
            break

    cid = data.get_component(component_id)
    data_arr = np.float32(cid.data)
    data_arr[data_arr == 0] = np.nan
    data.update_components({cid: data_arr})


@data_parser_registry("imviz-data-parser")
def parse_data(app, file_obj, ext=None, data_label=None,
               parent=None, cache=None, local_path=None, timeout=None):
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
    if isinstance(file_obj, str):
        if data_label is None:
            data_label = os.path.splitext(os.path.basename(file_obj))[0]

        # try parsing file_obj as a URI/URL:
        file_obj = download_uri_to_path(
            file_obj, cache=cache, local_path=local_path, timeout=timeout
        )

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
            _parse_image(app, pf, data_label, ext=ext, parent=parent)

        elif file_obj_lower.endswith('.asdf'):
            try:
                if HAS_ROMAN_DATAMODELS:
                    with rdd.open(file_obj) as pf:
                        _parse_image(app, pf, data_label, ext=ext, parent=parent)
            except TypeError:
                # if roman_datamodels cannot parse the file, load it with asdf:
                with asdf.open(file_obj) as af:
                    _parse_image(app, af, data_label, ext=ext, parent=parent)

        elif file_obj_lower.endswith('.reg'):
            # This will load DS9 regions as Subset but only if there is already data.
            app.get_tray_item_from_name('g-subset-tools').import_region(file_obj,
                                                                        combination_mode='new')

        else:  # Assume FITS
            with fits.open(file_obj) as pf:
                available_extensions = [hdu.name for hdu in pf]

                # if FITS file contains SCI and DQ extensions, assume the
                # parent for the DQ is SCI:
                if (
                    'SCI' in available_extensions and
                    ext == 'DQ' and parent is None
                ):
                    loaded_data_labels = [data.label for data in app.data_collection]
                    latest_sci_extension = [label for label in loaded_data_labels
                                            if label.endswith('[DATA]')][-1]
                    parent = latest_sci_extension

                _parse_image(app, pf, data_label, ext=ext, parent=parent)
    else:
        _parse_image(app, file_obj, data_label, ext=ext, parent=parent)


def get_image_data_iterator(app, file_obj, data_label, ext=None):
    """This function is for internal use, so other viz can also extract image data
    like Imviz does.
    """
    if isinstance(file_obj, fits.HDUList):
        if 'ASDF' in file_obj:  # JWST ASDF-in-FITS
            # Load multiple extensions
            if ext == '*' or isinstance(ext, (tuple, list)):
                data_iter = _jwst_all_to_glue_data(file_obj, data_label, load_extensions=ext)

            # Load only specified extension
            else:
                data_iter = _jwst_to_glue_data(file_obj, ext, data_label)

                # if more than one viewable extension is found in the file,
                # issue info message.
                _info_nextensions(app, file_obj)

        elif ext == '*' or isinstance(ext, (tuple, list)):  # Load multiple extensions
            data_iter = _hdus_to_glue_data(file_obj, data_label, ext=ext)

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
        if file_obj.meta.get(_wcs_only_label, False):
            data_iter = _wcsonly_to_glue_data(file_obj, data_label)
        else:
            data_iter = _nddata_to_glue_data(file_obj, data_label)

    elif isinstance(file_obj, np.ndarray):
        data_iter = _ndarray_to_glue_data(file_obj, data_label)

    # load Roman 2D datamodels:
    elif HAS_ROMAN_DATAMODELS and isinstance(file_obj, rdd.DataModel):
        data_iter = _roman_2d_to_glue_data(file_obj, data_label, ext=ext)

    # load ASDF files that may not validate as Roman datamodels:
    elif isinstance(file_obj, asdf.AsdfFile):
        data_iter = _roman_asdf_2d_to_glue_data(file_obj, data_label, ext=ext)

    else:
        raise NotImplementedError(f'Imviz does not support {file_obj}')

    return data_iter


def _parse_image(app, file_obj, data_label, ext=None, parent=None):
    if app is None:
        raise ValueError("app is None, cannot proceed")
    if data_label is None:
        data_label = app.return_data_label(file_obj, ext, alt_name="image_data")
    data_iter = get_image_data_iterator(app, file_obj, data_label, ext=ext)

    # Save the SCI extension to this list:
    sci_ext = None

    for data, data_label in data_iter:

        # if the science extension hasn't been identified yet, do so here:
        if sci_ext is None and data.ndim == 2 and ('[DATA' in data_label or '[SCI' in data_label):
            sci_ext = data_label

        if not data.meta.get(_wcs_only_label, False):
            data_label = app.return_data_label(data_label, alt_name="image_data")

        # TODO: generalize/centralize this for use in other configs too
        if '[DQ' in data_label:
            prep_data_layer_as_dq(data)

        if parent is not None:
            parent_data_label = parent
        elif '[DQ' in data_label:
            parent_data_label = sci_ext
        else:
            parent_data_label = None

        app.add_data(data, data_label, parent=parent_data_label)

    # Do not link image data here. We do it at the end in Imviz.load_data()


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

def _jwst_all_to_glue_data(file_obj, data_label, load_extensions='*'):
    for hdu in file_obj:
        if (
            _validate_fits_image2d(hdu, raise_error=False) and
            (load_extensions == '*' or hdu.name in load_extensions)
        ):

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


def _try_gwcs_to_fits_sip(gwcs):
    """
    Try to convert this GWCS to FITS SIP. Some GWCS models
    cannot be converted to FITS SIP. In that case, a warning
    is raised and the GWCS is used, as is.
    """
    try:
        result = WCS(gwcs.to_fits_sip())
    except ValueError as err:
        warnings.warn(
            "The GWCS coordinates could not be simplified to "
            "a SIP-based FITS WCS, the following error was "
            f"raised: {err}",
            UserWarning
        )
        result = gwcs

    return result


def _jwst2data(file_obj, ext, data_label, try_gwcs_to_fits_sip=False):
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
                gwcs = dm_meta['wcs']

                if try_gwcs_to_fits_sip:
                    coords = _try_gwcs_to_fits_sip(gwcs)
                else:
                    coords = gwcs

                data.coords = coords

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

    if ext == '*':
        # NOTE: Update as needed. Should cover all the image extensions available.
        ext_list = ('data', 'dq', 'err', 'var_poisson', 'var_rnoise')
    elif ext is None:
        ext_list = ('data', )
    elif isinstance(ext, (list, tuple)):
        ext_list = ext
    else:
        ext_list = (ext, )

    meta = standardize_roman_metadata(file_obj)
    coords = getattr(getattr(file_obj, 'meta', {}), 'wcs', None)

    for cur_ext in ext_list:
        comp_label = cur_ext.upper()
        new_data_label = f'{data_label}[{comp_label}]'
        data = Data(coords=coords, label=new_data_label)

        # This could be a quantity or a ndarray:
        ext_values = getattr(file_obj, cur_ext)
        bunit = getattr(ext_values, 'unit', '')
        component = Component.autotyped(np.array(ext_values), units=bunit)
        data.add_component(component=component, label=comp_label)
        data.meta.update(meta)

        if comp_label == 'dq':
            prep_data_layer_as_dq(data)

        yield data, new_data_label


def _roman_asdf_2d_to_glue_data(file_obj, data_label, ext=None, try_gwcs_to_fits_sip=False):
    if ext == '*':
        # NOTE: Update as needed. Should cover all the image extensions available.
        ext_list = ('data', 'dq', 'err', 'var_poisson', 'var_rnoise')
    elif ext is None:
        ext_list = ('data', )
    elif isinstance(ext, (list, tuple)):
        ext_list = ext
    else:
        ext_list = (ext, )

    roman = file_obj.tree.get('roman')
    meta = roman.get('meta', {})
    gwcs = meta.get('wcs', None)

    if try_gwcs_to_fits_sip and gwcs is not None:
        coords = _try_gwcs_to_fits_sip(gwcs)
    else:
        coords = gwcs

    for cur_ext in ext_list:
        if cur_ext in roman:
            comp_label = cur_ext.upper()
            new_data_label = f'{data_label}[{comp_label}]'
            data = Data(coords=coords, label=new_data_label)

            # This could be a quantity or a ndarray:
            ext_values = roman.get(cur_ext)
            bunit = getattr(ext_values, 'unit', '')
            component = Component(np.array(ext_values), units=bunit)
            data.add_component(component=component, label=comp_label)
            data.meta.update(standardize_metadata(dict(meta)))
            if comp_label == 'DQ':
                prep_data_layer_as_dq(data)

            yield data, new_data_label


# ---- Functions that handle input from non-JWST, non-Roman FITS files -----

def _hdu_to_glue_data(hdu, data_label, hdulist=None):
    data, data_label = _hdu2data(hdu, data_label, hdulist)
    yield data, data_label


def _hdus_to_glue_data(file_obj, data_label, ext=None):
    for hdu in file_obj:
        if ext is None or ext == '*' or hdu.name in ext:
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

    for attrib in ('data', 'mask', 'uncertainty'):
        arr = getattr(ndd, attrib)
        if arr is None:
            continue
        comp_label = attrib.upper()
        cur_label = f'{data_label}[{comp_label}]'
        cur_data = Data(label=cur_label)
        cur_data.meta.update(standardize_metadata(ndd.meta))
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
    yield (data, data_label)


# ---- Functions that handle WCS-only data -----

def _wcsonly_to_glue_data(ndd, data_label):
    """Return Data given NDData containing WCS-only data."""
    arr = ndd.data
    data = Data(label=data_label)
    data.meta.update(standardize_metadata(ndd.meta))
    data.coords = ndd.wcs
    component = Component.autotyped(arr, units="")
    data.add_component(component=component, label="DATA")
    yield (data, data_label)
