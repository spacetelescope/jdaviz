import os
import re
import warnings
from copy import deepcopy

import numpy as np
from astropy.utils.exceptions import AstropyDeprecationWarning
from glue.core import BaseData
from glue.core.link_helpers import LinkSame
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, NoAffineApproximation

from jdaviz.core.events import SnackbarMessage, NewViewerMessage, LinkUpdatedMessage
from jdaviz.core.helpers import ImageConfigHelper

__all__ = ['Imviz', 'link_image_data']


class Imviz(ImageConfigHelper):
    """Imviz Helper class."""
    _default_configuration = 'imviz'
    _default_viewer_reference_name = "image-viewer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app._link_type = None
        self.app._wcs_use_affine = None

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
            * JWST ASDF-in-FITS file (requires ``stdatamodels`` and ``gwcs``; ``data`` or given
              ``ext`` + GWCS)
            * Roman ASDF file or `roman_datamodels.datamodels.ImageModel`
              (requires ``roman-datamodels``)
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

    def get_aperture_photometry_results(self):
        """Return aperture photometry results, if any.
        Results are calculated using :ref:`aper-phot-simple` plugin.

        Returns
        -------
        results : `~astropy.table.QTable` or `None`
            Photometry results if available or `None` otherwise.

        """
        return self.plugins['Imviz Simple Aperture Photometry']._obj.export_table()

    def get_catalog_source_results(self):
        """Return table of sources given by querying from a catalog, if any.
        Results are calculated using :ref:`imviz-catalogs` plugin.

        Returns
        -------
        results : `~astropy.table.QTable` or `None`
            Table of sources if available or `None` otherwise.

        """
        return getattr(self.app, '_catalog_source_table', None)

    def get_data(self, data_label=None, spatial_subset=None, cls=None):
        """
        Returns data with name equal to data_label of type cls with subsets applied from
        spatial_subset.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spatial_subset : str, optional
            Spatial subset applied to data.
        cls : `~specutils.Spectrum1D`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        return self._get_data(data_label=data_label, spatial_subset=spatial_subset, cls=cls)


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


def layer_is_table_data(layer):
    return isinstance(layer, BaseData) and layer.ndim == 1


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

    .. note::

        Any markers added in Imviz will need to be removed manually before changing linking type.
        You can add back the markers using
        :meth:`~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin.add_markers`
        for the relevant viewer(s).

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
    if 'imviz-links-control' in [item['name'] for item in app.state.tray_items]:
        link_plugin = app.get_tray_item_from_name('imviz-links-control')
        if update_plugin:
            link_plugin.linking_in_progress = True
    else:
        link_plugin = None

    if link_type == app._link_type and wcs_use_affine == app._wcs_use_affine:
        data_already_linked = [link.data2 for link in app.data_collection.external_links]
    else:
        for viewer in app._viewer_store.values():
            if len(viewer._marktags):
                raise ValueError(f"cannot change link_type (from '{app._link_type}' to "
                                 f"'{link_type}') when markers are present. "
                                 f" Clear markers with viewer.reset_markers() first")
        data_already_linked = []

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

        if data in data_already_linked:
            # links already exist for this entry and we're not changing the type
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
            if len(data_already_linked):
                app.data_collection.add_link(links_list)
            else:
                app.data_collection.set_links(links_list)

        app.hub.broadcast(SnackbarMessage(
            'Images successfully relinked', color='success', timeout=8000, sender=app))

    app._link_type = link_type
    app._wcs_use_affine = wcs_use_affine

    if link_plugin is not None:
        # Only broadcast after success.
        app.hub.broadcast(LinkUpdatedMessage(link_type,
                                             wcs_fallback_scheme == 'pixels',
                                             wcs_use_affine,
                                             sender=app))
        # reset the progress spinner
        link_plugin.linking_in_progress = False

    for viewer in app._viewer_store.values():
        # viewer-state needs to know link type for reset_limits behavior
        viewer.state.linked_by_wcs = link_type == 'wcs'
