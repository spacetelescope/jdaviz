import numpy as np

from traitlets import Bool, List, Unicode, observe


from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        SelectPluginComponent,
                                        DatasetSelect,
                                        AddResults)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.marks import PluginLine

from astropy.nddata import NDData, StdDevUncertainty, VarianceUncertainty, UnknownUncertainty
from specutils import Spectrum1D
from specreduce import tracing
from specreduce import background
from specreduce import extract

__all__ = ['SpectralExtraction']


@tray_registry('spectral-extraction', label="Spectral Extraction")
class SpectralExtraction(PluginTemplateMixin):
    """
    The Spectral Extraction plugin exposes specreduce methods for tracing, background subtraction,
    and spectral extraction from 2D spectra.
    See the :ref:`Spectral Extraction Plugin Documentation <specviz2d-spectral-extraction>`
    for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :attr:`interactive_extract`
    * ``trace_dataset`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      controls the input dataset for generating the trace.
    * ``trace_type`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      controls the type of trace to be generated.
    * ``trace_peak_method`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      only applicable if ``trace_type`` is set to ``Auto``.
    * :attr:`trace_pixel` :
      pixel of the trace.  If ``trace_type`` is set to ``Auto``, then this
      is the "guess" for the automated trace.
    * :attr:`trace_bins` :
      only applicable if ``trace_type`` is set to ``Auto``.
    * :attr:`trace_window` :
      full width of the trace.
    * :meth:`import_trace`
    * :meth:`export_trace`
    * ``bg_dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      controls the input dataset for generating the background.
    * ``bg_type`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      controls the type of background to be generated.
    * :attr:`bg_trace_pixel` :
      only applicable if ``bg_type`` is set to ``Manual``
    * :attr:`bg_separation` :
      only applicable if ``bg_type`` set set to ``OneSided`` or ``TwoSided``.
      Separation from the referenced trace for the center of each of the background window(s).
    * :attr:`bg_width` :
      full width of each background window(s).
    * ``bg_add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * ``bg_sub_add_results``
    * :meth:`import_bg`
    * :meth:`export_bg`
    * :meth:`export_bg_img`
    * :meth:`export_bg_sub`
    * ``ext_dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      controls the input dataset for generating the extracted spectrum.  "From Plugin" will
      use the background-subtracted image as defined by the background options above.  To skip
      background extraction, select the original input 2D spectrum.
    * ``ext_trace`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`)
    * ``ext_type`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * :attr:`ext_width` :
      full width of the extraction window.
    * ``ext_add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`import_extract`
    * :meth:`export_extract`
    * :meth:`export_extract_spectrum`
    """
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "spectral_extraction.vue"

    active_step = Unicode().tag(sync=True)
    interactive_extract = Bool(True).tag(sync=True)

    # TRACE
    trace_trace_items = List().tag(sync=True)
    trace_trace_selected = Unicode().tag(sync=True)

    trace_offset = IntHandleEmpty(0).tag(sync=True)

    trace_dataset_items = List().tag(sync=True)
    trace_dataset_selected = Unicode().tag(sync=True)

    trace_type_items = List().tag(sync=True)
    trace_type_selected = Unicode().tag(sync=True)

    trace_pixel = FloatHandleEmpty(0).tag(sync=True)

    trace_peak_method_items = List().tag(sync=True)
    trace_peak_method_selected = Unicode().tag(sync=True)

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

    bg_type_items = List().tag(sync=True)
    bg_type_selected = Unicode().tag(sync=True)

    bg_trace_items = List().tag(sync=True)
    bg_trace_selected = Unicode().tag(sync=True)

    bg_trace_pixel = FloatHandleEmpty(0).tag(sync=True)

    bg_separation = FloatHandleEmpty(0).tag(sync=True)
    bg_width = FloatHandleEmpty(0).tag(sync=True)

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

    ext_type_items = List().tag(sync=True)
    ext_type_selected = Unicode().tag(sync=True)

    ext_width = FloatHandleEmpty(0).tag(sync=True)

    ext_uncert_warn = Bool(False).tag(sync=True)
    ext_specreduce_err = Unicode().tag(sync=True)

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
        self.trace_trace = DatasetSelect(self,
                                         'trace_trace_items',
                                         'trace_trace_selected',
                                         default_text='New Trace',
                                         filters=['is_trace'])

        self.trace_dataset = DatasetSelect(self,
                                           'trace_dataset_items',
                                           'trace_dataset_selected',
                                           filters=['layer_in_spectrum_2d_viewer', 'not_trace'])

        self.trace_type = SelectPluginComponent(self,
                                                items='trace_type_items',
                                                selected='trace_type_selected',
                                                manual_options=['Flat', 'Auto'])

        self.trace_peak_method = SelectPluginComponent(self,
                                                       items='trace_peak_method_items',
                                                       selected='trace_peak_method_selected',
                                                       manual_options=['Gaussian', 'Centroid' 'Max'])  # noqa

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

        self.bg_type = SelectPluginComponent(self,
                                             items='bg_type_items',
                                             selected='bg_type_selected',
                                             manual_options=['TwoSided', 'OneSided', 'Manual'])

        self.bg_trace = DatasetSelect(self,
                                      items='bg_trace_items',
                                      selected='bg_trace_selected',
                                      default_text='From Plugin',
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
                                       items='ext_trace_items',
                                       selected='ext_trace_selected',
                                       default_text='From Plugin',
                                       filters=['is_trace'])

        self.ext_type = SelectPluginComponent(self,
                                              items='ext_type_items',
                                              selected='ext_type_selected',
                                              manual_options=['Boxcar', 'Horne'])

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

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('interactive_extract',
                                           'trace_dataset', 'trace_type', 'trace_peak_method',
                                           'trace_pixel', 'trace_bins', 'trace_window',
                                           'import_trace',
                                           'export_trace',
                                           'bg_dataset', 'bg_type',
                                           'bg_trace_pixel', 'bg_separation', 'bg_width',
                                           'bg_add_results', 'bg_sub_add_results',
                                           'import_bg',
                                           'export_bg', 'export_bg_img', 'export_bg_sub',
                                           'ext_dataset', 'ext_trace', 'ext_type',
                                           'ext_width', 'ext_add_results',
                                           'import_extract',
                                           'export_extract', 'export_extract_spectrum'))

    @observe('trace_dataset_selected')
    def _trace_dataset_selected(self, msg=None):
        if not hasattr(self, 'trace_dataset'):
            # happens when first initializing plugin outside of tray
            return

        width = self.trace_dataset.selected_obj.shape[0]
        # estimate the pixel number by taking the median of the brightest pixel index in each column
        brightest_pixel = int(np.median(np.argmax(self.trace_dataset.selected_obj.flux, axis=0)))
        # do not allow to be an edge pixel
        if brightest_pixel < 1:
            brightest_pixel = 1
        if brightest_pixel > width - 1:
            brightest_pixel = width - 1
        distance_from_edge = min(brightest_pixel, width-brightest_pixel)
        # default width will be 10% of cross-dispersion "height",
        # but no larger than distance from the edge
        default_bg_width = int(np.ceil(width / 10))
        default_width = min(default_bg_width, distance_from_edge * 2)

        if self.trace_pixel == 0:
            self.trace_pixel = brightest_pixel
        if self.trace_window == 0:
            self.trace_window = default_width
        if self.bg_trace_pixel == 0:
            self.bg_trace_pixel = brightest_pixel
        if self.bg_separation == 0:
            if default_bg_width * 2 >= distance_from_edge:
                self.bg_type_selected = 'OneSided'
                # we want positive separation if brightest_pixel near bottom
                sign = 1 if (brightest_pixel < width / 2) else -1
                self.bg_separation = sign * default_bg_width * 2
            else:
                self.bg_separation = default_bg_width * 2
        if self.bg_width == 0:
            self.bg_width = default_bg_width
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
            self.plugin_opened = True
            if step == 'trace':
                self._interaction_in_trace_step()
            elif step == 'bg':
                self._interaction_in_bg_step()
            elif step == 'ext':
                self._interaction_in_ext_step()
            else:
                raise ValueError("step must be one of: trace, bg, ext")

    def clear_marks(self):
        """
        Manually clear the live-preview marks.
        """
        self.plugin_opened = False

    @observe('plugin_opened', 'interactive_extract')
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
        if self.interactive_extract:
            try:
                sp1d = self.export_extract_spectrum(add_data=False)
            except Exception as e:
                # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
                # NOTE: KosmosTrace or manual background are often giving a
                # "background regions overlapped" error from specreduce
                self.ext_specreduce_err = repr(e)
                self.marks['extract'].clear()
            else:
                self.ext_specreduce_err = ''
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
        if not viewer2d.state.reference_data:
            # we don't have data yet for scales, defer initializing
            return {}

        # the marks haven't been initialized yet, so initialize with empty
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
             'trace_trace_selected', 'trace_offset',
             'trace_pixel', 'trace_peak_method_selected',
             'trace_bins', 'trace_window', 'active_step')
    def _interaction_in_trace_step(self, event={}):
        if not self.plugin_opened or not self._do_marks:
            return
        if event.get('name', '') == 'active_step' and event.get('new') != 'trace':
            return

        try:
            trace = self.export_trace(add_data=False)
        except Exception:
            # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
            self.marks['trace'].clear()
        else:
            self.marks['trace'].update_xy(range(len(trace.trace)),
                                          trace.trace)
            self.marks['trace'].line_style = 'solid'
        self.active_step = 'trace'
        self._update_plugin_marks()

    @observe('bg_dataset_selected', 'bg_type_selected',
             'bg_trace_selected', 'bg_trace_pixel',
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

    @observe('ext_dataset_selected', 'ext_trace_selected',
             'ext_type_selected', 'ext_width', 'active_step')
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
            if self.ext_type_selected == 'Boxcar':
                self.marks['ext_lower'].update_xy(xs,
                                                  trace.trace-self.ext_width/2)
                self.marks['ext_upper'].update_xy(xs,
                                                  trace.trace+self.ext_width/2)
            else:
                for mark in ['ext_lower', 'ext_upper']:
                    self.marks[mark].clear()

        self.active_step = 'ext'
        self._update_plugin_marks()

        # TODO: remove this, the traitlet, and the row in spectral_extraction.vue
        # when specutils handles the warning/exception
        if self.ext_type_selected == 'Horne':
            inp_sp2d = self._get_ext_input_spectrum()
            self.ext_uncert_warn = isinstance(inp_sp2d.uncertainty, UnknownUncertainty)
        else:
            self.ext_uncert_warn = False

    def _set_create_kwargs(self, **kwargs):
        invalid_kwargs = [k for k in kwargs.keys() if not hasattr(self, k)]
        if len(invalid_kwargs):
            raise ValueError(f"{invalid_kwargs} are not valid attributes to pass as kwargs")

        for k, v in kwargs.items():
            setattr(self, k, v)

    def import_trace(self, trace):
        """
        Import the input parameters from an existing specreduce Trace object into the plugin.

        Parameters
        ----------
        trace : specreduce.tracing.Trace
            Trace object to import
        """
        if not isinstance(trace, tracing.Trace):  # pragma: no cover
            raise TypeError("trace must be a specreduce.tracing.Trace object")

        if isinstance(trace, tracing.FlatTrace):
            self.trace_type_selected = 'Flat'
            self.trace_pixel = trace.trace_pos
        elif isinstance(trace, tracing.KosmosTrace):
            self.trace_type_selected = 'Auto'
            self.trace_pixel = trace.guess
            self.trace_window = trace.window
            self.trace_bins = trace.bins
        elif isinstance(trace, tracing.ArrayTrace):  # pragma: no cover
            raise NotImplementedError(f"cannot import ArrayTrace into plugin.  Use viz.load_trace instead")  # noqa
        else:  # pragma: no cover
            raise NotImplementedError(f"trace of type {trace.__class__.__name__} not supported")

    def export_trace(self, add_data=False, **kwargs):
        """
        Create a specreduce Trace object from the input parameters
        defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting trace to the application, according to the options
            defined in the plugin.
        """
        self._set_create_kwargs(**kwargs)
        if len(kwargs) and self.active_step != 'trace':
            self.update_marks(step='trace')

        if self.trace_trace_selected != 'New Trace':
            # then we're offsetting an existing trace
            # for FlatTrace, we can keep and expose a new FlatTrace (which has the advantage of
            # being able to load back into the plugin)
            orig_trace = self.trace_trace.selected_obj
            if isinstance(orig_trace, tracing.FlatTrace):
                trace = tracing.FlatTrace(self.trace_dataset.selected_obj.data,
                                          orig_trace.trace_pos+self.trace_offset)
            else:
                trace = tracing.ArrayTrace(self.trace_dataset.selected_obj.data,
                                           self.trace_trace.selected_obj.trace+self.trace_offset)

        elif self.trace_type_selected == 'Flat':
            trace = tracing.FlatTrace(self.trace_dataset.selected_obj.data,
                                      self.trace_pixel)

        elif self.trace_type_selected == 'Auto':
            trace = tracing.KosmosTrace(self.trace_dataset.selected_obj.data,
                                        guess=self.trace_pixel,
                                        bins=int(self.trace_bins),
                                        window=self.trace_window,
                                        peak_method=self.trace_peak_method_selected.lower())

        else:
            raise NotImplementedError(f"trace_type={self.trace_type_selected} not implemented")

        if add_data:
            self.trace_add_results.add_results_from_plugin(trace, replace=False)

        return trace

    def vue_create_trace(self, *args):
        self.export_trace(add_data=True)

    def _get_bg_trace(self):
        if self.bg_type_selected == 'Manual':
            trace = tracing.FlatTrace(self.trace_dataset.selected_obj.data,
                                      self.bg_trace_pixel)
        elif self.bg_trace_selected == 'From Plugin':
            trace = self.export_trace(add_data=False)
        else:
            trace = self.bg_trace.selected_obj

        return trace

    def import_bg(self, bg):
        """
        Import the input parameters from an existing specreduce Background object into the plugin.

        Parameters
        ----------
        bg : specreduce.background.Background
            Background object to import
        """
        if not isinstance(bg, background.Background):  # pragma: no cover
            raise TypeError("bg must be a specreduce.background.Background object")

        # TODO: should we detect/set the referenced dataset?
        trace = self._get_bg_trace()
        if len(bg.traces) == 2:
            # try to detect constant separation
            seps1 = bg.traces[0].trace - trace.trace
            seps2 = trace.trace - bg.traces[1].trace
            if np.all(seps1 == seps1[0]) and np.all(seps2 == seps1[0]):
                self.bg_type_selected = 'TwoSided'
                self.bg_separation = abs(int(seps1[0]))
            else:  # pragma: no cover
                raise NotImplementedError("backgrounds with custom traces not supported (could not detect common separation)")  # noqa
        elif len(bg.traces) == 1:
            # either one_sided or trace, let's see if its constant offset from the trace
            seps = bg.traces[0].trace - trace.trace
            if np.all(seps == seps[0]):
                self.bg_type_selected = 'OneSided'
                self.bg_separation = int(seps[0])
            else:  # pragma: no cover
                raise NotImplementedError("backgrounds with custom traces not supported (could not detect common separation)")  # noqa
        else:  # pragma: no cover
            raise NotImplementedError("backgrounds with more than 2 traces not supported")

        self.bg_width = bg.width

    def export_bg(self, **kwargs):
        """
        Create a specreduce Background object from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting image to the application, according to the options
            defined in the plugin.
        """
        self._set_create_kwargs(**kwargs)
        if len(kwargs) and self.active_step != 'bg':
            self.update_marks(step='bg')

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
            bg = background.Background.two_sided(self.bg_dataset.selected_obj.data,
                                                 trace,
                                                 self.bg_separation,
                                                 width=self.bg_width)
        else:  # pragma: no cover
            raise NotImplementedError(f"bg_type={self.bg_type_selected} not implemented")

        return bg

    def export_bg_img(self, add_data=False, **kwargs):
        """
        Create a background 2D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting image to the application, according to the options
            defined in the plugin.
        """
        bg = self.export_bg(**kwargs)

        bg_spec = Spectrum1D(spectral_axis=self.bg_dataset.selected_obj.spectral_axis,
                             flux=bg.bkg_image()*self.bg_dataset.selected_obj.flux.unit)

        if add_data:
            self.bg_add_results.add_results_from_plugin(bg_spec, replace=True)

        return bg_spec

    def vue_create_bg_img(self, *args):
        try:
            self.export_bg_img(add_data=True)
        except Exception as e:
            self.app.hub.broadcast(
                SnackbarMessage(f"Specreduce background failed with the following error: {repr(e)}",
                                color='error', sender=self)
            )

    def export_bg_sub(self, add_data=False, **kwargs):
        """
        Create a background-subtracted 2D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting image to the application, according to the options
            defined in the plugin.
        """
        bg = self.export_bg(**kwargs)

        bg_sub_spec = Spectrum1D(spectral_axis=self.bg_dataset.selected_obj.spectral_axis,
                                 flux=bg.sub_image()*self.bg_dataset.selected_obj.flux.unit)

        if add_data:
            self.bg_sub_add_results.add_results_from_plugin(bg_sub_spec, replace=True)

        return bg_sub_spec

    def vue_create_bg_sub(self, *args):
        self.export_bg_sub(add_data=True)

    def _get_ext_trace(self):
        if self.ext_trace_selected == 'From Plugin':
            return self.export_trace(add_data=False)
        else:
            return self.ext_trace.selected_obj

    def _get_ext_input_spectrum(self):
        if self.ext_dataset_selected == 'From Plugin':
            return self.export_bg_sub(add_data=False)
        else:
            return self.ext_dataset.selected_obj

    def import_extract(self, ext):
        """
        Import the input parameters from an existing specreduce extract object into the plugin.

        Parameters
        ----------
        ext : specreduce.extract.BoxcarExtract
            Extract object to import
        """
        if isinstance(ext, extract.BoxcarExtract):
            self.ext_type_selected = 'Boxcar'
            self.ext_width = ext.width
        elif isinstance(ext, extract.HorneExtract):
            self.ext_type_selected = 'Horne'
        else:  # pragma: no cover
            raise TypeError("ext must be a specreduce.extract.BoxcarExtract or specreduce.extract.HorneExtract object")  # noqa

    def export_extract(self, **kwargs):
        """
        Create a specreduce extraction object from the input parameters defined in the plugin.
        """
        self._set_create_kwargs(**kwargs)
        if len(kwargs) and self.active_step != 'ext':
            self.update_marks(step='ext')

        trace = self._get_ext_trace()
        inp_sp2d = self._get_ext_input_spectrum()

        if self.ext_type_selected == 'Boxcar':
            ext = extract.BoxcarExtract(inp_sp2d.data, trace, width=self.ext_width)
        elif self.ext_type_selected == 'Horne':
            uncert = inp_sp2d.uncertainty if inp_sp2d.uncertainty is not None else VarianceUncertainty(np.ones_like(inp_sp2d.data))  # noqa
            if not hasattr(uncert, 'uncertainty_type'):
                uncert = StdDevUncertainty(uncert)
            image = NDData(inp_sp2d.data, uncertainty=uncert)
            ext = extract.HorneExtract(image, trace)
        else:
            raise NotImplementedError(f"extraction type '{self.ext_type_selected}' not supported")  # noqa

        return ext

    def export_extract_spectrum(self, add_data=False, **kwargs):
        """
        Create an extracted 1D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting spectrum to the application, according to the options
            defined in the plugin.
        """
        extract = self.export_extract(**kwargs)
        spectrum = extract.spectrum

        # Specreduce returns a spectral axis in pixels, so we'll replace with input spectral_axis
        # NOTE: this is currently disabled until proper handling of axes-limit linking between
        # the 2D spectrum image (plotted in pixels) and a 1D spectrum (plotted in freq or
        # wavelength) is implemented.

        # spectrum = Spectrum1D(spectral_axis=inp_sp2d.spectral_axis, flux=spectrum.flux)

        if add_data:
            self.ext_add_results.add_results_from_plugin(spectrum, replace=False)

        return spectrum

    def vue_extract_spectrum(self, *args):
        self.export_extract_spectrum(add_data=True)
