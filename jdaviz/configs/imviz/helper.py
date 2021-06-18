import os
import re
from copy import deepcopy

from astropy.coordinates import SkyCoord
from astropy.utils.introspection import minversion
from astropy.wcs.wcsapi import BaseHighLevelWCS
from echo import delay_callback
from glue.core import BaseData

from jdaviz.core.helpers import ConfigHelper

__all__ = ['Imviz']

ASTROPY_LT_4_3 = not minversion('astropy', '4.3')


class Imviz(ConfigHelper):
    """Imviz Helper class"""
    _default_configuration = 'imviz'

    def load_data(self, data, parser_reference=None, **kwargs):
        """Load data into Imviz.

        Parameters
        ----------
        data : obj or str
            File name or object to be loaded. Supported formats include:

            * ``'filename.fits'`` (or any extension that ``astropy.io.fits``
              supports; first image extension found is loaded unless ``ext``
              keyword is also given)
            * ``'filename.fits[SCI]'`` (loads only first SCI extension)
            * ``'filename.fits[SCI,2]'`` (loads the second SCI extension)
            * ``'filename.jpg'`` (requires ``scikit-image``; grayscale only)
            * ``'filename.png'`` (requires ``scikit-image``; grayscale only)
            * JWST ASDF-in-FITS file (requires ``jwst``; ``data`` or given
              ``ext`` + GWCS)
            * ``astropy.io.fits.HDUList`` object (first image extension found
              is loaded unless ``ext`` keyword is also given)
            * ``astropy.io.fits.ImageHDU`` object
            * ``astropy.nddata.NDData`` object (2D only but may have unit,
              mask, or uncertainty attached)
            * Numpy array (2D only)

        parser_reference
            This is used internally by the app.

        kwargs : dict
            Extra keywords to be passed into app-level parser.
            The only one you might call directly here is ``ext`` (any FITS
            extension format supported by ``astropy.io.fits``) and
            ``show_in_viewer`` (bool).

        Notes
        -----
        When loading image formats that support RGB color like JPG or PNG, the
        files are converted to greyscale. This is done following the algorithm
        of ``skimage.color.rgb2grey``, which involves weighting the channels as
        ``0.2125 R + 0.7154 G + 0.0721 B``. If you prefer a different weighting,
        you can use ``skimage.io.imread`` to produce your own greyscale
        image as Numpy array and load the latter instead.
        """
        if isinstance(data, str):
            filelist = data.split(',')

            if len(filelist) > 1 and 'data_label' in kwargs:
                raise ValueError('Do not manually overwrite data_label for '
                                 'a list of images')

            for data in filelist:
                kw = deepcopy(kwargs)
                filepath, ext, data_label = split_filename_with_fits_ext(data)

                # This, if valid, will overwrite input.
                if ext is not None:
                    kw['ext'] = ext

                # This will only overwrite if not provided.
                if 'data_label' not in kw:
                    kw['data_label'] = data_label

                self.app.load_data(
                    filepath, parser_reference=parser_reference, **kw)

        else:
            self.app.load_data(
                data, parser_reference=parser_reference, **kwargs)

    def center_on(self, point):
        """Centers the view on a particular point.

        Parameters
        ----------
        point : tuple or `~astropy.coordinates.SkyCoord`
            If tuple of ``(X, Y)`` is given, it is assumed
            to be in data coordinates and 0-indexed.

        Raises
        ------
        AttributeError
            Sky coordinates are given but image does not have a valid WCS.

        """
        viewer = self.app.get_viewer("viewer-1")

        if isinstance(point, SkyCoord):
            i_top = get_top_layer_index(viewer)
            image = viewer.layers[i_top].layer
            if hasattr(image, 'coords') and isinstance(image.coords, BaseHighLevelWCS):
                pix = image.coords.world_to_pixel(point)  # 0-indexed X, Y
            else:
                raise AttributeError(f'{image.label} does not have a valid WCS')
        else:
            pix = point

        with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            width = viewer.state.x_max - viewer.state.x_min
            height = viewer.state.y_max - viewer.state.y_min
            viewer.state.x_min = pix[0] - (width * 0.5)
            viewer.state.y_min = pix[1] - (height * 0.5)
            viewer.state.x_max = viewer.state.x_min + width
            viewer.state.y_max = viewer.state.y_min + height

    def offset_to(self, dx, dy, skycoord_offset=False):
        """Move the center to a point that is given offset
        away from the current center.

        Parameters
        ----------
        dx, dy : float or `~astropy.units.Quantity`
            Offset value. The presence of unit depends on ``skycoord_offset``.

        skycoord_offset : bool
            If `True`, offset (lon, lat) must be given as ``Quantity``.
            Otherwise, they are in pixel values (float).

        Raises
        ------
        AttributeError
            Sky offset is given but image does not have a valid WCS.

        """
        viewer = self.app.get_viewer("viewer-1")
        width = viewer.state.x_max - viewer.state.x_min
        height = viewer.state.y_max - viewer.state.y_min

        if skycoord_offset:
            i_top = get_top_layer_index(viewer)
            image = viewer.layers[i_top].layer
            if hasattr(image, 'coords') and isinstance(image.coords, BaseHighLevelWCS):
                # To avoid distortion headache, assume offset is relative to
                # displayed center.
                x_cen = viewer.state.x_min + (width * 0.5)
                y_cen = viewer.state.y_min + (height * 0.5)
                sky_cen = image.coords.pixel_to_world(x_cen, y_cen)
                if ASTROPY_LT_4_3:
                    from astropy.coordinates import SkyOffsetFrame
                    new_sky_cen = sky_cen.__class__(
                        SkyOffsetFrame(dx, dy, origin=sky_cen.frame).transform_to(sky_cen))
                else:
                    new_sky_cen = sky_cen.spherical_offsets_by(dx, dy)
                self.center_on(new_sky_cen)
            else:
                raise AttributeError(f'{image.label} does not have a valid WCS')
        else:
            with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                viewer.state.x_min += dx
                viewer.state.y_min += dy
                viewer.state.x_max = viewer.state.x_min + width
                viewer.state.y_max = viewer.state.y_min + height


def split_filename_with_fits_ext(filename):
    """Split a ``filename[ext]`` input into filename and FITS extension.

    Parameters
    ----------
    filename : str
        Can be a plain filename or ``filename[ext]``. The latter is a form
        of input that is commonly used by DS9. Example values:

        * ``'myimage.fits'``
        * ``'myimage.fits[SCI]'`` (assumes ``EXTVER=1``)
        * ``'myimage.fits[SCI,1]'``

    Returns
    -------
    filepath : str
        Path to the file, without extension.

    ext : str, tuple, or `None`
        FITS extension, if given. Examples: ``'SCI'`` or ``('SCI', 1)``

    data_label : str
        Human-readable data label for Glue. Extension info will be added
        later in the parser.

    """
    s = os.path.splitext(filename)
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
        elif not re.match(r'\D+', ext):
            ext = int(ext)

    filepath = f'{s[0]}{sfx}'
    data_label = os.path.basename(s[0])

    return filepath, ext, data_label


def get_top_layer_index(viewer):
    """Get index of the top visible layer in Imviz.
    This is because when blinked, first layer might not be top visible layer.

    """
    return [i for i, lyr in enumerate(viewer.layers)
            if lyr.visible and isinstance(lyr.layer, BaseData)][-1]
