import os
import re
import warnings
from copy import deepcopy

import numpy as np
from astropy.wcs.wcsapi import BaseHighLevelWCS
from glue.core import BaseData
from glue.core.link_helpers import LinkSame
from glue.core.subset import Subset, MaskSubsetState
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, NoAffineApproximation

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.helpers import ConfigHelper

__all__ = ['Imviz']


class Imviz(ConfigHelper):
    """Imviz Helper class."""
    _default_configuration = 'imviz'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_viewer = self.app.get_viewer('imviz-0')

    @property
    def default_viewer(self):
        """Default viewer instance. This is typically the first viewer ("imviz-0")."""
        return self._default_viewer

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
            * JWST ASDF-in-FITS file (requires ``asdf`` and ``gwcs``; ``data`` or given
              ``ext`` + GWCS)
            * `~astropy.io.fits.HDUList` object (first image extension found
              is loaded unless ``ext`` keyword is also given)
            * `~astropy.io.fits.ImageHDU` object
            * `~astropy.nddata.NDData` object (2D only but may have unit,
              mask, or uncertainty attached)
            * Numpy array (2D only)

        parser_reference
            This is used internally by the app.

        kwargs : dict
            Extra keywords to be passed into app-level parser.
            The only one you might call directly here is ``ext`` (any FITS
            extension format supported by `astropy.io.fits`) and
            ``show_in_viewer`` (bool).

        Notes
        -----
        When loading image formats that support RGB color like JPG or PNG, the
        files are converted to greyscale. This is done following the algorithm
        of :func:`skimage.color.rgb2grey`, which involves weighting the channels as
        ``0.2125 R + 0.7154 G + 0.0721 B``. If you prefer a different weighting,
        you can use :func:`skimage.io.imread` to produce your own greyscale
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

    def link_data(self, link_type='pixels', wcs_fallback_scheme='pixels', wcs_use_affine=True,
                  error_on_fail=False):
        """(Re)link loaded data with the desired link type.
        All existing links will be replaced.

        .. warning::

            Any markers added in Imviz would be removed automatically.
            You can add back the markers using
            :meth:`~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin.add_markers`
            for the relevant viewer(s). During the markers removal, pan/zoom will also reset.

        Parameters
        ----------
        link_type : {'pixels', 'wcs'}
            Choose to link by pixels or WCS.

        wcs_fallback_scheme : {None, 'pixels'}
            If WCS linking failed, choose to fall back to linking by pixels or not at all.
            This is only used when ``link_type='wcs'``.
            Choosing `None` may result in some Imviz functionality not working properly.

        wcs_use_affine : bool
            Use an affine transform to represent the offset between images if possible
            (requires that the approximation is accurate to within 1 pixel with the
            full WCS transformations). If approximation fails, it will automatically
            fall back to full WCS transformation. This is only used when ``link_type='wcs'``.
            Affine approximation is much more performant at the cost of accuracy.

        error_on_fail : bool
            If `True`, any failure in linking will raise an exception.
            If `False`, warnings will be emitted as snackbar messages.
            When only warnings are emitted and no links are assigned,
            some Imviz functionality may not work properly.

        Raises
        ------
        ValueError
            Invalid inputs or reference data.

        """
        if len(self.app.data_collection) <= 1:  # No need to link, we are done.
            return

        if link_type not in ('pixels', 'wcs'):
            raise ValueError(f"link_type must be 'pixels' or 'wcs', got {link_type}")
        if link_type == 'wcs' and wcs_fallback_scheme not in (None, 'pixels'):
            raise ValueError("wcs_fallback_scheme must be None or 'pixels', "
                             f"got {wcs_fallback_scheme}")

        # TODO: If different viewers have the same _marktags key, the key actually
        #       points to the same Data table. Subsequent attempt to remove the
        #       same key in this loop will emit warning.
        # Clear any existing markers. Otherwise, re-linking will crash.
        # Imviz can have multiple viewers open at the same time and each
        # tracks their own markers.
        for viewer in self.app._viewer_store.values():
            viewer.reset_markers()

        refdata, iref = get_reference_image_data(self.app)
        links_list = []
        ids0 = refdata.pixel_component_ids
        ndim_range = range(refdata.ndim)

        for i, data in enumerate(self.app.data_collection):
            # Do not link with self
            if i == iref:
                continue

            # We are not touching any existing Subsets. They keep their own links.
            if not layer_is_image_data(data):
                continue

            ids1 = data.pixel_component_ids
            try:
                if link_type == 'pixels':
                    new_links = [LinkSame(ids0[i], ids1[i]) for i in ndim_range]
                else:  # 'wcs'
                    wcslink = WCSLink(data1=refdata, data2=data, cids1=ids0, cids2=ids1)
                    if wcs_use_affine:
                        try:
                            new_links = [wcslink.as_affine_link()]
                        except NoAffineApproximation:  # pragma: no cover
                            new_links = [wcslink]
                    else:
                        new_links = [wcslink]
            except Exception as e:
                if link_type == 'wcs' and wcs_fallback_scheme == 'pixels':
                    try:
                        new_links = [LinkSame(ids0[i], ids1[i]) for i in ndim_range]
                    except Exception as e:  # pragma: no cover
                        if error_on_fail:
                            raise
                        else:
                            self.app.hub.broadcast(SnackbarMessage(
                                f"Error linking '{data.label}' to '{refdata.label}': "
                                f"{repr(e)}", color="warning", timeout=8000, sender=self.app))
                            continue
                else:
                    if error_on_fail:
                        raise
                    else:
                        self.app.hub.broadcast(SnackbarMessage(
                            f"Error linking '{data.label}' to '{refdata.label}': "
                            f"{repr(e)}", color="warning", timeout=8000, sender=self.app))
                        continue
            links_list += new_links

        if len(links_list) > 0:
            with self.app.data_collection.delay_link_manager_update():
                self.app.data_collection.set_links(links_list)
            self.app.hub.broadcast(SnackbarMessage(
                'Images successfully relinked', color='success', timeout=8000, sender=self.app))

    def load_static_regions(self, regions, **kwargs):
        """Load given region(s) into the viewer.
        Region(s) is relative to the reference image.
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

        kwargs : dict
            Extra keywords to be passed into the region's ``to_mask`` method.
            This is ignored if Numpy array is given.

        """
        # Subset is global, so we just use default viewer.
        data = self.default_viewer.state.reference_data

        for subset_label, region in regions.items():
            if subset_label.startswith('Subset'):
                warnings.warn(f'{subset_label} is not allowed, skipping. '
                              'Do not use region name that starts with Subset.')
                continue

            if hasattr(region, 'to_pixel'):
                if data_has_valid_wcs(data):
                    pixreg = region.to_pixel(data.coords)
                    mask = pixreg.to_mask(**kwargs)
                    im = mask.to_image(data.shape)
                else:
                    warnings.warn(f'{region} given but data has no valid WCS, skipping')
                    continue
            elif hasattr(region, 'to_mask'):
                mask = region.to_mask(**kwargs)
                im = mask.to_image(data.shape)
            elif (isinstance(region, np.ndarray) and region.shape == data.shape
                    and region.dtype == np.bool_):
                im = region
            else:
                warnings.warn(f'Unsupported region type: {type(region)}, skipping')
                continue

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
        regions = {}

        # Subset is global, so we just use default viewer.
        for lyr in self.default_viewer.layers:
            if (not hasattr(lyr, 'layer') or not isinstance(lyr.layer, Subset)
                    or lyr.layer.ndim != 2):
                continue

            subset_data = lyr.layer
            subset_label = subset_data.label

            # TODO: Remove this when Imviz support round-tripping, see
            # https://github.com/spacetelescope/jdaviz/pull/721
            if not subset_label.startswith('Subset'):
                continue

            region = subset_data.data.get_selection_definition(
                subset_id=subset_label, format='astropy-regions')
            regions[subset_label] = region

        return regions

    # See https://github.com/glue-viz/glue-jupyter/issues/253
    def _apply_interactive_region(self, toolname, from_pix, to_pix):
        """Mimic interactive region drawing.
        This is for internal testing only.
        """
        tool = self.default_viewer.toolbar.tools[toolname]
        tool.activate()
        tool.interact.brushing = True
        tool.interact.selected = [from_pix, to_pix]
        tool.interact.brushing = False


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


def data_has_valid_wcs(data):
    return hasattr(data, 'coords') and isinstance(data.coords, BaseHighLevelWCS)


def layer_is_image_data(layer):
    return isinstance(layer, BaseData) and layer.ndim == 2


def get_top_layer_index(viewer):
    """Get index of the top visible image layer in Imviz.
    This is because when blinked, first layer might not be top visible layer.

    """
    return [i for i, lyr in enumerate(viewer.layers)
            if lyr.visible and layer_is_image_data(lyr.layer)][-1]


def get_reference_image_data(app):
    """Return the first 2D image data in collection and its index to use as reference."""
    refdata = None
    iref = 0
    for i, data in enumerate(app.data_collection):
        if layer_is_image_data(data):
            iref = i
            refdata = data
            break
    if refdata is None:
        raise ValueError(f'No valid reference data found in collection: {app.data_collection}')
    return refdata, iref
