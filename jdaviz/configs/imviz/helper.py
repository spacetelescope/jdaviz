import os
import re
import warnings
from copy import deepcopy

import numpy as np
from glue.core import BaseData
from glue.core.link_helpers import LinkSame

from jdaviz.core.events import SnackbarMessage, NewViewerMessage
from jdaviz.core.helpers import ImageConfigHelper
from jdaviz.utils import data_has_valid_wcs, _wcs_only_label

__all__ = ['Imviz']


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
                layer_is_wcs_only.append(data.meta.get(_wcs_only_label, False))
                layer_has_wcs.append(data_has_valid_wcs(data))

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
            if 'Orientation' not in self.plugins.keys():
                # otherwise plugin will handle linking automatically with DataCollectionAddMessage
                self.link_data(link_type='wcs')

            # One input might load into multiple Data objects.
            # NOTE: If the batch_load context manager was used, it will
            # handle that logic instead.
            if show_in_viewer:
                for applied_label, visible, has_wcs in zip(
                        applied_labels, applied_visible, layer_has_wcs
                ):
                    if (has_wcs and linked_by_wcs) or not linked_by_wcs:
                        self.app.add_data_to_viewer(show_in_viewer, applied_label, visible=visible)

    def link_data(self, link_type='pixels', wcs_fallback_scheme=None, wcs_use_affine=True):
        """(Re)link loaded data in Imviz with the desired link type.
        All existing links will be replaced.

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

        """
        from jdaviz.configs.imviz.plugins.orientation.orientation import link_type_msg_to_trait
        plg = self.plugins["Orientation"]
        plg._obj.wcs_use_fallback = wcs_fallback_scheme == 'pixels'
        plg.wcs_use_affine = wcs_use_affine
        plg.link_type = link_type_msg_to_trait[link_type]

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
            One of the link types accepted by the Orientation plugin
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
            avail_links = [f"({elink.data1.label}, {elink.data2.label})"
                           for elink in self.app.data_collection.external_links]
            raise ValueError(f'{data_label_1} and {data_label_2} combo not found '
                             f'in data collection external links: {avail_links}')

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


def layer_is_image_data(layer):
    return layer_is_2d(layer) and not layer.meta.get(_wcs_only_label, False)


def layer_is_wcs_only(layer):
    return layer_is_2d(layer) and layer.meta.get(_wcs_only_label, False)


def get_wcs_only_layer_labels(app):
    return [data.label for data in app.data_collection
            if layer_is_wcs_only(data)]


def get_top_layer_index(viewer):
    """Get index of the top visible image layer in Imviz.
    This is because when blinked, first layer might not be top visible layer.

    """
    visible_image_layers = [
        i for i, lyr in enumerate(viewer.layers)
        if lyr.visible and layer_is_image_data(lyr.layer)
    ]

    if len(visible_image_layers):
        return visible_image_layers[-1]
    return None


def get_reference_image_data(app, viewer_id=None):
    """
    Return the current reference data in the given image viewer and its index.
    By default, the first viewer is used.
    """
    if viewer_id is None:
        refdata = app._jdaviz_helper.default_viewer._obj.state.reference_data
    else:
        viewer = app.get_viewer_by_id(viewer_id)
        refdata = viewer.state.reference_data

    if refdata is not None:
        iref = app.data_collection.index(refdata)
        return refdata, iref

    return None, -1
