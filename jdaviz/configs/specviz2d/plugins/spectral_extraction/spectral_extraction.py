import numpy as np

from traitlets import Bool, List, Unicode, observe


from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelect,
                                        AddResults)
from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.marks import (TraceLine,
                               ShadowLine)

from specutils import Spectrum1D
from specreduce import tracing
from specreduce import background
from specreduce import extract

__all__ = ['SpectralExtraction']


@tray_registry('spectral-extraction', label="Spectral Extraction")
class SpectralExtraction(PluginTemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "spectral_extraction.vue"

    active_step = Unicode().tag(sync=True)

    # TRACE
    trace_trace_items = List().tag(sync=True)
    trace_trace_selected = Unicode().tag(sync=True)

    trace_offset = IntHandleEmpty(0).tag(sync=True)

    trace_dataset_items = List().tag(sync=True)
    trace_dataset_selected = Unicode().tag(sync=True)

    trace_type_items = List(['FlatTrace', 'AutoTrace']).tag(sync=True)
    trace_type_selected = Unicode('FlatTrace').tag(sync=True)

    trace_pixel = IntHandleEmpty(0).tag(sync=True)

    trace_peak_method_items = List(['Gaussian', 'Centroid', 'Max']).tag(sync=True)
    trace_peak_method_selected = Unicode('Gaussian').tag(sync=True)

    trace_bins = IntHandleEmpty(20).tag(sync=True)
    trace_window = IntHandleEmpty(0).tag(sync=True)

    trace_results_label = Unicode().tag(sync=True)
    trace_results_label_default = Unicode().tag(sync=True)
    trace_results_label_auto = Bool(True).tag(sync=True)
    trace_results_label_invalid_msg = Unicode('').tag(sync=True)
    trace_results_label_overwrite = Bool().tag(sync=True)
    trace_add_to_viewer_items = List().tag(sync=True)
    trace_add_to_viewer_selected = Unicode().tag(sync=True)

    # BACKGROUND
    bg_dataset_items = List().tag(sync=True)
    bg_dataset_selected = Unicode().tag(sync=True)

    bg_type_items = List(['TwoSided', 'OneSided', 'Trace']).tag(sync=True)
    bg_type_selected = Unicode('TwoSided').tag(sync=True)

    bg_trace_items = List().tag(sync=True)
    bg_trace_selected = Unicode().tag(sync=True)

    bg_trace_pixel = IntHandleEmpty(0).tag(sync=True)

    bg_separation = IntHandleEmpty(0).tag(sync=True)
    bg_width = IntHandleEmpty(0).tag(sync=True)

    bg_results_label = Unicode().tag(sync=True)
    bg_results_label_default = Unicode().tag(sync=True)
    bg_results_label_auto = Bool(True).tag(sync=True)
    bg_results_label_invalid_msg = Unicode('').tag(sync=True)
    bg_results_label_overwrite = Bool().tag(sync=True)
    bg_add_to_viewer_items = List().tag(sync=True)
    bg_add_to_viewer_selected = Unicode().tag(sync=True)

    bg_sub_results_label = Unicode().tag(sync=True)
    bg_sub_results_label_default = Unicode().tag(sync=True)
    bg_sub_results_label_auto = Bool(True).tag(sync=True)
    bg_sub_results_label_invalid_msg = Unicode('').tag(sync=True)
    bg_sub_results_label_overwrite = Bool().tag(sync=True)
    bg_sub_add_to_viewer_items = List().tag(sync=True)
    bg_sub_add_to_viewer_selected = Unicode().tag(sync=True)

    # EXTRACT
    ext_dataset_items = List().tag(sync=True)
    ext_dataset_selected = Unicode().tag(sync=True)

    ext_trace_items = List().tag(sync=True)
    ext_trace_selected = Unicode().tag(sync=True)

    ext_trace_pixel = IntHandleEmpty(0).tag(sync=True)
    ext_width = IntHandleEmpty(0).tag(sync=True)

    ext_results_label = Unicode().tag(sync=True)
    ext_results_label_default = Unicode().tag(sync=True)
    ext_results_label_auto = Bool(True).tag(sync=True)
    ext_results_label_invalid_msg = Unicode('').tag(sync=True)
    ext_results_label_overwrite = Bool().tag(sync=True)
    ext_add_to_viewer_items = List().tag(sync=True)
    ext_add_to_viewer_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._marks = {}

        # TRACE
        self.trace_trace = DatasetSelect(self,
                                         'trace_trace_items',
                                         'trace_trace_selected',
                                         default_text='New Trace',
                                         filters=['is_trace'])

        self.trace_dataset = DatasetSelect(self,
                                           'trace_dataset_items',
                                           'trace_dataset_selected',
                                           filters=['layer_in_spectrum_2d_viewer', 'not_trace'])

        self.trace_add_results = AddResults(self, 'trace_results_label',
                                            'trace_results_label_default',
                                            'trace_results_label_auto',
                                            'trace_results_label_invalid_msg',
                                            'trace_results_label_overwrite',
                                            'trace_add_to_viewer_items',
                                            'trace_add_to_viewer_selected')
        self.trace_add_results.viewer.filters = ['is_spectrum_2d_viewer']
        self.trace_results_label_default = 'trace'

        # BACKGROUND
        self.bg_dataset = DatasetSelect(self,
                                        'bg_dataset_items',
                                        'bg_dataset_selected',
                                        filters=['layer_in_spectrum_2d_viewer', 'not_trace'])

        self.bg_trace = DatasetSelect(self,
                                      'bg_trace_items',
                                      'bg_trace_selected',
                                      default_text='From Plugin',
                                      manual_options=['Manual'],
                                      filters=['is_trace'])

        self.bg_add_results = AddResults(self, 'bg_results_label',
                                         'bg_results_label_default',
                                         'bg_results_label_auto',
                                         'bg_results_label_invalid_msg',
                                         'bg_results_label_overwrite',
                                         'bg_add_to_viewer_items',
                                         'bg_add_to_viewer_selected')
        self.bg_add_results.viewer.filters = ['is_spectrum_2d_viewer']
        self.bg_results_label_default = 'background'

        self.bg_sub_add_results = AddResults(self, 'bg_sub_results_label',
                                             'bg_sub_results_label_default',
                                             'bg_sub_results_label_auto',
                                             'bg_sub_results_label_invalid_msg',
                                             'bg_sub_results_label_overwrite',
                                             'bg_sub_add_to_viewer_items',
                                             'bg_sub_add_to_viewer_selected')
        self.bg_sub_add_results.viewer.filters = ['is_spectrum_2d_viewer']
        self.bg_sub_results_label_default = 'background-subtracted'

        # EXTRACT
        self.ext_dataset = DatasetSelect(self,
                                         'ext_dataset_items',
                                         'ext_dataset_selected',
                                         default_text='From Plugin',
                                         filters=['layer_in_spectrum_2d_viewer', 'not_trace'])

        self.ext_trace = DatasetSelect(self,
                                       'ext_trace_items',
                                       'ext_trace_selected',
                                       default_text='From Plugin',
                                       manual_options=['Manual'],
                                       filters=['is_trace'])

        self.ext_add_results = AddResults(self, 'ext_results_label',
                                          'ext_results_label_default',
                                          'ext_results_label_auto',
                                          'ext_results_label_invalid_msg',
                                          'ext_results_label_overwrite',
                                          'ext_add_to_viewer_items',
                                          'ext_add_to_viewer_selected')
        self.ext_add_results.viewer.filters = ['is_spectrum_viewer']
        self.ext_results_label_default = 'extracted spectrum'

    @observe('trace_dataset_selected')
    def _trace_dataset_selected(self, msg):
        width = self.trace_dataset.selected_obj.shape[0]
        half_pixel = int(np.floor(width / 2))
        if self.trace_pixel == 0:
            self.trace_pixel = half_pixel
        if self.trace_window == 0:
            self.trace_window = int(np.ceil(width / 10))
        if self.bg_trace_pixel == 0:
            self.bg_trace_pixel = half_pixel
        if self.bg_separation == 0:
            self.bg_separation = int(np.ceil(width / 10))
        if self.bg_width == 0:
            self.bg_width = int(np.ceil(width / 10))
        if self.ext_trace_pixel == 0:
            self.ext_trace_pixel = half_pixel
        if self.ext_width == 0:
            self.ext_width = int(np.ceil(width / 10))

    @observe('plugin_opened')
    def _update_plugin_marks(self, *args):
        if self.active_step == '':
            # on load, default to 'trace' (this will then trigger the observe to update the marks)
            self.active_step = 'trace'
            self._interaction_in_trace_step()
            return

        display_marks = {'trace': ['trace'],
                         'bg': ['trace',
                                'bg1_center', 'bg1_lower', 'bg1_upper',
                                'bg2_center', 'bg2_lower', 'bg2_upper'],
                         'ext': ['trace', 'ext_upper', 'ext_lower']}
        for step, mark in self.marks.items():
            mark.visible = self.plugin_opened and step in display_marks.get(self.active_step, [])

    @property
    def marks(self):
        if self._marks:
            # TODO: replace with cache property?
            return self._marks

        viewer = self.app.get_viewer('spectrum-2d-viewer')
        if not viewer.state.reference_data:
            # we don't have data yet for scales, defer initializing
            return {}

        # then haven't been initialized yet, so initialize with empty
        # marks that will be populated once the first analysis is done.
        self._marks = {'trace': TraceLine(viewer, visible=self.plugin_opened),
                       'ext_lower': TraceLine(viewer, visible=self.plugin_opened),
                       'ext_upper': TraceLine(viewer, visible=self.plugin_opened),
                       'bg1_center': TraceLine(viewer, visible=self.plugin_opened,
                                               line_style='dotted'),
                       'bg1_lower': TraceLine(viewer, visible=self.plugin_opened),
                       'bg1_upper': TraceLine(viewer, visible=self.plugin_opened),
                       'bg2_center': TraceLine(viewer, visible=self.plugin_opened,
                                               line_style='dotted'),
                       'bg2_lower': TraceLine(viewer, visible=self.plugin_opened),
                       'bg2_upper': TraceLine(viewer, visible=self.plugin_opened)}
        shadows = [ShadowLine(mark, shadow_width=2) for mark in self._marks.values()]
        # NOTE: += won't trigger the figure to notice new marks
        viewer.figure.marks = viewer.figure.marks + shadows + list(self._marks.values())

        return self._marks

    @observe('trace_trace_selected', 'trace_offset', 'trace_dataset_selected', 'trace_type_selected',
             'trace_pixel', 'trace_peak_method_selected', 'trace_bins', 'trace_window')
    def _interaction_in_trace_step(self, *args):
        if not self.plugin_opened:
            return
        trace = self.create_trace(add_data=False)
        # TODO: range(len(...)) is a temporary hack for this data displaying in meters instead of pixels
        self.marks['trace'].update_xy(range(len(trace.trace)),
                                      trace.trace)
        self.marks['trace'].line_style = 'solid'
        self.active_step = 'trace'
        self._update_plugin_marks()

    @observe('bg_dataset_selected', 'bg_type_selected', 'bg_trace_selected', 'bg_trace_pixel',
             'bg_separation', 'bg_width')
    def _interaction_in_bg_step(self, *args):
        if not self.plugin_opened:
            return
        trace = self._get_bg_trace()
        # TODO: range(len(...)) is a temporary hack for this data displaying in meters instead of pixels
        self.marks['trace'].update_xy(range(len(trace.trace)),
                                      trace.trace)
        self.marks['trace'].line_style = 'dashed'

        if self.bg_type_selected in ['OneSided', 'TwoSided']:
            self.marks['bg1_center'].update_xy(range(len(trace.trace)),
                                               trace.trace+self.bg_separation)
            self.marks['bg1_lower'].update_xy(range(len(trace.trace)),
                                              trace.trace+self.bg_separation-self.bg_width/2)
            self.marks['bg1_upper'].update_xy(range(len(trace.trace)),
                                              trace.trace+self.bg_separation+self.bg_width/2)
        else:
            self.marks['bg1_center'].update_xy([], [])
            self.marks['bg1_lower'].update_xy(range(len(trace.trace)),
                                              trace.trace-self.bg_width/2)
            self.marks['bg1_upper'].update_xy(range(len(trace.trace)),
                                              trace.trace+self.bg_width/2)

        if self.bg_type_selected == 'TwoSided':
            self.marks['bg2_center'].update_xy(range(len(trace.trace)),
                                               trace.trace-self.bg_separation)
            self.marks['bg2_lower'].update_xy(range(len(trace.trace)),
                                              trace.trace-self.bg_separation-self.bg_width/2)
            self.marks['bg2_upper'].update_xy(range(len(trace.trace)),
                                              trace.trace-self.bg_separation+self.bg_width/2)
        else:
            self.marks['bg2_center'].update_xy([], [])
            self.marks['bg2_lower'].update_xy([], [])
            self.marks['bg2_upper'].update_xy([], [])

        self.active_step = 'bg'
        self._update_plugin_marks()

    @observe('ext_dataset_selected', 'ext_trace_selected', 'ext_trace_pixel', 'ext_width')
    def _interaction_in_ext_step(self, *args):
        if not self.plugin_opened:
            return
        trace = self._get_ext_trace()
        # TODO: range(len(...)) is a temporary hack for this data displaying in m instead of pixels
        self.marks['trace'].update_xy(range(len(trace.trace)),
                                      trace.trace)
        self.marks['trace'].line_style = 'dashed'
        self.marks['ext_lower'].update_xy(range(len(trace.trace)),
                                          trace.trace-self.ext_width/2)
        self.marks['ext_upper'].update_xy(range(len(trace.trace)),
                                          trace.trace+self.ext_width/2)
        self.active_step = 'ext'
        self._update_plugin_marks()

    def create_trace(self, add_data=True):
        if self.trace_trace_selected != 'New Trace':
            # then we're offsetting an existing trace
            trace = self.trace_trace.selected_obj
            trace.shift(self.trace_offset)

        elif self.trace_type_selected == 'FlatTrace':
            trace = tracing.FlatTrace(self.trace_dataset.selected_obj.data,
                                      self.trace_pixel)

        elif self.trace_type_selected == 'AutoTrace':
            trace = tracing.KosmosTrace(self.trace_dataset.selected_obj.data,
                                        guess=self.trace_pixel,
                                        bins=self.trace_bins,
                                        window=self.trace_window,
                                        peak_method=self.trace_peak_method_selected.lower())

        else:
            raise NotImplementedError(f"trace_type={self.trace_type_selected} not implemented")

        if add_data:
            self.trace_add_results.add_results_from_plugin(trace, replace=False)

        return trace

    def vue_create_trace(self, *args):
        _ = self.create_trace(add_data=True)

    def _get_bg_trace(self):
        if self.bg_trace_selected == 'From Plugin':
            trace = self.create_trace(add_data=False)
        elif self.bg_trace_selected == 'Manual':
            trace = tracing.FlatTrace(self.bg_dataset.selected_obj.data,
                                      self.bg_trace_pixel)
        else:
            trace = self.bg_trace.selected_obj

        return trace

    def _get_bg(self):
        trace = self._get_bg_trace()

        if self.bg_type_selected == 'Trace':
            bg = background.Background(self.bg_dataset.selected_obj.data,
                                       trace, width=self.bg_width)
        elif self.bg_type_selected == 'OneSided':
            bg = background.Background.one_sided(self.bg_dataset.selected_obj.data,
                                                 trace,
                                                 self.bg_separation,
                                                 width=self.bg_width)
        elif self.bg_type_selected == 'TwoSided':
            bg = background.Background.one_sided(self.bg_dataset.selected_obj.data,
                                                 trace,
                                                 self.bg_separation,
                                                 width=self.bg_width)
        else:
            raise NotImplementedError(f"bg_type={self.bg_type_selected} not implemented")

        return bg

    def create_bg(self, add_data=True):
        bg = self._get_bg()

        bg_spec = Spectrum1D(spectral_axis=self.bg_dataset.selected_obj.spectral_axis,
                             flux=bg.bkg_image()*self.bg_dataset.selected_obj.flux.unit)

        if add_data:
            self.bg_add_results.add_results_from_plugin(bg_spec, replace=True)

        return bg_spec

    def vue_create_bg(self, *args):
        _ = self.create_bg(add_data=True)

    def create_bg_sub(self, add_data=True):
        bg = self._get_bg()

        bg_sub_spec = Spectrum1D(spectral_axis=self.bg_dataset.selected_obj.spectral_axis,
                                 flux=bg.sub_image()*self.bg_dataset.selected_obj.flux.unit)

        if add_data:
            self.bg_sub_add_results.add_results_from_plugin(bg_sub_spec, replace=True)

        return bg_sub_spec

    def vue_create_bg_sub(self, *args):
        _ = self.create_bg_sub(add_data=True)

    def _get_ext_trace(self):
        if self.ext_trace_selected == 'From Plugin':
            trace = self.create_trace(add_data=False)
        elif self.ext_trace_selected == 'Manual':
            # NOTE: we use trace_dataset here assuming its the same shape,
            # to avoid needing to create the background-subtracted image
            # if self.trace_dataset_selected == 'From Plugin'
            trace = tracing.FlatTrace(self.trace_dataset.selected_obj.data,
                                      self.ext_trace_pixel)
        else:
            trace = self.ext_trace.get_selected_obj

        return trace

    def create_extract(self, add_data=False):
        if self.ext_dataset_selected == 'From Plugin':
            inp_image = self.create_bg_sub(add_data=False).data
        else:
            inp_image = self.ext_dataset.selected_obj.data

        trace = self._get_ext_trace()

        boxcar = extract.BoxcarExtract()
        spectrum = boxcar(inp_image, trace, width=self.ext_width)

        if add_data:
            self.ext_add_results.add_results_from_plugin(spectrum, replace=False)

        return spectrum

    def vue_extract(self, *args):
        _ = self.create_extract(add_data=True)
