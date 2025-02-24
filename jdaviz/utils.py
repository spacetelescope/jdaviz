import operator
import os
import time
import threading
import warnings
from collections import deque
from urllib.parse import urlparse

import numpy as np
from astropy.io import fits
from astropy.utils import minversion
from astropy.utils.data import download_file
from astropy.wcs.wcsapi import BaseHighLevelWCS
from astroquery.mast import Observations, conf
from matplotlib import colors as mpl_colors
import matplotlib.cm as cm
from photutils.utils import make_random_cmap
from regions import CirclePixelRegion, CircleAnnulusPixelRegion

from glue.config import settings
from glue.config import colormaps as glue_colormaps
from glue.core import BaseData
from glue.core.exceptions import IncompatibleAttribute
from glue.core.subset import SubsetState, RangeSubsetState, RoiSubsetState
from glue_astronomy.spectral_coordinates import SpectralCoordinates
from ipyvue import watch


__all__ = ['SnackbarQueue', 'enable_hot_reloading', 'bqplot_clear_figure',
           'standardize_metadata', 'ColorCycler', 'alpha_index',
           'get_subset_type', 'download_uri_to_path', 'layer_is_2d',
           'layer_is_2d_or_3d', 'layer_is_image_data', 'layer_is_wcs_only',
           'get_wcs_only_layer_labels', 'get_top_layer_index',
           'get_reference_image_data', 'standardize_roman_metadata',
           'cmap_samples', 'glue_colormaps']

NUMPY_LT_2_0 = not minversion("numpy", "2.0.dev")

# For Metadata Viewer plugin internal use only.
PRIHDR_KEY = '_primary_header'
COMMENTCARD_KEY = '_fits_comment_card'


class SnackbarQueue:
    '''
    Class that performs the role of VSnackbarQueue, which is not
    implemented in ipyvuetify.
    '''
    def __init__(self):
        self.queue = deque()
        # track whether we're showing a loading message which won't clear by timeout,
        # but instead requires another message with msg.loading = False to clear
        self.loading = False
        # track whether this is the first message - we'll increase the timeout for that
        # to give time for the app to load.
        self.first = True

    def put(self, state, msg, history=True, popup=True):
        if msg.color not in ['info', 'warning', 'error', 'success', None]:
            raise ValueError(f"color ({msg.color}) must be on of: info, warning, error, success")

        if not msg.loading and history:
            now = time.localtime()
            timestamp = f'{now.tm_hour}:{now.tm_min:02d}:{now.tm_sec:02d}'
            new_history = {'time': timestamp, 'text': msg.text, 'color': msg.color}
            # for now, we'll hardcode the max length of the stored history
            if len(state.snackbar_history) >= 50:
                state.snackbar_history = state.snackbar_history[1:] + [new_history]
            else:
                state.snackbar_history.append(new_history)

        if not (popup or msg.loading):
            if self.loading:
                # then we still need to clear the existing loading message
                self.loading = False
                self.close_current_message(state)
            return

        if msg.loading:
            # immediately show the loading message indefinitely until cleared by a new message
            # with loading=False (or overwritten by a new indefinite message with loading=True)
            self.loading = True
            self._write_message(state, msg)
        elif self.loading:
            # clear the loading state, immediately show this message, then re-enter the queue
            self.loading = False
            self._write_message(state, msg)
        else:
            warn_and_err = ('warning', 'error')
            if msg.color in warn_and_err:
                if (state.snackbar.get('show') and
                        ((msg.color == 'warning' and state.snackbar.get('color') in warn_and_err) or  # noqa
                         (msg.color == 'error' and state.snackbar.get('color') == 'error'))):
                    # put this NEXT in the queue immediately FOLLOWING all warning/errors
                    non_warning_error = [msg.color not in warn_and_err for msg in self.queue]  # noqa
                    if True in non_warning_error:
                        # insert BEFORE index
                        self.queue.insert(non_warning_error.index(True), msg)
                    else:
                        self.queue.append(msg)
                else:
                    # interrupt the queue IMMEDIATELY
                    # (any currently shown messages will repeat after)
                    self._write_message(state, msg)
            else:
                # put this LAST in the queue
                self.queue.append(msg)
            if len(self.queue) == 1:
                self._write_message(state, msg)

    def close_current_message(self, state):

        if self.loading:
            # then we've been interrupted, so keep this item in the queue to show after
            # loading is complete
            return

        # turn off snackbar iteself
        state.snackbar['show'] = False

        if len(self.queue) > 0:
            # determine if the closed entry came from the queue (not an interrupt)
            # in which case we should remove it from the queue.  We clear here instead
            # of when creating the snackbar so that items that are interrupted
            # (ie by a loading message) will reappear again at the top of the queue
            # so they are not missed
            msg = self.queue[0]
            if msg.text == state.snackbar['text']:
                _ = self.queue.popleft()

        # in case there are messages in the queue still,
        # display the next.
        if len(self.queue) > 0:
            msg = self.queue[0]
            self._write_message(state, msg)

    def _write_message(self, state, msg):
        state.snackbar['show'] = False
        state.snackbar['text'] = msg.text
        state.snackbar['color'] = msg.color
        # TODO: in vuetify >2.3, timeout should be set to -1 to keep open
        #  indefinitely
        state.snackbar['timeout'] = 0  # timeout controlled by thread
        state.snackbar['loading'] = msg.loading
        state.snackbar['show'] = True

        if msg.loading:
            # do not create timeout - the message will be indefinite until
            # cleared by another message
            return

        # timeout of the first message needs to be increased by a
        # few seconds to account for the time spent in page rendering.
        # A more elegant way to address this should be via a callback
        # from a vue hook such as  mounted(). It doesn't work though.
        # Since this entire queue effort is temporary anyway (pending
        # the implementation of VSnackbarQueue in ipyvuetify, it's
        # better to keep the solution contained all in one place here.
        timeout = msg.timeout
        if timeout < 500:
            # half-second minimum timeout
            timeout = 500
        if self.first:
            timeout += 5000
            self.first = False

        # create the timeout function which will close this message and
        # show the next message if one has been added to the queue since
        def sleep_function(timeout, text):
            timeout_ = float(timeout) / 1000
            time.sleep(timeout_)
            if state.snackbar['show'] and state.snackbar['text'] == text:
                # don't close the next message if the user manually clicked close!
                self.close_current_message(state)

        x = threading.Thread(target=sleep_function,
                             args=(timeout, msg.text),
                             daemon=True)
        x.start()


def enable_hot_reloading():
    """Use ``watchdog`` to perform hot reloading."""
    try:
        watch(os.path.dirname(__file__))
    except ModuleNotFoundError:
        print((
            'Watchdog module, needed for hot reloading, not found.'
            ' Please install with `pip install watchdog`'))


def bqplot_clear_figure(fig):
    """Clears a given ``bqplot.Figure`` to mimic matplotlib ``clf()``.
    This is necessary when we draw multiple plots across different plugins.
    """
    # Clear bqplot figure (copied from bqplot/pyplot.py)
    fig.marks = []
    fig.axes = []
    setattr(fig, 'axis_registry', {})


def alpha_index(index):
    """Converts an index to label (A-Z, AA-ZZ).

    Parameters
    ----------
    index : int
        Index between 0 and 701, inclusive. Higher number is accepted but
        will have special characters.

    Returns
    -------
    label : str
        String in the range A-Z, AA-ZZ if index is within 0-701 range, inclusive.

    Raises
    ------
    TypeError
        Index is not integer.

    ValueError
        Index is negative.
    """
    # if we ever want to support more than 702 layers, then we'll need a third
    # "digit" and will need to account for the horizontal space in the legends
    if not isinstance(index, int):
        raise TypeError("index must be an integer")
    if index < 0:
        raise ValueError("index must be positive")
    if index <= 25:
        # a-z
        return chr(97 + index)
    else:
        # aa-zz (26-701), then overflow strings like '{a'
        return chr(97 + index//26 - 1) + chr(97 + index % 26)


def data_has_valid_wcs(data, ndim=None):
    """Check if given glue Data has WCS that is compatible with APE 14."""
    status = hasattr(data, 'coords') and isinstance(data.coords, BaseHighLevelWCS)
    if ndim is not None:
        status = status and data.coords.world_n_dim == ndim
    return status


def layer_is_table_data(layer):
    return isinstance(layer, BaseData) and layer.ndim == 1


_wcs_only_label = "_WCS_ONLY"


def is_wcs_only(layer):
    # identify WCS-only layers
    if hasattr(layer, 'layer'):
        layer = layer.layer

    return (
        # WCS-only layers have a metadata label:
        getattr(layer, 'meta', {}).get(_wcs_only_label, False)
    )


def is_not_wcs_only(layer):
    return not is_wcs_only(layer)


def layer_is_not_dq(data):
    return '[DQ' not in data.label


def standardize_metadata(metadata):
    """Standardize given metadata so it can be viewed in
    Metadata Viewer plugin. The input can be plain
    dictionary or FITS header object. Output is just a plain
    dictionary.
    """
    if isinstance(metadata, fits.Header):
        try:
            out_meta = dict(metadata)
            out_meta[COMMENTCARD_KEY] = metadata.comments
        except Exception:  # Invalid FITS header  # pragma: no cover
            out_meta = {}
    elif isinstance(metadata, dict):
        out_meta = metadata.copy()
        # specutils nests it but we do not want nesting
        if 'header' in metadata and isinstance(metadata['header'], fits.Header):
            out_meta.update(standardize_metadata(metadata['header']))
            del out_meta['header']
    else:
        raise TypeError('metadata must be dictionary or FITS header')

    return out_meta


def standardize_roman_metadata(data_model):
    """
    Metadata standardization for Roman datamodels ``meta`` attributes.

    Converts to a flat dictionary and strips the redundant top-level
    tags ("roman", and "meta").

    Parameters
    ----------
    data_model : `~roman_datamodels.datamodels.DataModel`
        Roman datamodel.

    Returns
    -------
    d : dict
        Flattened dictionary of metadata
    """
    import roman_datamodels.datamodels as rdm
    if isinstance(data_model, rdm.DataModel):
        # Roman metadata are in nested dicts that we flatten:
        flat_dict_meta = data_model.to_flat_dict()

        # split off the redundant parts of the metadata:
        return {
            k.split('roman.meta.')[1]: v
            for k, v in flat_dict_meta.items()
            if 'roman.meta' in k
        }


class ColorCycler:
    """
    Cycles through matplotlib's default color palette after first
    using the Glue default data color.
    """
    # default color cycle starts with the Glue default data color
    # followed by the matplotlib default color cycle, except for the
    # second color (orange) in the matplotlib cycle, which is too close
    # to the jdaviz accent color (also orange).
    default_dark_gray = settings._defaults['DATA_COLOR']
    default_color_palette = [
        default_dark_gray,
        '#1f77b4',
        '#2ca02c',
        '#d62728',
        '#9467bd',
        '#8c564b',
        '#e377c2',
        '#7f7f7f',
        '#bcbd22',
        '#17becf'
    ]

    def __init__(self, counter=-1):
        self.counter = counter

    def __call__(self):
        self.counter += 1

        cycle_index = self.counter % len(self.default_color_palette)
        color = self.default_color_palette[cycle_index]

        return color

    def reset(self):
        self.counter = -1


def _chain_regions(regions, ops):
    """
    Combine multiple regions into a compound pixel/sky region based on the
    specified operators.

    If the operators are valid binary operators recognized  by both glue and
    Regions, the function returns a compound region. Otherwise, it returns a
    list of individual regions paired with their respective operators, or just
    returns the region if regions only contains one region.

    Parameters
    ----------
    regions : list
        A list of region objects.
    ops : list of str
        A list of glue states that map to operator names to describe how to
        combine regions (e.g. 'AndState').

    Returns
    -------
    Compound region or list
        A single compound region if valid operators are provided; otherwise,
        a list of tuples containing individual regions and their associated
        operators.
    """

    if len(regions) == 1:
        return regions[0]

    valid_operators = {
        'AndState': operator.and_,
        'OrState': operator.or_,
        'XorState': operator.xor
    }

    operators = ops[1:]  # first subset doesn't need an operator

    # if regions cant be combined into a compound region as an annulus or with
    # and/or/xor, return list of tuples of (region, operator)
    annulus = _combine_if_annulus(regions[0], regions[1], operators[0])
    if annulus is None:
        if not np.all(np.isin(operators, list(valid_operators.keys()))):
            return list(zip(regions, [''] + operators))

    r1 = annulus or regions[0]
    for i in range(2 if annulus else 0, len(operators)):
        r1 = valid_operators[operators[i]](r1, regions[i + 1])

    return r1


def _combine_if_annulus(region1, region2, op):
    """
    Determine whether applying `region2` to `region1` using the specified
    operator results in a circular annulus. If the conditions are met,
    return a `CircleAnnulusPixelRegion`; otherwise, return `None`.
    """
    if (
        isinstance(region1, (CirclePixelRegion))
        and isinstance(region1, (CirclePixelRegion))
        and op == 'AndNotState'
        and region1.center == region2.center
        and region1.radius > region2.radius
    ):
        return CircleAnnulusPixelRegion(center=region1.center,
                                        inner_radius=region2.radius,
                                        outer_radius=region1.radius)


def get_subset_type(subset):
    """
    Determine the subset type of a subset or layer

    Parameters
    ----------
    subset : glue.core.subset.Subset or glue.core.subset_group.GroupedSubset
        should have ``subset_state`` as an attribute, otherwise will return ``None``.

    Returns
    -------
    subset_type : str or None
        'spatial', 'spectral', 'temporal', or None
    """
    if not hasattr(subset, 'subset_state'):
        return None

    while hasattr(subset.subset_state, 'state1'):
        # this assumes no mixing between spatial and spectral subsets and just
        # taking the first component (down the hierarchical tree) to determine the type
        subset = subset.subset_state.state1

    if isinstance(subset.subset_state, RoiSubsetState):
        return 'spatial'
    elif isinstance(subset.subset_state, RangeSubsetState):
        # look within a SubsetGroup, or a single Subset
        subset_list = getattr(subset, 'subsets', [subset])

        for ss in subset_list:
            if hasattr(ss, 'data'):
                ss_data = ss.data
            elif hasattr(ss.att, 'parent'):
                # if `ss` is a subset state, it won't have a `data` attr,
                # check the world coordinate's parent data:
                ss_data = ss.att.parent
            else:
                # if we reach this `else`, continue searching
                # through other subsets in the group to identify the
                # subset type:
                continue

            # check for a spectral coordinate in FITS WCS:
            wcs_coords = (
                ss_data.coords.wcs.ctype if hasattr(ss_data.coords, 'wcs')
                else []
            )

            has_spectral_coords = (
                any(str(coord).startswith('WAVE') for coord in wcs_coords) or

                # also check for a spectral coordinate from the glue_astronomy translator:
                isinstance(ss_data.coords, SpectralCoordinates)
            )

            if has_spectral_coords:
                return 'spectral'

        # otherwise, assume temporal:
        return 'temporal'
    else:
        return None


class MultiMaskSubsetState(SubsetState):
    """
    A subset state that can include a different mask for different datasets.
    Adopted from https://github.com/glue-viz/glue/pull/2415

    Parameters
    ----------
    masks : dict
        A dictionary mapping data UUIDs to boolean arrays with the same
        dimensions as the data arrays.
    """

    def __init__(self, masks=None):
        super(MultiMaskSubsetState, self).__init__()
        self._masks = masks

    def to_mask(self, data, view=None):
        if data.uuid in self._masks:
            mask = self._masks[data.uuid]
            if view is not None:
                mask = mask[view]
            return mask
        else:
            raise IncompatibleAttribute()

    def copy(self):
        return MultiMaskSubsetState(masks=self._masks)

    def __gluestate__(self, context):
        serialized = {key: context.do(value) for key, value in self._masks.items()}
        return {'masks': serialized}

    def total_masked_first_data(self):
        first_data = next(iter(self._masks))
        return len(np.where(self._masks[first_data])[0])

    @classmethod
    def __setgluestate__(cls, rec, context):
        masks = {key: context.object(value) for key, value in rec['masks'].items()}
        return cls(masks=masks)


def download_uri_to_path(possible_uri, cache=None, local_path=os.curdir, timeout=None,
                         dryrun=False):
    """
    Retrieve data from a URI (or a URL). Return the input if it
    cannot be parsed as a URI.

    If ``possible_uri`` is a MAST URI, the file will be retrieved via
    astroquery's `~astroquery.mast.ObservationsClass.download_file`.
    If ``possible_uri`` is a URL, it will be retrieved via astropy with
    `~astropy.utils.data.download_file`.

    Parameters
    ----------
    possible_uri : str or other
        This input will be returned without changes if it is not a string,
        or if it is a local file path to an existing file. Otherwise,
        it will be parsed as a URI. Local file URIs beginning with ``file://``
        are not supported by this method – nor are they necessary, since string
        paths without the scheme work fine! Cloud FITS are not yet supported.
    cache: None, bool, or ``"update"``, optional
        Cache file after download. If ``possible_uri`` is a
        URL, ``cache`` may be a boolean or ``"update"``, see documentation for
        `~astropy.utils.data.download_file` for details. If cache is None,
        the file is cached and a warning is raised suggesting to set ``cache``
        explicitly in the future.
    local_path : str, optional
        Save the downloaded file to this path. Default is to
        save the file with its remote filename in the current
        working directory. This is only used if data is requested
        from `astroquery.mast`.
    timeout : float, optional
        If downloading from a remote URI, set the timeout limit for
        remote requests in seconds (passed to
        `~astropy.utils.data.download_file` or
        `~astroquery.mast.Conf.timeout`).
    dryrun : bool
        Set to `True` to skip downloading data from MAST.
        This is only used for debugging.

    Returns
    -------
    possible_uri : str or other
        If ``possible_uri`` cannot be retrieved as a URI, returns the input argument
        unchanged. If ``possible_uri`` can be retrieved as a URI, returns the
        local path to the downloaded file.
    """

    if not isinstance(possible_uri, str):
        # only try to parse strings:
        return possible_uri

    if os.path.exists(possible_uri):
        # don't try to parse file paths:
        return possible_uri

    if os.environ.get("JDAVIZ_START_DIR", ""):
        # avoiding creating local paths in a tmp dir when in standalone:
        local_path = os.path.join(os.environ["JDAVIZ_START_DIR"], local_path)

    parsed_uri = urlparse(possible_uri)

    cache_none_msg = (
        "You may be querying for a remote file "
        f"at '{possible_uri}', but the `cache` argument was not "
        f"in the call to `load_data`. Unless you set `cache` "
        f"explicitly, remote files will be cached locally and "
        f"this warning will be raised."
    )

    local_path_msg = (
        f"You requested to cache data to the `local_path`='{local_path}'. This "
        f"keyword argument is supported for downloads of MAST URIs via astroquery, "
        f"but since the remote file at '{possible_uri}' will be downloaded "
        f"using `astropy.utils.data.download_file`, the file will be "
        f"stored in the astropy download cache instead."
    )

    cache_warning = False
    if cache is None:
        cache = True
        cache_warning = True

    if parsed_uri.scheme.lower() == 'mast':
        if cache_warning:
            warnings.warn(cache_none_msg, UserWarning)

        if local_path is not None and os.path.isdir(local_path):
            # if you give a directory, save the file there with default name:
            # os.path.sep does not work because on windows that is a back slash
            # and this web path needs to be split with a forward slash
            local_path = os.path.join(local_path, parsed_uri.path.split('/')[-1])

        if not dryrun:
            with conf.set_temp('timeout', timeout):
                (status, msg, url) = Observations.download_file(
                    possible_uri, cache=cache, local_path=local_path
                )
        else:
            status = "COMPLETE"

        if status != 'COMPLETE':
            # pass along the error message from astroquery if the
            # data were not successfully downloaded:
            raise ValueError(
                f"Failed query for URI '{possible_uri}' at '{url}':\n\n{msg}"
            )

        if local_path is None:
            # if not specified, this is the default location:
            # os.path.sep does not work because on Windows that is a back slash
            # and this web path needs to be split with a forward slash
            local_path = os.path.join(os.getcwd(), parsed_uri.path.split('/')[-1])
        return local_path

    elif parsed_uri.scheme.lower() in ('http', 'https', 'ftp'):
        if cache_warning:
            warnings.warn(cache_none_msg, UserWarning)

        if local_path not in (os.curdir, None):
            warnings.warn(local_path_msg, UserWarning)

        return download_file(possible_uri, cache=cache, timeout=timeout)

    elif parsed_uri.scheme == '':
        raise ValueError(f"The input file '{possible_uri}' cannot be parsed as a "
                         f"URL or URI, and no existing local file is available "
                         f"at this path.")

    else:
        raise ValueError(f"URI {possible_uri} with scheme {parsed_uri.scheme} is not "
                         f"currently supported.")

    # assume this isn't a URI after all:
    return possible_uri


def layer_is_2d(layer):
    # returns True for subclasses of BaseData with ndim=2, both for
    # layers that are WCS-only as well as images containing data:
    return isinstance(layer, BaseData) and layer.ndim == 2


def layer_is_2d_or_3d(layer):
    return isinstance(layer, BaseData) and layer.ndim in (2, 3)


def layer_is_image_data(layer):
    return layer_is_2d_or_3d(layer) and not layer.meta.get(_wcs_only_label, False)


def layer_is_wcs_only(layer):
    return layer_is_2d(layer) and layer.meta.get(_wcs_only_label, False)


def get_wcs_only_layer_labels(app):
    return [data.label for data in app.data_collection
            if layer_is_wcs_only(data)]


def get_top_layer_index(viewer):
    """Get index of the top visible image layer in a viewer.
    This is because when blinked, first layer might not be top visible layer.

    """
    # exclude children of layer associations
    associations = viewer.jdaviz_app._data_associations

    visible_image_layers = [
        i for i, lyr in enumerate(viewer.layers)
        if (
            lyr.visible and
            layer_is_image_data(lyr.layer) and
            # check that this layer is a root, without parents:
            associations[lyr.layer.label]['parent'] is None
        )
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


# Add new and inverse colormaps to Glue global state. Also see ColormapRegistry in
# https://github.com/glue-viz/glue/blob/main/glue/config.py
new_cms = (['Rainbow', cm.rainbow],
           ['Seismic', cm.seismic],
           ['Reversed: Gray', cm.gray_r],
           ['Reversed: Viridis', cm.viridis_r],
           ['Reversed: Plasma', cm.plasma_r],
           ['Reversed: Inferno', cm.inferno_r],
           ['Reversed: Magma', cm.magma_r],
           ['Reversed: Hot', cm.hot_r],
           ['Reversed: Rainbow', cm.rainbow_r])
for cur_cm in new_cms:
    if cur_cm not in glue_colormaps.members:
        glue_colormaps.add(*cur_cm)


def _register_random_cmap(
    cmap_name,
    bkg_color=[0, 0, 0],
    bkg_alpha=1,
    seed=42,
    ncolors=10_000
):
    """
    Custom random colormap, useful for rendering image
    segmentation maps. The default background for
    `label==0` is *transparent*. If the segmentation map
    contains more than 10,000 labels, adjust the `ncolors`
    kwarg to ensure uniqueness.
    """
    cmap = make_random_cmap(ncolors=ncolors, seed=seed)
    cmap.colors[0] = bkg_color + [bkg_alpha]
    cmap.name = cmap_name
    glue_colormaps.add(cmap_name, cmap)


_register_random_cmap('Random', bkg_alpha=1)


# give UI access to sampled version of the available colormap choices
def _hex_for_cmap(cmap):
    N = 50
    cm_sampled = cmap.resampled(N)
    return [mpl_colors.to_hex(cm_sampled(i)) for i in range(N)]


cmap_samples = {cmap[1].name: _hex_for_cmap(cmap[1]) for cmap in glue_colormaps.members}
