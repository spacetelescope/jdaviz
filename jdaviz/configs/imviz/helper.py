import os
import re
import warnings
from copy import deepcopy

import numpy as np
import astropy.units as u
from astropy.wcs.wcsapi import BaseHighLevelWCS
from gwcs.wcs import WCS as GWCS
from glue.core import BaseData
from glue.core.link_helpers import LinkSame
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, NoAffineApproximation

from jdaviz.core.events import SnackbarMessage, NewViewerMessage, LinkUpdatedMessage
from jdaviz.core.helpers import ImageConfigHelper
from jdaviz.configs.imviz.wcs_utils import (
    _get_rotated_nddata_from_label, get_compass_info
)

__all__ = ['Imviz', 'link_image_data']

base_wcs_layer_label = 'Default orientation'


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

        # add WCS-only layers from all viewers into the new viewer
        add_layers_to_viewer = get_wcs_only_layer_labels(self.app)

        return self.app._on_new_viewer(
            NewViewerMessage(ImvizImageView, data=None, sender=self.app),
            vid=viewer_name, name=viewer_name,
            add_layers_to_viewer=add_layers_to_viewer)

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

    def load_data(self, data, data_label=None, show_in_viewer=True, **kwargs):
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
        applied_labels = []
        applied_visible = []
        layer_is_wcs_only = []
        layer_has_wcs = []
        for data in self.app.data_collection:
            label = data.label
            if label not in prev_data_labels:
                applied_labels.append(label)
                applied_visible.append(True)
                layer_is_wcs_only.append(data.meta.get(self.app._wcs_only_label, False))
                layer_has_wcs.append(hasattr(data.coords, 'pixel_to_world'))

        if show_in_viewer is True:
            show_in_viewer = f"{self.app.config}-0"

        if show_in_viewer:
            linked_by_wcs = self.app._link_type == 'wcs'
            if linked_by_wcs:
                for applied_label, visible, is_wcs_only, has_wcs in zip(
                        applied_labels, applied_visible, layer_is_wcs_only, layer_has_wcs
                ):
                    if not is_wcs_only and linked_by_wcs and not has_wcs:
                        self.app.hub.broadcast(SnackbarMessage(
                            f"'{applied_label}' will be added to the data collection but not "
                            f"the viewer '{show_in_viewer}', since data are linked by WCS, but "
                            f"'{applied_label}' has no WCS.",
                            color="warning", timeout=8000, sender=self)
                        )

        if self._in_batch_load and show_in_viewer:
            for applied_label, is_wcs_only in zip(applied_labels, layer_is_wcs_only):
                if not is_wcs_only:
                    self._delayed_show_in_viewer_labels[applied_label] = show_in_viewer

        else:
            if 'Links Control' not in self.plugins.keys():
                # otherwise plugin will handle linking automatically with DataCollectionAddMessage
                self.link_data(link_type='pixels', error_on_fail=False)

            # One input might load into multiple Data objects.
            # NOTE: If the batch_load context manager was used, it will
            # handle that logic instead.
            if show_in_viewer:
                for applied_label, visible, has_wcs in zip(
                        applied_labels, applied_visible, layer_has_wcs
                ):
                    if (has_wcs and linked_by_wcs) or not linked_by_wcs:
                        self.app.add_data_to_viewer(show_in_viewer, applied_label, visible=visible)

    def link_data(self, **kwargs):
        """(Re)link loaded data in Imviz with the desired link type.
        All existing links will be replaced.

        See :func:`~jdaviz.configs.imviz.helper.link_image_data`
        for available keyword options and more details.
        """
        link_image_data(self.app, **kwargs)

    def get_link_type(self, data_label_1, data_label_2):
        """Find the type of ``glue`` linking between the given
        data labels. A link is bi-directional. If there are
        more than 2 data in the collection, one of the given
        labels should be the reference data or look-up will fail.

        Parameters
        ----------
        data_label_1, data_label_2 : str
           Labels for the data linked together.

        Returns
        -------
        link_type : {'pixels', 'wcs', 'self'}
            One of the link types accepted by :func:`~jdaviz.configs.imviz.helper.link_image_data`
            or ``'self'`` if the labels are identical.

        Raises
        ------
        ValueError
            Link look-up failed.

        """
        if data_label_1 == data_label_2:
            return "self"

        link_type = None
        for elink in self.app.data_collection.external_links:
            elink_labels = (elink.data1.label, elink.data2.label)
            if data_label_1 in elink_labels and data_label_2 in elink_labels:
                if isinstance(elink, LinkSame):  # Assumes WCS link never uses LinkSame
                    link_type = 'pixels'
                else:  # If not pixels, must be WCS
                    link_type = 'wcs'
                break  # Might have duplicate, just grab first match

        if link_type is None:
            raise ValueError(f'{data_label_1} and {data_label_2} combo not found '
                             'in data collection external links')

        return link_type

    def get_aperture_photometry_results(self):
        """Return aperture photometry results, if any.
        Results are calculated using :ref:`aper-phot-simple` plugin.

        Returns
        -------
        results : `~astropy.table.QTable` or `None`
            Photometry results if available or `None` otherwise.

        """
        return self.plugins['Aperture Photometry']._obj.export_table()

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

    def get_ref_data(self):
        return get_reference_image_data(self.app)


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


def layer_is_2d(layer):
    # returns True for subclasses of BaseData with ndim=2, both for
    # layers that are WCS-only as well as images containing data:
    return isinstance(layer, BaseData) and layer.ndim == 2


# NOTE: Sync with app._wcs_only_label as needed.
def layer_is_image_data(layer):
    return layer_is_2d(layer) and not layer.meta.get("_WCS_ONLY", False)


# NOTE: Sync with app._wcs_only_label as needed.
def layer_is_wcs_only(layer):
    return layer_is_2d(layer) and layer.meta.get("_WCS_ONLY", False)


def layer_is_table_data(layer):
    return isinstance(layer, BaseData) and layer.ndim == 1


def get_bottom_layer(viewer):
    """
    Get the first-loaded image layer in Imviz.
    """
    image_layers = [lyr.layer for lyr in viewer.layers
                    if lyr.visible and layer_is_image_data(lyr.layer)]
    if not len(image_layers):
        return None
    return image_layers[0]


def get_wcs_only_layer_labels(app):
    return [data.label for data in app.data_collection
            if layer_is_wcs_only(data)]


def get_top_layer_index(viewer):
    """Get index of the top visible image layer in Imviz.
    This is because when blinked, first layer might not be top visible layer.

    """
    return [i for i, lyr in enumerate(viewer.layers)
            if lyr.visible and layer_is_image_data(lyr.layer)][-1]


def get_reference_image_data(app, viewer_id=None):
    """
    Return the reference data in the first image viewer and its index
    """
    if viewer_id is None:
        refdata = app._jdaviz_helper.default_viewer.state.reference_data
    else:
        viewer = app.get_viewer_by_id(viewer_id)
        refdata = viewer.state.reference_data

    if refdata is not None:
        iref = app.data_collection.index(refdata)
        return refdata, iref

    # if reference data not found above, fall back on old method:
    for i, data in enumerate(app.data_collection):
        if layer_is_image_data(data):
            iref = i
            refdata = data
            break
    if refdata is None:
        raise ValueError(f'No valid reference data found in collection: {app.data_collection}')
    return refdata, iref


def link_image_data(app, link_type='pixels', wcs_fallback_scheme=None, wcs_use_affine=True,
                    error_on_fail=False, update_plugin=True):
    """(Re)link loaded data in Imviz with the desired link type.

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
    if len(app.data_collection) <= 1 and link_type != 'wcs':  # No need to link, we are done.
        return

    if link_type not in ('pixels', 'wcs'):
        raise ValueError(f"link_type must be 'pixels' or 'wcs', got {link_type}")
    if link_type == 'wcs' and wcs_fallback_scheme not in (None, 'pixels'):
        raise ValueError("wcs_fallback_scheme must be None or 'pixels', "
                         f"got {wcs_fallback_scheme}")
    if link_type == 'wcs':
        at_least_one_data_have_wcs = len([
            hasattr(d, 'coords') and isinstance(d.coords, (BaseHighLevelWCS, GWCS))
            for d in app.data_collection
        ]) > 0
        if not at_least_one_data_have_wcs:
            if wcs_fallback_scheme is None:
                if error_on_fail:
                    raise ValueError("link_type can only be 'wcs' when wcs_fallback_scheme "
                                     "is 'None' if all data have valid WCS.")
                else:
                    return
            else:
                # fall back on pixel linking
                link_type = 'pixels'
    # if the plugin exists, send a message so that the plugin's state is updated and spinner
    # is shown (the plugin will make a call back here)
    if 'imviz-links-control' in [item['name'] for item in app.state.tray_items]:
        link_plugin = app.get_tray_item_from_name('imviz-links-control')
        if update_plugin:
            link_plugin.linking_in_progress = True
    else:
        link_plugin = None

    data_already_linked = []
    if link_type == app._link_type and wcs_use_affine == app._wcs_use_affine:
        for link in app.data_collection.external_links:
            if link.data1.label != app._wcs_only_label:
                data_already_linked.append(link.data2)
    else:
        for viewer in app._viewer_store.values():
            if len(viewer._marktags):
                raise ValueError(f"cannot change link_type (from '{app._link_type}' to "
                                 f"'{link_type}') when markers are present. "
                                 f" Clear markers with viewer.reset_markers() first")

    old_link_type = getattr(app, '_link_type', None)
    refdata, iref = get_reference_image_data(app)
    # default reference layer is the first-loaded image:
    default_reference_layer = get_bottom_layer(app._jdaviz_helper.default_viewer)

    # if linking via WCS, add WCS-only reference data layer:
    insert_base_wcs_layer = (
        link_type == 'wcs' and
        base_wcs_layer_label not in [d.label for d in app.data_collection]
    )

    if insert_base_wcs_layer:
        degn = get_compass_info(default_reference_layer.coords, default_reference_layer.shape)[-3]
        # Default rotation is the same orientation as the original reference data:
        rotation_angle = -degn * u.deg
        ndd = _get_rotated_nddata_from_label(
            app, default_reference_layer.label, rotation_angle
        )
        app._jdaviz_helper.load_data(ndd, base_wcs_layer_label)

        # set base layer to reference data in all viewers:
        for viewer_id in app.get_viewer_ids():
            app._change_reference_data(
                base_wcs_layer_label, viewer_id=viewer_id
            )

        refdata, iref = get_reference_image_data(app)

    if link_type == 'pixels' and old_link_type == 'wcs':
        # if changing from WCS to pixel linking, set bottom image data
        # layer as reference data in all viewers:
        refdata = get_bottom_layer(app._jdaviz_helper.default_viewer)

        for viewer_id in app.get_viewer_ids():
            app._change_reference_data(
                refdata.label, viewer_id=viewer_id
            )

    links_list = []
    ids0 = refdata.pixel_component_ids
    ndim_range = range(refdata.ndim)

    for i, data in enumerate(app.data_collection):
        # Do not link with self
        if i == iref:
            continue

        # We are not touching any existing Subsets. They keep their own links.
        if not layer_is_2d(data):
            continue

        if data in data_already_linked:
            # links already exist for this entry and we're not changing the type
            continue

        ids1 = data.pixel_component_ids
        new_links = []
        try:
            if link_type == 'pixels':
                new_links = [LinkSame(ids0[i], ids1[i]) for i in ndim_range]
            # otherwise if linking by WCS *and* this data entry has WCS:
            elif hasattr(data.coords, 'pixel_to_world'):
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
    viewer_ref = app._jdaviz_helper.default_viewer.reference
    viewer_item = app._get_viewer_item(viewer_ref)

    viewer_item['reference_data_label'] = refdata.label

    if link_plugin is not None:
        # Only broadcast after success.
        app.hub.broadcast(LinkUpdatedMessage(link_type,
                                             wcs_fallback_scheme == 'pixels',
                                             wcs_use_affine,
                                             sender=app))

        if insert_base_wcs_layer:
            # update all viewer items with reference data:
            for viewer_id in app.get_viewer_ids():
                viewer_item = app._get_viewer_item(viewer_id)
                viewer_item['reference_data_label'] = refdata.label

        # reset the progress spinner
        link_plugin.linking_in_progress = False

    for viewer in app._viewer_store.values():
        wcs_linked = link_type == 'wcs'
        # viewer-state needs to know link type for reset_limits behavior
        viewer.state.linked_by_wcs = wcs_linked
        # also need to store a copy in the viewer item for the data dropdown to access
        viewer_item['linked_by_wcs'] = wcs_linked

        # if changing from one link type to another, reset the limits:
        if link_type != old_link_type:
            viewer.state.reset_limits()
