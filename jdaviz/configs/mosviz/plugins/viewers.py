from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.table import TableViewer
from specutils import Spectrum1D
from astropy import units as u

from jdaviz.core.events import (AddDataToViewerMessage,
                                RemoveDataFromViewerMessage,
                                TableClickMessage)
from jdaviz.core.registries import viewer_registry
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin

__all__ = ['MosvizProfileView', 'MosvizImageView', 'MosvizProfile2DView',
           'MosvizTableViewer']


@viewer_registry("mosviz-profile-viewer", label="Profile 1D (Mosviz)")
class MosvizProfileView(BqplotProfileView, JdavizViewerMixin):
    default_class = Spectrum1D

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscribe_to_layers_update()
        self._initialize_toolbar_nested()

    def data(self, cls=None):
        return [layer_state.layer.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def set_plot_axes(self):
        data = self.data()[0]
        # Set axes labels for the spectrum viewer
        spectral_axis_unit_type = str(data.spectral_axis.unit.physical_type).title()
        # flux_unit_type = data.flux.unit.physical_type.title()
        flux_unit_type = "Flux density"

        if data.spectral_axis.unit.is_equivalent(u.m):
            spectral_axis_unit_type = "Wavelength"
        elif data.spectral_axis.unit.is_equivalent(u.pixel):
            spectral_axis_unit_type = "pixel"

        label_0 = f"{spectral_axis_unit_type} [{data.spectral_axis.unit.to_string()}]"
        self.figure.axes[0].label = label_0
        self.figure.axes[1].label = f"{flux_unit_type} [{data.flux.unit.to_string()}]"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"

        # Set Y-axis to scientific notation
        self.figure.axes[1].tick_format = '0.1e'


@viewer_registry("mosviz-image-viewer", label="Image 2D (Mosviz)")
class MosvizImageView(BqplotImageView, JdavizViewerMixin):
    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['jdaviz:homezoom', 'jdaviz:boxzoom',
             'jdaviz:panzoom', 'bqplot:rectangle',
             'bqplot:circle']

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom'],
                    ['jdaviz:panzoom'],
                    ['bqplot:circle', 'bqplot:rectangle'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscribe_to_layers_update()
        self._initialize_toolbar_nested()

    def data(self, cls=None):
        return [layer_state.layer  # .get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def set_plot_axes(self):
        self.figure.axes[1].tick_format = None
        self.figure.axes[0].tick_format = None

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"


@viewer_registry("mosviz-profile-2d-viewer", label="Spectrum 2D (Mosviz)")
class MosvizProfile2DView(BqplotImageView, JdavizViewerMixin):
    # Due to limitations in CCDData and 2D data that has spectral and spatial
    #  axes, the default conversion class must handle cubes
    default_class = Spectrum1D

    # replace the default tools (which include rect and circle region)
    # with only the tools we want (likely the same as in SpecvizProfileView)
    inherit_tools = False
    tools = ['jdaviz:homezoom',
             'jdaviz:boxzoom',
             'jdaviz:xrangezoom',
             'jdaviz:panzoom',
             'jdaviz:panzoom_x',
             'bqplot:xrange']

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x'],
                    ['bqplot:xrange'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscribe_to_layers_update()
        self._initialize_toolbar_nested()
        # Setup viewer option defaults
        self.state.aspect = 'auto'

    def data(self, cls=None):
        return [layer_state.layer.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def set_plot_axes(self):
        self.figure.axes[0].visible = False

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[1].tick_format = None
        self.figure.axes[1].label_location = "start"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"


@viewer_registry("mosviz-table-viewer", label="Table (Mosviz)")
class MosvizTableViewer(TableViewer, JdavizViewerMixin):
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, *args, **kwargs)

        self.figure_widget.observe(self._on_row_selected, names=['highlighted'])
        # enable scrolling: # https://github.com/glue-viz/glue-jupyter/pull/287
        self.widget_table.scrollable = True

        self._selected_data = {}
        self._shared_image = False
        self.row_selection_in_progress = False

        self._on_row_selected_begin = None
        self._on_row_selected_end = None

    def redraw(self):

        # Overload to hide components - we do this via overloading instead of
        # checking for changes in self.figure_widget.data because some components
        # might be added inplace to the dataset.

        if self.figure_widget.data is None:
            self.figure_widget.hidden_components = []
        else:
            components_str = [cid.label for cid in self.figure_widget.data.main_components]
            hidden = []
            for colname in ['Images', '1D Spectra', '2D Spectra']:
                if colname in components_str:
                    hidden.append(self.figure_widget.data.id[colname])
            self.figure_widget.hidden_components = hidden

        super().redraw()

    @property
    def nrows(self):
        return self.widget_table.get_state()['total_length']

    @property
    def current_row(self):
        return self.widget_table.highlighted

    def select_row(self, n):
        if n < 0 or n >= self.nrows:
            raise ValueError("n must be between 0 and {}".format(self.nrows-1))

        # compute and set the appropriate page
        # NOTE: traitlets won't detect internal changes to a dict
        options = self.widget_table.get_state()['options']
        page = int(n / options['itemsPerPage']) + 1
        if options['page'] != page:
            self.widget_table.set_state({'options': {**options, 'page': page}})
            self.widget_table.send_state()
        # select and highlight the row
        self.widget_table.highlighted = n

    def next_row(self):
        current_row = self.current_row
        new_row = 0 if current_row == self.nrows - 1 else current_row + 1
        self.select_row(new_row)

    def prev_row(self):
        current_row = self.current_row
        new_row = self.nrows - 1 if current_row == 0 else current_row - 1
        self.select_row(new_row)

    def _on_row_selected(self, event):
        if self._on_row_selected_begin:
            self._on_row_selected_begin(event)

        self.row_selection_in_progress = True
        # Grab the index of the latest selected row
        selected_index = event['new']
        mos_data = self.session.data_collection['MOS Table']

        # plugin data entries: select all in new row, deselect all others
        for data_item in self.jdaviz_app.data_collection:
            if data_item.meta.get('Plugin') is not None:
                if data_item.meta.get('mosviz_row') == selected_index:
                    self.session.hub.broadcast(AddDataToViewerMessage(
                        'spectrum-viewer', data_item.label, sender=self))
                else:
                    self.session.hub.broadcast(RemoveDataFromViewerMessage(
                        'spectrum-viewer', data_item.label, sender=self))

        for component in mos_data.components:
            comp_data = mos_data.get_component(component).data
            selected_data = comp_data[selected_index]

            if component.label == '1D Spectra':
                prev_data = self._selected_data.get('spectrum-viewer')
                if prev_data != selected_data:
                    if prev_data:
                        # This covers the cases where data is unit converted
                        # and the name is modified
                        all_prev_data = [x
                                         for x in self.session.data_collection.labels
                                         if prev_data in x]
                        for modified_prev_data in all_prev_data:
                            if modified_prev_data:
                                remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                                    'spectrum-viewer', modified_prev_data, sender=self)
                                self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        'spectrum-viewer', selected_data, sender=self)
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data['spectrum-viewer'] = selected_data

            if component.label == '2D Spectra':
                prev_data = self._selected_data.get('spectrum-2d-viewer')
                if prev_data != selected_data:
                    if prev_data:
                        remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                            'spectrum-2d-viewer', prev_data, sender=self)
                        self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        'spectrum-2d-viewer', selected_data, sender=self)
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data['spectrum-2d-viewer'] = selected_data

            if component.label == 'Images':
                prev_data = self._selected_data.get('image-viewer')
                if prev_data != selected_data:
                    if prev_data:
                        remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                            'image-viewer', prev_data, sender=self)
                        self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        'image-viewer', selected_data, sender=self)
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data['image-viewer'] = selected_data

        message = TableClickMessage(selected_index=selected_index,
                                    shared_image=self._shared_image,
                                    sender=self)
        self.session.hub.broadcast(message)

        self.row_selection_in_progress = False

        if self._on_row_selected_end:
            self._on_row_selected_end(event)

    def set_plot_axes(self, *args, **kwargs):
        return
