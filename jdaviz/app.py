import logging
import os
import uuid

import ipywidgets as w
import pkg_resources
import yaml
from astropy.nddata import CCDData
from echo import (CallbackProperty, ListCallbackProperty,
                  DictCallbackProperty)
from glue.config import data_translator
from glue.core import BaseData
from glue.core.autolinking import find_possible_links
from glue.core.message import DataCollectionAddMessage
from glue.core.state_objects import State
from glue.core.subset import Subset
from glue_jupyter.app import JupyterApplication
from glue_jupyter.state_traitlets_helpers import GlueState
from ipygoldenlayout import GoldenLayout
from ipysplitpanes import SplitPanes
from traitlets import Dict

from .core.events import LoadDataMessage, NewViewerMessage, AddDataMessage, SnackbarMessage
from .core.registries import tool_registry, tray_registry, viewer_registry
from .core.template_mixin import TemplateMixin
from .utils import load_template

__all__ = ['Application']

SplitPanes()
GoldenLayout()

CONTAINER_TYPES = dict(row='gl-row', col='gl-col', stack='gl-stack')


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
        'timeout': 3000
    }, docstring="State of the quick toast messages.")

    settings = DictCallbackProperty({
        'visible': {
            'menu_bar': True,
            'toolbar': True,
            'tray': True,
            'tab_headers': True,
        },
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


class Application(TemplateMixin):
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

    def __init__(self, configuration=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Generate a state object for this application to maintain the state of
        #  the user interface.
        self.state = ApplicationState()

        # The application handler stores the state of the data and the
        #  underlying glue infrastructure
        self._application_handler = JupyterApplication()

        # We manually load plugins that are part of the "jdaviz_plugins"
        #  group into the current namespace
        plugins = {
            entry_point.name: entry_point.load()
            for entry_point
            in pkg_resources.iter_entry_points(group='jdaviz_plugins')}

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

        # Subscribe to snackbar messages and tie them to the display of the
        #  message box
        self.hub.subscribe(self, SnackbarMessage,
                           handler=self._on_snackbar_message)

        # Add callback that updates the layout when the data item array changes
        self.state.add_callback('stack_items', self.vue_relayout)

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
        self.state.snackbar['show'] = False
        self.state.snackbar['text'] = msg.text
        self.state.snackbar['color'] = msg.color
        self.state.snackbar['timeout'] = msg.timeout
        self.state.snackbar['show'] = True

    def load_data(self, path):
        """
        Provided a path to a data file, open and parse the data into the
        `~glue.core.DataCollection` for this session. This also attempts to
        find WCS links that exist between data components.

        Parameters
        ----------
        path : str
            File path for the data file to be loaded.
        """
        self._application_handler.load_data(path)

        # Send out a toast message
        snackbar_message = SnackbarMessage("Data successfully loaded.",
                                           sender=self)
        self.hub.broadcast(snackbar_message)

        # Attempt to link the data
        links = find_possible_links(self.data_collection)

        # self.data_collection.add_link(links['Astronomy WCS'])

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

    def get_data_from_viewer(self, viewer_reference, data_label=None, cls=None,
                             include_subsets=True):
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
            ``https://github.com/glue-viz/glue-astronomy`` for more info.
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
        cls = cls or viewer.default_class

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
                        layer_data = layer_data.get_object(cls=cls,
                                                           statistic=statistic)
                    # If the shape of the data is 2d, then use CCDData as the
                    #  output data type
                    elif len(layer_data.shape) == 2:
                        layer_data = layer_data.get_object(cls=CCDData)

                    data[label] = layer_data

                # For subsets, make sure to apply the subset mask to the
                #  layer data first
                elif isinstance(layer_state.layer, Subset):
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

    def add_data_to_viewer(self, viewer_reference, data_label,
                           clear_other_data=False):
        """
        Plots a data set from the data collection in the specific viewer.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        clear_other_data : bool
            Removes all other currently plotted data and only shows the newly
            defined data set.
        """
        viewer_item = self._viewer_item_by_reference(viewer_reference)
        data_id = self._data_id_from_label(data_label)

        data_ids = viewer_item['selected_data_items'] \
            if not clear_other_data else []

        if data_id is not None:
            data_ids.append(data_id)
            self._update_selected_data_items(viewer_item['id'], data_ids)
        else:
            raise ValueError(
                f"No data item found with label '{data_label}'. Label must be one "
                f"of:\n\t" + f"\n\t".join([
                    data_item['name'] for data_item in self.state.data_items]))

    def remove_data_from_viewer(self, viewer_reference, data_label):
        """
        Removes a data set from the specified viewer.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        """
        viewer_item = self._viewer_item_by_reference(viewer_reference)
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
                    return find_viewer_item(stack_item.get('children'))

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
            for stack_item in stack_items:
                for viewer_item in stack_item.get('viewers'):
                    if viewer_item['reference'] == reference:
                        return viewer_item

                if len(stack_item.get('children')) > 0:
                    return find_viewer_item(stack_item.get('children'))

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

                # If the stack is empty of viewers, also delete the stack
                if len(stack['viewers']) == 0 and \
                        len(stack['children']) == 0:
                    stack_items.remove(stack)
                    continue

                if len(stack.get('children', [])) > 0:
                    stack['children'] = remove(stack['children'])

            return stack_items

        remove(self.state.stack_items)

        # self.vue_relayout()

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
        viewer_id, selected_items = event['id'], event['selected_items']

        self._update_selected_data_items(viewer_id, selected_items)

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

            add_data_message = AddDataMessage(data, viewer, sender=self)
            self.hub.broadcast(add_data_message)

        # Remove any deselected data objects from viewer
        viewer_data = [layer_state.layer
                       for layer_state in viewer.state.layers
                       if hasattr(layer_state, 'layer') and
                       isinstance(layer_state.layer, BaseData)]

        for data in viewer_data:
            if data.label not in active_data_labels:
                viewer.remove_data(data)

    def _on_data_added(self, msg):
        """
        Callback for when data is added to the internal ``DataCollection``.
        Adds a new data item dictionary to the ``data_items`` state list.

        Parameters
        ----------
        msg : `~glue.core.DataCollectionAddMessage`
            The Glue data collection add message containing information about
            the new data.
        """
        data_item = self._create_data_item(msg.data.label)
        self.state.data_items.append(data_item)

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

        return viewer

    def load_configuration(self, path=None):
        """
        Parses the provided configuration yaml file and populates the
        appropriate state values with the results.

        Parameters
        ----------
        path : str, optional
            Path to the configuration file to be loaded. In the case where this
            is ``None``, it loads the default configuration. Optionally, this
            can be provided as name reference. **NOTE** This optional way to
            define the configuration will be removed in future versions.
        """
        # Parse the default configuration file
        default_path = os.path.join(os.path.dirname(__file__), "configs")

        if path is None or path == 'default':
            path = os.path.join(default_path, "default", "default.yaml")
        elif path == 'cubeviz':
            path = os.path.join(default_path, "cubeviz", "cubeviz.yaml")
        elif path == 'specviz':
            path = os.path.join(default_path, "specviz", "specviz.yaml")
        elif not os.path.isfile(path):
            raise ValueError("Configuration must be path to a .yaml file.")

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

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
            # self.vue_relayout()

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            tool = tool_registry.members.get(name)(app=self)

            self.state.tool_items.append({
                'name': name,
                'widget': "IPY_MODEL_" + tool.model_id
            })

        for name in config.get('tray', []):
            tray = tray_registry.members.get(name)
            tray_item_instance = tray.get('cls')(app=self)
            tray_item_label = tray.get('label')

            self.state.tray_items.append({
                'name': name,
                'label': tray_item_label,
                'widget': "IPY_MODEL_" + tray_item_instance.model_id
            })
