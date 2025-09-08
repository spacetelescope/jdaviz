import os
import re
import warnings
from copy import deepcopy

import numpy as np
from astropy.io import fits
from astropy.utils import deprecated
from glue.core.link_helpers import LinkSame

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.helpers import ImageConfigHelper
from jdaviz.utils import (get_wcs_only_layer_labels,
                          get_reference_image_data)

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True

__all__ = ['Imviz']

# temporary implementation of a "current app" feature for imviz,
# useful for Cobalt dev work until imviz is fully superceded by
# the current app feature in deconfigged. see:
# https://github.com/spacetelescope/jdaviz/pull/3632
global _current_app
_current_app = None


class Imviz(ImageConfigHelper):
    """Imviz Helper class."""
    _default_configuration = 'imviz'
    _default_viewer_reference_name = "image-viewer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        global _current_app
        _current_app = self

        # Temporary during deconfig process
        self.load = self._load
        self.app.state.dev_loaders = True

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

    @deprecated(since="4.3", alternative="load")
    def load_data(self, data, data_label=None, show_in_viewer=True,
                  gwcs_to_fits_sip=False, **kwargs):
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

        gwcs_to_fits_sip : bool, optional
            Try to convert GWCS coordinates into an approximate FITS SIP solution. Typical
            precision loss due to this approximation is of order 0.1 pixels. This may
            improve image rendering performance for images with expensive GWCS
            transformations. (Default: False)

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
        extensions = kwargs.pop('ext', None)

        if isinstance(data, str) and "," in data:
            data = data.split(',')

        if isinstance(data, (tuple, list)) and not isinstance(data, fits.HDUList):
            if len(data) > 1 and data_label:
                raise ValueError('Do not manually overwrite data_label for '
                                 'a list of images')
            with self.batch_load():
                for data_i in data:
                    kw = deepcopy(kwargs)
                    self.load_data(data_i,
                                   data_label=data_label,
                                   show_in_viewer=show_in_viewer,
                                   gwcs_to_fits_sip=gwcs_to_fits_sip,
                                   **kw)
            return

        if isinstance(show_in_viewer, str):
            viewer = [show_in_viewer]
        elif isinstance(show_in_viewer, bool):
            viewer = '*' if show_in_viewer else []
        else:
            raise TypeError('show_in_viewer must be a bool or str')

        if isinstance(data, np.ndarray) and data.ndim >= 3:
            if data.ndim > 3:
                data = data.squeeze()
                # in parser, if nddata, return self.input.squeeze()
                if data.ndim != 3:
                    raise ValueError(f'Imviz cannot load this array with ndim={data.ndim}')

            max_n_slice = 16  # Arbitrary limit for performance reasons
            for i in range(data.shape[0]):
                if i == max_n_slice:
                    warnings.warn(f'{max_n_slice} or more 3D slices found, stopping; '
                                  'please use Cubeviz')
                    break

                self._load(data[i, :, :],
                           format='Image',
                           data_label=data_label,
                           extension=extensions,
                           parent=kwargs.pop('parent', None),
                           viewer=viewer,
                           gwcs_to_fits_sip=gwcs_to_fits_sip)
        elif isinstance(data, str) and data.endswith('.reg'):
            self._load(data,
                       format='Subset',
                       data_label=data_label,
                       extension=extensions,
                       parent=kwargs.pop('parent', None),
                       viewer=viewer,
                       gwcs_to_fits_sip=gwcs_to_fits_sip)
        else:
            # if the data-label is provided but without an
            # extension in the label, maintain previous behavior of appending
            # the extension
            data_label_as_prefix = (data_label is not None
                                    and not data_label.endswith(']')
                                    and getattr(data, 'meta', {}).get('plugin', None) is None)

            # extensions for roman data models cannot be none, so switch default to 'data'
            if (HAS_ROMAN_DATAMODELS and isinstance(data, (rdd.ImageModel, rdd.DataModel))
                    and extensions is None):
                extensions = 'data'

            if data_label is None:
                # maintain previous default label behaviors
                from astropy.nddata import NDData
                if data.__class__ is NDData:
                    data_label = 'NDData'

            self._load(data,
                       format='Image',
                       data_label=data_label,
                       data_label_as_prefix=data_label_as_prefix,
                       extension=extensions,
                       parent=kwargs.pop('parent', None),
                       viewer=viewer,
                       gwcs_to_fits_sip=gwcs_to_fits_sip)

    def link_data(self, align_by='pixels', wcs_fallback_scheme=None, wcs_fast_approximation=True):
        """(Re)link loaded data in Imviz with the desired link type.
        All existing links will be replaced.

        Parameters
        ----------
        align_by : {'pixels', 'wcs'}
            Choose to link by pixels or WCS.

        wcs_fallback_scheme : {None, 'pixels'}
            If WCS linking failed, choose to fall back to linking by pixels or not at all.
            This is only used when ``align_by='wcs'``.
            Choosing `None` may result in some Imviz functionality not working properly.

        wcs_fast_approximation : bool
            Use an affine transform to represent the offset between images if possible
            (requires that the approximation is accurate to within 1 pixel with the
            full WCS transformations). If approximation fails, it will automatically
            fall back to full WCS transformation. This is only used when ``align_by='wcs'``.
            Affine approximation is much more performant at the cost of accuracy.

        """
        from jdaviz.configs.imviz.plugins.orientation.orientation import align_by_msg_to_trait
        plg = self.plugins["Orientation"]
        plg._obj.wcs_use_fallback = wcs_fallback_scheme == 'pixels'
        plg.wcs_fast_approximation = wcs_fast_approximation
        plg.align_by = align_by_msg_to_trait[align_by]

    @deprecated(since="4.0", alternative="get_alignment_method")
    def get_link_type(self, data_label_1, data_label_2):
        return self.get_alignment_method(data_label_1, data_label_2)

    def get_alignment_method(self, data_label_1, data_label_2):
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
        align_by : {'pixels', 'wcs', 'self'}
            One of the link types accepted by the Orientation plugin
            or ``'self'`` if the labels are identical.

        Raises
        ------
        ValueError
            Link look-up failed.

        """
        if data_label_1 == data_label_2:
            return "self"

        align_by = None
        for elink in self.app.data_collection.external_links:
            elink_labels = (elink.data1.label, elink.data2.label)
            if data_label_1 in elink_labels and data_label_2 in elink_labels:
                if isinstance(elink, LinkSame):  # Assumes WCS link never uses LinkSame
                    align_by = 'pixels'
                else:  # If not pixels, must be WCS
                    align_by = 'wcs'
                break  # Might have duplicate, just grab first match

        if align_by is None:
            avail_links = [f"({elink.data1.label}, {elink.data2.label})"
                           for elink in self.app.data_collection.external_links]
            raise ValueError(f'{data_label_1} and {data_label_2} combo not found '
                             f'in data collection external links: {avail_links}')

        return align_by

    @deprecated(since="4.2", alternative="plugins['Aperture Photometry'].export_table()")
    def get_aperture_photometry_results(self):
        """Return aperture photometry results, if any.
        Results are calculated using :ref:`aper-phot-simple` plugin.

        Returns
        -------
        results : `~astropy.table.QTable` or `None`
            Photometry results if available or `None` otherwise.

        """
        return self.plugins['Aperture Photometry'].export_table()

    @deprecated(since="4.2", alternative="plugins['Catalog Search'].export_table()")
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
        cls : `~specutils.Spectrum`, `~astropy.nddata.CCDData`, optional
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
