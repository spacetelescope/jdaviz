import os
import re
from copy import deepcopy

from jdaviz.core.helpers import ConfigHelper

__all__ = ['Imviz']


class Imviz(ConfigHelper):
    """Imviz Helper class"""
    _default_configuration = 'imviz'

    def __init__(self, app=None, **kwargs):
        super().__init__(app=app)

        # astrowidgets ducktyping (not MVP)

        if 'image_width' in kwargs:
            self.image_width = kwargs['image_width']

        if 'image_height' in kwargs:
            self.image_height = kwargs['image_height']

        if 'pixel_coords_offset' in kwargs:
            # This gets tied to self.pixel_offset
            raise NotImplementedError

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

    # astrowidgets ducktyping (MVP)

    def center_on(self, point):
        raise NotImplementedError

    def offset_to(self, dx, dy, skycoord_offset=False):
        raise NotImplementedError

    @property
    def zoom_level(self):
        raise NotImplementedError

    @zoom_level.setter
    def zoom_level(self, val):
        raise NotImplementedError

    def zoom(self, val):
        raise NotImplementedError

    @property
    def stretch_options(self):
        raise NotImplementedError

    @property
    def stretch(self):
        raise NotImplementedError

    @stretch.setter
    def stretch(self, val):
        raise NotImplementedError

    @property
    def autocut_options(self):
        raise NotImplementedError

    @property
    def cuts(self):
        raise NotImplementedError

    @cuts.setter
    def cuts(self, val):
        raise NotImplementedError

    @property
    def colormap_options(self):
        raise NotImplementedError

    def set_colormap(self, cmap):
        raise NotImplementedError

    @property
    def click_center(self):
        return False  # No way to do this right now

    @click_center.setter
    def click_center(self, val):
        raise NotImplementedError

    @property
    def click_drag(self):
        return False  # No way to do this right now

    @click_drag.setter
    def click_drag(self, value):
        raise NotImplementedError

    @property
    def scroll_pan(self):
        return False  # No way to do this right now

    @scroll_pan.setter
    def scroll_pan(self, value):
        raise NotImplementedError

    def save(self, filename):
        raise NotImplementedError

    # astrowidgets ducktyping (not MVP)
    #
    # NOTES:
    # * logger is excluded because it is too Ginga-specific.
    # * cursor is excluded because coordinate info is in a plugin.

    @property
    def image_width(self):
        raise NotImplementedError

    @image_width.setter
    def image_width(self, value):
        raise NotImplementedError

    @property
    def image_height(self):
        raise NotImplementedError

    @image_height.setter
    def image_height(self, value):
        raise NotImplementedError

    @property
    def pixel_offset(self):
        return 0  # No way to customize right now

    # Loaders

    def load_fits(self, fitsorfn, numhdu=None, memmap=None):
        raise NotImplementedError

    def load_nddata(self, nddata):
        raise NotImplementedError

    def load_array(self, arr):
        raise NotImplementedError

    # Markers

    RESERVED_MARKER_SET_NAMES = ['all']

    @property
    def is_marking(self):
        return False  # No way to mark right now

    def start_marking(self, marker_name=None, marker=None):
        raise NotImplementedError

    def stop_marking(self, clear_markers=False):
        raise NotImplementedError

    @property
    def marker(self):
        return {}  # No way to mark right now

    @marker.setter
    def marker(self, val):
        raise NotImplementedError

    def get_markers(self, x_colname='x', y_colname='y',
                    skycoord_colname='coord', marker_name=None):
        raise NotImplementedError

    def add_markers(self, table, x_colname='x', y_colname='y',
                    skycoord_colname='coord', use_skycoord=False,
                    marker_name=None):
        raise NotImplementedError

    def remove_markers(self, marker_name=None):
        raise NotImplementedError

    def reset_markers(self):
        raise NotImplementedError


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
