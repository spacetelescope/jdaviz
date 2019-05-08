# This provides a simplified version of the bqplot profile viewer

from ipywidgets import Button, VBox, HBox

from glue.core.application_base import Application
from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.widgets import LinkedDropdown
from glue_jupyter.common.slice_helpers import MultiSliceWidgetHelper

__all__ = ['SimpleBqplotProfileViewer', 'simple_profile']


def simple_profile(app, data=None):
    viewer = Application.new_data_viewer(app, SimpleBqplotProfileViewer)
    if data is not None:
        viewer.add_data(data)
    return viewer


class SimpleBqplotProfileViewer(BqplotProfileView):

    def __init__(self, *args, **kwargs):

        # Set up the default profile viewer
        super().__init__(*args, **kwargs)

        # Fix the figure size
        self.figure.layout.width = '600px'
        self.figure.layout.height = '400px'

        # Make sure the selection toolbar is centered
        self.widget_toolbar.layout.justify_content = 'center'

        # Set button to toggle advanced mode
        self.advanced_button = Button(description='Show advanced')
        self.advanced_button.on_click(self._toggle_mode)

        # Set up layouts and override main_widgets
        self.top_layout = HBox([], layout={'justify_content': 'center'})
        self.middle_layout = HBox([self.figure], layout={'justify_content': 'center'})
        self.bottom_layout = HBox([self.advanced_button], layout={'justify_content': 'center'})
        self.main_widget.children = (self.widget_toolbar, self.top_layout, self.middle_layout, self.bottom_layout, self.output_widget)

        # Default to basic mode
        self.advanced = False

        # Update visibility of widgets
        self._update_layout()

        self.state.add_callback('layers', self._on_layers_change)

    def _on_layers_change(self, *args):
        # Show the attribute dropdown when the first dataset is added
        if len(self.top_layout.children) == 0:
            self.attribute_dropdown = LinkedDropdown(self.state.layers[0], 'attribute', label='attribute:')
            self.top_layout.children = (self.attribute_dropdown,)

    def _toggle_mode(self, *args):
        # Switch between basic and advanced mode
        self.advanced = not self.advanced
        self._update_layout()

    def _update_layout(self, *args):
        # Show/hide widgets dependending on whether we are in basic or advanced mode
        if self.advanced:
            self.middle_layout.children = (self.figure, self.tab)
            self.widget_toolbar.children = (self.toolbar,
                                            self.session.application.widget_subset_select,
                                            self.session.application.widget_subset_mode)
            self.advanced_button.description = 'Hide advanced'
        else:
            self.middle_layout.children = (self.figure,)
            self.widget_toolbar.children = (self.toolbar,
                                            self.session.application.widget_subset_select)
            self.advanced_button.description = 'Show advanced'
