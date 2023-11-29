from astropy.coordinates.sky_coordinate import SkyCoord
from astropy.nddata import NDData
from astropy.table import QTable
from astropy.table.row import Row as QTableRow
import astropy.units as u
import bqplot
from contextlib import contextmanager
import numpy as np
import os
import threading
import time

from echo import delay_callback
from functools import cached_property
from ipyvuetify import VuetifyTemplate
from glue.config import colormaps
from glue.core import Data, HubListener
from glue.core.link_helpers import LinkSame
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage,
                               SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue.core.roi import CircularAnnulusROI
from glue_jupyter import jglue
from glue_jupyter.bqplot.histogram import BqplotHistogramView
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.registries import viewer_registry
from glue_jupyter.widgets.linked_dropdown import get_choices as _get_glue_choices
from specutils import Spectrum1D
from traitlets import Any, Bool, HasTraits, List, Unicode, observe

from ipywidgets import widget_serialization
from ipypopout import PopoutButton

from jdaviz import __version__
from jdaviz.components.toolbar_nested import NestedJupyterToolbar
from jdaviz.core.events import (AddDataMessage, RemoveDataMessage,
                                ViewerAddedMessage, ViewerRemovedMessage,
                                ViewerRenamedMessage, SnackbarMessage,
                                AddDataToViewerMessage)
from jdaviz.core.region_translators import _get_region_from_spatial_subset
from jdaviz.core.user_api import UserApiWrapper, PluginUserApi
from jdaviz.utils import get_subset_type


__all__ = ['show_widget', 'TemplateMixin', 'PluginTemplateMixin',
           'skip_if_no_updates_since_last_active', 'with_spinner',
           'ViewerPropertiesMixin',
           'BasePluginComponent',
           'SelectPluginComponent', 'UnitSelectPluginComponent', 'EditableSelectPluginComponent',
           'PluginSubcomponent',
           'SubsetSelect', 'SpatialSubsetSelectMixin', 'SpectralSubsetSelectMixin',
           'DatasetSpectralSubsetValidMixin',
           'ViewerSelect', 'ViewerSelectMixin',
           'LayerSelect', 'LayerSelectMixin',
           'NonFiniteUncertaintyMismatchMixin',
           'DatasetSelect', 'DatasetSelectMixin', 'DatasetMultiSelectMixin',
           'FileImportSelectPluginComponent', 'HasFileImportSelect',
           'Table', 'TableMixin',
           'Plot', 'PlotMixin',
           'AutoTextField', 'AutoTextFieldMixin',
           'AddResults', 'AddResultsMixin',
           'PlotOptionsSyncState',
           'SPATIAL_DEFAULT_TEXT']

SPATIAL_DEFAULT_TEXT = "Entire Cube"
GLUE_STATES_WITH_HELPERS = ('size_att', 'cmap_att')

# this histogram viewer (along with other viewers) are not in the glue viewer-registry by default
# but may be added in the future.  If it is not in the registry, we'll add it now.
# Once glue-jupyter with https://github.com/glue-viz/glue-jupyter/pull/402 is pinned,
# we can safely remove this block.
if 'histogram' not in viewer_registry.members.keys():
    @viewer_registry('histogram')
    class RegisteredHistogramViewer(BqplotHistogramView):
        pass


def show_widget(widget, loc, title):  # pragma: no cover
    from IPython import get_ipython
    from IPython.display import display

    # Check if the user is running Jdaviz in the correct environments.
    # If not, provide a friendly msg to guide them!
    cur_shell_name = get_ipython().__class__.__name__
    if cur_shell_name != 'ZMQInteractiveShell':
        raise RuntimeError("\nYou are currently running Jdaviz from an unsupported "
                           f"shell ({cur_shell_name}). Jdaviz is intended to be run within a "
                           "Jupyter notebook, or directly from the command line.\n\n"
                           "To run from Jupyter, call <your viz>.show() from a notebook cell.\n"
                           "To see how to run from the command line, run: "
                           "'jdaviz --help' outside of Python.\n\n"
                           "To learn more, see our documentation at: "
                           "https://jdaviz.readthedocs.io")

    if loc == "inline":
        display(widget)

    elif loc.startswith('sidecar'):
        from sidecar import Sidecar

        # Use default behavior if loc is exactly 'sidecar', else split anchor from the arg
        anchor = None if loc == 'sidecar' else loc.split(':')[1]

        scar = Sidecar(anchor=anchor, title=title)
        with scar:
            display(widget)

    elif loc.startswith('popout'):
        anchor = None if loc == 'popout' else loc.split(':')[1]

        # Default behavior (no anchor specified): display popout in new window
        if anchor in (None, 'window'):
            widget.popout_button.open_window()
        elif anchor == "tab":
            widget.popout_button.open_tab()
        else:
            raise ValueError("Unrecognized popout anchor")

    else:
        raise ValueError(f"Unrecognized display location: {loc}")


class ViewerPropertiesMixin:
    # assumes that self.app is defined by the class
    @cached_property
    def spectrum_viewer(self):
        if hasattr(self, '_default_spectrum_viewer_reference_name'):
            viewer_reference = self._default_spectrum_viewer_reference_name
        else:
            viewer_reference = self.app._get_first_viewer_reference_name(
                require_spectrum_viewer=True
            )

        return self.app.get_viewer(viewer_reference)

    @cached_property
    def spectrum_2d_viewer(self):
        if hasattr(self, '_default_spectrum_2d_viewer_reference_name'):
            viewer_reference = self._default_spectrum_2d_viewer_reference_name
        else:
            viewer_reference = self.app._get_first_viewer_reference_name(
                require_spectrum_2d_viewer=True
            )

        return self.app.get_viewer(viewer_reference)


class TemplateMixin(VuetifyTemplate, HubListener, ViewerPropertiesMixin):
    config = Unicode("").tag(sync=True)
    vdocs = Unicode("").tag(sync=True)
    popout_button = Any().tag(sync=True, **widget_serialization)

    def __new__(cls, *args, **kwargs):
        """
        Overload object creation so that we can inject a reference to the
        `~glue.core.hub.Hub` class before components can be initialized. This makes it so
        hub references on plugins can be passed along to components in the
        call to the initialization method.
        """
        app = kwargs.pop('app', None)
        obj = super().__new__(cls, *args, **kwargs)
        obj._app = app

        # give the vue templates access to the current config/layout
        obj.config = app.state.settings.get("configuration", "default")

        # give the vue templates access to jdaviz version
        obj.vdocs = 'latest' if 'dev' in __version__ else 'v'+__version__

        # store references to all bqplot widgets that need to handle resizing
        obj.bqplot_figs_resize = []

        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.popout_button = PopoutButton(self, window_features='popup,width=400,height=600')
        self._viewer_callbacks = {}
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=lambda msg: self._remove_viewer_callbacks(msg.viewer_id))

    @property
    def app(self):
        """
        Allows access to the underlying Jdaviz application instance. This is
        **not** access to the helper class, but instead the
        `jdaviz.app.Application` object.
        """
        return self._app

    @property
    def hub(self):
        return self._app.session.hub

    @property
    def session(self):
        return self._app.session

    @property
    def data_collection(self):
        return self._app.session.data_collection

    @property
    def _specviz_helper(self):
        # for helpers that have a .specviz, return that, otherwise the original helper
        helper = self.app._jdaviz_helper
        return getattr(helper, 'specviz', helper)

    def _viewer_callback(self, viewer, plugin_method):
        """
        Cached access to callbacks to a plugin method to attach to a viewer.
        To define a callback:
        def _on_callback(self, viewer, data):
        To add callback:
        viewer.add_event_calback(self._viewer_callback(viewer, self._on_callback),
                                 events=['keydown'])
        To remove callback:
        viewer.remove_event_callback(self._viewer_callback(viewer, self._on_callback))
        """
        def plugin_viewer_callback(viewer, plugin_method):
            return lambda data: plugin_method(viewer, data)

        key = f'{viewer.reference_id}:{plugin_method.__name__}'
        if key not in self._viewer_callbacks.keys():
            self._viewer_callbacks[key] = plugin_viewer_callback(viewer, plugin_method)
        return self._viewer_callbacks.get(key)

    def _remove_viewer_callbacks(self, viewer_id):
        # removes the cache of a callback when a viewer is removed (the viewer object is already
        # assumed destroyed, so we do not need to remove the event callback itself from the viewer)
        self._viewer_callbacks = {k: v for k, v in self._viewer_callbacks.items()
                                  if k.split(':')[0] != viewer_id}


def skip_if_no_updates_since_last_active(skip_if_not_active=True):
    def decorator(meth):
        def wrapper(self, msg={}):
            if isinstance(msg, dict) and msg.get('name', None) == 'is_active':
                if self.is_active and meth.__name__ in self._methods_skip_since_last_active:
                    # then we haven't received any other messages since the last time the plugin
                    # received an is_active switch, and so we should skip calling the method.
                    return
            elif not self.is_active:
                # then we've received some other message while the plugin is inactive.
                # Next time the plugin becomes active we want to call the wrapped method,
                # so we'll remove from the skip list.
                if meth.__name__ in self._methods_skip_since_last_active:
                    self._methods_skip_since_last_active.remove(meth.__name__)

            if skip_if_not_active and not self.is_active:
                return

            # call the method as normal, and add it to the skip list (to be skipped if is_active
            # toggles before any *other* messages are received)
            # if the method returns False, then the method is not considered to have fully run
            # and so is NOT added to the skip list
            if meth.__name__ not in self._methods_skip_since_last_active:
                self._methods_skip_since_last_active.append(meth.__name__)
            ret_ = meth(self, msg)
            if ret_ is False:
                self._methods_skip_since_last_active.remove(meth.__name__)
            return ret_

        return wrapper
    return decorator


def with_spinner(spinner_traitlet='spinner'):
    """
    decorator on a plugin method to set a traitlet to True at the beginning
    and False either on failure or successful completion.  This traitlet can
    then be used in the UI to disable elements or display a spinner during
    operation.  Each plugin gets a 'spinner' traitlet by default, but some plugins
    may want different controls for different sections/actions within the plugin.
    """
    def decorator(meth):
        def wrapper(self, *args, **kwargs):
            setattr(self, spinner_traitlet, True)
            try:
                ret_ = meth(self, *args, **kwargs)
            except Exception:
                setattr(self, spinner_traitlet, False)
                raise
            setattr(self, spinner_traitlet, False)
            return ret_
        return wrapper
    return decorator


class PluginTemplateMixin(TemplateMixin):
    """
    This base class can be inherited by all sidebar/tray plugins to expose common functionality.
    """
    disabled_msg = Unicode("").tag(sync=True)
    docs_link = Unicode("").tag(sync=True)  # set to non-empty to override value in vue file
    plugin_opened = Bool(False).tag(sync=True)  # noqa any instance of the plugin is open (recently sent an "alive" ping)
    uses_active_status = Bool(False).tag(sync=True)  # noqa whether the plugin has live-preview marks, set to True in plugins to expose keep_active switch
    keep_active = Bool(False).tag(sync=True)  # noqa whether the live-preview marks show regardless of active state, inapplicable unless uses_active_status is True
    is_active = Bool(False).tag(sync=True)  # noqa read-only: whether the previews should be shown according to plugin_opened and keep_active
    spinner = Bool(False).tag(sync=True)  # noqa use along-side @with_spinner() and <plugin-add-results :action_spinner="spinner">

    def __init__(self, **kwargs):
        self._viewer_callbacks = {}
        # _inactive_thread: thread checking for alive pings to control plugin_opened
        self._inactive_thread = None
        self._ping_timestamp = 0
        # _ping_delay_ms should match value in setTimeout in tray_plugin.vue
        # NOTE: could control with a traitlet, but then would need to pass through each
        # <j-tray-plugin> component
        self._ping_delay_ms = 200

        # _methods_skip_since_last_active: methods that should be skipped when is_active is next
        # set to True because no changes have been made.  This can be used to prevent queuing
        # of expensive method calls, especially when the browser throttles the ping resulting
        # in repeated toggling of is_active.  To use, decorate any method that observes traitlet
        # changes (including is_active) with @skip_if_no_updates_since_last_active()
        self._methods_skip_since_last_active = []
        super().__init__(**kwargs)

    @property
    def user_api(self):
        # plugins should override this to pass their own list of expose functionality, which
        # can even be dependent on config, etc.
        return PluginUserApi(self, expose=[])

    def vue_plugin_ping(self, ping_timestamp):
        if isinstance(ping_timestamp, dict):
            # popout windows can sometimes ping but send an empty dictionary instead of the
            # timestamp, in that case, let's set the latest ping time to now
            ping_timestamp = time.time() * 1000
        self._ping_timestamp = ping_timestamp

        # we've received a ping, so immediately set plugin_opened state to True
        if not self.plugin_opened:
            self.plugin_opened = True

        if self._inactive_thread is not None and self._inactive_thread.is_alive():
            # a thread already exists to check for pings, the latest ping will allow
            # the existing while-loop to continue
            return

        # create a thread to monitor for pings.  If a ping hasn't been received in the
        # expected time, then plugin_opened will be set to False.
        self._inactive_thread = threading.Thread(target=self._watch_active)
        self._inactive_thread.start()

    def _watch_active(self):
        # plugin_ping (ms) set by setTimeout in tray_plugin.vue
        # time.time() is in s, so need to convert to ms
        while time.time()*1000 - self._ping_timestamp < 2 * self._ping_delay_ms:
            # at least one plugin has sent an "alive" ping within twice of the expected
            # interval, wait a full (double) interval and then check again
            time.sleep(2 * self._ping_delay_ms / 1000)

        # "alive" ping has not been received within the expected time, consider all instances
        # of the plugin to be closed
        self.plugin_opened = False

    def _viewer_callback(self, viewer, plugin_method):
        """
        Cached access to callbacks to a plugin method to attach to a viewer.

        To define a callback:
        def _on_callback(self, viewer, data):

        To add callback:
        viewer.add_event_calback(self._viewer_callback(viewer, self._on_callback),
                                 events=['keydown'])

        To remove callback:
        viewer.remove_event_callback(self._viewer_callback(viewer, self._on_callback))
        """
        def plugin_viewer_callback(viewer, plugin_method):
            return lambda data: plugin_method(viewer, data)

        key = f'{viewer.reference_id}:{plugin_method.__name__}'
        if key not in self._viewer_callbacks.keys():
            self._viewer_callbacks[key] = plugin_viewer_callback(viewer, plugin_method)
        return self._viewer_callbacks.get(key)

    def open_in_tray(self):
        """
        Open the plugin in the sidebar/tray (and open the sidebar if it is not already).
        """
        app_state = self.app.state
        app_state.drawer = True
        index = [ti['name'] for ti in app_state.tray_items].index(self._registry_name)
        if index not in app_state.tray_items_open:
            app_state.tray_items_open = app_state.tray_items_open + [index]

    def close_in_tray(self, close_sidebar=False):
        """
        Close the plugin in the sidebar/tray.

        Parameters
        ----------
        close_sidebar : bool
            Whether to also close the sidebar itself.
        """
        app_state = self.app.state
        index = [ti['name'] for ti in app_state.tray_items].index(self._registry_name)
        app_state.tray_items_open = [ind for ind in app_state.tray_items_open if ind != index]
        if close_sidebar:
            self.app.state.drawer = False

    @observe('plugin_opened', 'keep_active')
    def _update_is_active(self, *args):
        self.is_active = self.keep_active or self.plugin_opened

    @contextmanager
    def as_active(self):
        """
        Context manager to temporarily enable keep_active and enable live-previews and keypress
        events, even if the plugin UI is not opened.
        """
        _keep_active = self.keep_active
        self.keep_active = True
        yield
        self.keep_active = _keep_active

    def show(self, loc="inline", title=None):  # pragma: no cover
        """Display the plugin UI.

        Parameters
        ----------
        loc : str
            The display location determines where to present the viz app.
            Supported locations:

            "inline": Display the plugin inline in a notebook.

            "sidecar": Display the plugin in a separate JupyterLab window from the
            notebook, the location of which is decided by the 'anchor.' right is the default

                Other anchors:

                * ``sidecar:right`` (The default, opens a tab to the right of display)
                * ``sidecar:tab-before`` (Full-width tab before the current notebook)
                * ``sidecar:tab-after`` (Full-width tab after the current notebook)
                * ``sidecar:split-right`` (Split-tab in the same window right of the notebook)
                * ``sidecar:split-left`` (Split-tab in the same window left of the notebook)
                * ``sidecar:split-top`` (Split-tab in the same window above the notebook)
                * ``sidecar:split-bottom`` (Split-tab in the same window below the notebook)

                See `jupyterlab-sidecar <https://github.com/jupyter-widgets/jupyterlab-sidecar>`_
                for the most up-to-date options.

            "popout": Display the plugin in a detached display. By default, a new
            window will open. Browser popup permissions required.

                Other anchors:

                * ``popout:window`` (The default, opens Jdaviz in a new, detached popout)
                * ``popout:tab`` (Opens Jdaviz in a new, detached tab in your browser)

        title : str, optional
            The title of the sidecar tab.  Defaults to the name of the plugin.

            NOTE: Only applicable to a "sidecar" display.

        Notes
        -----
        If "sidecar" is requested in the "classic" Jupyter notebook, the plugin will appear inline,
        as only JupyterLab has a mechanism to have multiple tabs.
        """
        title = title if title is not None else self._registry_label
        show_widget(self, loc=loc, title=title)


class BasePluginComponent(HubListener, ViewerPropertiesMixin):
    """
    This base class handles attaching traitlets from the plugin itself to logic
    handled within the component, support for caching and clearing caches on properties,
    and common properties for accessing the app, etc.
    """
    def __init__(self, plugin, **kwargs):
        self._plugin_traitlets = {k: v for k, v in kwargs.items() if v is not None}
        self._plugin = plugin
        self._cached_properties = []
        super().__init__()

    def __getattr__(self, attr):
        if attr[0] == '_' or attr not in self._plugin_traitlets.keys():
            return super().__getattribute__(attr)

        return getattr(self._plugin, self._plugin_traitlets.get(attr))

    def __setattr__(self, attr, value, force_super=False):
        if attr[0] == '_' or force_super or attr not in self._plugin_traitlets.keys():
            return super().__setattr__(attr, value)

        return setattr(self._plugin, self._plugin_traitlets.get(attr), value)

    def _clear_cache(self, *attrs):
        """
        provide convenience function to clearing the cache for cached_properties
        """
        if not len(attrs):
            attrs = self._cached_properties
        for attr in attrs:
            if attr in self.__dict__:
                del self.__dict__[attr]

    def add_observe(self, traitlet_name, handler, first=False):
        self._plugin.observe(handler, traitlet_name)
        if first:
            # re-order the callbacks so this one is first
            existing_callbacks = self._plugin._trait_notifiers[traitlet_name]['change']
            new_order = [handler] + [other for other in existing_callbacks if other != handler]
            self._plugin._trait_notifiers[traitlet_name]['change'] = new_order

    @property
    def plugin(self):
        """
        Access the parent plugin object
        """
        return self._plugin

    @property
    def app(self):
        """
        Access the parent app object
        """
        return self._plugin.app

    @property
    def hub(self):
        """
        Access the hub attached to the parent plugin object
        """
        return self._plugin.hub

    @property
    def viewer_dicts(self):
        def _dict_from_viewer(viewer, viewer_item):
            d = {'viewer': viewer,
                 'id': viewer_item.get('id'),
                 'icon': self.app.state.viewer_icons.get(viewer_item.get('id'))}
            if viewer_item.get('reference') is not None:
                d['reference'] = viewer_item.get('reference')
                d['label'] = viewer_item.get('reference')
            else:
                d['reference'] = None
                d['label'] = viewer_item.get('id')

            return d

        return [_dict_from_viewer(viewer, self.app._viewer_item_by_id(vid))
                for vid, viewer in self.app._viewer_store.items()
                if viewer.__class__.__name__ != 'MosvizTableViewer']


class SelectPluginComponent(BasePluginComponent, HasTraits):
    """
    Plugin select, with support for single or multi-selection.

    Useful API methods/attributes:

    * :meth:`choices`
    * ``selected``
    * :meth:`~SelectPluginComponent.is_multiselect`
    * :meth:`select_default`
    * :meth:`select_all` (only if ``is_multiselect``)
    * :meth:`select_none` (only if ``is_multiselect``)
    """
    filters = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        """
        This extends BasePluginComponent for common functionality for a select/dropdown
        component.  The subclasses MUST have an ``items`` traitlet as a list of dictionaries, with
        'label' as the selection entry (and any other optional entries for styling, etc) and a
        ``selected`` string traitlet.  The subclasses should also override ``selected_obj`` and may
        choose to override ``_selected_changed`` (likely with a super call to keep the base logic).
        """

        # default_mode can be one of empty, first, default_text (requires default_text to be set)
        default_mode = kwargs.pop('default_mode', 'empty' if kwargs.get('multiselect', False) else 'first')  # noqa
        default_text = kwargs.pop('default_text', None)
        manual_options = kwargs.pop('manual_options', [])
        self._viewers = kwargs.pop('viewers', None)
        # we'll pop from kwargs now to avoid passing to the super.__init__, but need to
        # wait for everything else to be set before setting to the traitlet
        filters = kwargs.pop('filters', [])[:]  # [:] needed to force copy from kwarg default

        super().__init__(*args, **kwargs)
        self._selected_previous = None
        self._cached_properties = ["selected_obj", "selected_item"]

        self._default_mode = default_mode
        self._default_text = default_text
        if default_text is not None and default_text not in manual_options:
            manual_options = [default_text] + manual_options
        self._manual_options = manual_options

        self.items = [{"label": opt} for opt in manual_options]
        # set default values for traitlets
        if default_text is not None:
            self.selected = default_text

        if kwargs.get('multiselect'):
            self.add_observe(kwargs.get('multiselect'), self._multiselect_changed)

        # this callback MUST come first so that any plugins that use @observe have those
        # callbacks triggered AFTER the cache is cleared and the value is checked against
        # valid options
        self.add_observe(kwargs.get('selected'), self._selected_changed, first=True)
        self.filters = filters

        if default_mode != 'empty' and self.selected == '':
            self._apply_default_selection()

    def __repr__(self):
        if hasattr(self, 'multiselect'):
            return f"<selected={self.selected} multiselect={self.multiselect} choices={self.choices}>"  # noqa
        return f"<selected='{self.selected}' choices={self.choices}>"

    def __eq__(self, other):
        return self.selected == other

    def __hash__(self):
        # defining __eq__ without defining __hash__ makes the object unhashable
        return super().__hash__()

    @property
    def choices(self):
        return self.labels

    @choices.setter
    def choices(self, choices=[]):
        self.items = [{'label': choice} for choice in choices]

    @property
    def is_multiselect(self):
        if not hasattr(self, 'multiselect'):
            return False
        else:
            return self.multiselect

    def select_default(self):
        """
        Apply and return the default selection.
        """
        self._apply_default_selection(skip_if_current_valid=False)
        return self.selected

    def select_all(self):
        """
        Select (and return) all available options.  Raises an error if not :meth:`is_multiselect`
        """
        if not self.is_multiselect:
            raise ValueError("not currently in multiselect mode")
        self.selected = self.choices
        return self.selected

    def select_none(self):
        """
        Select (and return) and empty list.  Raises an error if not :meth:`is_multiselect`
        """
        if not self.is_multiselect:
            raise ValueError("not currently in multiselect mode")
        self.selected = []
        return self.selected

    def select_next(self):
        """
        Select next entry in the choices, wrapping when reaching the end.  Raises an error if
        :meth:`is_multiselect`
        """
        if self.is_multiselect:
            raise ValueError("currently in multiselect mode")

        cycle = self.choices
        if not len(cycle):  # pragma: no cover
            raise ValueError("no choices")
        if self.selected == '':
            curr_ind = -1
        else:
            curr_ind = cycle.index(self.selected)
        self.selected = cycle[(curr_ind + 1) % len(cycle)]
        return self.selected

    def select_previous(self):
        """
        Apply and return the previous selection (or default option if no previous selection)
        """
        if self._selected_previous is None:
            return self.select_default()
        self.selected = self._selected_previous
        return self.selected

    @property
    def default_text(self):
        return self._default_text

    @property
    def manual_options(self):
        return self._manual_options
        # read-only access to manual options (cannot change after init)

    @property
    def cached_properties(self):
        return self._cached_properties

    def add_filter(self, *filters):
        self.filters += [filter for filter in filters]

    @property
    def viewer_dicts(self):
        all_viewer_dicts = super().viewer_dicts
        if self._viewers is None:
            return all_viewer_dicts
        # filter to those provided (either by id or reference)
        return [v for v in all_viewer_dicts
                if v['reference'] in self._viewers or v['id'] in self._viewers]

    @property
    def viewer_refs(self):
        return [v['reference'] for v in self.viewer_dicts]

    @property
    def viewer_ids(self):
        return [v['id'] for v in self.viewer_dicts]

    @property
    def viewers(self):
        return [v['viewer'] for v in self.viewer_dicts]

    @property
    def labels(self):
        return [s['label'] for s in self.items if 'label' in s.keys()]

    def _get_selected_item(self, selected):
        for item in self.items:
            if item['label'] == selected:
                return item
        return {}

    @cached_property
    def selected_item(self):
        if self.is_multiselect:
            items = [self._get_selected_item(selected) for selected in self.selected]
            if not len(items):
                return {}
            return {k: [item[k] for item in items] for k in items[0].keys()}
        return self._get_selected_item(self.selected)

    @cached_property
    def selected_obj(self):
        raise NotImplementedError(f"selected_obj not implemented by {self.__class__.__name__}")

    @property
    def default_mode(self):
        return self._default_mode

    def _apply_default_selection(self, skip_if_current_valid=True):
        if self.is_multiselect:
            if skip_if_current_valid and len(self.selected) == 0:
                # current selection is empty and so should remain that way
                return
            is_valid = [s in self.labels for s in self.selected]
            if skip_if_current_valid and np.any(is_valid):
                if np.all(is_valid):
                    return
                self.selected = [s for s in self.labels if s in self.selected]
                return
            is_valid = False
        is_valid = self.selected in self.labels
        if callable(self.default_mode):
            # callable was defined and passed by the plugin or inheriting component.
            # the callable takes the viewer component as input as well as the `is_valid` boolean
            # which states if the current selection is already valid and returns the default label
            # (to keep the current selection
            self.selected = self.default_mode(self, is_valid=is_valid)
            return

        if is_valid and skip_if_current_valid:
            # current selection is valid
            return

        default_empty = [] if self.is_multiselect else ''
        if self.default_mode == 'first':
            self.selected = self.labels[0] if len(self.labels) else default_empty
        elif self.default_mode == 'default_text':
            self.selected = self._default_text if self._default_text else default_empty
        else:
            self.selected = default_empty

    def _is_valid_item(self, item, filter_callables={}):
        for valid_filter in self.filters:
            if isinstance(valid_filter, str):
                # pull from the functions above (should be subclassed),
                # will raise an error if not in locals
                try:
                    valid_filter = filter_callables[valid_filter]
                except KeyError:
                    raise ValueError(f"{valid_filter} not an implemented filter.")
            if not valid_filter(item):
                return False
        return True

    def _multiselect_changed(self, event):
        self._clear_cache()
        if self.is_multiselect:
            self.selected = [self.selected] if self.selected != '' else []
        elif isinstance(self.selected, list) and len(self.selected):
            self.selected = self.selected[0]
        else:
            self._apply_default_selection()

    def _selected_changed(self, event):
        self._selected_previous = event['old']
        self._clear_cache()
        if self.is_multiselect:
            if not isinstance(event['new'], list):
                self.selected = [event['new']]
                return
            if not np.all([item in self.labels + [''] for item in event['new']]):
                self.selected = event['old']
                raise ValueError(f"not all items in {event['new']} are one of {self.labels}, reverting selection to {event['old']}")  # noqa
        else:
            if event['new'] not in self.labels + ['']:
                self.selected = event['old']
                raise ValueError(f"{event['new']} not one of {self.labels}, reverting selection to {event['old']}")  # noqa


class UnitSelectPluginComponent(SelectPluginComponent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_observe('items', lambda _: self._clear_cache('unit_choices'))
        self._addl_unit_strings = []

    @cached_property
    def unit_choices(self):
        return [u.Unit(lbl) for lbl in self.labels]

    @property
    def addl_unit_choices(self):
        return [u.Unit(choice) for choice in self._addl_unit_strings]

    def _selected_changed(self, event):
        self._clear_cache()
        if event['new'] in self.labels + ['']:
            # the string is an exact match, no converting necessary
            return
        elif not len(self.labels):
            raise ValueError("no valid unit choices")
        try:
            new_u = u.Unit(event['new'])
        except ValueError:
            self.selected = event['old']
            raise ValueError(f"{event['new']} could not be converted to a valid unit, reverting selection to {event['old']}")  # noqa
        if new_u not in self.unit_choices:
            if new_u in self.addl_unit_choices:
                # append this one (as the valid string representation) to the list of user-choices
                addl_index = self.addl_unit_choices.index(new_u)
                self.choices = self.choices + [self._addl_unit_strings[addl_index]]
                # clear the cache so we can find the appropriate entry in unit_choices
                self._clear_cache('unit_choices')
            else:
                self.selected = event['old']
                raise ValueError(f"{event['new']} not one of {self.labels}, reverting selection to {event['old']}")  # noqa

        # convert to default string representation from the valid choices
        ind = self.unit_choices.index(new_u)
        self.selected = self.labels[ind]


class FileImportSelectPluginComponent(SelectPluginComponent):
    """
    IMPORTANT: Always accompany with HasFileImportSelect
    IMPORTANT: currently assumed only one instance per-plugin

    Example template (label and hint are optional)::

      <plugin-file-import
        title="Import File"
        hint="Select a file to import"
        :show="method_selected === 'From File...' && from_file.length === 0"
        :from_file="from_file"
        :from_file_message.sync="from_file_message"
        @click-cancel="method_selected=method_items[0].label"
        @click-import="file_import_accept()">
          <g-file-import id="file-uploader"></g-file-import>
      </plugin-file-import>
    """
    def __init__(self, plugin, **kwargs):
        self._cached_obj = {}

        if "From File..." not in kwargs['manual_options']:
            kwargs['manual_options'] += ['From File...']

        if not isinstance(plugin, HasFileImportSelect):  # pragma: no cover
            raise NotImplementedError("plugin must inherit from HasFileImportSelect")

        super().__init__(plugin,
                         from_file='from_file', from_file_message='from_file_message',
                         **kwargs)

        self.plugin._file_chooser.observe(self._on_file_path_changed, names='file_path')
        # reference back here so the plugin can reset to default
        self.plugin._file_chooser._select_component = self

        def _default_file_parser(path):
            # by default, just return the file path itself (and allow all files)
            return '', {path: path}

        self._file_parser = kwargs.pop('file_parser', _default_file_parser)
        self.add_observe('from_file', self._from_file_changed)

    @property
    def selected_obj(self):
        if self.selected == 'From File...':
            return self._cached_obj.get(self.from_file, self._file_parser(self.from_file)[1])
        return super().selected_obj

    def _from_file_changed(self, event):
        if event['new'].startswith('API:'):
            # object imported from the API: parsing is already handled
            return
        if len(event['new']):
            if event['new'] != self.plugin._file_chooser.file_path:
                # then need to run the parser or check for valid path
                if not os.path.exists(event['new']):
                    if self.selected == 'From File...':
                        self.select_previous()
                    raise ValueError(f"{event['new']} is not a valid file path")

                # run through the parsers and check the validity
                self._on_file_path_changed(event)
                if self.from_file_message:
                    if self.selected == 'From File...':
                        self.select_previous()
                    raise ValueError(self.from_file_message)

            self.selected = 'From File...'

        elif self.selected == 'From File...':
            self.select_previous()

    def _on_file_path_changed(self, event):
        self.from_file_message = 'Checking if file is valid'
        path = event['new']
        if (path is not None
                and not os.path.exists(path)
                or not os.path.isfile(path)):
            self.from_file_message = 'File path does not exist'
            return

        self.from_file_message, self._cached_obj = self._file_parser(path)

    def import_file(self, path):
        """
        Select 'From File...' and set the path.
        """
        # NOTE: this will trigger self._from_file_changed which in turn will
        # pass through the parser, raise an error if necessary, and set
        # self.selected accordingly
        self.from_file = path

    def import_obj(self, obj):
        """
        Import a supported object directly from the API.
        """
        msg, self._cached_obj = self._file_parser(obj)
        if msg:
            raise ValueError(msg)
        self.from_file = list(self._cached_obj.keys())[0]
        self.selected = 'From File...'


class HasFileImportSelect(VuetifyTemplate, HubListener):
    from_file = Unicode().tag(sync=True)
    from_file_message = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # imported here to avoid circular import
        from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser

        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)
        self._file_chooser = FileChooser(start_path)
        self.components = {'g-file-import': self._file_chooser}

    def vue_file_import_accept(self, *args, **kwargs):
        self.from_file = self._file_chooser.file_path

    def vue_file_import_cancel(self, *args, **kwargs):
        self._file_chooser._select_component.select_previous()
        self.from_file = ''


class EditableSelectPluginComponent(SelectPluginComponent):
    """
    Plugin select with support for renaming, adding, and deleting items (by the user).

    Useful API methods/attributes:

    * :meth:`~SelectPluginComponent.choices`
    * ``selected``
    * :meth:`~EditableSelectPluginComponent.add_choice`
    * :meth:`~EditableSelectPluginComponent.rename_choice`
    * :meth:`~EditableSelectPluginComponent.remove_choice`
    """

    """
    Traitlets (in the object, custom traitlets in the plugin)

    * ``items`` (list of dicts with keys: label, color)
    * ``selected`` (string)
    * ``mode`` (string)
    * ``edit_value`` (string)

    Properties (in the object only):

    * ``labels`` (list of labels corresponding to items)


    To use in a plugin:

    * create (empty) traitlets in the plugin
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets.
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component
    * observe the traitlets created and defined in the plugin, as necessary

    Example template (label and hint are optional)::

      <plugin-editable-select
        :mode.sync="mode"
        :edit_value.sync="edit_value"
        :items="items"
        :selected.sync="selected"
        label="Label"
        hint="Select an item to modify."
      </plugin-editable-select>
    """
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        plugin
            the parent plugin object
        items : str
            the name of the items traitlet defined in ``plugin``
        selected : str
            the name of the selected traitlet defined in ``plugin``
        edit_value : str
            the name of the traitlet containing the temporary edit value defined in ``plugin``
        manual_options : list
            list of entries present before user-modification
        name : str
            the user-friendly name of the items, used in error message in place of "entry"
        on_add : callable
            callback when a new item is added, but before the selection is updated
        on_add_after_selection : callable
            callback when a new item is added and the selection is updated
        on_rename : callable
            callback when an item is renamed, but before the selection is updated
        on_rename_after_selection : callable
            callback when an item is renamed and the selection is updated
        on_remove : callable
            callback when an item is removed, but before the selection is updated
        on_remove_after_selection : callable
            callback when an item is removed and the selection is updated
        """
        super().__init__(*args, **kwargs)
        if self.is_multiselect:
            self._multiselect_changed()
        self.add_observe(kwargs.get('mode'), self._mode_changed)
        self.mode = 'select'  # select, rename, add
        self._name = kwargs.get('name', 'entry')  # used for error messages
        self._on_add = kwargs.get('on_add', lambda *args: None)
        self._on_add_after_selection = kwargs.get('on_add_after_selection', lambda *args: None)
        self._on_rename = kwargs.get('on_rename', lambda *args: None)
        self._on_rename_after_selection = kwargs.get('on_rename_after_selection', lambda *args: None)  # noqa
        self._on_remove = kwargs.get('on_remove', lambda *args: None)
        self._on_remove_after_selection = kwargs.get('on_remove_after_selection', lambda *args: None)  # noqa

    def _multiselect_changed(self):
        # already subscribed to traitlet by SelectPluginComponent
        if self.multiselect:
            raise ValueError("EditableSelectPluginComponent does not support multiselect")

    def _selected_changed(self, event):
        super()._selected_changed(event)
        self.edit_value = self.selected

    def _mode_changed(self, event):
        if self.mode == 'rename:accept':
            try:
                self.rename_choice(self.selected, self.edit_value)
            except ValueError as e:
                self.hub.broadcast(SnackbarMessage(f"Renaming {self._name} failed: {e}",
                                   sender=self, color="error"))
            else:
                self.mode = 'select'
                self.edit_value = self.selected
        elif self.mode == 'add:accept':
            try:
                self.add_choice(self.edit_value)
            except ValueError as e:
                self.hub.broadcast(SnackbarMessage(f"Adding {self._name} failed: {e}",
                                   sender=self, color="error"))
            else:
                self.mode = 'select'
                self.edit_value = self.selected
        elif self.mode == 'remove:accept':
            self.remove_choice(self.edit_value)
            if len(self.choices):
                self.mode = 'select'
            else:
                self.mode = 'add'

    def _update_items(self):
        self.items = [{"label": opt} for opt in self._manual_options]

    def _check_new_choice(self, label):
        if not len(label):
            raise ValueError("new choice must not be blank")
        if label in self.choices:
            raise ValueError(f"'{label}' is already a valid choice")

    def add_choice(self, label, set_as_selected=True):
        """
        Add a new entry/choice.

        Parameters
        ----------
        * label : str
            label of the new entry, must not already be one of the choices
        * set_as_selected : bool
            whether to immediately set the new entry as the selected entry
        """
        self._check_new_choice(label)
        self._manual_options += [label]
        self._update_items()
        self._on_add(label)
        if set_as_selected:
            self.selected = label
        self._on_add_after_selection(label)

    def remove_choice(self, label=None):
        """
        Remove an existing entry.

        Parameters
        ----------
        * label : str
            label of an existing entry.  If not provided, will default to the currently selected
            entry
        """
        if label is None:
            label = self.selected
        if label not in self.choices:
            raise ValueError(f"'{label}' not one of available choices ({self.choices})")
        self._manual_options.remove(label)
        self._update_items()
        self._on_remove(label)
        self._apply_default_selection(skip_if_current_valid=True)
        self._on_remove_after_selection(label)

    def rename_choice(self, old, new):
        """
        Rename an existing entry.

        Parameters
        ----------
        * old : str
            label of the existing entry to modify
        * new : str
            new label.  Must not be another existing entry.
        """
        if old not in self.choices:
            raise ValueError(f"'{old}' not one of available choices ({self.choices})")
        self._check_new_choice(new)
        was_selected = self.selected == old
        self._manual_options[self._manual_options.index(old)] = new
        self._update_items()
        self._on_rename(old, new)
        if was_selected:
            self.selected = new
        self._on_rename_after_selection(old, new)


class LayerSelect(SelectPluginComponent):
    """
    Plugin select for layers, with support for single or multi-selection.

    Useful API methods/attributes:

    * :meth:`~SelectPluginComponent.choices`
    * ``selected``
    * :meth:`~SelectPluginComponent.is_multiselect`
    * :meth:`~SelectPluginComponent.select_default`
    * :meth:`~SelectPluginComponent.select_all` (only if ``is_multiselect``)
    * :meth:`~SelectPluginComponent.select_none` (only if ``is_multiselect``)
    * :attr:`selected_obj`
    """

    """
    Traitlets (in the object, custom traitlets in the plugin)

    * ``items`` (list of dicts with keys: label, color)
    * ``selected`` (string)

    Properties (in the object only):

    * ``labels`` (list of labels corresponding to items)
    * ``selected_item`` (dictionary in ``items`` coresponding to ``selected``, cached)
    * ``selected_obj`` (layer object corresponding to ``selected``, cached)


    To use in a plugin:

    * create (empty) traitlets in the plugin
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets.
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component
    * observe the traitlets created and defined in the plugin, as necessary

    Example template (label and hint are optional)::

      <plugin-layer-select
        :items="layer_items"
        :selected.sync="layer_selected"
        :show_if_single_entry="true"
        label="Layer"
        hint="Select layer."
      />
    """
    def __init__(self, plugin, items, selected, viewer,
                 multiselect=None,
                 default_text=None, manual_options=[],
                 default_mode='first'):
        """
        Parameters
        ----------
        plugin
            the parent plugin object
        items : str
            the name of the items traitlet defined in ``plugin``
        selected : str
            the name of the selected traitlet defined in ``plugin``
        viewer: str
            the name of the traitlet defined in ``plugin`` storing the viewer(s) to expose the
            layers
        default_text : str or None
            the text to show for no selection.  If not provided or None, no entry will be provided
            in the dropdown for no selection.
        manual_options: list
            list of options to provide that are not automatically populated by subsets.  If
            ``default`` text is provided but not in ``manual_options`` it will still be included as
            the first item in the list.
        """
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         viewer=viewer,
                         multiselect=multiselect,
                         default_text=default_text,
                         manual_options=manual_options,
                         default_mode=default_mode)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_data_added)
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda _: self._update_layer_items())
        self.hub.subscribe(self, AddDataToViewerMessage,
                           handler=self._on_data_added)
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda _: self._on_subset_created())
        # will need SubsetUpdateMessage for name only (style shouldn't force a full refresh)
        # self.hub.subscribe(self, SubsetUpdateMessage,
        #                    handler=lambda _: self._update_layer_items())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda _: self._update_layer_items())

        self.app.state.add_callback('layer_icons', self._update_layer_items)
        self.add_observe(viewer, self._on_viewer_selected_changed)
        self.add_observe(selected, self._update_layer_items)
        self._update_layer_items()

    def _get_viewer(self, viewer):
        # newer will likely be the viewer name in most cases, but viewer id in the case
        # of additional viewers in imviz.
        try:
            return self.app.get_viewer(viewer)
        except TypeError:
            return self.app.get_viewer_by_id(viewer)

    @property
    def viewer_objs(self):
        viewer_names = self.viewer
        if not isinstance(viewer_names, list):
            viewer_names = [viewer_names]
        return [self._get_viewer(viewer) for viewer in viewer_names]

    def _layer_to_dict(self, layer_label):
        is_subset = None
        colors = []
        visibilities = []
        for viewer in self.viewer_objs:
            for layer in viewer.layers:
                if layer.layer.label == layer_label:
                    if is_subset is None:
                        is_subset = ((hasattr(layer, 'state') and hasattr(layer.state, 'subset_state')) or  # noqa
                                     (hasattr(layer, 'layer') and hasattr(layer.layer, 'subset_state')))  # noqa

                    if (getattr(viewer.state, 'color_mode', None) == 'Colormaps'
                            and hasattr(layer.state, 'cmap')):
                        colors.append(layer.state.cmap.name)
                    else:
                        colors.append(layer.state.color)

                    visibilities.append(getattr(layer.state, 'bitmap_visible', True)
                                        and layer.visible)

        return {"label": layer_label,
                "is_subset": is_subset,
                "icon": self.app.state.layer_icons.get(layer_label),
                "visible": visibilities[0] if len(list(set(visibilities))) == 1 else 'mixed',
                "colors": np.unique(colors).tolist()}

    def _on_viewer_selected_changed(self, msg=None):
        # we don't want to update the layers if we're just toggling
        # between single and multi-select
        old, new = msg['old'], msg['new']
        if not isinstance(old, list):
            old = [old]
        if not isinstance(new, list):
            new = [new]
        if new != old:
            self._clear_cache()
            self._update_layer_items()
            added_viewers = list(set(new) - set(old))
            removed_viewers = list(set(old) - set(new))
            for old_viewer in removed_viewers:
                old_viewer = self._get_viewer(old_viewer)
                if old_viewer is None:
                    continue
                # NOTE: color_mode callback must be conflicting with something else, so instead
                # we call _update_layer_items in the PlotOptionsSyncState for color_mode
                # old_viewer.state.remove_callback('color_mode', self._update_layer_items)
                for layer in old_viewer.state.layers:
                    layer.remove_callback('color', self._update_layer_items)
                    if hasattr(layer, 'cmap'):
                        layer.remove_callback('cmap', self._update_layer_items)
                    if hasattr(layer, 'bitmap_visible'):
                        layer.remove_callback('bitmap_visible', self._update_layer_items)
                    elif hasattr(layer, 'visible'):
                        layer.remove_callback('visible', self._update_layer_items)

            for new_viewer in added_viewers:
                new_viewer = self._get_viewer(new_viewer)
                if new_viewer is None:
                    continue
                # NOTE: color_mode callback must be conflicting with something else, so instead
                # we call _update_layer_items in the PlotOptionsSyncState for color_mode
                # new_viewer.state.add_callback('color_mode', self._update_layer_items)
                for layer in new_viewer.state.layers:
                    layer.add_callback('color', self._update_layer_items)
                    if hasattr(layer, 'cmap'):
                        layer.add_callback('cmap', self._update_layer_items)
                    if hasattr(layer, 'bitmap_visible'):
                        layer.add_callback('bitmap_visible', self._update_layer_items)
                    if hasattr(layer, 'visible'):
                        layer.add_callback('visible', self._update_layer_items)

    def _on_subset_created(self, msg=None):
        new_subset_label = self.app.data_collection.subset_groups[-1].label
        viewer = self.viewer if isinstance(self.viewer, list) else [self.viewer]
        for current_viewer in viewer:
            for layer in self._get_viewer(current_viewer).state.layers:
                if layer.layer.label == new_subset_label:
                    # Is it ok if only one subset layer has this callback?
                    layer.add_callback('color', self._update_layer_items)
                    layer.add_callback('visible', self._update_layer_items)
                    break
                    # TODO: Add ability to add new item to self.items instead of recompiling
        self._update_layer_items({'source': 'subset_added'})

    def _on_data_added(self, msg=None):
        if msg is None or not hasattr(msg, 'data') or msg.data is None:
            return
        new_data_label = msg.data.label
        viewer = self.viewer if isinstance(self.viewer, list) else [self.viewer]
        for current_viewer in viewer:
            for layer in self._get_viewer(current_viewer).state.layers:
                if layer.layer.label == new_data_label and not hasattr(layer.layer, 'subset_state'):
                    # Add a callback to the layer's color attribute to call
                    # _on_layers_changed whenever the color changes
                    # TODO: find out if this conflicts with another color change event
                    #  and is causing the lag in the color picker
                    layer.add_callback('color', self._update_layer_items)
                    if hasattr(layer, 'cmap'):
                        layer.add_callback('cmap', self._update_layer_items)
                    if hasattr(layer, 'bitmap_visible'):
                        layer.add_callback('bitmap_visible', self._update_layer_items)
                    if hasattr(layer, 'visible'):
                        layer.add_callback('visible', self._update_layer_items)

        self._update_layer_items({'source': 'data_added'})

    @observe('filters')
    def _update_layer_items(self, msg={}):
        # NOTE: _on_layers_changed is passed without a msg object during init
        # TODO: Handle changes to just one item without recompiling the whole thing
        manual_items = [{'label': label} for label in self.manual_options]
        all_layers = [layer for viewer in self.viewer_objs
                      for layer in getattr(viewer, 'layers', [])]
        # remove duplicates - we'll loop back through all selected viewers to get a list of colors
        # and visibilities later within _layer_to_dict
        layer_labels = [layer.layer.label for layer in all_layers if self.app.state.layer_icons.get(layer.layer.label)]  # noqa
        unique_layer_labels = list(set(layer_labels))

        layer_items = [self._layer_to_dict(layer_label) for layer_label in unique_layer_labels]

        def _sort_by_icon(items_dict):
            return items_dict['icon']
        layer_items.sort(key=_sort_by_icon)

        self.items = manual_items + layer_items

        self._apply_default_selection()

    @cached_property
    def selected_obj(self):
        viewer_names = self.viewer
        if not isinstance(viewer_names, list):
            # case for single-select on the viewer select
            viewer_names = [viewer_names]

        selected = self.selected
        if not isinstance(selected, list):
            selected = [selected]

        viewers = [self._get_viewer(viewer_name) for viewer_name in viewer_names]

        layers = [[layer for layer in viewer.layers
                   if layer.layer.label in selected]
                  for viewer in viewers]

        if not self.is_multiselect and len(layers) == 1:
            return layers[0]
        else:
            return layers


class LayerSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the LayerSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``LayerSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.layer``.

    Example template (label and hint are optional)::

      <plugin-layer-select
        :items="layer_items"
        :selected.sync="layer_selected"
        :show_if_single_entry="true"
        label="Layer"
        hint="Select layer."
      />

    """
    layer_items = List().tag(sync=True)
    layer_selected = Any().tag(sync=True)
    layer_viewer = Unicode().tag(sync=True)
    layer_multiselect = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layer = LayerSelect(self,
                                 'layer_items',
                                 'layer_selected',
                                 'layer_viewer',
                                 'layer_multiselect')


class SubsetSelect(SelectPluginComponent):
    """
    Plugin select for subsets, with support for single or multi-selection.

    Useful API methods/attributes:

    * :meth:`~SelectPluginComponent.choices`
    * ``selected``
    * :meth:`~SelectPluginComponent.is_multiselect`
    * :meth:`~SelectPluginComponent.select_default`
    * :meth:`~SelectPluginComponent.select_all` (only if ``is_multiselect``)
    * :meth:`~SelectPluginComponent.select_none` (only if ``is_multiselect``)
    * :attr:`selected_obj`
    * :attr:`selected_subset_state`
    * :meth:`selected_min_max`
    """

    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: label, color, type)
    * ``selected`` (string)
    * ``selected_has_subregions`` (bool, OPTIONAL)

    Properties (in the object only):

    * ``labels`` (list of labels corresponding to items)
    * ``selected_item`` (dictionary in ``items`` coresponding to ``selected``, cached)
    * ``selected_obj`` (subset object corresponding to ``selected``, cached)

    Methods (in the object only):

    * ``selected_min_max(cube)`` (quantity, only applicable for spectral subsets)

    To use in a plugin:

    * create (empty) traitlets in the plugin
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets.
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component
    * observe the traitlets created and defined in the plugin, as necessary

    Example template (label and hint are optional)::

      <plugin-subset-select
        :items="spectral_subset_items"
        :selected.sync="spectral_subset_selected"
        :show_if_single_entry="true"
        label="Subset"
        hint="Select subset."
      />

    """
    def __init__(self, plugin, items, selected, multiselect=None, selected_has_subregions=None,
                 dataset=None, viewers=None, default_text=None, manual_options=[], filters=[],
                 default_mode='default_text'):
        """
        Parameters
        ----------
        plugin
            the parent plugin object
        items : str
            the name of the items traitlet defined in ``plugin``
        selected : str
            the name of the selected traitlet defined in ``plugin``
        multiselect : str
            the name of the traitlet defining whether the dropdown should accept multiple selections
        selected_has_subregions : str
            the name of the selected_has_subregions traitlet defined in ``plugin``, optional
        dataset : str
            the name of the dataset traitlet defined in ``plugin``, to be used for accessing how
            the subset is applied to the data (masks, etc), optional
        viewers : list
            the reference names or ids of the viewer to extract the subregion.  If not provided o
            None, will loop through all references.
        default_text : str or None
            the text to show for no selection.  If not provided or None, no entry will be provided
            in the dropdown for no selection.
        manual_options : list
            list of options to provide that are not automatically populated by subsets.  If
            ``default`` text is provided but not in ``manual_options`` it will still be included as
            the first item in the list.
        filters : list
            list of strings (for built-in filters) or callables to filter to only valid options.
        """
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         multiselect=multiselect,
                         filters=filters,
                         selected_has_subregions=selected_has_subregions,
                         dataset=dataset,
                         viewers=viewers,
                         default_text=default_text,
                         manual_options=manual_options,
                         default_mode=default_mode)

        self._cached_properties += ["selected_subset_state",
                                    "selected_spatial_region",
                                    "selected_subset_mask"]
        if dataset is not None:
            # clear selected_subset_mask and selected_spatial_region on change to dataset
            self.add_observe(self.dataset._plugin_traitlets['selected'],
                             self._on_dataset_selected_changed)

        if selected_has_subregions is not None:
            self.selected_has_subregions = False

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda msg: self._update_subset(msg.subset, msg.attribute))
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda msg: self._delete_subset(msg.subset))

        # intialize any subsets that have already been created
        for lyr in self.app.data_collection.subset_groups:
            self._update_subset(lyr)

    def _selected_changed(self, event):
        super()._selected_changed(event)
        self._update_has_subregions()

    def _on_dataset_selected_changed(self, event):
        self._clear_cache('selected_subset_mask', 'selected_spatial_region')

    def _subset_to_dict(self, subset):
        # find layer artist in default spectrum-viewer
        for viewer in self.viewers:
            for layer in viewer.layers:
                if layer.layer.label == subset.label:
                    color = layer.state.color
                    type = get_subset_type(subset)
                    return {"label": subset.label, "color": color, "type": type}
        return {"label": subset.label, "color": False, "type": False}

    def _delete_subset(self, subset):
        # NOTE: calling .remove will not trigger traitlet update
        self.items = [s for s in self.items
                      if s['label'] != subset.label]
        if self.selected not in self.labels:
            self._apply_default_selection()

    def _is_valid_item(self, subset):
        def is_spectral(subset):
            return get_subset_type(subset) == 'spectral'

        def is_spatial(subset):
            return get_subset_type(subset) == 'spatial'

        def is_not_composite(subset):
            return not hasattr(subset.subset_state, 'state1')

        def is_not_annulus(subset):
            # this will be considered "not an annulus" if it is composite, even
            # if that composite subset contains an annulus
            return (not is_not_composite(subset)
                    or not isinstance(subset.subset_state.roi, CircularAnnulusROI))

        return super()._is_valid_item(subset, locals())

    def _update_subset(self, subset, attribute=None):
        if subset.label not in self.labels:
            # NOTE: this logic will need to be revisited if generic renaming of subsets is added
            # see https://github.com/spacetelescope/jdaviz/pull/1175#discussion_r829372470
            if subset.label.startswith('Subset') and self._is_valid_item(subset):
                # NOTE: += will not trigger traitlet update
                self.items = self.items + [self._subset_to_dict(subset)]  # noqa
        else:
            # 'type' can be passed manually rather than coming from SubsetUpdateMessage.attribute
            if attribute in ('style', 'type'):
                # TODO: may need to add label and then rebuild the entire list if/when
                # we add support for renaming subsets

                # NOTE: in-line replacement (self.spectral_subset_items[i] = ...)
                # will not trigger traitlet update
                self.items = [s if s['label'] != subset.label
                              else self._subset_to_dict(subset)
                              for s in self.items]

        if (attribute == 'subset_state' and
            ((self.is_multiselect and subset.label in self.selected)
             or (subset.label == self.selected))):
            # updated the currently selected subset
            self._clear_cache("selected_obj", "selected_item", "selected_subset_state",
                              "selected_subset_mask", "selected_subset", "selected_spatial_region")
            self._update_has_subregions()

    def _update_has_subregions(self):
        if "selected_has_subregions" in self._plugin_traitlets.keys():
            if self.is_multiselect:
                self.selected_has_subregions = False
            elif (
                self.selected in self._manual_options or
                not hasattr(self.selected_obj, 'subregions')
            ):
                self.selected_has_subregions = False
            else:
                self.selected_has_subregions = len(self.selected_obj.subregions) > 1

    def _get_selected_obj(self, selected):
        if (
            selected in self.manual_options or
            selected not in self.labels or
            selected is None
        ):
            return None
        return self.app.get_subsets(selected)

    @cached_property
    def selected_obj(self):
        if self.is_multiselect:
            return [self._get_selected_obj(subset) for subset in self.selected]
        return self._get_selected_obj(self.selected)

    def _get_subset_state(self, subset):
        subset_group = [s for s in self.app.data_collection.subset_groups if
                        s.label == subset]
        if len(subset_group) == 0:
            return None
        if len(subset_group) != 1:  # pragma: no cover
            raise ValueError("found multiple matches for subset")
        return subset_group[0].subset_state

    @cached_property
    def selected_subset_state(self):
        if self.is_multiselect:
            return [self._get_subset_state(subset) for subset in self.selected]
        return self._get_subset_state(self.selected)

    def _get_subset_mask(self, subset=None, dataset=None):
        if subset is None:
            subset = self.selected
        if dataset is None:
            if getattr(self.plugin, 'dataset', None) is None:  # pragma: no cover
                raise ValueError("Retrieving subset mask requires associated dataset")
            dataset = self.plugin.dataset.selected
        get_data_kwargs = {'data_label': dataset}
        if 'is_spectral' in self.filters:
            get_data_kwargs['spectral_subset'] = subset
        elif 'is_spatial' in self.filters:
            get_data_kwargs['spatial_subset'] = subset

        if self.app.config == 'cubeviz' and 'is_spectral' in self.filters:
            viewer_ref = getattr(self.plugin,
                                 '_default_spectrum_viewer_reference_name',
                                 self.viewers[0].reference_id)
            get_data_kwargs['function'] = self.app.get_viewer(viewer_ref).state.function

        subset = self.app._jdaviz_helper.get_data(**get_data_kwargs)
        return subset.mask

    @cached_property
    def selected_subset_mask(self):
        if self.is_multiselect:  # pragma: no cover
            raise NotImplementedError("Retrieving subset mask is not"
                                      " supported in multiselect mode")

        return self._get_subset_mask()

    def _get_spatial_region(self, dataset, subset=None):
        if subset is None:
            subset = self.selected
            subset_state = self.selected_subset_state
        else:
            subset_state = self._get_subset_state(subset)
        region = _get_region_from_spatial_subset(self.plugin,
                                                 subset_state,
                                                 dataset=dataset)
        region.meta['label'] = subset
        return region

    @cached_property
    def selected_spatial_region(self):
        if not getattr(self, 'dataset', None):  # pragma: no cover
            raise ValueError("Retrieving subset mask requires associated dataset")
        if self.is_multiselect and self.dataset.is_multiselect:  # pragma: no cover
            # technically this could work if either has length of one, but would require extra
            # logic
            raise NotImplementedError("cannot access selected_spatial_region for multiple subsets and multiple datasets")  # noqa
        types = self.selected_item.get('type')
        if not isinstance(types, list):
            types = [types]
        if np.any([type != 'spatial' for type in types]):
            raise TypeError("This action is only supported on spatial-type subsets")
        if self.is_multiselect:
            return [self._get_spatial_region(dataset=self.dataset.selected, subset=subset) for subset in self.selected]  # noqa
        return self._get_spatial_region(dataset=self.dataset.selected)

    def selected_min_max(self, dataset):
        """
        Get the min/max spectral range of ``dataset`` given the selected spectral subset
        """
        if self.is_multiselect:  # pragma: no cover
            raise TypeError("This action cannot be done when multiselect is active")
        if not isinstance(dataset, Spectrum1D):  # pragma: no cover
            raise TypeError("dataset must be a Spectrum1D object")

        if self.selected_obj is None:
            return np.nanmin(dataset.spectral_axis), np.nanmax(dataset.spectral_axis)
        if self.selected_item.get('type') != 'spectral':
            raise TypeError("This action is only supported on spectral-type subsets")
        else:
            return self.selected_obj.lower, self.selected_obj.upper


class SpectralSubsetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the SubsetSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``SpectralSubsetSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.spectral_subset``.

    Example template (label and hint are optional)::

      <plugin-subset-select
        :items="spectral_subset_items"
        :selected.sync="spectral_subset_selected"
        :show_if_single_entry="true"
        label="Spectral region"
        hint="Select spectral region."
      />

    """
    spectral_subset_items = List().tag(sync=True)
    spectral_subset_selected = Any().tag(sync=True)
    spectral_subset_selected_has_subregions = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        spectrum_viewer = kwargs.get('spectrum_viewer_reference_name')
        self.spectral_subset = SubsetSelect(self,
                                            'spectral_subset_items',
                                            'spectral_subset_selected',
                                            'spectral_subset_selected_has_subregions',
                                            dataset='dataset' if hasattr(self, 'dataset') else None,  # noqa
                                            viewers=[spectrum_viewer],
                                            default_text='Entire Spectrum',
                                            filters=['is_spectral'])


class SpatialSubsetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the SubsetSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``SpatialSubsetSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.spatial_subset``.

    Example template (label and hint are optional)::

      <plugin-subset-select
        :items="spatial_subset_items"
        :selected.sync="spatial_subset_selected"
        label="Spatial region"
        hint="Select spatial region."
      />

    """
    spatial_subset_items = List().tag(sync=True)
    spatial_subset_selected = Any().tag(sync=True)
    spatial_subset_selected_has_subregions = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spatial_subset = SubsetSelect(self,
                                           'spatial_subset_items',
                                           'spatial_subset_selected',
                                           'spatial_subset_selected_has_subregions',
                                           dataset='dataset' if hasattr(self, 'dataset') else None,
                                           default_text='Entire Cube',
                                           filters=['is_spatial'])


class DatasetSpectralSubsetValidMixin(VuetifyTemplate, HubListener):
    """
    Adds a traitlet tracking whether self.dataset and self.spectral_subset
    overlap in the spectral axis.

    Note that if using in another method that is also observing dataset_selected
    or spectral_subset_selected, that that method could be called before the traitlet
    is updated.  In that case, call self._check_dataset_spectral_subset_valid() itself
    directly.  The traitlet can still be used for any warning text in the plugin UI.
    """
    spectral_subset_valid = Bool(True).tag(sync=True)

    @observe("dataset_selected", "spectral_subset_selected")
    def _check_dataset_spectral_subset_valid(self, event={}, return_ranges=False):
        if not hasattr(self, 'dataset'):
            # plugin not fully initialized
            return
        if self.spectral_subset_selected == "Entire Spectrum":
            self.spectral_subset_valid = True
        else:
            spec = self.dataset.selected_obj
            spec_min, spec_max = np.nanmin(spec.spectral_axis), np.nanmax(spec.spectral_axis)
            subset_min, subset_max = self.spectral_subset.selected_min_max(spec)
            self.spectral_subset_valid = bool(subset_min < spec_max and subset_max > spec_min)
        if return_ranges:
            return (self.spectral_subset_valid,
                    (spec_min.value, spec_max.value),
                    (subset_min.value, subset_max.value))
        else:
            return self.spectral_subset_valid


class NonFiniteUncertaintyMismatchMixin(VuetifyTemplate, HubListener):
    """Adds a traitlet that identifies if there are any finite data values
    that correspond to a non-finite uncertainty at that index.

    In model fitting, the presence of finite, fittable data with corresponding
    non-finite uncertainties can cause issues. Finite data values will be
    filtered out in this case which may be undesirable. This traitlet when
    True triggers a warning in the model fitting plugin (in Specviz only,
    currently) if there are any finite values with non-finite uncertainties.

    Note that if a the uncertainty array is FULLY non-finite and the data is
    FULLY finite, uncertainties will be set to None (in the Specviz parser),
    so this traitlet will be False in that case (and therefore no warning
    message displayed in the plugin).
    """

    non_finite_uncertainty_mismatch = Bool(False).tag(sync=True)

    # every time a data/subset selection is changed, check the data selection and
    # its uncertainties to see if there are any finite data elements with
    # uncertainties. Warn in plugin if this occurs.

    @observe("dataset_selected", "spectral_subset_selected")
    def _check_non_finite_uncertainty_mismatch(self, event={}):

        if not hasattr(self, 'dataset') or self.dataset_selected == '':
            # during initial init, this can trigger before the component is initialized
            return

        if not hasattr(self, '_get_1d_spectrum'):
            # only model_fitting has _get_1d_spectrum(), but this method is here
            # instead of there  because it may eventually be used by other plugins.
            # if that happens, move _get_1d_spectrum() somewhere more general
            raise NotImplementedError("_get_1d_spectrum() must be available in "
                                      "plugin to use NonFiniteUncertaintyMismatchMixin")

        spec = self._get_1d_spectrum()

        if spec.uncertainty is None:
            self.non_finite_uncertainty_mismatch = False
            return

        if self.spectral_subset_selected == "Entire Spectrum":
            flux = spec.flux
            uncert = spec.uncertainty
        else:
            # get selected subset
            spec = self._apply_subset_masks(self._get_1d_spectrum(), self.spectral_subset)
            flux = spec.flux[~spec.mask]
            uncert = spec.uncertainty[~spec.mask]

        uncert = uncert.array

        if not np.any(uncert):
            self.non_finite_uncertainty_mismatch = False
            return

        flux = flux.value

        mismatch = np.any(np.logical_and(~np.isfinite(uncert), np.isfinite(flux)))

        # np.any returns numpy bool type, which traitlets doesn't like
        # so cast to boolean
        self.non_finite_uncertainty_mismatch = bool(mismatch)


class ViewerSelect(SelectPluginComponent):
    """
    Plugin select for viewers, with support for single or multi-selection.

    Useful API methods/attributes:

    * :meth:`~SelectPluginComponent.choices`
    * ``selected``
    * :attr:`selected_id`
    * :attr:`selected_obj`
    * :meth:`~SelectPluginComponent.is_multiselect`
    * :meth:`~SelectPluginComponent.select_default`
    * :meth:`~SelectPluginComponent.select_all` (only if ``is_multiselect``)
    * :meth:`~SelectPluginComponent.select_none` (only if ``is_multiselect``)
    """

    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: id, reference, label)
    * ``selected`` (string)

    Properties (in the object only):

    * ``ids`` (list of ids corresponding to ``items``)
    * ``references`` (list of references corresponding to ``items``)
    * ``labels`` (list of references falling back on ids corresponding to ``items``.  These
        are the values seen in the dropdown, although setting either id or reference to the traitlet
        will still process correctly)
    * ``selected_item`` (dict of the currently selected entry in ``items``)
    * ``selected_id`` (string corresponding to the id of ``selected_item``)
    * ``selected_obj`` (viewer item corresponding to ``selected``)

    To use in a plugin:

    * create traitlets with default values
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component

    Example template (label and hint are optional)::

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        label="Viewer"
        hint="Select viewer."
      />

    """
    def __init__(self, plugin, items, selected,
                 multiselect=None,
                 default_text=None, manual_options=[], default_mode='first'):
        super().__init__(plugin, items=items, selected=selected,
                         multiselect=multiselect,
                         default_text=default_text, manual_options=manual_options,
                         default_mode=default_mode)

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRenamedMessage, handler=self._on_viewers_changed)

        # initialize viewer_items from original viewers
        self._on_viewers_changed()

    @property
    def ids(self):
        return [item['id'] for item in self.items]

    @property
    def references(self):
        return [item['reference'] for item in self.items]

    def _get_selected_item(self, selected):
        if selected in self.manual_options:
            return {}
        item = super()._get_selected_item(selected)
        if item:
            return item

        # try again but this time allow match to id alone.  Note that _selected_changed
        # will handle resetting the trait to the reference since it exists, but this
        # will allow access to the underlying item/object for any observes in the meantime.
        for item in self.items:
            if item['id'] == selected:
                return item

    @property
    def selected_id(self):
        return self.selected_item.get('id', None)

    @property
    def selected_reference(self):
        return self.selected_item.get('reference', None)

    def _get_selected_obj(self, selected, selected_id):
        if selected in self.manual_options or selected_id is None:
            return None
        return self.app.get_viewer_by_id(selected_id)

    @cached_property
    def selected_obj(self):
        if self.is_multiselect and len(self.selected):
            return [self._get_selected_obj(selected, selected_id)
                    for selected, selected_id in zip(self.selected, self.selected_id)]
        return self._get_selected_obj(self.selected, self.selected_id)

    def _selected_changed(self, event):
        self._clear_cache()
        if self.is_multiselect and isinstance(event['new'], list):
            new_selected = []
            for entry in event['new']:
                if entry in self.labels + self.manual_options:
                    new_selected.append(entry)
                elif entry in self.ids:
                    new_selected.append(self.labels[self.ids.index(entry)])
                else:
                    self.selected = event['old']
                    raise ValueError(f"could not map {entry} to valid choice, reverting selection to {event['old']}")  # noqa
            self.selected = new_selected
            return
        else:
            if event['new'] not in self.labels + self.manual_options:
                if self.selected in self.ids:
                    # provided id in place of ref
                    self.selected = self.labels[self.ids.index(self.selected)]
                    return
        return super()._selected_changed(event)

    def add_filter(self, *filters):
        super().add_filter(*filters)
        if 'reference_has_wcs' in filters:
            # reference data can change whenever data is added OR removed from a viewer
            self.hub.subscribe(self, AddDataMessage, handler=self._on_viewers_changed)
            self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewers_changed)

    def _is_valid_item(self, viewer):
        def is_spectrum_viewer(viewer):
            return 'ProfileView' in viewer.__class__.__name__

        def is_spectrum_2d_viewer(viewer):
            return 'Profile2DView' in viewer.__class__.__name__

        def is_image_viewer(viewer):
            return 'ImageView' in viewer.__class__.__name__

        def reference_has_wcs(viewer):
            return getattr(viewer.state.reference_data, 'coords', None) is not None

        return super()._is_valid_item(viewer, locals())

    @observe('filters')
    def _on_viewers_changed(self, msg=None):
        # NOTE: _on_viewers_changed is passed without a msg object during init
        # list of dictionaries with id, ref, ref_or_id
        was_empty = len(self.items) == 0
        manual_items = [{'label': label} for label in self.manual_options]
        self.items = manual_items + [{k: v for k, v in vd.items() if k != 'viewer'}
                                     for vd in self.viewer_dicts if self._is_valid_item(vd['viewer'])] # noqa
        self._apply_default_selection(skip_if_current_valid=not was_empty)


class ViewerSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the ViewerSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``ViewerSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.viewer``.

    Example template (label and hint are optional)::

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        label="Viewer"
        hint="Select viewer."
      />

    """
    viewer_items = List().tag(sync=True)
    viewer_selected = Any().tag(sync=True)
    viewer_multiselect = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected', 'viewer_multiselect')


class DatasetSelect(SelectPluginComponent):
    """
    Plugin select for data entries, with support for single or multi-selection.

    Useful API methods/attributes:

    * :meth:`~SelectPluginComponent.choices`
    * ``selected``
    * :attr:`selected_obj`
    * :attr:`selected_dc_item`
    * :meth:`~SelectPluginComponent.is_multiselect`
    * :meth:`~SelectPluginComponent.select_default`
    * :meth:`~SelectPluginComponent.select_all` (only if ``is_multiselect``)
    * :meth:`~SelectPluginComponent.select_none` (only if ``is_multiselect``)
    """

    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: label)
    * ``selected`` (string)

    Properties (in the object only):

    * ``selected_obj``
    * ``selected_dc_item``

    Methods (in the object only):

    * ``get_object``
    * ``add_filter`` (more useful for the mixin, when creating a custom component, pass ``filters``)

    To use in a plugin:

    * create traitlets with default values
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component

    Example template (label and hint are optional)::

      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        label="Data"
        hint="Select data."
      />

    """
    def __init__(self, plugin, items, selected,
                 multiselect=None,
                 filters=['not_from_plugin_model_fitting', 'layer_in_viewers'],
                 default_text=None, manual_options=[],
                 default_mode='first'):
        """
        Parameters
        ----------
        plugin
            the parent plugin object
        items : str
            the name of the items traitlet defined in ``plugin``
        selected : str
            the name of the selected traitlet defined in ``plugin``
        multiselect : str
            the name of the traitlet defining whether the dropdown should accept multiple selections
        filters : list
            list of strings (for built-in filters) or callables to filter to only valid options.
        default_text : str or None
            the text to show for no selection.  If not provided or None, no entry will be provided
            in the dropdown for no selection.
        manual_options: list
            list of options to provide that are not automatically populated by datasets.  If
            ``default`` text is provided but not in ``manual_options`` it will still be included as
            the first item in the list.
        """
        super().__init__(plugin, items=items, selected=selected,
                         multiselect=multiselect, filters=filters,
                         default_text=default_text, manual_options=manual_options,
                         default_mode=default_mode)
        self._cached_properties += ["selected_dc_item"]
        # Add/Remove Data are triggered when checked/unchecked from viewers
        self.hub.subscribe(self, AddDataMessage, handler=self._on_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_data_changed)
        self.hub.subscribe(self, DataCollectionAddMessage, handler=self._on_data_changed)
        self.hub.subscribe(self, DataCollectionDeleteMessage, handler=self._on_data_changed)

        self.app.state.add_callback('layer_icons', lambda _: self._on_data_changed())
        # initialize items from original viewers
        self._on_data_changed()

    def _cubeviz_include_spatial_subsets(self):
        """
        Call this method to prepend spatial subsets to the list of datasets (and listen for newly
        created spatial subsets).  For a single viewer, consider using LayerSelect instead.
        """
        if self.app.config != 'cubeviz':
            return

        # add additional callback for subsets
        # We have to use SubsetUpdateMessage instead of SubsetCreateMessage to ensure it has already
        # been added to data_collection.subset_groups.  To avoid extra calls to _on_data_changed
        # for changes in style, etc, we'll try to filter out extra messages in advance.
        def _subset_update(msg):
            if msg.attribute == 'subset_state':
                if get_subset_type(msg.subset) == 'spatial':
                    self._on_data_changed()

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=_subset_update)
        self._include_spatial_subsets = True

    @property
    def default_data_cls(self):
        if self.app.config == 'imviz':
            return NDData
        if 'is_trace' in self.filters:
            return None
        return Spectrum1D

    def _get_dc_item(self, selected):
        if selected not in self.labels:
            # _apply_default_selection will override shortly anyways
            return None
        return next((x for x in self.app.data_collection if x.label == selected))

    @cached_property
    def selected_dc_item(self):
        if self.is_multiselect:
            return [self._get_dc_item(selected) for selected in self.selected]
        return self._get_dc_item(self.selected)

    def get_object(self, *args, **kwargs):
        if self.is_multiselect:
            return [dc_item.get_object(*args, **kwargs) for dc_item in self.selected_dc_item]

        if self.selected not in self.labels:
            # _apply_default_selection will override shortly anyways
            return None
        return self.selected_dc_item.get_object(*args, **kwargs)

    @cached_property
    def selected_obj(self):
        if not self.is_multiselect:
            if self.selected not in self.labels:
                # _apply_default_selection will override shortly anyways
                return None
            match = self.app._jdaviz_helper.get_data(data_label=self.selected)
            if match is not None:
                return match
        # handle the case of empty Application with no viewer, we'll just pull directly
        # from the data collection
        return self.get_object(cls=self.default_data_cls)

    def selected_spectrum_for_spatial_subset(self,
                                             spatial_subset=SPATIAL_DEFAULT_TEXT,
                                             use_display_units=True):
        if spatial_subset == SPATIAL_DEFAULT_TEXT:
            spatial_subset = None
        return self.plugin._specviz_helper.get_data(data_label=self.selected,
                                                    spatial_subset=spatial_subset,
                                                    use_display_units=use_display_units)

    def _is_valid_item(self, data):
        def not_from_plugin(data):
            return data.meta.get('Plugin', None) is None

        def not_from_this_plugin(data):
            return data.meta.get('Plugin', None) != self.plugin.__class__.__name__

        def not_from_plugin_model_fitting(data):
            return data.meta.get('Plugin', None) != 'ModelFitting'

        def has_metadata(data):
            return hasattr(data, 'meta') and isinstance(data.meta, dict) and len(data.meta)

        def layer_in_viewers(data):
            if not len(self.app.get_viewer_reference_names()):
                # then this is a bar Application object, so ignore this filter
                return True
            for viewer in self.viewers:
                if data.label in [l.layer.label for l in viewer.layers]: # noqa E741
                    return True
            return False

        def layer_in_spectrum_viewer(data):
            if not len(self.app.get_viewer_reference_names()):
                # then this is a bare Application object, so ignore this filter
                return True
            return data.label in [l.layer.label for l in self.spectrum_viewer.layers]  # noqa E741

        def layer_in_spectrum_2d_viewer(data):
            if not len(self.app.get_viewer_reference_names()):
                # then this is a bare Application object, so ignore this filter
                return True
            return data.label in [l.layer.label for l in self.spectrum_2d_viewer.layers]  # noqa E741

        def is_trace(data):
            return hasattr(data, 'meta') and 'Trace' in data.meta

        def not_trace(data):
            return not is_trace(data)

        def is_image(data):
            return len(data.shape) == 2

        def is_cube(data):
            return len(data.shape) == 3

        return super()._is_valid_item(data, locals())

    @observe('filters')
    def _on_data_changed(self, msg=None):
        # NOTE: _on_data_changed is passed without a msg object during init
        # future improvement: don't recreate the entire list when msg is passed
        def _dc_to_dict(data):
            d = {'label': data.label,
                 'icon': self.app.state.layer_icons.get(data.label)}

            return d

        manual_items = [{'label': label} for label in self.manual_options]
        self.items = manual_items + [_dc_to_dict(data) for data in self.app.data_collection
                                     if self._is_valid_item(data)]
        if getattr(self, '_include_spatial_subsets', False):
            # allow for spatial subsets to be listed
            self.items = self.items + [_dc_to_dict(subset) for subset in self.app.data_collection.subset_groups  # noqa
                                       if get_subset_type(subset) == 'spatial']
        self._apply_default_selection()
        # future improvement: only clear cache if the selected data entry was changed?
        self._clear_cache(*self._cached_properties)


class DatasetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the DatasetSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``DatasetSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.dataset``.

    Example template (label and hint are optional)::

      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        label="Data"
        hint="Select data."
      />

    """
    dataset_items = List().tag(sync=True)
    dataset_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: cannot be named self.data or will conflict with existing self.data traitlet!
        self.dataset = DatasetSelect(self, 'dataset_items', 'dataset_selected',
                                     multiselect=None)


class DatasetMultiSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the DatasetSelect component as a mixin in the base plugin with togglable multiselect.
    This automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``DatasetMultiSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.dataset``.

    Example template (label and hint are optional)::

      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        :multiselect="multiselect"
        label="Data"
        hint="Select data."
      />

    """
    dataset_items = List().tag(sync=True)
    dataset_selected = Any().tag(sync=True)
    multiselect = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: cannot be named self.data or will conflict with existing self.data traitlet!
        self.dataset = DatasetSelect(self, 'dataset_items', 'dataset_selected',
                                     multiselect='multiselect')  # noqa


class AutoTextField(BasePluginComponent):
    """
    Label component with the ability to synchronize to a plugin-provided default value or override
    with a custom value.  Setting ``value`` will set ``auto`` to False.  Setting ``auto`` to True,
    will set ``value`` to the default value.

    Useful API methods/attributes:

    * ``value``
    * ``auto``
    """

    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``value`` (string: user-provided label for the results data-entry.  If ``auto``, changes
        to ``default`` will update ``value``.  Otherwise, changes to ``value`` will set
        ``auto`` to False.)
    * ``default`` (string: plugin-determined default label that will be synced to ``value``
        if/when ``auto`` is set to True)
    * ``auto`` (bool: whether to sync ``default`` to ``value``)
    * ``invalid_msg`` (string: validation string for the current value of ``value``.)

    Example template::

      <plugin-auto-label
        :value.sync="value"
        :default="comp_label_default"
        :auto.sync="comp_label_auto"
        :invalid_msg="invalid_msg"
        hint="Label hint."
      ></plugin-auto-label>

    """
    def __init__(self, plugin, value, default, auto,
                 invalid_msg):
        super().__init__(plugin, value=value,
                         default=default, auto=auto,
                         invalid_msg=invalid_msg)

        self.add_observe(default, self._on_set_to_default)
        self.add_observe(auto, self._on_set_to_default)

    def __repr__(self):
        return f"<AutoTextField label='{self.value}' auto={self.auto}>"

    def __eq__(self, other):
        return self.value == other

    def __hash__(self):
        # defining __eq__ without defining __hash__ makes the object unhashable
        return super().__hash__()

    def _on_set_to_default(self, msg={}):
        if self.auto:
            self.value = self.default


class AutoTextFieldMixin(VuetifyTemplate, HubListener):
    """
    Applies the AutoTextField component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``AutoTextFieldMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.auto_label``.

    Example template::

      <plugin-auto-label
        :value.sync="label"
        :default="label_default"
        :auto.sync="label_auto"
        :invalid_msg="invalid_msg"
        hint="Label hint."
      ></plugin-auto-label>
    """
    label = Unicode().tag(sync=True)
    label_default = Unicode().tag(sync=True)
    label_auto = Bool(True).tag(sync=True)
    label_invalid_msg = Unicode('').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_label = AutoTextField(self, 'label',
                                        'label_default', 'label_auto',
                                        'label_invalid_msg')


class AddResults(BasePluginComponent):
    """
    Plugin component for providing a data-label and selecting a viewer to add the results from
    the plugin.

    Useful API methods/attributes:

    * :attr:`label` (`AutoTextField`):
        the label component.  Setting will redirect to setting ``label.value``.
    * :attr:`auto`
        shortcut to ``label.auto``.  Setting will redirect to setting ``label.auto``.
    * ``viewer`` (`ViewerSelect`):
        the viewer to add the results, or None to add the results to the data-collection but
        not load into a viewer.
    """

    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``label`` (string: user-provided label for the results data-entry.  If ``label_auto``, changes
        to ``label_default`` will update ``label``.  Otherwise, changes to ``label`` will set
        ``label_auto`` to False.)
    * ``label_default`` (string: plugin-determined default label that will be synced to ``label``
        if/when ``label_auto`` is set to True)
    * ``label_auto`` (bool: whether to sync ``label_default`` to ``label``)
    * ``label_invalid_msg`` (string: validation string for the current value of ``label``.  If
        not an empty string, calls to ``add_results_from_plugin`` will raise an error.)
    * ``label_overwrite`` (bool: whether the value of ``label`` already exists for a data-entry
        from the same plugin)
    * ``add_to_viewer_items`` (list of dicts: see ``ViewerSelect``)
    * ``add_to_viewer_selected`` (string: name of the viewer to add the results,
        see ``ViewerSelect``)


    Methods:

    * ``add_results_from_plugin``


    Example template::

      <plugin-add-results
        :label.sync="results_label"
        :label_default="results_label_default"
        :label_auto.sync="results_label_auto"
        :label_invalid_msg="results_label_invalid_msg"
        :label_overwrite="results_label_overwrite"
        label_hint="Label for the smoothed data"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
        action_label="Apply"
        action_tooltip="Apply the action to the data"
        @click:action="apply"
      ></plugin-add-results>

    """
    def __init__(self, plugin, label, label_default, label_auto,
                 label_invalid_msg, label_overwrite,
                 add_to_viewer_items, add_to_viewer_selected,
                 label_whitelist_overwrite=[]):
        super().__init__(plugin, label=label,
                         label_default=label_default, label_auto=label_auto,
                         label_invalid_msg=label_invalid_msg, label_overwrite=label_overwrite,
                         add_to_viewer_items=add_to_viewer_items,
                         add_to_viewer_selected=add_to_viewer_selected)

        # DataCollectionAdd/Delete are fired even if remain unchecked in all viewers
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=lambda _: self._on_label_changed())
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=lambda _: self._on_label_changed())

        # allows overwriting specific data entries not from the same plugin
        self.label_whitelist_overwrite = label_whitelist_overwrite

        self.viewer = ViewerSelect(plugin, add_to_viewer_items, add_to_viewer_selected,
                                   manual_options=['None'],
                                   default_mode=self._handle_default_viewer_selected)

        self.auto_label = AutoTextField(plugin, label, label_default, label_auto, label_invalid_msg)
        self.auto = self.auto_label.auto
        self.add_observe(label, self._on_label_changed)

    def __repr__(self):
        return f"<AddResults label='{self.label}', auto={self.auto}, viewer={self.viewer.selected}>"

    @property
    def user_api(self):
        return UserApiWrapper(self, ('label', 'auto', 'viewer'))

    @property
    def label(self):
        """
        Access the value of the ``AutoTextField`` object.  Changing the value manually will also
        disable the ``auto`` option.
        """
        return self.auto_label.value

    @label.setter
    def label(self, label):
        self.auto_label.value = label

    @property
    def auto(self):
        """
        Access the ``auto`` property of the ``AutoTextField`` object.  If enabling, the ``label``
        will automatically be changed and kept in sync with the default label.
        """
        return self.auto_label.auto

    @auto.setter
    def auto(self, auto):
        self.auto_label.auto = auto

    def _handle_default_viewer_selected(self, viewer_comp, is_valid):
        if len(viewer_comp.items) == 2:
            # then we're a switch, so we want to default to ON
            return viewer_comp.labels[1]
        else:
            # then we're a dropdown, so want to default to None and force the user to choose
            return 'None'

    def _on_label_changed(self, msg={}):
        if not len(self.label.strip()):
            # strip will raise the same error for a label of all spaces
            self.label_invalid_msg = 'label must be provided'
            return

        for data in self.app.data_collection:
            if self.label == data.label:
                if data.meta.get('Plugin', None) == self._plugin.__class__.__name__ or\
                        data.label in self.label_whitelist_overwrite:
                    self.label_invalid_msg = ''
                    self.label_overwrite = True
                    return
                else:
                    self.label_invalid_msg = 'label already in use'
                    self.label_overwrite = False
                    return

        self.label_invalid_msg = ''
        self.label_overwrite = False

    def add_results_from_plugin(self, data_item, replace=None, label=None):
        """
        Add ``data_item`` to the app's data_collection according to the default or user-provided
        label and adds to any requested viewers.
        """

        # Note that we can only preserve one of percentile or vmin+vmax
        ignore_attributes = ("layer", "attribute", "percentile")

        if self.label_invalid_msg:
            raise ValueError(self.label_invalid_msg)

        if label is None:
            label = self.label

        if self.label_overwrite:
            # the switch for add_to_viewer is hidden, and so the loaded state of the overwritten
            # entry should be the same as the original entry (to avoid deleting reference data)
            add_to_viewer_refs = []
            add_to_viewer_vis = []
            preserved_attributes = []
            for viewer_select_item in self.add_to_viewer_items[1:]:
                # index 0 is for "None"
                viewer_ref = viewer_select_item['reference']
                viewer_item = self.app._viewer_item_by_reference(viewer_ref)
                viewer = self.app.get_viewer(viewer_ref)
                for layer in viewer.layers:
                    if layer.layer.label != label:
                        continue
                    else:
                        add_to_viewer_refs.append(viewer_ref)
                        add_to_viewer_vis.append(label in viewer_item['visible_layers'])
                        preserve_these = {}
                        for att in layer.state.as_dict():
                            # Can't set cmap_att, size_att, etc
                            if att not in ignore_attributes and "_att" not in att:
                                preserve_these[att] = getattr(layer.state, att)
                        preserved_attributes.append(preserve_these)
        else:
            if self.add_to_viewer_selected == 'None':
                add_to_viewer_refs = []
                add_to_viewer_vis = []
                preserved_attributes = []
            else:
                add_to_viewer_refs = [self.add_to_viewer_selected]
                add_to_viewer_vis = [True]
                preserved_attributes = [{}]

        if label in self.app.data_collection:
            for viewer_ref in add_to_viewer_refs:
                self.app.remove_data_from_viewer(viewer_ref, label)
            self.app.data_collection.remove(self.app.data_collection[label])

        if not hasattr(data_item, 'meta'):
            data_item.meta = {}
        data_item.meta['Plugin'] = self._plugin.__class__.__name__
        if self.app.config == 'mosviz':
            data_item.meta['mosviz_row'] = self.app.state.settings['mosviz_row']
        self.app.add_data(data_item, label)

        for viewer_ref, visible, preserved in zip(add_to_viewer_refs, add_to_viewer_vis,
                                                  preserved_attributes):
            # replace the contents in the selected viewer with the results from this plugin
            this_viewer = self.app.get_viewer(viewer_ref)
            if replace is not None:
                this_replace = replace
            else:
                this_replace = isinstance(this_viewer, BqplotImageView)

            self.app.add_data_to_viewer(viewer_ref,
                                        label,
                                        visible=visible, clear_other_data=this_replace)

            if preserved != {}:
                layer_state = [layer.state for layer in this_viewer.layers if
                               layer.layer.label == label][0]
                for att in preserved:
                    setattr(layer_state, att, preserved[att])

        # update overwrite warnings, etc
        self._on_label_changed()


class AddResultsMixin(VuetifyTemplate, HubListener):
    """
    Applies the AddResults component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``AddResultsMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.add_results``.

    Example template::

      <plugin-add-results
        :label.sync="results_label"
        :label_default="results_label_default"
        :label_auto.sync="results_label_auto"
        :label_invalid_msg="results_label_invalid_msg"
        :label_overwrite="results_label_overwrite"
        label_hint="Label for the smoothed data"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
        action_label="Apply"
        action_tooltip="Apply the action to the data"
        @click:action="apply"
      ></plugin-add-results>

    """
    results_label = Unicode().tag(sync=True)
    results_label_default = Unicode().tag(sync=True)
    results_label_auto = Bool(True).tag(sync=True)
    results_label_invalid_msg = Unicode('').tag(sync=True)
    results_label_overwrite = Bool().tag(sync=True)

    add_to_viewer_items = List().tag(sync=True)
    add_to_viewer_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_results = AddResults(self, 'results_label',
                                      'results_label_default', 'results_label_auto',
                                      'results_label_invalid_msg', 'results_label_overwrite',
                                      'add_to_viewer_items', 'add_to_viewer_selected')


class PlotOptionsSyncState(BasePluginComponent):
    """
    Plugin component for syncing with glue state objects.

    Useful API methods/attributes:

    * ``value``: the currently set value sent to the underlying ``linked_states`` objects in glue
    * ``text``: the user-friendly equivalent of the currently set value (only when has ``choices``)
    * :meth:`choices` (only when applicable)
    * :attr:`linked_states`
    * :meth:`unmix_state`
    """
    def __init__(self, plugin, viewer_select, layer_select, glue_name,
                 value, sync, spinner=None, state_filter=None):
        super().__init__(plugin, value=value, sync=sync)
        self._state_filter = state_filter
        self._linked_states = []
        self._spinner = spinner
        self._processing_change_from_glue = False
        self._processing_change_to_glue = False
        self._cached_properties = ["subscribed_states", "subscribed_icons"]

        self._viewer_select = viewer_select
        self._layer_select = layer_select
        self._glue_name = glue_name
        self.add_observe(viewer_select._plugin_traitlets['selected'], self._on_viewer_layer_changed)
        self.add_observe(layer_select._plugin_traitlets['selected'], self._on_viewer_layer_changed)
        self.add_observe(value, self._on_value_changed)
        self._on_viewer_layer_changed()

    def __repr__(self):
        choices = self.choices
        glue_name = self._glue_name if isinstance(self._glue_name, str) else ''
        if len(choices):
            return f"<PlotOptionsSyncState {glue_name}={self.value} choices={self.choices} (linked_states: {len(self.linked_states)}/{len(self.subscribed_states)})>"  # noqa
        return f"<PlotOptionsSyncState {glue_name}={self.value} (linked_states: {len(self.linked_states)}/{len(self.subscribed_states)})>"  # noqa

    @property
    def user_api(self):
        expose = ['value', 'unmix_state', 'linked_states']
        if len(self.choices):
            expose += ['choices', 'text']
        return UserApiWrapper(self, expose=expose)

    def __eq__(self, other):
        return self.value == other or (len(self.choices) and self.text == other)

    def __hash__(self):
        # defining __eq__ without defining __hash__ makes the object unhashable
        return super().__hash__()

    @property
    def text(self):
        """
        The user-friendly text equivalent of the currently set value
        """
        value = self.value
        for choice in self.sync.get('choices', {}):
            if choice['value'] == value:
                return choice['text']

    @property
    def choices(self):
        return [choice['text'] for choice in self.sync.get('choices', {})]

    def state_filter(self, state):
        if self._state_filter is None:
            return True
        return self._state_filter(state)

    def glue_name(self, state):
        if isinstance(self._glue_name, str):
            return self._glue_name
        # also support a callable that takes the state as input and returns a string
        return self._glue_name(state)

    @property
    def subscribed_viewers(self):
        viewers = self._viewer_select.selected_obj
        if not isinstance(viewers, list):
            # which is the case for single-select
            viewers = [viewers]
        return viewers

    @cached_property
    def subscribed_states(self):
        # states object that according to the viewer selection, we *should*
        # link if this entry is found there
        viewers = self.subscribed_viewers

        def _state_item(item):
            if isinstance(item, list):
                return [_state_item(item_i) for item_i in item]
            elif item is None:
                return None
            else:
                return item.state

        viewer_states = [_state_item(viewer) for viewer in viewers]

        layer_labels = self._layer_select.selected
        if not isinstance(layer_labels, list):
            layer_labels = [layer_labels]

        # NOTE: accessing from self._layer_select.selected_obj would give us a per-viewer
        # list, but we need a per-selected-layer list.
        layer_states = []
        for selected_layer_label in layer_labels:
            layer_states.append([])
            for viewer in viewers:
                if viewer is None:
                    continue
                for layer in viewer.layers:
                    if layer.layer.label == selected_layer_label:
                        layer_states[-1].append(layer.state)

        # subscribed states can still be nested list
        return viewer_states + layer_states

    @cached_property
    def subscribed_icons(self):
        # dictionary items giving information about the entries in subscribed_states
        viewer_icons = self._viewer_select.selected_item.get('icon', [])
        if not isinstance(viewer_icons, list):
            viewer_icons = [viewer_icons]

        layer_icons = self._layer_select.selected_item.get('icon', [])
        if not isinstance(layer_icons, list):
            layer_icons = [layer_icons]

        return viewer_icons + layer_icons

    @property
    def linked_states(self):
        # access glue state objects for which the callbacks are currently connected
        return self._linked_states

    def _get_glue_value(self, state):
        glue_name = self.glue_name(state)
        if glue_name == 'cmap':
            return getattr(state, glue_name).name
        if glue_name in GLUE_STATES_WITH_HELPERS:
            return str(getattr(state, glue_name))
        if glue_name == 'color':
            # Set to lower() so that all linked states of a subset
            # (data in viewer with this subset applied) have matching color values
            return str(getattr(state, glue_name)).lower()
        if glue_name in ('contour_visible', 'bitmap_visible'):
            # return False if the layer itself is not visible.  Setting this object
            # to True will then set both glue_name and visible to True.
            return getattr(state, glue_name) and getattr(state, 'visible')

        return getattr(state, glue_name)

    def _get_glue_choices(self, state):
        glue_name = self.glue_name(state)
        if glue_name == 'cmap':
            return [{'text': cmap[0], 'value': cmap[1].name} for cmap in colormaps.members]
        if glue_name in GLUE_STATES_WITH_HELPERS:
            helper = getattr(state, f'{glue_name}_helper')
            return [{'text': str(choice), 'value': str(choice)} for choice in helper.choices]
        if glue_name == 'color_mode':
            return [{'text': 'Colormap', 'value': 'Colormaps'},
                    {'text': 'Monochromatic', 'value': 'One color per layer'}]

        values, labels = _get_glue_choices(state, glue_name)
        return [{'text': l, 'value': v} for v, l in zip(values, labels)]

    def _on_viewer_layer_changed(self, msg=None):
        self._clear_cache(*self._cached_properties)

        # clear existing callbacks - we'll re-create those we need later
        for state in self.linked_states:
            glue_name = self.glue_name(state)
            state.remove_callback(glue_name, self._on_glue_value_changed)
            if glue_name in ['contour_visible', 'bitmap_visible']:
                state.remove_callback('visible', self._on_glue_layer_visible_changed)

        in_subscribed_states = False
        icons = []
        current_glue_values = []
        self._linked_states = []
        for states, icon in zip(self.subscribed_states, self.subscribed_icons):
            if not isinstance(states, list):
                states = [states]

            for state in states:
                if state is None or not self.state_filter(state):
                    continue
                glue_name = self.glue_name(state)
                if glue_name is None or not hasattr(state, glue_name):
                    continue

                in_subscribed_states = True
                if icon not in icons:
                    icons.append(icon)
                current_glue_values.append(self._get_glue_value(state))
                self._linked_states.append(state)  # these will be iterated when value is set
                state.add_callback(glue_name, self._on_glue_value_changed)
                if glue_name in ['contour_visible', 'bitmap_visible']:
                    state.add_callback('visible', self._on_glue_layer_visible_changed)

                if (
                    # We are assuming here that each state-instance with this same name
                    # will have the same choices and that those will not change. If we
                    # ever hookup options with changing choices, we'll need additional
                    # logic to sync to those and handle mixed state in the choices...
                    self.sync.get('choices') is None and
                    (
                        hasattr(getattr(type(state), glue_name), 'get_display_func') or
                        glue_name == 'cmap'
                    )
                ) or (
                    # update choices in `sync` if glue state choices are updated
                    # during glue Component add/rename/delete:
                    glue_name == 'cmap_att'
                ):
                    # then we can access and populate/update the choices.
                    self.sync = {**self.sync, 'choices': self._get_glue_choices(state)}
        self.sync = {**self.sync,
                     'in_subscribed_states': in_subscribed_states,
                     'icons': icons,
                     'mixed': len(np.unique(current_glue_values, axis=0)) > 1}

        if len(current_glue_values):
            # sync the initial value of the widget, avoiding recursion
            self._on_glue_value_changed(current_glue_values[0])

    def _update_mixed_state(self):
        if len(self.linked_states) <= 1:
            mixed = False
        else:
            current_glue_values = []
            for state in self.linked_states:
                current_glue_values.append(self._get_glue_value(state))
                mixed = len(np.unique(current_glue_values, axis=0)) > 1
        self.sync = {**self.sync,
                     'mixed': mixed}

    def _on_value_changed(self, msg):
        if self._processing_change_from_glue:
            return

        if self._spinner is not None:
            setattr(self.plugin, self._spinner, True)

        self._processing_change_to_glue = True
        for glue_state in self.linked_states:
            glue_name = self.glue_name(glue_state)
            if glue_name == 'cmap':
                cmap = None
                for member in colormaps.members:
                    if member[1].name == msg['new']:
                        cmap = member[1]
                        break
                setattr(glue_state, glue_name, cmap)
            elif glue_name in GLUE_STATES_WITH_HELPERS:
                helper = getattr(glue_state, f'{glue_name}_helper')
                value = [choice for choice in helper.choices if str(choice) == msg['new']][0]
                setattr(glue_state, glue_name, value)
            else:
                setattr(glue_state, glue_name, msg['new'])

            if glue_name in ['bitmap_visible', 'contour_visible'] and msg['new'] is True:
                # ensure that the layer is also visible
                if not glue_state.visible:
                    setattr(glue_state, 'visible', msg['new'])

        # need to recompute mixed state
        self._update_mixed_state()
        self._processing_change_to_glue = False

        if self._spinner is not None:
            setattr(self.plugin, self._spinner, False)

    def _on_glue_layer_visible_changed(self, value):
        # this is only triggered for glue_name contour_visible or bitmap_visible
        self._processing_change_from_glue = True
        if value is False:
            self.value = False
        elif len(self.linked_states):
            # then this is a little tricky since we don't have the calling state object,
            # instead we'll set the value based on the first state object and will still
            # make a call to update the mixed state
            self.value = self._get_glue_value(self.linked_states[0])
        self._processing_change_from_glue = False
        self._update_mixed_state()

    def _on_glue_value_changed(self, value):
        if self._glue_name == 'color_mode':
            # then we need to force updates to the layer-icon colors
            # NOTE: this will only trigger when the change to color_mode was handled
            # through this plugin.  Manual changes to the glue state for viewers not
            # currently in subscribed states will be ignored.
            for viewer in self.subscribed_viewers:
                viewer._update_layer_icons()
            # callbacks from the viewer state also do not trigger an update to the
            # layer items (tabs), so we'll force those to update from here as well.
            self.plugin.layer._update_layer_items()

        if self._processing_change_to_glue:
            return

        self._processing_change_from_glue = True
        if "Colormap" in value.__class__.__name__:
            value = value.name
        elif self._glue_name in GLUE_STATES_WITH_HELPERS:
            value = str(value)
        elif isinstance(self.value, (int, float)) and self._glue_name != 'percentile':
            # glue might pass us ints for float or vice versa, but our traitlets care
            # so let's cast to the type expected by the traitlet to avoid having to
            # use Any traitlets for all of these.  We skip percentile as that needs
            # to be an Any traitlet in order to handle "Custom"
            value = type(self.value)(value)
        self.value = value
        # need to recompute mixed state
        self._update_mixed_state()
        self._processing_change_from_glue = False

    def unmix_state(self, new_value=None):
        if new_value is None:
            new_value = self.value
        self._on_value_changed({'new': new_value})
        self.sync = {**self.sync,
                     'mixed': False}


# SUBCOMPONENTS (will not have top-level plugin traitlets but can be rendered on their own in
# popout windows or in the app)

class PluginSubcomponent(VuetifyTemplate):
    popout_button = Any().tag(sync=True, **widget_serialization)

    def __init__(self, plugin, component_type='table', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plugin = plugin
        self._component_type = component_type
        self.popout_button = PopoutButton(self, window_features='popup,width=800,height=300')

    @property
    def display_name(self):
        return f'{self._plugin._plugin_name}: {self._component_type}'

    def vue_popout(self, data=None):
        self.show(loc='popout')

    def show(self, loc="inline", title=None):  # pragma: no cover
        """Display the component UI.

        Parameters
        ----------
        loc : str
            The display location determines where to present the viz app.
            Supported locations:

            "inline": Display the component inline in a notebook.

            "app": Display below the viewers in the main app.

            "sidecar": Display the component in a separate JupyterLab window from the
            notebook, the location of which is decided by the 'anchor.' right is the default

                Other anchors:

                * ``sidecar:right`` (The default, opens a tab to the right of display)
                * ``sidecar:tab-before`` (Full-width tab before the current notebook)
                * ``sidecar:tab-after`` (Full-width tab after the current notebook)
                * ``sidecar:split-right`` (Split-tab in the same window right of the notebook)
                * ``sidecar:split-left`` (Split-tab in the same window left of the notebook)
                * ``sidecar:split-top`` (Split-tab in the same window above the notebook)
                * ``sidecar:split-bottom`` (Split-tab in the same window below the notebook)

                See `jupyterlab-sidecar <https://github.com/jupyter-widgets/jupyterlab-sidecar>`_
                for the most up-to-date options.

            "popout": Display the component in a detached display. By default, a new
            window will open. Browser popup permissions required.

                Other anchors:

                * ``popout:window`` (The default, opens Jdaviz in a new, detached popout)
                * ``popout:tab`` (Opens Jdaviz in a new, detached tab in your browser)

        title : str, optional
            The title of the sidecar tab.  Defaults to the name of the component.

            NOTE: Only applicable to a "sidecar" display.

        Notes
        -----
        If "sidecar" is requested in the "classic" Jupyter notebook, the component will appear
        inline, as only JupyterLab has a mechanism to have multiple tabs.
        """
        title = title if title is not None else self.display_name
        show_widget(self, loc=loc, title=title)


class Table(PluginSubcomponent):
    """
    Table subcomponent.  For most cases where a plugin only requires a single table, use the mixin
    instead.

    To use in a plugin, define ``plugin.table = Table(plugin)``, create a ``table_widget`` Unicode
    traitlet, and set ``plugin.table_widget = 'IPY_MODEL_'+self.table.model_id``.

    To render in the plugin's vue file::

      <jupyter-widget :widget="table_widget"></jupyter-widget>

    """
    template_file = __file__, "../components/plugin_table.vue"

    _default_values_by_colname = {}

    headers_visible = List([]).tag(sync=True)  # list of strings
    headers_avail = List([]).tag(sync=True)   # list of strings
    items = List().tag(sync=True)  # list of dictionaries, pass single dict to add_row

    def __init__(self, plugin, *args, **kwargs):
        self._qtable = None
        super().__init__(plugin, 'Table', *args, **kwargs)

    def default_value_for_column(self, colname=None, value=None):
        if colname in self._default_values_by_colname:
            return self._default_values_by_colname.get(colname)
        if isinstance(value, (tuple, list)):
            return [self.default_value_for_column(value=v) for v in value]
        if isinstance(value, (float, int)):
            return np.nan
        if isinstance(value, str):
            return ''
        return None

    @staticmethod
    def _new_col_visible(colname):
        return True

    def add_item(self, item):
        """
        Add an item/row to the table.

        Parameters
        ----------
        item : QTable, QTableRow, or dictionary of row-name, value pairs
        """
        def json_safe(column, item):
            def float_precision(column, item):
                if column in ('slice', 'index'):
                    # stored in astropy table as a float so we can also store nans,
                    # but should display in the UI without any decimals
                    return f"{item:.0f}"
                elif column in ('pixel', ):
                    return f"{item:0.3f}"
                elif column in ('xcenter', 'ycenter'):
                    return f"{item:0.1f}"
                elif column in ('sum', ):
                    return f"{item:.3e}"
                else:
                    return f"{item:0.5f}"

            if isinstance(item, SkyCoord):
                return item.to_string('hmsdms', precision=4)
            if isinstance(item, u.Quantity) and not np.isnan(item):
                return f"{float_precision(column, item.value)} {item.unit.to_string()}"

            if hasattr(item, 'to_string'):
                return item.to_string()
            if isinstance(item, float) and np.isnan(item):
                return ''
            if isinstance(item, tuple) and np.all([np.isnan(i) for i in item]):
                return ''

            if isinstance(item, float):
                return float_precision(column, item)
            elif isinstance(item, (list, tuple)):
                return [float_precision(column, i) if isinstance(i, float) else i for i in item]

            return item

        if isinstance(item, QTable):
            for row in item:
                self.add_item(row)
            return
        if isinstance(item, QTableRow):
            # Row does not have .items() implemented
            item = {k: v for k, v in zip(item.keys(), item.values())}

        # save original sent values to the cached QTable object
        if self._qtable is None:
            self._qtable = QTable([item])
        else:
            # add any missing columns with a default value for all previous rows
            for colname, value in item.items():
                if colname in self._qtable.colnames:
                    continue
                default_value = self.default_value_for_column(colname=colname,
                                                              value=value)
                self._qtable.add_column(default_value, name=colname)

            self._qtable.add_row(item)

        missing_headers = [k for k in item.keys() if k not in self.headers_avail]
        if len(missing_headers):
            self.headers_avail = self.headers_avail + missing_headers
            self.headers_visible = self.headers_visible + [m for m in missing_headers if self._new_col_visible(m)]  # noqa

        # clean data to show in the UI
        self.items = self.items + [{k: json_safe(k, v) for k, v in item.items()}]

    def __len__(self):
        return len(self.items)

    def clear_table(self):
        """
        Clear all entries/markers from the current table.
        """
        self.items = []
        self._qtable = None

    def vue_clear_table(self, data=None):
        # if the plugin (or via the TableMixin) has its own clear_table implementation,
        # call that, otherwise call the one defined here
        getattr(self._plugin, 'clear_table', self.clear_table)()

    def export_table(self):
        """
        Export the QTable representation of the table.
        """
        # TODO: default to only showing selected columns?
        return self._qtable


class TableMixin(VuetifyTemplate, HubListener):
    """
    Table subcomponent mixin.

    In addition to ``table``, this provides the following methods at the plugin-level:

    * :meth:`clear_table`
    * :meth:`export_table`

    To render in the plugin's vue file::

      <jupyter-widget :widget="table_widget"></jupyter-widget>

    """
    table_widget = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table = Table(self)
        self.table_widget = 'IPY_MODEL_'+self.table.model_id

    def clear_table(self):
        """
        Clear all entries/markers from the current table.
        """
        self.table.clear_table()

    def vue_clear_table(self, data=None):
        # call clear_table directly in case the class overloads that method
        # (to also clear markers, etc)
        self.clear_table()

    def export_table(self):
        """
        Export the QTable representation of the table.
        """
        return self.table.export_table()


class Plot(PluginSubcomponent):
    """
    Plot subcomponent.  For most cases where a plugin only requires a single plot, use the mixin
    instead.

    To use in a plugin, define ``plugin.plot = Plot(plugin)``, create a ``plot_widget`` Unicode
    traitlet, and set ``plugin.plot_widget = 'IPY_MODEL_'+self.plot.model_id``.

    To render in the plugin's vue file::

      <jupyter-widget :widget="plot_widget"></jupyter-widget>

    """
    template_file = __file__, "../components/plugin_plot.vue"

    figure = Any().tag(sync=True, **widget_serialization)
    toolbar = Any().tag(sync=True, **widget_serialization)

    def __init__(self, plugin, viewer_type='scatter', app=None, *args, **kwargs):
        super().__init__(plugin, 'Plot', *args, **kwargs)
        if app is None:
            app = jglue()

        self._app = app
        self._plugin = plugin
        self.viewer = app.new_data_viewer(viewer_type, show=False)
        self.viewer._plugin = plugin
        self._viewer_type = viewer_type
        if viewer_type == 'histogram':
            self._viewer_components = ('x',)
        else:
            self._viewer_components = ('x', 'y')
        self.figure = self.viewer.figure
        self._marks = {}

        self.figure.title_style = {'font-size': '12px'}
        self.figure.fig_margin = {'top': 60, 'bottom': 60, 'left': 60, 'right': 10}

        self.tools_nested = [
                        ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                        ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                        ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ]
        self._initialize_toolbar()

    def _initialize_toolbar(self, default_tool_priority=[]):
        self.toolbar = NestedJupyterToolbar(self.viewer, self.tools_nested, default_tool_priority)

    @property
    def app(self):
        return self._app

    @property
    def layers(self):
        return {layer.layer.label: layer for layer in self.viewer.layers}

    def _check_valid_components(self, **kwargs):
        for k, v in kwargs.items():
            if k not in self._viewer_components:
                raise ValueError(f"{k} is not one of {self._viewer_components}")
            if self._viewer_type == 'histogram' and len(v) <= 1:
                # temporary guardrails for segfault
                # https://github.com/astrofrog/fast-histogram/issues/60
                raise ValueError("histogram requires data entries with length > 1")

    def _remove_data(self, label):
        dc_entry = self.app.data_collection[label]
        self.viewer.remove_data(dc_entry)
        self.app.data_collection.remove(dc_entry)

    def _update_data(self, label, reset_lims=False, **kwargs):
        self._check_valid_components(**kwargs)
        if label not in self.app.data_collection:
            self._add_data(label, **kwargs)
            return
        data = self.app.data_collection[label]

        # if not provided, fallback on existing data
        length_mismatch = False
        for component in self._viewer_components:
            kwargs.setdefault(component, data[component])
            if len(kwargs[component]) != len(data[component]):
                length_mismatch = True

        if not length_mismatch:
            # then we can update the existing entry
            components = {c.label: c for c in data.components}
            data.update_components({components[comp]: kwargs[comp]
                                    for comp in self._viewer_components})
        else:
            # then we need to replace the existing entry, restoring any existing styles,
            # if they exist
            if label in self.layers.keys():
                style_state = self.layers[label].state.as_dict()
            else:
                style_state = {}
            self._remove_data(label)
            self._add_data(label, **kwargs)
            self.update_style(label, **style_state)
        if reset_lims:
            self.viewer.state.reset_limits()

    def update_style(self, label, **kwargs):
        kwargs.setdefault('visible', True)
        if label not in self.layers.keys():
            if not kwargs['visible']:
                # then we were only trying to hide anyways
                # (note: this ignores any other passed styles)
                return
        dc_entry = self.app.data_collection[label]
        if kwargs['visible']:
            if label not in self.layers.keys():
                self.viewer.add_data(dc_entry)
        else:
            # remove from viewer, leave in app (note: this will clear style options)
            # NOTE: if we want to keep styles, we could skip this and only toggle visibilities,
            # but then the zooming logic will need to be updated to account for visibility
            # states and the if not kwargs['visible'] check above to return should ensure no
            # style options are passed
            self.viewer.remove_data(dc_entry)
            return

        lyr = self.layers[label]
        with delay_callback(lyr.state, *list(kwargs.keys())):
            for k, v in kwargs.items():
                if k == 'layer' or k.endswith('_att'):
                    continue
                setattr(lyr.state, k, v)

    def _add_data(self, label, **kwargs):
        self._check_valid_components(**kwargs)
        data = Data(label=label, **kwargs)
        dc = self.app.data_collection
        dc.append(data)
        dc_entry = dc[label]

        if len(dc) > 1:
            # we can assume the same units/components since this only accepts x and y
            ref_data = dc[0]
            links = [LinkSame(dc_entry.components[i], ref_data.components[i])
                     for i in range(1, len(ref_data.components))]
            dc.add_link(links)
        self.viewer.add_data(dc_entry)

    def _refresh_marks(self):
        # ensure all marks are drawn
        # NOTE: this seems to only be necessary for histogram viewers and may be an upstream bug
        # if that is fixed upstream, we should test to see if we can safely remove this method
        # and all calls to it
        other_marks = list(self.marks.values())
        layer_marks = [m for m in self.figure.marks if m not in other_marks]
        self.figure.marks = layer_marks + other_marks

    @property
    def marks(self):
        return self._marks

    def clear_marks(self, *mark_labels):
        with self.hold_sync():
            for mark_label, mark in self.marks.items():
                if mark_label in mark_labels:
                    if isinstance(mark, bqplot.Bins):
                        # NOTE: cannot completely empty samples
                        # may want to also set mark.visible=False manually if clearing
                        # (but this will still at least clear any internal arrays)
                        mark.samples = [0]
                    else:
                        mark.x, mark.y = [], []

    def clear_all_marks(self):
        self.clear_marks(*self.marks.keys())

    def _add_mark(self, cls, label, xnorm=False, ynorm=False, **kwargs):
        """
        Parameters
        ----------
        xnorm : bool or str
            If True, axes will be normalized.  If a string of an existing mark, this mark will
            share that same x-axis scale.
        ynorm : bool or str
            If True, axes will be normalized.  If a string of an existing mark, this mark will
            share that same y-axis scale.
        """
        if label in self._marks:
            raise ValueError(f"mark with label '{label}' already exists")
        scales = {}
        for dim, norm in zip(('x', 'y'), (xnorm, ynorm)):
            if isinstance(norm, str) and norm in self._marks.keys():
                # point to an existing marks scales
                scales[dim] = self._marks[norm].scales[dim]
            elif norm:
                scales[dim] = bqplot.LinearScale()
            else:
                scales[dim] = self.figure.axes[0].scale
        mark = cls(scales=scales,
                   labels=[label],
                   **kwargs)
        self.figure.marks = self.figure.marks + [mark]
        self._marks[label] = mark
        return mark

    def add_line(self, label, x=[], y=[], xnorm=False, ynorm=False, **kwargs):
        return self._add_mark(bqplot.Lines, label, x=x, y=y,
                              xnorm=xnorm, ynorm=ynorm,
                              colors=kwargs.pop('color', kwargs.pop('colors', 'gray')),
                              **kwargs)

    def add_scatter(self, label, x=[], y=[], xnorm=False, ynorm=False, **kwargs):
        return self._add_mark(bqplot.Scatter, label, x=x, y=y,
                              xnorm=xnorm, ynorm=ynorm,
                              colors=kwargs.pop('color', kwargs.pop('colors', 'gray')),
                              **kwargs)

    def add_bins(self, label, sample=[0], bins=2, density=True, **kwargs):
        # NOTE: initializing with bins=1 breaks the figure until a resize event
        return self._add_mark(bqplot.Bins, label, sample=sample, bins=bins,
                              density=density,
                              colors=kwargs.pop('color', kwargs.pop('colors', 'gray')),
                              **kwargs)

    def set_limits(self, x_min=None, x_max=None, y_min=None, y_max=None):
        with delay_callback(self.viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            if x_min is not None:
                self.viewer.state.x_min = x_min
            if x_max is not None:
                self.viewer.state.x_max = x_max
            if y_min is not None:
                self.viewer.state.y_min = y_min
            if y_max is not None:
                self.viewer.state.y_max = y_max


class PlotMixin(VuetifyTemplate, HubListener):
    """
    Plot subcomponent mixin.

    In addition to ``plot``, this provides the following methods at the plugin-level:

    * :meth:`clear_plot`

    To render in the plugin's vue file::

      <jupyter-widget :widget="plot_widget"></jupyter-widget>

    """
    plot_widget = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot = Plot(self)
        self.plot_widget = 'IPY_MODEL_'+self.plot.model_id

    def clear_plot(self):
        """
        Clear all data from the current plot.
        """
        self.plot.clear_plot()
