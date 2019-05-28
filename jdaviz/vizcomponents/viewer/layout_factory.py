# As described in the glue-jupyter documentation:
# http://glueviz.org/glue-jupyter/developer_notes.html#accessing-individual-parts-of-viewers
# it is possible to customize the layout of viewers. To do this, we need to
# create a single function that takes a viewer and returns the layout to use.

from ipywidgets import VBox, HBox, Button, Tab
from glue_jupyter.common.slice_helpers import MultiSliceWidgetHelper
from glue_jupyter.widgets.linked_dropdown import LinkedDropdown

from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.matplotlib.image import ImageJupyterViewer

__all__ = ['jdaviz_layout_factory']


class JDAVizStandardLayout(VBox):

    def __init__(self, viewer):

        self.viewer = viewer

        self._layout_tab = Tab([self.viewer.viewer_options,
                                self.viewer.layer_options])
        self._layout_tab.set_title(0, "General")
        self._layout_tab.set_title(1, "Layers")

        self._advanced_button = Button(description='Show advanced')
        self._advanced_button.on_click(self._toggle_basic_advanced)

        self._layout_toolbar = HBox([], layout={'justify_content': 'center'})
        self._layout_top = HBox([], layout={'justify_content': 'center'})
        self._layout_middle = HBox([], layout={'justify_content': 'center'})
        self._layout_bottom = HBox([self._advanced_button], layout={'justify_content': 'center'})

        # Default to basic mode
        self.advanced = False

        super().__init__([self._layout_toolbar,
                         self._layout_top,
                         self._layout_middle,
                         self._layout_bottom,
                         self.viewer.output_widget])

        self._update_layout()

    def _toggle_basic_advanced(self, *args):
        # Switch between basic and advanced mode
        self.advanced = not self.advanced
        self._update_layout()

    def _update_layout(self, *args):

        # Show/hide widgets dependending on whether we are in basic or advanced mode

        if self.advanced:

            self._layout_middle.children = (self.viewer.figure_widget, self._layout_tab)
            self._layout_toolbar.children = (self.viewer.toolbar_selection_tools,
                                             self.viewer.toolbar_active_subset,
                                             self.viewer.toolbar_selection_mode)
            self._advanced_button.description = 'Hide advanced'

        else:

            self._layout_middle.children = (self.viewer.figure_widget,)
            self._layout_toolbar.children = (self.viewer.toolbar_selection_tools,
                                             self.viewer.toolbar_active_subset)
            self._advanced_button.description = 'Show advanced'


class JDAVizImageLayout(JDAVizStandardLayout):
    """
    As for the standard layout, but adds a slider and attribute drop-down.
    """

    def __init__(self, viewer):

        super().__init__(viewer)

        # Set up sliders for slices
        self._layout_slice = VBox()
        self._slice_helper = MultiSliceWidgetHelper(self.viewer.state, self._layout_slice)

        self._layout_bottom.children = (self._layout_slice,) + self._layout_bottom.children

        self.viewer.state.add_callback('layers', self._on_layers_change)

    def _on_layers_change(self, *args):
        # Show the attribute dropdown when the first dataset is added
        if len(self._layout_top.children) == 0:
            self._attribute_dropdown = LinkedDropdown(self.viewer.state.layers[0], 'attribute', label='attribute:')
            self._layout_top.children = (self._attribute_dropdown,)


def jdaviz_layout_factory(viewer):

    if isinstance(viewer, (BqplotImageView, ImageJupyterViewer)):
        layout_cls = JDAVizImageLayout
        # viewer.figure.layout.width = '400px'
        # viewer.figure.layout.height = '400px'
    else:
        layout_cls = JDAVizStandardLayout
        # viewer.figure.layout.width = '600px'
        # viewer.figure.layout.height = '400px'

    return layout_cls(viewer)
