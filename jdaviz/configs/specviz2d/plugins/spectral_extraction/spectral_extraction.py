import numpy as np

from traitlets import Bool, List, Unicode, observe


from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelect,
                                        AddResults)
from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.marks import PluginLine

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
    setting_interactive_extract = Bool(True).tag(sync=True)

    # TRACE
    trace_dataset_items = List().tag(sync=True)
    trace_dataset_selected = Unicode().tag(sync=True)

    trace_type_items = List(['Flat', 'Auto']).tag(sync=True)
    trace_type_selected = Unicode('Flat').tag(sync=True)

    trace_pixel = IntHandleEmpty(0).tag(sync=True)

    trace_bins = IntHandleEmpty(20).tag(sync=True)
    trace_window = IntHandleEmpty(0).tag(sync=True)

    # BACKGROUND
    bg_dataset_items = List().tag(sync=True)
    bg_dataset_selected = Unicode().tag(sync=True)

    bg_type_items = List(['TwoSided', 'OneSided', 'Manual']).tag(sync=True)
    bg_type_selected = Unicode('TwoSided').tag(sync=True)

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
        self._do_marks = kwargs.get('interactive', True)

        # TRACE
        self.trace_dataset = DatasetSelect(self,
                                           'trace_dataset_items',
                                           'trace_dataset_selected',
                                           filters=['layer_in_spectrum_2d_viewer', 'not_trace'])

        # BACKGROUND
        self.bg_dataset = DatasetSelect(self,
                                        'bg_dataset_items',
                                        'bg_dataset_selected',
                                        filters=['layer_in_spectrum_2d_viewer', 'not_trace'])

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

        self.ext_add_results = AddResults(self, 'ext_results_label',
                                          'ext_results_label_default',
                                          'ext_results_label_auto',
                                          'ext_results_label_invalid_msg',
                                          'ext_results_label_overwrite',
                                          'ext_add_to_viewer_items',
                                          'ext_add_to_viewer_selected')
        self.ext_add_results.viewer.filters = ['is_spectrum_viewer']
        # NOTE: defaults to overwriting original spectrum
        self.ext_add_results.label_whitelist_overwrite = ['Spectrum 1D']
        self.ext_results_label_default = 'Spectrum 1D'

    @observe('trace_dataset_selected')
    def _trace_dataset_selected(self, msg=None):
        if not hasattr(self, 'trace_dataset'):
            # happens when first initializing plugin outside of tray
            return

        width = self.trace_dataset.selected_obj.shape[0]
        # estimate the pixel number by taking the median of the brightest pixel index in each column
        brightest_pixel = int(np.median(np.argmax(self.trace_dataset.selected_obj.flux, axis=0)))
        # default width will be 10% of cross-dispersion "height"
        default_width = int(np.ceil(width / 10))
        if self.trace_pixel == 0:
            self.trace_pixel = brightest_pixel
        if self.trace_window == 0:
            self.trace_window = default_width
        if self.bg_trace_pixel == 0:
            self.bg_trace_pixel = brightest_pixel
        if self.bg_separation == 0:
            self.bg_separation = default_width * 2
        if self.bg_width == 0:
            self.bg_width = default_width
        if self.ext_width == 0:
            self.ext_width = default_width

    def update_marks(self, step=None):
        """
        Manually update the live-preview marks for a given step in spectral extraction.  This API
        mimics opening the plugin and interacting with one of the steps.

        Parameters
        ----------
        step : str
            Step in the extraction process to visualize.  Must be one of: 'trace', 'bg', 'ext'.
        """
        if step is not None:
            if step not in ['trace', 'bg', 'ext']:
                raise ValueError("step must be one of: trace, bg, ext")
            self.active_step = step
        self.plugin_opened = True

    def clear_marks(self):
        """
        Manually clear the live-preview marks.
        """
        self.plugin_opened = False

    @observe('plugin_opened', 'setting_interactive_extract')
    def _update_plugin_marks(self, *args):
        if not self._do_marks:
            return

        if not self.plugin_opened:
            for step, mark in self.marks.items():
                mark.visible = False
            return

        if self.active_step == '':
            # on load, default to 'extract' (this will then trigger the observe to update the marks)
            self._interaction_in_ext_step()
            return

        # update extracted 1d spectrum preview, regardless of the step
        if self.setting_interactive_extract:
            try:
                sp1d = self.create_extract(add_data=False)
            except Exception:
                # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
                # NOTE: KosmosTrace or manual background are often giving a
                # "background regions overlapped" error from specreduce
                self.marks['extract'].clear()
            else:
                self.marks['extract'].update_xy(sp1d.spectral_axis.value,
                                                sp1d.flux.value)
        else:
            self.marks['extract'].clear()

        display_marks = {'trace': ['trace', 'extract'],
                         'bg': ['trace',
                                'bg1_center', 'bg1_lower', 'bg1_upper',
                                'bg2_center', 'bg2_lower', 'bg2_upper',
                                'extract'],
                         'ext': ['trace',
                                 'ext_upper', 'ext_lower',
                                 'extract']}
        for step, mark in self.marks.items():
            mark.visible = step in display_marks.get(self.active_step, [])

    @property
    def marks(self):
        """
        Access the marks created by this plugin in both the spectrum-viewer and spectrum-2d-viewer.
        """
        if self._marks:
            # TODO: replace with cache property?
            return self._marks

        if not self._do_marks:
            return {}

        viewer2d = self.app.get_viewer('spectrum-2d-viewer')
        viewer1d = self.app.get_viewer('spectrum-viewer')
        if not viewer2d.state.reference_data or not viewer1d.state.reference_data:
            # we don't have data yet for scales, defer initializing
            return {}

        # then haven't been initialized yet, so initialize with empty
        # marks that will be populated once the first analysis is done.
        self._marks = {'trace': PluginLine(viewer2d, visible=self.plugin_opened),
                       'ext_lower': PluginLine(viewer2d, visible=self.plugin_opened),
                       'ext_upper': PluginLine(viewer2d, visible=self.plugin_opened),
                       'bg1_center': PluginLine(viewer2d, visible=self.plugin_opened,
                                                line_style='dotted'),
                       'bg1_lower': PluginLine(viewer2d, visible=self.plugin_opened),
                       'bg1_upper': PluginLine(viewer2d, visible=self.plugin_opened),
                       'bg2_center': PluginLine(viewer2d, visible=self.plugin_opened,
                                                line_style='dotted'),
                       'bg2_lower': PluginLine(viewer2d, visible=self.plugin_opened),
                       'bg2_upper': PluginLine(viewer2d, visible=self.plugin_opened)}
        # NOTE: += won't trigger the figure to notice new marks
        viewer2d.figure.marks = viewer2d.figure.marks + list(self._marks.values())

        mark1d = PluginLine(viewer1d, visible=self.plugin_opened)
        self._marks['extract'] = mark1d

        # NOTE: += won't trigger the figure to notice new marks
        viewer1d.figure.marks = viewer1d.figure.marks + [mark1d]

        return self._marks

    @observe('trace_dataset_selected', 'trace_type_selected',
             'trace_pixel', 'trace_bins', 'trace_window', 'active_step')
    def _interaction_in_trace_step(self, event={}):
        if not self.plugin_opened or not self._do_marks:
            return
        if event.get('name', '') == 'active_step' and event.get('new') != 'trace':
            return

        try:
            trace = self.create_trace(add_data=False)
        except Exception:
            # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
            self.marks['trace'].clear()
        else:
            self.marks['trace'].update_xy(range(len(trace.trace)),
                                          trace.trace)
            self.marks['trace'].line_style = 'solid'
        self.active_step = 'trace'
        self._update_plugin_marks()

    @observe('bg_dataset_selected', 'bg_type_selected', 'bg_trace_pixel',
             'bg_separation', 'bg_width', 'active_step')
    def _interaction_in_bg_step(self, event={}):
        if not self.plugin_opened or not self._do_marks:
            return
        if event.get('name', '') == 'active_step' and event.get('new') != 'bg':
            return

        try:
            trace = self._get_bg_trace()
        except Exception:
            # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
            for mark in ['trace', 'bg1_center', 'bg1_lower', 'bg1_upper',
                         'bg2_center', 'bg2_lower', 'bg2_upper']:
                self.marks[mark].clear()
        else:
            xs = range(len(trace.trace))
            self.marks['trace'].update_xy(xs,
                                          trace.trace)
            self.marks['trace'].line_style = 'dashed'

            if self.bg_type_selected in ['OneSided', 'TwoSided']:
                self.marks['bg1_center'].update_xy(xs,
                                                   trace.trace+self.bg_separation)
                self.marks['bg1_lower'].update_xy(xs,
                                                  trace.trace+self.bg_separation-self.bg_width/2)
                self.marks['bg1_upper'].update_xy(xs,
                                                  trace.trace+self.bg_separation+self.bg_width/2)
            else:
                self.marks['bg1_center'].clear()
                self.marks['bg1_lower'].update_xy(xs,
                                                  trace.trace-self.bg_width/2)
                self.marks['bg1_upper'].update_xy(xs,
                                                  trace.trace+self.bg_width/2)

            if self.bg_type_selected == 'TwoSided':
                self.marks['bg2_center'].update_xy(xs,
                                                   trace.trace-self.bg_separation)
                self.marks['bg2_lower'].update_xy(xs,
                                                  trace.trace-self.bg_separation-self.bg_width/2)
                self.marks['bg2_upper'].update_xy(xs,
                                                  trace.trace-self.bg_separation+self.bg_width/2)
            else:
                for mark in ['bg2_center', 'bg2_lower', 'bg2_upper']:
                    self.marks[mark].clear()

        self.active_step = 'bg'
        self._update_plugin_marks()

    @observe('ext_dataset_selected', 'ext_width', 'active_step')
    def _interaction_in_ext_step(self, event={}):
        if not self.plugin_opened or not self._do_marks:
            return
        if event.get('name', '') == 'active_step' and event.get('new') != 'ext':
            return

        try:
            trace = self._get_ext_trace()
        except Exception:
            # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
            for mark in ['trace', 'ext_lower', 'ext_upper']:
                self.marks[mark].clear()
        else:
            xs = range(len(trace.trace))
            self.marks['trace'].update_xy(xs,
                                          trace.trace)
            self.marks['trace'].line_style = 'dashed'
            self.marks['ext_lower'].update_xy(xs,
                                              trace.trace-self.ext_width/2)
            self.marks['ext_upper'].update_xy(xs,
                                              trace.trace+self.ext_width/2)

        self.active_step = 'ext'
        self._update_plugin_marks()

    def create_trace(self, add_data=False):
        """
        Create a trace object from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting trace to the application, according to the options
            defined in the plugin.
        """
        if self.trace_type_selected == 'Flat':
            trace = tracing.FlatTrace(self.trace_dataset.selected_obj.data,
                                      self.trace_pixel)

        elif self.trace_type_selected == 'Auto':
            trace = tracing.KosmosTrace(self.trace_dataset.selected_obj.data,
                                        guess=self.trace_pixel,
                                        bins=self.trace_bins,
                                        window=self.trace_window)

        else:
            raise NotImplementedError(f"trace_type={self.trace_type_selected} not implemented")

        if add_data:
            raise NotImplementedError("exporting trace to data entry not yet supported")

        return trace

    def vue_create_trace(self, *args):
        _ = self.create_trace(add_data=True)

    def _get_bg_trace(self):
        if self.bg_type_selected == 'Manual':
            trace = tracing.FlatTrace(self.trace_dataset.selected_obj.data,
                                      self.bg_trace_pixel)
        else:
            trace = self.create_trace(add_data=False)

        return trace

    def _get_bg(self):
        trace = self._get_bg_trace()

        if self.bg_type_selected == 'Manual':
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

    def create_bg(self, add_data=False):
        """
        Create a background 2D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting image to the application, according to the options
            defined in the plugin.
        """
        bg = self._get_bg()

        bg_spec = Spectrum1D(spectral_axis=self.bg_dataset.selected_obj.spectral_axis,
                             flux=bg.bkg_image()*self.bg_dataset.selected_obj.flux.unit)

        if add_data:
            self.bg_add_results.add_results_from_plugin(bg_spec, replace=True)

        return bg_spec

    def vue_create_bg(self, *args):
        _ = self.create_bg(add_data=True)

    def create_bg_sub(self, add_data=False):
        """
        Create a background-subtracted 2D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting image to the application, according to the options
            defined in the plugin.
        """
        bg = self._get_bg()

        bg_sub_spec = Spectrum1D(spectral_axis=self.bg_dataset.selected_obj.spectral_axis,
                                 flux=bg.sub_image()*self.bg_dataset.selected_obj.flux.unit)

        if add_data:
            self.bg_sub_add_results.add_results_from_plugin(bg_sub_spec, replace=True)

        return bg_sub_spec

    def vue_create_bg_sub(self, *args):
        _ = self.create_bg_sub(add_data=True)

    def _get_ext_trace(self):
        return self.create_trace(add_data=False)

    def _get_ext_input_spectrum(self):
        if self.ext_dataset_selected == 'From Plugin':
            return self.create_bg_sub(add_data=False)
        else:
            return self.ext_dataset.selected_obj

    def create_extract(self, add_data=False):
        """
        Create an extracted 1D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting spectrum to the application, according to the options
            defined in the plugin.
        """
        inp_sp2d = self._get_ext_input_spectrum()
        trace = self._get_ext_trace()

        boxcar = extract.BoxcarExtract()
        spectrum = boxcar(inp_sp2d.data, trace, width=self.ext_width)
        # Specreduce returns a spectral axis in pixels, so we'll replace with input spectral_axis
        # NOTE: this is currently disabled until proper handling of axes-limit linking between
        # the 2D spectrum image (plotted in pixels) and a 1D spectrum (plotted in freq or
        # wavelength) is implemented.

        # spectrum = Spectrum1D(spectral_axis=inp_sp2d.spectral_axis, flux=spectrum.flux)

        if add_data:
            self.ext_add_results.add_results_from_plugin(spectrum, replace=False)

        return spectrum

    def vue_extract(self, *args):
        _ = self.create_extract(add_data=True)
