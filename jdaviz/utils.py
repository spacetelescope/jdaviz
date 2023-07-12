import os
import time
import threading
from collections import deque

import matplotlib.pyplot as plt
from astropy.io import fits
from ipyvue import watch
from glue.config import settings
from glue.core.subset import RangeSubsetState, RoiSubsetState


__all__ = ['SnackbarQueue', 'enable_hot_reloading', 'bqplot_clear_figure',
           'standardize_metadata', 'ColorCycler', 'alpha_index', 'get_subset_type']

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


class ColorCycler:
    """
    Cycles through matplotlib's default color palette after first
    using the Glue default data color.
    """
    # default color cycle starts with the Glue default data color
    # followed by the matplotlib default color cycle
    default_dark_gray = settings._defaults['DATA_COLOR']
    default_color_palette = (
        [default_dark_gray] + plt.rcParams['axes.prop_cycle'].by_key()['color']
    )

    def __init__(self, counter=-1):
        self.counter = counter

    def __call__(self):
        self.counter += 1

        cycle_index = self.counter % len(self.default_color_palette)
        color = self.default_color_palette[cycle_index]

        return color

    def reset(self):
        self.counter = -1


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
        'spatial', 'spectral', or None
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
        return 'spectral'
    else:
        return None
