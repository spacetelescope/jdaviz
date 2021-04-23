import base64
import os
import uuid

from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from glue.core.data import Component, Data
try:
    from jwst import datamodels
    HAS_JWST_ASDF = True
except ImportError:
    HAS_JWST_ASDF = False

from jdaviz.core.registries import data_parser_registry

__all__ = ['parse_data']


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
    # TODO: How much support needed for URL/URI?
    if isinstance(file_obj, str):
        if data_label is None:
            data_label = os.path.splitext(os.path.basename(file_obj))[0]
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
                data, data_label = _jwst_to_glue_data(file_obj, ext, data_label)
            else:
                raise ImportError('jwst package is missing')

        elif ext is not None:  # Load just the EXT user wants
            hdu = file_obj[ext]
            _validate_image2d(hdu)
            data, data_label = _hdu_to_glue_data(hdu, data_label)

        else:  # Load first image extension found
            found = False
            for hdu in file_obj:
                if _validate_image2d(hdu, raise_error=False):
                    data, data_label = _hdu_to_glue_data(hdu, data_label)
                    found = True
                    break
            if not found:
                raise ValueError(f'{file_obj} does not have any FITS image')

    elif isinstance(file_obj, (fits.ImageHDU, fits.CompImageHDU, fits.PrimaryHDU)):
        # NOTE: ext is not used here. It only means something if HDUList is given.
        _validate_image2d(file_obj)
        data, data_label = _hdu_to_glue_data(file_obj, data_label)

    else:
        raise NotImplementedError(f'Imviz does not support {file_obj}')

    app.add_data(data, data_label)
    if show_in_viewer:
        app.add_data_to_viewer("viewer-1", data_label)


def _validate_image2d(hdu, raise_error=True):
    valid = hdu.data is not None and hdu.is_image and hdu.data.ndim == 2
    if not valid and raise_error:
        raise ValueError(f'Imviz cannot load this HDU ({hdu}): '
                         f'is_image={hdu.is_image}, data={hdu.data}')
    return valid


def _validate_bunit(bunit, raise_error=True):
    try:
        u.Unit(bunit)
    except Exception:
        if raise_error:
            raise
        valid = False
    else:
        valid = True
    return valid


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

    comp_label = ext.upper()
    data_label = f'{data_label}[{comp_label}]'
    data = Data(label=data_label)

    # This is very specific to JWST pipeline image output.
    with datamodels.open(file_obj) as dm:
        if 'bunit' in dm.meta and _validate_bunit(dm.meta.bunit, raise_error=False):
            bunit = dm.meta.bunit
        else:
            bunit = 'count'

        # This is instance of gwcs.WCS, not astropy.wcs.WCS
        data.coords = dm.meta.wcs

        imdata = getattr(dm, ext)
        component = Component.autotyped(imdata, units=bunit)
        data.add_component(component=component, label=comp_label)

    return data, data_label


def _hdu_to_glue_data(hdu, data_label):
    if 'BUNIT' in hdu.header and _validate_bunit(hdu.header['BUNIT'], raise_error=False):
        bunit = hdu.header['BUNIT']
    else:
        bunit = 'count'

    comp_label = f'{hdu.name.upper()},{hdu.ver}'
    data_label = f'{data_label}[{comp_label}]'
    data = Data(label=data_label)
    data.coords = WCS(hdu.header)
    component = Component.autotyped(hdu.data, units=bunit)
    data.add_component(component=component, label=comp_label)
    return data, data_label
