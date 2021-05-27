import os
import re
from copy import deepcopy
import warnings

import numpy as np
from glue.core.subset import MaskSubsetState

from jdaviz.core.helpers import ConfigHelper

__all__ = ['Imviz']


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

    def load_static_regions(self, regions, data_label, **kwargs):
        """Load given region(s) into the viewer.
        Once loaded, the region(s) cannot be modified.

        Parameters
        ----------
        regions : dict
            Dictionary mapping desired region name to one of the following:

            * Astropy ``regions`` object
            * ``photutils`` apertures (limited support until ``photutils``
              fully supports ``regions``)
            * Numpy boolean array (shape must match data)

            Region name that starts with "Subset" is forbidden and reserved
            for internal use only.

        data_label : str
            Label to retrieve a specific data set from the viewer instance.
            Glue Subset object representing this region will be created
            based on this data set.

        kwargs : dict
            Extra keywords to be passed into the region's ``to_mask`` method.
            This is ignored if Numpy array is given.

        """
        # TODO: Refactor after https://github.com/spacetelescope/jdaviz/pull/644
        # is merged.
        # Or do I have to use self.app.get_data_from_viewer for some reason?
        data = self.app.data_collection[
            self.app.data_collection.labels.index(data_label)]

        for subset_label, region in regions.items():
            if subset_label.startswith('Subset'):
                warnings.warn(f'{subset_label} is now allowed, skipping. '
                              'Do not use region name that starts with Subset.')
                continue

            if hasattr(region, 'to_mask'):
                mask = region.to_mask(**kwargs)
                im = mask.to_image(data.shape)
            elif (isinstance(region, np.ndarray) and region.shape == data.shape
                    and region.dtype == np.bool_):
                im = region
            else:
                raise TypeError(f'Unsupported region type: {type(region)}')

            # NOTE: Region creation info is thus lost.
            state = MaskSubsetState(im, data.pixel_component_ids)
            self.app.data_collection.new_subset_group(subset_label, state)

    def get_interactive_regions(self):
        """Return regions interactively drawn in the viewer.
        This does not return regions added via :meth:`load_static_regions`.

        Returns
        -------
        regions : dict
            Dictionary mapping interactive region names to respective Astropy
            ``regions`` objects.

        """
        return self.app.get_subsets_from_viewer('viewer-1')


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
