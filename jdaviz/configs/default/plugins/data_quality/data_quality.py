import os
from traitlets import Any, Dict, Bool, List, Unicode, Float, observe

import numpy as np
from glue_jupyter.common.toolbar_vuetify import read_icon
from echo import delay_callback
from matplotlib.colors import hex2color

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (
    PluginTemplateMixin, LayerSelect, ViewerSelectMixin
)
from jdaviz.core.tools import ICON_DIR
from jdaviz.configs.default.plugins.data_quality.dq_utils import (
    decode_flags, generate_listed_colormap, dq_flag_map_paths, load_flag_map
)

__all__ = ['DataQuality']

telescope_names = {
    "jwst": "JWST",
    "roman": "Roman"
}


@tray_registry('g-data-quality', label="Data Quality", viewer_requirements="image")
class DataQuality(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "data_quality.vue"

    # TODO: uncomment this line before merging into main:
    # irrelevant_msg = Unicode("Data Quality plugin is in development.").tag(sync=True)

    # `layer` is the science data layer
    science_layer_multiselect = Bool(False).tag(sync=True)
    science_layer_items = List().tag(sync=True)
    science_layer_selected = Any().tag(sync=True)  # Any needed for multiselect

    # `dq_layer` is the data quality layer corresponding to the
    # science data in `layer`
    dq_layer_multiselect = Bool(False).tag(sync=True)
    dq_layer_items = List().tag(sync=True)
    dq_layer_selected = Any().tag(sync=True)  # Any needed for multiselect
    dq_layer_opacity = Float(0.9).tag(sync=True)  # Any needed for multiselect

    flag_map_definitions = Dict().tag(sync=True)
    flag_map_selected = Any().tag(sync=True)
    flag_map_definitions_selected = Dict().tag(sync=True)
    flag_map_items = List().tag(sync=True)
    decoded_flags = List().tag(sync=True)
    flags_filter = List().tag(sync=True)

    icons = Dict().tag(sync=True)
    icon_radialtocheck = Unicode(read_icon(os.path.join(ICON_DIR, 'radialtocheck.svg'), 'svg+xml')).tag(sync=True)  # noqa
    icon_checktoradial = Unicode(read_icon(os.path.join(ICON_DIR, 'checktoradial.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.icons = {k: v for k, v in self.app.state.icons.items()}

        self.science_layer = LayerSelect(
            self, 'science_layer_items', 'science_layer_selected',
            'viewer_selected', 'science_layer_multiselect', is_root=True
        )

        self.dq_layer = LayerSelect(
            self, 'dq_layer_items', 'dq_layer_selected',
            'viewer_selected', 'dq_layer_multiselect', is_root=False,
            is_child_of=self.science_layer.selected
        )

        self.load_default_flag_maps()
        self.init_decoding()

    @observe('science_layer_selected')
    def update_dq_layer(self, *args):
        if not hasattr(self, 'dq_layer'):
            return

        self.dq_layer.filter_is_child_of = self.science_layer_selected
        self.dq_layer._update_layer_items()

        # listen for changes on the image opacity, and update the
        # data quality layer opacity on changes to the science layer opacity
        plot_options = self.app.get_tray_item_from_name('g-plot-options')
        plot_options.observe(self.update_opacity, 'image_opacity_value')

    def load_default_flag_maps(self):
        for name in dq_flag_map_paths:
            self.flag_map_definitions[name] = load_flag_map(name)
            self.flag_map_items = self.flag_map_items + [telescope_names[name]]

    @property
    def unique_flags(self):
        selected_dq = self.dq_layer.selected_obj
        if not len(selected_dq):
            return []

        dq = selected_dq[0].get_image_data()
        return np.unique(dq[~np.isnan(dq)])

    @property
    def validate_flag_decode_possible(self):
        return (
            self.flag_map_selected is not None and
            len(self.dq_layer.selected_obj) > 0
        )

    @observe('flag_map_selected')
    def update_flag_map_definitions_selected(self, event):
        selected = self.flag_map_definitions[self.flag_map_selected.lower()]
        self.flag_map_definitions_selected = selected

    @observe('dq_layer_selected')
    def init_decoding(self, event={}):
        if not self.validate_flag_decode_possible:
            return

        unique_flags = self.unique_flags
        cmap, rgba_colors = generate_listed_colormap(n_flags=len(unique_flags))
        self.decoded_flags = decode_flags(
            flag_map=self.flag_map_definitions_selected,
            unique_flags=unique_flags,
            rgba_colors=rgba_colors
        )
        dq_layer = self.get_dq_layer()
        dq_layer.composite._allow_bad_alpha = True

        flag_bits = np.array([flag['flag'] for flag in self.decoded_flags])

        dq_layer.state.stretch = 'lookup'
        stretch_object = dq_layer.state.stretch_object
        stretch_object.flags = flag_bits

        with delay_callback(dq_layer.state, 'alpha', 'cmap', 'v_min', 'v_max'):
            if len(flag_bits):
                dq_layer.state.v_min = min(flag_bits)
                dq_layer.state.v_max = max(flag_bits)

            dq_layer.state.alpha = self.dq_layer_opacity
            dq_layer.state.cmap = cmap

    def get_dq_layer(self):
        if self.dq_layer_selected == '':
            return

        viewer = self.viewer.selected_obj
        [dq_layer] = [
            layer for layer in viewer.layers if
            layer.layer.label == self.dq_layer_selected
        ]
        return dq_layer

    def get_science_layer(self):
        viewer = self.viewer.selected_obj
        [science_layer] = [
            layer for layer in viewer.layers if
            layer.layer.label == self.science_layer_selected
        ]
        return science_layer

    @observe('dq_layer_opacity')
    def update_opacity(self, event={}):
        science_layer = self.get_science_layer()
        dq_layer = self.get_dq_layer()

        if dq_layer is not None:
            # DQ opacity is a fraction of the science layer's opacity:
            dq_layer.state.alpha = self.dq_layer_opacity * science_layer.state.alpha

    @observe('decoded_flags', 'flags_filter')
    def update_cmap(self, event={}):
        dq_layer = self.get_dq_layer()
        flag_bits = np.array([flag['flag'] for flag in self.decoded_flags])
        rgb_colors = [hex2color(flag['color']) for flag in self.decoded_flags]

        hidden_flags = np.array([
            flag['flag'] for flag in self.decoded_flags

            # hide the flag if the visibility toggle is False:
            if not flag['show'] or

            # hide the flag if `flags_filter` has entries but not this one:
            (
                len(self.flags_filter) and
                not np.isin(list(flag['decomposed'].keys()), list(self.flags_filter)).any()
            )
        ])

        with delay_callback(dq_layer.state, 'v_min', 'v_max', 'alpha', 'stretch', 'cmap'):
            # set correct stretch and limits:
            # dq_layer.state.stretch = 'lookup'
            stretch_object = dq_layer.state.stretch_object
            stretch_object.flags = flag_bits
            stretch_object.dq_array = dq_layer.get_image_data()
            stretch_object.hidden_flags = hidden_flags

            # update the colors of the listed colormap without
            # reassigning the layer.state.cmap object
            cmap = dq_layer.state.cmap
            cmap.colors = rgb_colors
            cmap._init()

            # trigger updates to cmap in viewer:
            dq_layer.update()

            if len(flag_bits):
                dq_layer.state.v_min = min(flag_bits)
                dq_layer.state.v_max = max(flag_bits)

            dq_layer.state.alpha = self.dq_layer_opacity

    def update_visibility(self, index):
        self.decoded_flags[index]['show'] = not self.decoded_flags[index]['show']
        self.send_state('decoded_flags')
        self.update_cmap()

    def vue_update_visibility(self, index):
        self.update_visibility(index)

    def update_color(self, index, color):
        self.decoded_flags[index]['color'] = color
        self.send_state('decoded_flags')
        self.update_cmap()

    def vue_update_color(self, args):
        index, color = args
        self.update_color(index, color)

    @observe('science_layer_selected')
    def mission_or_instrument_from_meta(self, event):
        if not hasattr(self, 'science_layer'):
            return

        layer = self.science_layer.selected_obj
        if not len(layer):
            return

        # this is defined for JWST and ROMAN, should be upper case:
        telescope = layer[0].layer.meta.get('telescope', None)

        if telescope is not None:
            self.flag_map_selected = telescope_names[telescope.lower()]

    def vue_hide_all_flags(self, event):
        for flag in self.decoded_flags:
            flag['show'] = False

        self.send_state('decoded_flags')
        self.update_cmap()

    def vue_clear_flags_filter(self, event):
        self.flags_filter = []

    def vue_show_all_flags(self, event):
        for flag in self.decoded_flags:
            flag['show'] = True

        self.send_state('decoded_flags')
        self.flags_filter = []
