import os
import re
import warnings
from copy import deepcopy

import numpy as np
from astropy.utils.decorators import deprecated
from astropy.utils.exceptions import AstropyDeprecationWarning
from glue.core import BaseData
from glue.core.link_helpers import LinkSame
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, NoAffineApproximation

from jdaviz.core.events import SnackbarMessage, NewViewerMessage, LinkUpdatedMessage
from jdaviz.core.helpers import ImageConfigHelper, data_has_valid_wcs

__all__ = ['Imviz', 'link_image_data']


class Imviz(ImageConfigHelper):
    """Imviz Helper class."""
    _default_configuration = 'imviz'
    _default_viewer_reference_name = "image-viewer"

    def create_image_viewer(self, viewer_name=None):
        """Create a new image viewer.

        To display data in this new viewer programmatically,
        first get the new viewer ID from the small tab on the top
        left of viewer display. Then, use
        :meth:`~jdaviz.app.Application.add_data_to_viewer` from ``imviz.app``
        by passing in the new viewer ID and the desired data label,
        once per dataset you wish to display.

        Alternately, you can also display data interactively via the GUI.

        Parameters
        ----------
        viewer_name : str or `None`
            Viewer name/ID to use. If `None`, it is auto-generated.

        Returns
        -------
        viewer : `~jdaviz.configs.imviz.plugins.viewers.ImvizImageView`
            Image viewer instance.

        """
        from jdaviz.configs.imviz.plugins.viewers import ImvizImageView

        # Cannot assign data to real Data because it loads but it will
        # not update checkbox in Data menu.
        return self.app._on_new_viewer(
            NewViewerMessage(ImvizImageView, data=None, sender=self.app),
            vid=viewer_name, name=viewer_name)

    def destroy_viewer(self, viewer_id):
        """Destroy a viewer associated with the given ID.

        Raises
        ------
        ValueError
            Default viewer cannot be destroyed.

        """
        if viewer_id not in self.app._viewer_store:  # Silent no-op
            return
        if viewer_id == f'{self.app.config}-0':
            raise ValueError(f"Default viewer '{viewer_id}' cannot be destroyed")
        self.app.vue_destroy_viewer_item(viewer_id)

    def load_data(self, data, data_label=None, do_link=True, show_in_viewer=True, **kwargs):
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
            * Numpy array (2D or 3D); if 3D, it will treat each slice at
              ``axis=0`` as a separate image (limit is 16 slices), however
              loading too many slices will cause performance issue,
              so consider using Cubeviz instead.

        data_label : str or `None`
            Data label to go with the given data. If not given, this is
            automatically determined from filename or randomly generated.
            The final label shown in Imviz may have additional information
            appended for clarity.

        do_link : bool
            Link the data after parsing. Set this to `False` if you want to
            load multiple data back-to-back but you must remember to run
            :meth:`link_data` manually at the end.

        show_in_viewer : str or bool
            If `True`, show the data in default viewer.  If a string, show in that viewer.

        kwargs : dict
            Extra keywords to be passed into app-level parser.
            The only one you might call directly here is ``ext`` (any FITS
            extension format supported by `astropy.io.fits`).

        Notes
        -----
        When loading image formats that support RGB color like JPG or PNG, the
        files are converted to greyscale. This is done following the algorithm
        of :func:`skimage.color.rgb2gray`, which involves weighting the channels as
        ``0.2125 R + 0.7154 G + 0.0721 B``. If you prefer a different weighting,
        you can use :func:`skimage.io.imread` to produce your own greyscale
        image as Numpy array and load the latter instead.

        """
        prev_data_labels = self.app.data_collection.labels

        if isinstance(data, str):
            filelist = data.split(',')

            if len(filelist) > 1 and data_label:
                raise ValueError('Do not manually overwrite data_label for '
                                 'a list of images')

            for data in filelist:
                kw = deepcopy(kwargs)
                filepath, ext, cur_data_label = split_filename_with_fits_ext(data)

                # This, if valid, will overwrite input.
                if ext is not None:
                    kw['ext'] = ext

                # This will only overwrite if not provided.
                if not data_label:
                    kw['data_label'] = None
                else:
                    kw['data_label'] = data_label

                self.app.load_data(filepath, parser_reference='imviz-data-parser', **kw)

        elif isinstance(data, np.ndarray) and data.ndim >= 3:
            if data.ndim > 3:
                data = data.squeeze()
                if data.ndim != 3:
                    raise ValueError(f'Imviz cannot load this array with ndim={data.ndim}')

            max_n_slice = 16  # Arbitrary limit for performance reasons
            for i in range(data.shape[0]):
                if i == max_n_slice:
                    warnings.warn(f'{max_n_slice} or more 3D slices found, stopping; '
                                  'please use Cubeviz')
                    break

                kw = deepcopy(kwargs)

                if data_label:
                    kw['data_label'] = data_label

                self.app.load_data(data[i, :, :], parser_reference='imviz-data-parser', **kw)

        else:
            if data_label:
                kwargs['data_label'] = data_label
            self.app.load_data(data, parser_reference='imviz-data-parser', **kwargs)

        # find the current label(s) - TODO: replace this by calling default label functionality
        # above instead of having to refind it
        applied_labels = [label for label in self.app.data_collection.labels if label not in prev_data_labels]  # noqa

        if show_in_viewer is True:
            show_in_viewer = f"{self.app.config}-0"

        if self._in_batch_load and show_in_viewer:
            for applied_label in applied_labels:
                self._delayed_show_in_viewer_labels[applied_label] = show_in_viewer

        elif do_link:
            if 'Links Control' not in self.plugins.keys():
                # otherwise plugin will handle linking automatically with DataCollectionAddMessage
                self.link_data(link_type='pixels', error_on_fail=False)

            # One input might load into multiple Data objects.
            # NOTE: this will not add entries that were skipped with do_link=False
            # but the batch_load context manager will handle that logic
            if show_in_viewer:
                for applied_label in applied_labels:
                    self.app.add_data_to_viewer(show_in_viewer, applied_label)
        else:
            warnings.warn(AstropyDeprecationWarning("do_link=False is deprecated in v3.1 and will "
                                                    "be removed in a future release.  Use with "
                                                    "viz.batch_load() instead."))

    def link_data(self, **kwargs):
        """(Re)link loaded data in Imviz with the desired link type.
        All existing links will be replaced.

        See :func:`~jdaviz.configs.imviz.helper.link_image_data`
        for available keyword options and more details.
        """
        link_image_data(self.app, **kwargs)

    @deprecated('2.9', alternative='load_regions_from_file')
    def load_static_regions_from_file(self, region_file, region_format='ds9', prefix='region',
                                      max_num_regions=20, **kwargs):
        """Load regions defined in the given file.
        See :ref:`regions:regions_io` for supported file formats.

        Parameters
        ----------
        region_file : str
            Path to region file.

        region_format : {'crtf', 'ds9', 'fits'}
            See :meth:`regions.Regions.get_formats`.

        prefix : str
            Prefix for the Subset names generated by loaded regions.
            Names will have the format of ``<prefix>_<i>``, where ``i``
            is the index in the load order.

        max_num_regions : int
            Maximum number of regions to read from the file, starting
            from top of the file, invalid regions included.

        kwargs : dict
            See :meth:`load_static_regions`.

        Returns
        -------
        bad_regions : dict
            See :meth:`load_static_regions`.

        """
        from regions import Regions
        raw_regs = Regions.read(region_file, format=region_format)
        my_regions = dict([(f'{prefix}_{i}', reg) for i, reg in
                           enumerate(raw_regs[:max_num_regions])])
        with warnings.catch_warnings():  # No need to emit deprecation again.
            warnings.filterwarnings('ignore', category=AstropyDeprecationWarning)
            bad_regions = self.load_static_regions(my_regions, **kwargs)
        return bad_regions

    @deprecated('2.9', alternative='load_regions')
    def load_static_regions(self, regions, **kwargs):
        """Load given region(s) into the viewer.
        Region(s) is relative to the reference image.
        Once loaded, the region(s) cannot be modified.

        .. note:: Loading too many regions will affect Imviz performance.

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

        Returns
        -------
        bad_regions : dict
            Dictionary mapping region names to the regions that failed to load.
            If all the regions loaded successfully, this will be empty.

        """
        from glue.core.subset import MaskSubsetState

        bad_regions = {}
        # Subset is global, so we just use default viewer.
        data = self.default_viewer.state.reference_data

        # TODO: Enable this after https://github.com/glue-viz/glue/issues/2275 is fixed.
        # existing_labels = [lyr.layer.label for lyr in self.default_viewer.layers]

        for subset_label, region in regions.items():
            if subset_label.startswith('Subset'):
                bad_regions[subset_label] = region
                warnings.warn(f'{subset_label} is not allowed, skipping. '
                              'Do not use region name that starts with Subset.')
                continue

            # TODO: Enable this after https://github.com/glue-viz/glue/issues/2275 is fixed.
            # if subset_label in existing_labels:
            #    bad_regions[subset_label] = region
            #    warnings.warn(f'{subset_label} is already used, skipping. '
            #                  'Consider using a different region name.')
            #    continue

            im = None

            if hasattr(region, 'to_pixel'):
                if data_has_valid_wcs(data):
                    try:
                        pixreg = region.to_pixel(data.coords)
                        mask = pixreg.to_mask(**kwargs)
                        im = mask.to_image(data.shape)
                    except Exception as e:
                        bad_regions[subset_label] = region
                        warnings.warn(f'{subset_label}: {region} failed to load, skipping: '
                                      f'{repr(e)}')
                        continue
                else:
                    bad_regions[subset_label] = region
                    warnings.warn(f'{subset_label}: {region} given but data has no valid WCS, '
                                  'skipping')
                    continue
            elif hasattr(region, 'to_mask'):
                try:
                    mask = region.to_mask(**kwargs)
                    im = mask.to_image(data.shape)
                except Exception as e:
                    bad_regions[subset_label] = region
                    warnings.warn(f'{subset_label}: {region} failed to load, skipping: {repr(e)}')
                    continue
            elif (isinstance(region, np.ndarray) and region.shape == data.shape
                    and region.dtype == np.bool_):
                im = region

            if im is None:
                bad_regions[subset_label] = region
                warnings.warn(f'{subset_label}: Unsupported region type for {region}, skipping')
                continue

            # NOTE: Region creation info is thus lost.
            try:
                state = MaskSubsetState(im, data.pixel_component_ids)
                self.app.data_collection.new_subset_group(subset_label, state)
            except Exception as e:
                bad_regions[subset_label] = region
                warnings.warn(f'{subset_label}: {region} failed to load, skipping: {repr(e)}')
                continue

        n_reg_in = len(regions)
        n_reg_out = n_reg_in - len(bad_regions)
        if n_reg_out == n_reg_in:
            snack_color = "success"
        elif n_reg_out == 0:
            snack_color = "error"
        else:
            snack_color = "warning"
        self.app.hub.broadcast(SnackbarMessage(
            f"Loaded {n_reg_out}/{n_reg_in} regions",
            color=snack_color, timeout=8000, sender=self.app))

        return bad_regions

    def get_aperture_photometry_results(self):
        """Return aperture photometry results, if any.
        Results are calculated using :ref:`aper-phot-simple` plugin.

        Returns
        -------
        results : `~astropy.table.QTable` or `None`
            Photometry results if available or `None` otherwise.

        """
        return getattr(self.app, '_aper_phot_results', None)

    def get_catalog_source_results(self):
        """Return table of sources given by querying from a catalog, if any.
        Results are calculated using :ref:`imviz-catalogs` plugin.

        Returns
        -------
        results : `~astropy.table.QTable` or `None`
            Table of sources if available or `None` otherwise.

        """
        return getattr(self.app, '_catalog_source_table', None)


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


def link_image_data(app, link_type='pixels', wcs_fallback_scheme='pixels', wcs_use_affine=True,
                    error_on_fail=False, update_plugin=True):
    """(Re)link loaded data in Imviz with the desired link type.
    All existing links will be replaced.

    .. warning::

        Any markers added in Imviz would be removed automatically.
        You can add back the markers using
        :meth:`~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin.add_markers`
        for the relevant viewer(s). During the markers removal, pan/zoom will also reset.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        Application associated with Imviz, e.g., ``imviz.app``.

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

    update_plugin : bool
        Whether to update the state of the "Links Control" plugin, if available.

    Raises
    ------
    ValueError
        Invalid inputs or reference data.

    """
    if len(app.data_collection) <= 1:  # No need to link, we are done.
        return

    if link_type not in ('pixels', 'wcs'):
        raise ValueError(f"link_type must be 'pixels' or 'wcs', got {link_type}")
    if link_type == 'wcs' and wcs_fallback_scheme not in (None, 'pixels'):
        raise ValueError("wcs_fallback_scheme must be None or 'pixels', "
                         f"got {wcs_fallback_scheme}")

    # if the plugin exists, send a message so that the plugin's state is updated and spinner
    # is shown (the plugin will make a call back here)
    if update_plugin and 'imviz-links-control' in [item['name'] for item in app.state.tray_items]:
        link_plugin = app.get_tray_item_from_name('imviz-links-control')
        link_plugin.linking_in_progress = True
    else:
        link_plugin = None

    # TODO: If different viewers have the same _marktags key, the key actually
    #       points to the same Data table. Subsequent attempt to remove the
    #       same key in this loop will emit warning.
    # Clear any existing markers. Otherwise, re-linking will crash.
    # Imviz can have multiple viewers open at the same time and each
    # tracks their own markers.
    for viewer in app._viewer_store.values():
        viewer.reset_markers()

    refdata, iref = get_reference_image_data(app)
    links_list = []
    ids0 = refdata.pixel_component_ids
    ndim_range = range(refdata.ndim)

    for i, data in enumerate(app.data_collection):
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
                        app.hub.broadcast(SnackbarMessage(
                            f"Error linking '{data.label}' to '{refdata.label}': "
                            f"{repr(e)}", color="warning", timeout=8000, sender=app))
                        continue
            else:
                if error_on_fail:
                    raise
                else:
                    app.hub.broadcast(SnackbarMessage(
                        f"Error linking '{data.label}' to '{refdata.label}': "
                        f"{repr(e)}", color="warning", timeout=8000, sender=app))
                    continue
        links_list += new_links

    if len(links_list) > 0:
        with app.data_collection.delay_link_manager_update():
            app.data_collection.set_links(links_list)

        app.hub.broadcast(SnackbarMessage(
            'Images successfully relinked', color='success', timeout=8000, sender=app))

    if link_plugin is not None:
        # Only broadcast after success.
        app.hub.broadcast(LinkUpdatedMessage(link_type,
                                             wcs_fallback_scheme == 'pixels',
                                             wcs_use_affine,
                                             sender=app))
        # reset the progress spinner
        link_plugin.linking_in_progress = False
