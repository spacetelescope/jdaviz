import logging
import os
import pathlib
import re
import uuid
from inspect import isclass

import ipywidgets as w

from astropy.nddata import CCDData
from echo import CallbackProperty, DictCallbackProperty, ListCallbackProperty
from ipygoldenlayout import GoldenLayout
from ipysplitpanes import SplitPanes
from traitlets import Dict, Bool
from regions import RectanglePixelRegion, PixCoord
from specutils import Spectrum1D

from glue.config import data_translator
from glue.config import settings as glue_settings
from glue.core import BaseData, HubListener, Data, DataCollection
from glue.core.link_helpers import LinkSame
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from glue.core.state_objects import State
from glue.core.subset import Subset
from glue_jupyter.app import JupyterApplication
from glue_jupyter.state_traitlets_helpers import GlueState
from ipyvuetify import VuetifyTemplate

from .core.config import read_configuration, get_configuration
from .core.events import (LoadDataMessage, NewViewerMessage, AddDataMessage,
                          SnackbarMessage, RemoveDataMessage,
                          AddDataToViewerMessage, RemoveDataFromViewerMessage)
from .core.registries import (tool_registry, tray_registry, viewer_registry,
                              data_parser_registry)
from .utils import load_template, SnackbarQueue

__all__ = ['Application']

SplitPanes()
GoldenLayout()

CONTAINER_TYPES = dict(row='gl-row', col='gl-col', stack='gl-stack')
EXT_TYPES = dict(flux=['flux', 'sci'],
                 uncert=['ivar', 'err', 'var', 'uncert'],
                 mask=['mask', 'dq'])


# Set default opacity for data layers to 1 instead of 0.8 in
# some glue-core versions
glue_settings.DATA_ALPHA = 1


class ApplicationState(State):
    """
    The application state object contains all the current front-end state,
    including the loaded data name references, the active viewers, plugins,
    and layout.

    This state object allows for nested callbacks in mutable objects like
    dictionaries and makes it so incremental changes to nested values
    propagate to the traitlet in order to trigger a UI re-render.
    """
    drawer = CallbackProperty(
        False, docstring="State of the plugins drawer.")

    snackbar = DictCallbackProperty({
        'show': False,
        'test': "",
        'color': None,
        'timeout': 3000,
        'loading': False
    }, docstring="State of the quick toast messages.")

    snackbar_queue = SnackbarQueue()

    settings = DictCallbackProperty({
        'data': {
            'auto_populate': False,
            'parser': None
        },
        'visible': {
            'menu_bar': True,
            'toolbar': True,
            'tray': True,
            'tab_headers': True,
        },
        'dense_toolbar': True,
        'context': {
            'notebook': {
                'max_height': '600px'
            }
        },
        'layout': {
        }
    }, docstring="Top-level application settings.")

    data_items = ListCallbackProperty(
        docstring="List of data items parsed from the Glue data collection.")

    tool_items = ListCallbackProperty(
        docstring="Collection of toolbar items displayed in the application.")

    tray_items = ListCallbackProperty(
        docstring="List of plugins displayed in the sidebar tray area.")

    stack_items = ListCallbackProperty(
        docstring="Nested collection of viewers constructed to support the "
                  "Golden Layout viewer area.")


class Application(VuetifyTemplate, HubListener):
    """
    The main application object containing implementing the ipyvue/vuetify
    template instructions for composing the interface.
    """
    _metadata = Dict({"mount_id": "content"}).tag(sync=True)

    state = GlueState().tag(sync=True)

    template = load_template("app.vue", __file__).tag(sync=True)

    # Pure vue components are added through the components attribute. This
    #  allows us to do recursive component instantiation only in the vue
    #  component file
    components = Dict({"g-viewer-tab": load_template(
        "container.vue", __file__, traitlet=False)}).tag(
            sync=True, **w.widget_serialization)

    loading = Bool(False).tag(sync=True)

    def __init__(self, configuration=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Generate a state object for this application to maintain the state of
        #  the user interface.
        self.state = ApplicationState()

        # The application handler stores the state of the data and the
        #  underlying glue infrastructure
        self._application_handler = JupyterApplication()

        # Create a dictionary for holding non-ipywidget viewer objects so we
        #  can reference their state easily since glue does not store viewers
        self._viewer_store = {}

        # Parse the yaml configuration file used to compose the front-end UI
        self.load_configuration(configuration)

        # Subscribe to messages indicating that a new viewer needs to be
        #  created. When received, information is passed to the application
        #  handler to generate the appropriate viewer instance.
        self.hub.subscribe(self, NewViewerMessage,
                           handler=self._on_new_viewer)

        # Subscribe to messages indicating new data should be loaded into the
        #  application
        self.hub.subscribe(self, LoadDataMessage,
                           handler=lambda msg: self.load_data(msg.path))

        # Subscribe to the event fired when data is added to the application-
        #  level data collection object
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_added)

        # Subscribe to the event fired when data is deleted from the
        #  application-level data collection object
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_deleted)

        self.hub.subscribe(self, AddDataToViewerMessage,
                           handler=lambda msg: self.add_data_to_viewer(
                               msg.viewer_reference, msg.data_label))

        self.hub.subscribe(self, RemoveDataFromViewerMessage,
                           handler=lambda msg: self.remove_data_from_viewer(
                               msg.viewer_reference, msg.data_label))

        # Subscribe to snackbar messages and tie them to the display of the
        #  message box
        self.hub.subscribe(self, SnackbarMessage,
                           handler=self._on_snackbar_message)

        # Add callback that updates the layout when the data item array changes
        self.state.add_callback('stack_items', self.vue_relayout)

        # Add a fitted_models dictionary that the helpers (or user) can access
        self.fitted_models = {}

    @property
    def hub(self):
        """
        Reference to the stored application handler hub instance.

        Returns
        -------
        `glue.core.Hub`
            The internal ``Hub`` instance for the application.
        """
        return self._application_handler.data_collection.hub

    @property
    def session(self):
        """
        Reference to the stored session instance.

        Returns
        -------
        `glue.core.Session`
            The ``Session`` instance maintained by Glue for this application.
        """
        return self._application_handler.session

    @property
    def data_collection(self):
        """
        Reference to the stored data collection instance, used to maintain the
        the data objects that been loaded into the application this session.

        Returns
        -------
        `glue.core.DataCollection`
            The ``DataCollection`` instance for this application session.
        """
        return self._application_handler.data_collection

    def _on_snackbar_message(self, msg):
        """
        Displays a toast message with an editable message that be dismissed
        manually or will dismiss automatically after a timeout.

        Parameters
        ----------
        msg : `~glue.core.SnackbarMessage`
            The Glue snackbar message containing information about displaying
            the message box.
        """
        self.state.snackbar_queue.put(self.state, msg)

    def _link_new_data(self):
        """
        When additional data is loaded, check to see if the spectral axis of
        any components are compatible with already loaded data. If so, link
        them so that they can be displayed on the same profile1D plot.
        """
        new_len = len(self.data_collection)
        # Can't link if there's no world_component_ids
        wc_new = self.data_collection[new_len-1].world_component_ids
        if wc_new == []:
            return

        # Link to the first dataset with compatible coordinates
        for i in range(0, new_len-1):
            wc_old = self.data_collection[i].world_component_ids
            if wc_old == []:
                continue
            else:
                self.data_collection.add_link(LinkSame(wc_old[0], wc_new[0]))
                break

    def load_data(self, file_obj, parser_reference=None, **kwargs):
        """
        Provided a path to a data file, open and parse the data into the
        `~glue.core.DataCollection` for this session. This also attempts to
        find WCS links that exist between data components. Extra key word
        arguments are passed to the parsing functions.

        Parameters
        ----------
        file_obj : str or file-like
            File object for the data to be loaded.
        """
        self.loading = True
        try:
            try:
                # Properly form path and check if a valid file
                file_obj = pathlib.Path(file_obj)
                if not file_obj.exists():
                    msg_text = "Error: File {} does not exist".format(file_obj)
                    snackbar_message = SnackbarMessage(msg_text, sender=self,
                                                       color='error')
                    self.hub.broadcast(snackbar_message)
                    raise FileNotFoundError("Could not locate file: {}".format(file_obj))
                else:
                    # Convert path to properly formatted string (Parsers do not accept path objs)
                    file_obj = str(file_obj)
            except TypeError:
                # If it's not a str/path type, it might be a compatible class.
                # Pass to parsers to see if they can accept it
                pass

            # attempt to get a data parser from the config settings
            parser = None
            data = self.state.settings.get('data', None)
            if parser_reference:
                parser = data_parser_registry.members.get(parser_reference)
            elif data and isinstance(data, dict):
                data_parser = data.get('parser', None)
                if data_parser:
                    parser = data_parser_registry.members.get(data_parser)

            if parser is not None:
                # If the parser returns something other than known, assume it's
                #  a message we want to make the user aware of.
                msg = parser(self, file_obj, **kwargs)

                if msg is not None:
                    snackbar_message = SnackbarMessage(
                        msg, color='error', sender=self)
                    self.hub.broadcast(snackbar_message)
                    return
            else:
                self._application_handler.load_data(file_obj)

            # Send out a toast message
            snackbar_message = SnackbarMessage("Data successfully loaded.",
                                               sender=self)
            self.hub.broadcast(snackbar_message)
        finally:
            self.loading = False

    def get_viewer(self, viewer_reference):
        """
        Return a `~glue_jupyter.bqplot.common.BqplotBaseView` viewer instance.
        This is *not* an ``IPyWidget``. This is stored here because
        the state of the viewer and data methods that allow add/removing data
        to the viewer exist in a wrapper around the core ``IPyWidget``, which
        is needed to interact with the data rendered within a viewer.

        Notes
        -----
            This is only used in cases where the viewers have been pre-defined
            in the configuration file. Otherwise, viewers are not stored via
            reference.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.

        Returns
        -------
        `~glue_jupyter.bqplot.common.BqplotBaseView`
            The viewer class instance.
        """
        return self._viewer_by_reference(viewer_reference)

    def get_data_from_viewer(self, viewer_reference, data_label=None,
                             cls='default', include_subsets=True):
        """
        Returns each data component currently rendered within a viewer
        instance. Viewers themselves store a default data type to which the
        Glue data components are transformed upon retrieval. This can be
        optionally overridden with the ``cls`` keyword.

        Notes
        -----
            This is only used in cases where the viewers have been pre-defined
            in the configuration file. Otherwise, viewers are not stored via
            reference.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str, optional
            Optionally provide a label to retrieve a specific data set from the
            viewer instance.
        cls : class
            The class definition the Glue data components get transformed to
            when retrieved. This requires that a working set of translation
            functions exist in the ``glue_astronomy`` package. See
            https://github.com/glue-viz/glue-astronomy for more info.
            If this is the special string ``'default'``,  the ``default_class``
            attribute of the viewer referenced by ``viewer_reference`` is used.
        include_subsets : bool
            Whether to include subset layer data that exists in the viewer but
            has not been included in the core data collection object.

        Returns
        -------
        data : dict
            A dict of the transformed Glue data objects, indexed to
            corresponding viewer data labels.
        """
        viewer = self.get_viewer(viewer_reference)
        cls = viewer.default_class if cls == 'default' else cls

        if cls is not None and not isclass(cls):
            raise TypeError(
                "cls in get_data_from_viewer must be a class, None, or "
                "the 'default' string.")

        data = {}

        # If the viewer also supports collapsing, then grab the user's chosen
        #  statistic for collapsing data
        if hasattr(viewer.state, 'function'):
            statistic = viewer.state.function
        else:
            statistic = None

        for layer_state in viewer.state.layers:
            label = layer_state.layer.label

            if hasattr(layer_state, 'layer') and \
                    (data_label is None or label == data_label):

                # For raw data, just include the data itself
                if isinstance(layer_state.layer, BaseData):
                    layer_data = layer_state.layer

                    if cls is not None:
                        # If data is one-dimensional, assume that it can be
                        #  collapsed via the defined statistic
                        if cls == Spectrum1D:
                            layer_data = layer_data.get_object(cls=cls,
                                                               statistic=statistic)
                        else:
                            layer_data = layer_data.get_object(cls=cls)
                    # If the shape of the data is 2d, then use CCDData as the
                    #  output data type
                    elif len(layer_data.shape) == 2:
                        layer_data = layer_data.get_object(cls=CCDData)

                    data[label] = layer_data

                # For subsets, make sure to apply the subset mask to the
                #  layer data first
                elif isinstance(layer_state.layer, Subset):
                    if include_subsets:
                        layer_data = layer_state.layer

                        if cls is not None:
                            handler, _ = data_translator.get_handler_for(cls)
                            layer_data = handler.to_object(layer_data,
                                                           statistic=statistic)

                        data[label] = layer_data

        # If a data label was provided, return only the data requested
        if data_label is not None:
            return data.get(data_label)

        return data

    def get_subsets_from_viewer(self, viewer_reference, data_label=None):
        """
        Returns the subsets of a specified viewer converted to astropy regions
        objects.

        It should be noted that the subset translation machinery lives in the
        glue-astronomy repository. Currently, the machinery only works on 2D
        data for cases like range selection. For e.g. a profile viewer that is
        ostensibly just a view into a 3D data set, it is necessary to first
        reduce the dimensions of the data, then retrieve the subset information
        as a regions object. This means that the returned y extents in the
        region are not strictly representative of the subset range in y.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str, optional
            Optionally provide a label to retrieve a specific data set from the
            viewer instance.

        Returns
        -------
        data : dict
            A dict of the transformed Glue subset objects, with keys
            representing the subset name and values as astropy regions
            objects.
        """
        viewer = self.get_viewer(viewer_reference)
        data = self.get_data_from_viewer(viewer_reference,
                                         data_label,
                                         cls=None)
        regions = {}

        if data_label is not None:
            data = {data_label: data}

        for key, value in data.items():
            if isinstance(value, Subset):
                # Range selection on a profile is currently not supported in
                #  the glue translation machinery for astropy regions, so we
                #  have to do it manually. Only data that is 2d is supported,
                #  therefore, if the data is already 2d, simply use as is.
                if value.data.ndim == 2:
                    region = value.data.get_selection_definition(
                        format='astropy-regions')
                    regions[key] = region
                    continue
                # There is a special case for 1d data (which is also not
                #  supported currently). We now eschew the use of the
                #  translation machinery entirely and construct the astropy
                #  region ourselves.
                elif value.data.ndim == 1:
                    # Grab the data units from the glue-astronomy spectral axis
                    # TODO: this needs to be much simpler; i.e. data units in
                    #  the glue component objects
                    unit = value.data.coords.spectral_axis.unit
                    hi, lo = value.subset_state.hi, value.subset_state.lo
                    xcen = 0.5 * (lo + hi)
                    width = hi - lo
                    region = RectanglePixelRegion(
                        PixCoord(xcen, 0), width, 0,
                        meta={'spectral_axis_unit': unit})
                    regions[key] = region
                    continue

                # Get the pixel coordinate [z] of the 3D data, repeating the
                #  wavelength axis. This doesn't seem strictly necessary as it
                #  returns the same data if the pixel axis is [y] or [x]
                xid = value.data.pixel_component_ids[0]

                # Construct a new data object collapsing over one of the
                #  spatial dimensions. This is necessary because the astropy
                #  region translation machinery in glue-astronomy does not
                #  support non-2D data, even for range objects.
                stat_func = 'median'

                if hasattr(viewer.state, 'function'):
                    stat_func = viewer.state.function

                # Compute reduced data based on the current viewer's statistic
                #  function. This doesn't seem particularly useful, but better
                #  to be consistent.
                reduced_data = Data(x=value.data.compute_statistic(
                    stat_func, value.data.id[xid],
                    subset_state=value.subset_state.copy(), axis=1))

                # Instantiate a new data collection since we need to compose
                #  the collapsed data with the current subset state. We use a
                #  new data collection so as not to inference with the one used
                #  by the application.
                temp_data_collection = DataCollection()
                temp_data_collection.append(reduced_data)

                # Get the data id of the pixel axis that will be used in the
                #  range composition. This is the wavelength axis for the new
                #  2d data.
                xid = reduced_data.pixel_component_ids[1]

                # Create a new subset group to hold our current subset state
                subset_group = temp_data_collection.new_subset_group(
                    label=value.label, subset_state=value.subset_state.copy())

                # Set the subset state axis to the wavelength pixel coordinate
                subset_group.subsets[0].subset_state.att = xid

                # Use the associated collapsed subset data to get an astropy
                #  regions object dependent on the extends of the subset.
                # **Note** that the y values in this region object are not
                #  useful, only the x values are.
                region = subset_group.subsets[0].data.get_selection_definition(
                    format='astropy-regions')
                regions[key] = region

        return regions

    def add_data(self, data, data_label):
        """
        Add data to the Glue ``DataCollection``.

        Parameters
        ----------
        data : any
            Data to be stored in the ``DataCollection``. This must either be
            a `~glue.core.data.Data` instance, or an arbitrary data instance
            for which there exists data translation functions in the
            glue astronomy repository.
        data_label : str, optional
            The name associated with this data. If none is given, a generic
            name is generated.
        """

        # Include the data in the data collection
        data_label = data_label or "New Data"
        self.data_collection[data_label] = data

        # Send out a toast message
        snackbar_message = SnackbarMessage(
            f"Data '{data_label}' successfully added.", sender=self)
        self.hub.broadcast(snackbar_message)

    @staticmethod
    def _build_data_label(path, ext=None):
        """ Build a data label from a filename and data extension

        Builds a data_label out of a filename and data extension.
        If the input string path already ends with a data
        extension, the label is returned directly.  Otherwise a valid
        extension must be specified to append to the file stem.

        Parameters
        ----------
            path : str
                The data filename to use as a
            ext : str
                The data extension to access from the file.
        Returns
        -------
        A string data label used by Glue

        """

        # if path is not a file or already ends in [ ] extension, assume it is a data-label
        if not os.path.isfile(path) or re.search(r'(.+)(\[(.*?)\])$', path):
            return path
        else:
            assert ext, 'A data extension must be specified'
            p = pathlib.Path(path)
            stem = p.stem.split(os.extsep)[0]
            label = f'{stem}[{ext}]'
            return label

    def add_data_to_viewer(self, viewer_reference, data_path,
                           clear_other_data=False, ext=None):
        """
        Plots a data set from the data collection in the specific viewer.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_path : str
            Either the data filename or the Glue data label found in the ``DataCollection``.
        clear_other_data : bool
            Removes all other currently plotted data and only shows the newly
            defined data set.
        ext: str
            The data extension to access from a file.  If data_path is a filename, ext
            is required.
        """
        viewer_item = self._viewer_item_by_reference(viewer_reference)
        data_label = self._build_data_label(data_path, ext=ext)
        data_id = self._data_id_from_label(data_label)

        data_ids = viewer_item['selected_data_items'] \
            if not clear_other_data else []

        if data_id is not None:
            data_ids.append(data_id)
            self._update_selected_data_items(viewer_item['id'], data_ids)
        else:
            raise ValueError(
                f"No data item found with label '{data_label}'. Label must be one "
                "of:\n\t" + "\n\t".join([
                    data_item['name'] for data_item in self.state.data_items]))

    def _set_plot_axes_labels(self, viewer_id):
        """
        Sets the plot axes labels to be the units of the data to be loaded.

        Parameters
        ----------
        viewer_id : str
            The UUID associated with the desired viewer item.
        """
        viewer = self._viewer_by_id(viewer_id)

        viewer.set_plot_axes()

    def remove_data_from_viewer(self, viewer_reference, data_path, ext=None):
        """
        Removes a data set from the specified viewer.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_path : str
            Either the data filename or the Glue data label found in the ``DataCollection``.
        ext: str
            The data extension to access from a file.  If data_path is a filename, ext
            is required.
        """
        viewer_item = self._viewer_item_by_reference(viewer_reference)
        data_label = self._build_data_label(data_path, ext=ext)
        data_id = self._data_id_from_label(data_label)

        selected_items = viewer_item['selected_data_items']

        if data_id in selected_items:
            selected_items.remove(data_id)

            self._update_selected_data_items(
                viewer_item['id'], selected_items)

    def _data_id_from_label(self, label):
        """
        Retrieve the data item given the Glue ``DataCollection`` data label.

        Parameters
        ----------
        label : str
            Label associated with the ``DataCollection`` item. This is also the
            name shown in the data list.

        Returns
        -------
        dict
            The data item dictionary containing the id and name of the given
            data set.
        """
        for data_item in self.state.data_items:
            if data_item['name'] == label:
                return data_item['id']

    def _viewer_by_id(self, vid):
        """
        Viewer instance by id.

        Parameters
        ----------
        vid : str
            The UUID associated with the parent viewer item dictionary.

        Returns
        -------
        `~glue_jupyter.bqplot.common.BqplotBaseView`
            The viewer class instance.
        """
        return self._viewer_store.get(vid)

    def _viewer_item_by_id(self, vid):
        """
        Retrieve a viewer item dictionary by id.

        Parameters
        ----------
        vid : str
            The UUID associated with the desired viewer item.

        Returns
        -------
        viewer_item : dict
            The dictionary containing the viewer instances and associated
            attributes.
        """
        def find_viewer_item(stack_items):
            for stack_item in stack_items:
                for viewer_item in stack_item.get('viewers'):
                    if viewer_item['id'] == vid:
                        return viewer_item

                if len(stack_item.get('children')) > 0:
                    result = find_viewer_item(stack_item.get('children'))
                    if result is not None:
                        return result

        viewer_item = find_viewer_item(self.state.stack_items)

        return viewer_item

    def _viewer_by_reference(self, reference):
        """
        Viewer instance by reference defined in the yaml configuration file.

        Parameters
        ----------
        reference : str
            Reference for viewer defined in the yaml configuration file.

        Returns
        -------
        `~glue_jupyter.bqplot.common.BqplotBaseView`
            The viewer class instance.
        """
        viewer_item = self._viewer_item_by_reference(reference)

        return self._viewer_store[viewer_item['id']]

    def _viewer_item_by_reference(self, reference):
        """
        Retrieve a viewer item dictionary by reference.

        Parameters
        ----------
        reference : str
            Reference for viewer defined in the yaml configuration file.

        Returns
        -------
        viewer_item : dict
            The dictionary containing the viewer instances and associated
            attributes.
        """
        def find_viewer_item(stack_items):
            out_viewer_item = None

            for stack_item in stack_items:
                for viewer_item in stack_item.get('viewers'):
                    if viewer_item['reference'] == reference:
                        out_viewer_item = viewer_item
                        break

                if len(stack_item.get('children')) > 0:
                    out_viewer_item = find_viewer_item(stack_item.get('children'))

            return out_viewer_item

        viewer_item = find_viewer_item(self.state.stack_items)

        return viewer_item

    def vue_relayout(self, *args, **kwargs):
        """
        Forces any rendered ``Bqplot`` instances to resize themselves.
        """
        def resize(stack_items):
            for stack in stack_items:
                for viewer_item in stack.get('viewers'):
                    viewer = self._viewer_by_id(viewer_item['id'])

                    if viewer is not None:
                        viewer.figure_widget.layout.height = '99.9%'
                        viewer.figure_widget.layout.height = '100%'

                if len(stack.get('children')) > 0:
                    resize(stack.get('children'))

        resize(self.state.stack_items)

    def vue_destroy_viewer_item(self, cid):
        """
        Callback for when viewer area tabs are destroyed. Finds the viewer item
        associated with the provided id and removes it from the ``stack_items``
        list.

        Parameters
        ----------
        cid : str
            The UUID associated with the viewer item dictionary.
        """
        def remove(stack_items):
            for stack in stack_items:
                for viewer in stack['viewers']:
                    if viewer['id'] == cid:
                        stack['viewers'].remove(viewer)

                if len(stack.get('children', [])) > 0:
                    stack['children'] = remove(stack['children'])

            return stack_items

        remove(self.state.stack_items)

        # Also remove the viewer from the stored viewer instance dictionary
        # FIXME: This is getting called twice for some reason
        if cid in self._viewer_store:
            del self._viewer_store[cid]

    def vue_data_item_selected(self, event):
        """
        Callback for selection events in the front-end data list. Selections
        mean that the checkbox associated with the list item has been toggled.
        When the checkbox is toggled off, remove the data from the viewer;
        when it is toggled on, add the data to the viewer.

        Parameters
        ----------
        event : dict
            Traitlet event provided the 'old' and 'new' values.
        """
        viewer_id, item_id, checked = event['id'], event['item_id'], event['checked']
        viewer_item = self._viewer_item_by_id(viewer_id)

        if viewer_item is None:
            raise ValueError(f'viewer {viewer_id} not found')

        if checked:
            selected_items = [*viewer_item['selected_data_items'], item_id]
        else:
            selected_items = list(filter(
                lambda id: id != item_id, viewer_item['selected_data_items']))

        self._update_selected_data_items(viewer_id, selected_items)

    def vue_save_figure(self, event):
        """
        Callback for save figure events in the front end viewer toolbars. Uses
        the bqplot.Figure save methods.
        """
        viewer_id, filetype = event['id'], event['filetype']
        viewer = self._viewer_store[viewer_id]
        if filetype == "png":
            viewer.figure.save_png()
        elif filetype == "svg":
            viewer.figure.save_svg()

    def vue_close_snackbar_message(self, event):
        """
        Callback to close a message in the snackbar when the "close"
        button is clicked.

        Still need to find out how to perform the same action, but
        triggered by a snackbar message timeout.
        """
        self.state.snackbar_queue.close_current_message(self.state)

    def _update_selected_data_items(self, viewer_id, selected_items):
        # Find the active viewer
        viewer_item = self._viewer_item_by_id(viewer_id)
        viewer = self._viewer_by_id(viewer_id)

        # Update the stored selected data items
        viewer_item['selected_data_items'] = selected_items
        data_ids = viewer_item['selected_data_items']

        active_data_labels = []

        # Include any selected data in the viewer
        for data_id in data_ids:
            label = next((x['name'] for x in self.state.data_items
                          if x['id'] == data_id), None)

            if label is None:
                logging.warning(f"No data item with id '{data_id}' found in "
                                f"viewer '{viewer_id}'.")
                continue

            active_data_labels.append(label)

            [data] = [x for x in self.data_collection if x.label == label]

            viewer.add_data(data)

            add_data_message = AddDataMessage(data, viewer,
                                              viewer_id=viewer_id,
                                              sender=self)
            self.hub.broadcast(add_data_message)

        # Remove any deselected data objects from viewer
        viewer_data = [layer_state.layer
                       for layer_state in viewer.state.layers
                       if hasattr(layer_state, 'layer') and
                       isinstance(layer_state.layer, BaseData)]

        for data in viewer_data:
            if data.label not in active_data_labels:
                viewer.remove_data(data)
                remove_data_message = RemoveDataMessage(data, viewer,
                                                        viewer_id=viewer_id,
                                                        sender=self)
                self.hub.broadcast(remove_data_message)

        # Sets the plot axes labels to be the units of the most recently
        # active data.
        if len(active_data_labels) > 0:
            active_data = self.data_collection[active_data_labels[0]]
            if hasattr(active_data, "_preferred_translation") \
                    and active_data._preferred_translation is not None:
                pass
                self._set_plot_axes_labels(viewer_id)

    def _on_data_added(self, msg):
        """
        Callback for when data is added to the internal ``DataCollection``.
        Adds a new data item dictionary to the ``data_items`` state list and
        links the new data to any compatible previously loaded data.

        Parameters
        ----------
        msg : `~glue.core.DataCollectionAddMessage`
            The Glue data collection add message containing information about
            the new data.
        """
        self._link_new_data()
        data_item = self._create_data_item(msg.data.label)
        self.state.data_items.append(data_item)

    def _on_data_deleted(self, msg):
        """
        Callback for when data is removed from the internal ``DataCollection``.
        Removes the data item dictionary in the ``data_items`` state list.

        Parameters
        ----------
        msg : `~glue.core.DataCollectionAddMessage`
            The Glue data collection add message containing information about
            the new data.
        """
        for data_item in self.state.data_items:
            if data_item['name'] == msg.data.label:
                self.state.data_items.remove(data_item)

    @staticmethod
    def _create_data_item(label):
        return {
            'id': str(uuid.uuid4()),
            'name': label,
            'locked': False,
            'children': []}

    @staticmethod
    def _create_stack_item(container='gl-stack', children=None, viewers=None):
        """
        Convenience method for generating stack item dictionaries.

        Parameters
        ----------
        container : str
            The GoldenLayout container type used to encapsulate the children
            items within this stack item.
        children : list
            List of children stack item dictionaries used for recursively
            including layout items within each GoldenLayout component cell.
        viewers : list
            List of viewer item dictionaries containing the information used
            to render the viewer and associated tool widgets.

        Returns
        -------
        dict
            Dictionary containing information for this stack item.
        """
        children = [] if children is None else children
        viewers = [] if viewers is None else viewers

        return {
            'id': str(uuid.uuid4()),
            'container': container,
            'children': children,
            'viewers': viewers}

    @staticmethod
    def _create_viewer_item(viewer, name=None, reference=None):
        """
        Convenience method for generating viewer item dictionaries.

        Parameters
        ----------
        viewer : `~glue_jupyter.bqplot.common.BqplotBaseView`
            The ``Bqplot`` viewer instance.
        name : str, optional
            The name shown in the GoldenLayout tab for this viewer.
        reference : str, optional
            The reference associated with this viewer as defined in the yaml
            configuration file.

        Returns
        -------
        dict
            Dictionary containing information for this viewer item.
        """
        tools = viewer.toolbar_selection_tools
        tools.borderless = True
        tools.tile = True

        return {
            'id': str(uuid.uuid4()),
            'name': name or "Unnamed Viewer",
            'widget': "IPY_MODEL_" + viewer.figure_widget.model_id,
            'tools': "IPY_MODEL_" + viewer.toolbar_selection_tools.model_id,
            'layer_options': "IPY_MODEL_" + viewer.layer_options.model_id,
            'viewer_options': "IPY_MODEL_" + viewer.viewer_options.model_id,
            'selected_data_items': [],
            'collapse': True,
            'reference': reference}

    def _on_new_viewer(self, msg):
        """
        Callback for when the `~jdaviz.core.events.NewViewerMessage` message is
        raised. This method asks the application handler to generate a new
        viewer and then created the associated stack and viewer items.

        Parameters
        ----------
        msg : `~jdaviz.core.events.NewViewerMessage`
            The message received from the ``Hub`` broadcast.

        Returns
        -------
        viewer : `~glue_jupyter.bqplot.common.BqplotBaseView`
            The new viewer instance.
        """

        viewer = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            viewer.state.x_att = x

        # Create the viewer item dictionary
        new_viewer_item = self._create_viewer_item(
            viewer=viewer)

        new_stack_item = self._create_stack_item(
            container='gl-stack',
            viewers=[new_viewer_item])

        # Store the glupyter viewer object so we can access the add and remove
        #  data methods in the future
        self._viewer_store[new_viewer_item['id']] = viewer

        # Add viewer locally
        self.state.stack_items.append(new_stack_item)

        # Send out a toast message
        snackbar_message = SnackbarMessage("New viewer successfully created.",
                                           sender=self)
        self.hub.broadcast(snackbar_message)

        self.session.application.viewers.append(viewer)

        return viewer

    def load_configuration(self, path=None, config=None):
        """
        Parses the provided input into a configuration
        dictionary and populates the appropriate state values
        with the results.  Provided input can either be a
        configuration YAML file or a pre-made configuration
        dictionary.

        Parameters
        ----------
        path : str, optional
            Path to the configuration file to be loaded. In the case where this
            is ``None``, it loads the default configuration. Optionally, this
            can be provided as name reference. **NOTE** This optional way to
            define the configuration will be removed in future versions.
        config : dict, optional
            A dictionary of configuration settings to be loaded.  The dictionary
            contents should be the same as a YAML config file specification.
        """
        # reset the application state
        self._reset_state()

        # load the configuration from the yaml file or configuration object
        assert not (path and config), 'Cannot specify both a path and a config object!'
        if config:
            assert isinstance(config, dict), 'configuration object must be a dictionary'
        else:
            # check if the input path is actually a dict object
            if isinstance(path, dict):
                config = path
            else:
                config = read_configuration(path=path)

        # store the loaded config object
        self._loaded_configuration = config

        self.state.settings.update(config.get('settings'))

        def compose_viewer_area(viewer_area_items):
            stack_items = []

            for item in viewer_area_items:
                stack_item = self._create_stack_item(
                    container=CONTAINER_TYPES[item.get('container')])

                stack_items.append(stack_item)

                for view in item.get('viewers', []):
                    viewer = self._application_handler.new_data_viewer(
                        viewer_registry.members.get(view['plot'])['cls'],
                        data=None, show=False)

                    viewer_item = self._create_viewer_item(
                        name=view.get('name'),
                        viewer=viewer,
                        reference=view.get('reference'))

                    self._viewer_store[viewer_item['id']] = viewer

                    stack_item.get('viewers').append(viewer_item)

                if len(item.get('children', [])) > 0:
                    child_stack_items = compose_viewer_area(
                        item.get('children'))
                    stack_item['children'] = child_stack_items

            return stack_items

        if config.get('viewer_area') is not None:
            stack_items = compose_viewer_area(config.get('viewer_area'))
            self.state.stack_items.extend(stack_items)

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            tool = tool_registry.members.get(name)(app=self)

            self.state.tool_items.append({
                'name': name,
                'widget': "IPY_MODEL_" + tool.model_id
            })

            self._application_handler._tools[name] = tool

        for name in config.get('tray', []):
            tray = tray_registry.members.get(name)
            tray_item_instance = tray.get('cls')(app=self)
            tray_item_label = tray.get('label')

            self.state.tray_items.append({
                'name': name,
                'label': tray_item_label,
                'widget': "IPY_MODEL_" + tray_item_instance.model_id
            })

    def _reset_state(self):
        """ Resets the application state """
        self.state = ApplicationState()
        self.state.add_callback('stack_items', self.vue_relayout)
        self._application_handler._tools = {}

    def get_configuration(self, path=None, section=None):
        """ Returns a copy of the application configuration

        Returns a copy of the configuration specification.  If path
        is not specified, returns the currently loaded configuration.

        Parameters
        ----------
        path : str, optional
            path to the configuration file to be retrieved.
        section : str, optional
            A section of the configuration to retrieve

        Returns
        -------
        A configuration specification dictionary

        """

        config = None
        if not path:
            config = self._loaded_configuration

        cfg = get_configuration(path=path, section=section, config=config)
        return cfg
