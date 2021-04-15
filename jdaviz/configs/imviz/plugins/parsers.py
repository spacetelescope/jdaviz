import base64
import os
import re
import uuid

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
def parse_data(app, file_obj, data_label=None, show_in_viewer=True):
    """Parse a data file into Imviz.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.

    file_path : str
        The path to an image data file.

    data_label : str, optional
        The label to be applied to the Glue data component.

    show_in_viewer : bool
        Show data in viewer.

    """
    # TODO: How much support needed for URL/URI?
    if isinstance(file_obj, str):
        s = os.path.splitext(file_obj)
        ext_match = re.match(r'(.+)\[(.+)\]', s[1])
        if ext_match is None:
            sfx = s[1]
            ext = None
        else:
            sfx = ext_match.group(1)
            ext = ext_match.group(2)
            if ',' in ext:
                ext = ext.split(',')
                ext[1] = int(ext[1])
                ext = tuple(ext)
        if data_label is None:
            data_label = os.path.basename(s[0])
        with fits.open(f'{s[0]}{sfx}') as pf:
            _parse_image(app, pf, data_label, show_in_viewer, ext=ext)
    else:
        if data_label is None:
            data_label = f'imviz_data|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'
        _parse_image(app, file_obj, data_label, show_in_viewer)


def _parse_image(app, file_obj, data_label, show_in_viewer, ext=None):
    if isinstance(file_obj, fits.HDUList):
        if 'ASDF' in file_obj:  # JWST ASDF-in-FITS
            if HAS_JWST_ASDF:
                if ext is None:
                    ext = 'data'
                else:
                    if isinstance(ext, tuple):
                        ext = ext[0]  # EXTVER means nothing in ASDF
                    ext = ext.lower()
                    if ext in ('sci', 'asdf'):
                        ext = 'data'

                data_label += f'[{ext.upper()}]'
                with datamodels.open(file_obj) as dm:
                    if 'bunit' in dm.meta:
                        bunit = dm.meta.bunit
                    else:
                        bunit = 'count'
                    image_ccd = Data(label=data_label)

                    # This is instance of gwcs.WCS, not astropy.wcs.WCS
                    image_ccd.coords = dm.meta.wcs

                    imdata = getattr(dm, ext)
                    component = Component.autotyped(imdata, units=bunit)
                    image_ccd.add_component(component=component, label=ext)
            else:
                raise ImportError('jwst package is missing')

        elif ext is not None:  # Load just the EXT user wants
            hdu = file_obj[ext]
            if hdu.data is not None and hdu.is_image:
                data_label += f'[{hdu.name},{hdu.ver}]'
                image_ccd = _hdu_to_ccddata(hdu, data_label)
            else:
                raise ValueError(f'{file_obj}[{ext}] is not FITS image')

        else:  # Load first image extension found
            found = False
            for hdu in file_obj:
                if hdu.data is not None and hdu.is_image:
                    data_label += f'[{hdu.name},{hdu.ver}]'
                    image_ccd = _hdu_to_ccddata(hdu, data_label)
                    found = True
                    break
            if not found:
                raise ValueError(f'{file_obj} does not have any FITS image')

    elif isinstance(file_obj, (fits.ImageHDU, fits.CompImageHDU, fits.PrimaryHDU)):
        # NOTE: ext is not used here. It only means something if HDUList is given.
        if hdu.data is not None and hdu.is_image:
            data_label += f'[{hdu.name},{hdu.ver}]'
            image_ccd = _hdu_to_ccddata(file_obj, data_label)
        else:
            raise ValueError(f'{file_obj} is not FITS image')
    else:
        raise NotImplementedError(f'Imviz does not support {file_obj}')

    app.add_data(image_ccd, data_label)
    if show_in_viewer:
        app.add_data_to_viewer("viewer-1", data_label)


def _hdu_to_ccddata(hdu, data_label):
    image_ccd = Data(label=data_label)
    image_ccd.coords = WCS(hdu.header)
    component = Component.autotyped(hdu.data, units=hdu.header.get('BUNIT', 'count'))
    image_ccd.add_component(component=component, label=f'{hdu.name},{hdu.ver}')
    return image_ccd
