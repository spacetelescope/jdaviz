import numpy as np

from traitlets import Bool, List, Unicode, observe


from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelect,
                                        AddResults)
from jdaviz.core.custom_traitlets import IntHandleEmpty

from specreduce import tracing

__all__ = ['SpectralExtraction']


@tray_registry('spectral-extraction', label="Spectral Extraction")
class SpectralExtraction(PluginTemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "spectral_extraction.vue"

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
            self.trace_trace.selected = self.trace_results_label
        return trace

    def vue_create_trace(self, *args):
        _ = self.create_trace(add_data=True)

    def vue_create_bg(self, *args):
        raise NotImplementedError()

    def vue_create_bg_sub(self, *args):
        raise NotImplementedError()

    def vue_extract(self, *args):
        raise NotImplementedError()
