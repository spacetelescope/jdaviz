import numpy as np
from functools import cached_property

from traitlets import Bool, List, Unicode, observe

from jdaviz.configs.mosviz.plugins.viewers import Spectrum1DViewer
from jdaviz.core.events import (SnackbarMessage, NewViewerMessage,
                                ViewerVisibleLayersChangedMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        SelectPluginComponent,
                                        DatasetSelect,
                                        AddResults,
                                        skip_if_no_updates_since_last_active,
                                        skip_if_not_tray_instance,
                                        skip_if_not_relevant,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.marks import PluginMarkCollection, PluginLine

from astropy.modeling import models
from astropy.nddata import StdDevUncertainty, VarianceUncertainty, UnknownUncertainty
from specutils import Spectrum
from specreduce import tracing
from specreduce import background
from specreduce import extract

__all__ = ['SpectralExtraction2D']

_model_cls = {'Spline': models.Spline1D,
              'Polynomial': models.Polynomial1D,
              'Legendre': models.Legendre1D,
              'Chebyshev': models.Chebyshev1D}


@tray_registry('spectral-extraction-2d', label="2D Spectral Extraction",
               category="data:reduction")
class SpectralExtraction2D(PluginTemplateMixin):
    """
    The Spectral Extraction 2D plugin exposes specreduce methods for tracing,
    background subtraction, and spectral extraction from 2D spectra.
    See the :ref:`2D Spectral Extraction Plugin Documentation <specviz2d-spectral-extraction>`
    for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * :attr:`interactive_extract`
    * ``trace_dataset`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      controls the input dataset for generating the trace.
    * ``trace_type`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      controls the type of trace to be generated.
    * ``trace_peak_method`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      only applicable if ``trace_type`` is not ``Flat``.
    * :attr:`trace_pixel` :
      pixel of the trace.  If ``trace_type`` is not ``Flat``, then this
      is the "guess" for the automated trace.
    * :attr:`trace_do_binning` :
      only applicable if ``trace_type`` is not ``Flat``.  Bin the input data when fitting the
      trace.
    * :attr:`trace_bins` :
      only applicable if ``trace_type`` is not ``Flat`` and ``trace_do_binning``.
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
    * ``bg_statistic`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      statistic to use when computing the background.  'Average' will account for partial pixel
      weights, 'Median' will include all partial pixels.
    * ``bg_add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * ``bg_sub_add_results``
    * :meth:`import_bg`
    * :meth:`export_bg`
    * :meth:`export_bg_spectrum`
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
    * ``horne_ext_profile`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      For Horne extract, choice of 'Gaussian' or 'Self (interpolated)' to use
      empirical profile from data.
    * :attr:`self_prof_n_bins` :
      Number of bins to use when computing the self-derived profile for Horne Extract.
    * :attr:`self_prof_interp_degree_x` :
      Interpolation degree (in X) to use when computing the self-derived profile
      for Horne Extract.
    * :attr:`self_prof_interp_degree_y` :
      Interpolation degree (in Y) to use when computing the self-derived profile
      for Horne Extract.
    * ``ext_add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`import_extract`
    * :meth:`export_extract`
    * :meth:`export_extract_spectrum`
    """
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "spectral_extraction.vue"
    uses_active_status = Bool(True).tag(sync=True)

    active_step = Unicode().tag(sync=True)

    # SETTINGS
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
    trace_order = IntHandleEmpty(3).tag(sync=True)

    trace_peak_method_items = List().tag(sync=True)
    trace_peak_method_selected = Unicode().tag(sync=True)

    trace_do_binning = Bool(True).tag(sync=True)
    trace_bins = IntHandleEmpty(20).tag(sync=True)
    trace_window = IntHandleEmpty(0).tag(sync=True)

    trace_results_label = Unicode().tag(sync=True)
    trace_results_label_default = Unicode().tag(sync=True)
    trace_results_label_auto = Bool(True).tag(sync=True)
    trace_results_label_invalid_msg = Unicode('').tag(sync=True)
    trace_results_label_overwrite = Bool().tag(sync=True)
    trace_add_to_viewer_items = List().tag(sync=True)
    trace_add_to_viewer_selected = Unicode().tag(sync=True)
    trace_spinner = Bool(False).tag(sync=True)

    # BACKGROUND
    bg_dataset_items = List().tag(sync=True)
    bg_dataset_selected = Unicode().tag(sync=True)

    bg_type_items = List().tag(sync=True)
    bg_type_selected = Unicode().tag(sync=True)

    bg_trace_items = List().tag(sync=True)
    bg_trace_selected = Unicode().tag(sync=True)

    bg_trace_pixel = FloatHandleEmpty(0).tag(sync=True)

    bg_statistic_items = List().tag(sync=True)
    bg_statistic_selected = Unicode().tag(sync=True)

    bg_separation = FloatHandleEmpty(0).tag(sync=True)
    bg_width = FloatHandleEmpty(0).tag(sync=True)

    bg_results_label = Unicode().tag(sync=True)
    bg_results_label_default = Unicode().tag(sync=True)
    bg_results_label_auto = Bool(True).tag(sync=True)
    bg_results_label_invalid_msg = Unicode('').tag(sync=True)
    bg_results_label_overwrite = Bool().tag(sync=True)
    bg_add_to_viewer_items = List().tag(sync=True)
    bg_add_to_viewer_selected = Unicode().tag(sync=True)
    bg_img_spinner = Bool(False).tag(sync=True)

    bg_spec_results_label = Unicode().tag(sync=True)
    bg_spec_results_label_default = Unicode().tag(sync=True)
    bg_spec_results_label_auto = Bool(True).tag(sync=True)
    bg_spec_results_label_invalid_msg = Unicode('').tag(sync=True)
    bg_spec_results_label_overwrite = Bool().tag(sync=True)
    bg_spec_add_to_viewer_items = List().tag(sync=True)
    bg_spec_add_to_viewer_selected = Unicode().tag(sync=True)
    bg_spec_spinner = Bool(False).tag(sync=True)

    bg_sub_results_label = Unicode().tag(sync=True)
    bg_sub_results_label_default = Unicode().tag(sync=True)
    bg_sub_results_label_auto = Bool(True).tag(sync=True)
    bg_sub_results_label_invalid_msg = Unicode('').tag(sync=True)
    bg_sub_results_label_overwrite = Bool().tag(sync=True)
    bg_sub_add_to_viewer_items = List().tag(sync=True)
    bg_sub_add_to_viewer_selected = Unicode().tag(sync=True)
    bg_sub_spinner = Bool(False).tag(sync=True)

    # EXTRACT
    ext_dataset_items = List().tag(sync=True)
    ext_dataset_selected = Unicode().tag(sync=True)

    ext_trace_items = List().tag(sync=True)
    ext_trace_selected = Unicode().tag(sync=True)

    ext_type_items = List().tag(sync=True)
    ext_type_selected = Unicode().tag(sync=True)

    horne_ext_profile_items = List().tag(sync=True)
    horne_ext_profile_selected = Unicode().tag(sync=True)

    self_prof_n_bins = IntHandleEmpty(10).tag(sync=True)
    self_prof_interp_degree_x = IntHandleEmpty(1).tag(sync=True)
    self_prof_interp_degree_y = IntHandleEmpty(1).tag(sync=True)

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
    # uses default "spinner"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Extract 1D spectrum from 2D image.'

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
        self.trace_dataset.get_data_cls = Spectrum

        self.trace_type = SelectPluginComponent(self,
                                                items='trace_type_items',
                                                selected='trace_type_selected',
                                                manual_options=['Flat', 'Polynomial',
                                                                'Legendre', 'Chebyshev',
                                                                'Spline'])

        self.trace_peak_method = SelectPluginComponent(self,
                                                       items='trace_peak_method_items',
                                                       selected='trace_peak_method_selected',
                                                       manual_options=['Gaussian', 'Centroid', 'Max'])  # noqa

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

        self.bg_statistic = SelectPluginComponent(self,
                                                  items='bg_statistic_items',
                                                  selected='bg_statistic_selected',
                                                  manual_options=['Average', 'Median'])

        self.bg_add_results = AddResults(self, 'bg_results_label',
                                         'bg_results_label_default',
                                         'bg_results_label_auto',
                                         'bg_results_label_invalid_msg',
                                         'bg_results_label_overwrite',
                                         'bg_add_to_viewer_items',
                                         'bg_add_to_viewer_selected')
        self.bg_add_results.viewer.filters = ['is_spectrum_2d_viewer']
        self.bg_results_label_default = 'background'

        self.bg_spec_add_results = AddResults(self, 'bg_spec_results_label',
                                              'bg_spec_results_label_default',
                                              'bg_spec_results_label_auto',
                                              'bg_spec_results_label_invalid_msg',
                                              'bg_spec_results_label_overwrite',
                                              'bg_spec_add_to_viewer_items',
                                              'bg_spec_add_to_viewer_selected')
        self.bg_spec_add_results.viewer.filters = ['is_spectrum_viewer']
        self.bg_spec_results_label_default = 'background-spectrum'

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

        self.horne_ext_profile = SelectPluginComponent(self,
                                                       items='horne_ext_profile_items',
                                                       selected='horne_ext_profile_selected',
                                                       manual_options=['Gaussian', 'Self (interpolated)'])  # noqa

        self.ext_add_results = AddResults(self, 'ext_results_label',
                                          'ext_results_label_default',
                                          'ext_results_label_auto',
                                          'ext_results_label_invalid_msg',
                                          'ext_results_label_overwrite',
                                          'ext_add_to_viewer_items',
                                          'ext_add_to_viewer_selected')
        self.ext_add_results.viewer.filters = ['is_spectrum_viewer']
        # NOTE: defaults to overwriting original spectrum
        self.ext_add_results.label_whitelist_overwrite = ['1D Spectrum', '2D Spectrum (auto-ext)']
        self.ext_results_label_default = '2D Spectrum (auto-ext)'

        self.app.hub.subscribe(self, ViewerVisibleLayersChangedMessage,
                               lambda _: self._update_plugin_marks())

        if self.config == "deconfigged":
            self.observe_traitlets_for_relevancy(traitlets_to_observe=['trace_dataset_items'])

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('interactive_extract',
                                           'trace_dataset', 'trace_type',
                                           'trace_order', 'trace_peak_method',
                                           'trace_pixel',
                                           'trace_do_binning', 'trace_bins', 'trace_window',
                                           'import_trace',
                                           'export_trace',
                                           'bg_dataset', 'bg_type',
                                           'bg_trace_pixel', 'bg_separation', 'bg_width',
                                           'bg_statistic',
                                           'bg_add_results', 'bg_sub_add_results',
                                           'import_bg',
                                           'export_bg', 'export_bg_spectrum',
                                           'export_bg_img', 'export_bg_sub',
                                           'ext_dataset', 'ext_trace', 'ext_type',
                                           'ext_width', 'ext_add_results',
                                           'horne_ext_profile',
                                           'self_prof_n_bins',
                                           'self_prof_interp_degree_x',
                                           'self_prof_interp_degree_y',
                                           'import_extract',
                                           'export_extract', 'export_extract_spectrum'))

    def _clear_default_inputs(self):
        self.trace_pixel = 0
        self.trace_window = 0
        self.bg_trace_pixel = 0
        self.bg_separation = 0
        self.bg_width = 0
        self.ext_width = 0

    @observe('irrelevant_msg')
    def _updates_when_becoming_relevant(self, msg):
        if msg.get('new') != '':
            return
        # reset all defaults for the selected trace dataset, _trace_dataset_selected
        # should be triggered shortly after
        self._clear_default_inputs()

    def _extract_in_new_instance(self, dataset=None, add_data=False):
        # create a new instance of the 2D Spectral Extraction plugin (to not
        # affect the instance in the tray) and extract the entire cube with defaults.
        plg = self.new()
        # all other settings remain at their plugin defaults
        plg._clear_default_inputs()
        plg.trace_dataset.selected = self.trace_dataset.selected if dataset is None else dataset
        plg._trace_dataset_selected()  # should only be necessary if default dataset
        return plg.export_extract_spectrum(add_data=add_data)

    @observe('trace_dataset_selected')
    @skip_if_not_relevant()
    def _trace_dataset_selected(self, msg=None):
        if not hasattr(self, 'trace_dataset'):
            # happens when first initializing plugin outside of tray
            return
        if not len(self.trace_dataset.selected):
            return

        width = self.trace_dataset.get_selected_spectrum(use_display_units=True).shape[0]
        # estimate the pixel number by taking the median of the brightest pixel index
        # in each column, ignoring columns where the sum in that column is not
        # positive (ie. columns of all zeros or nans)
        trace_flux = self.trace_dataset.get_selected_spectrum(use_display_units=True).flux
        trace_flux_ignore_zeros = trace_flux[:, np.nansum(trace_flux, axis=0) != 0]
        if trace_flux_ignore_zeros.shape[1] == 0:
            # default to trace in middle of image
            brightest_pixel = int(trace_flux.shape[0]/2)
        else:
            brightest_pixel = int(np.nanmedian(np.nanargmax(trace_flux_ignore_zeros, axis=0)))
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

        # sign for one-sided and single trace-pixel depending on whether the brightest pixel is
        # above or below the middle of the image
        if default_bg_width * 2 >= distance_from_edge:
            sign = 1 if (brightest_pixel < width / 2) else -1
            default_bg_separation = sign * default_bg_width * 2
        else:
            default_bg_separation = default_bg_width * 2

        if self.trace_pixel == 0:
            self.trace_pixel = brightest_pixel
        if self.trace_window == 0:
            self.trace_window = default_width
        if self.bg_trace_pixel == 0:
            self.bg_trace_pixel = brightest_pixel + default_bg_separation
        if self.bg_separation == 0:
            if default_bg_width * 2 >= distance_from_edge:
                self.bg_type_selected = 'OneSided'
            self.bg_separation = default_bg_separation
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
            if step == 'trace':
                self._interaction_in_trace_step()
            elif step == 'bg':
                self._interaction_in_bg_step()
            elif step == 'ext':
                self._interaction_in_ext_step()
            elif step == '':
                return
            else:
                raise ValueError("step must be one of: trace, bg, ext")

    @observe('ext_add_to_viewer_selected', 'ext_results_label_overwrite')
    def _spectrum1d_viewer_changed(self, *args):
        self.update_marks(self.active_step)

    @observe('is_active', 'active_step')
    @skip_if_not_tray_instance()
    def _update_plugin_marks(self, msg={}):
        if self.app._jdaviz_helper is None:
            return

        if not len(self.marks):
            # plugin has never been opened, no need to create marks just to hide them,
            # we'll create marks when the plugin is first opened
            return

        if not (self.is_active):
            for step, mark in self.marks.items():
                mark.clear()
            return

        if self.active_step == '':
            # on load, default to 'extract' (this will then trigger the observe to update the marks)
            self.active_step = 'ext'
            return

        marks_info = self.marks_info(include_mark_obj=False)  # viewer + step info for each mark
        viewers = {'1d': self.marks_viewers1d, '2d': self.marks_viewers2d}
        for step, mark in self.marks.items():
            visible = self.active_step in marks_info[step]['steps']
            mark.set_for_viewers('visible', visible, viewers[marks_info[step]['viewer']])
            mark.clear_if_not_in_viewers(viewers[marks_info[step]['viewer']])

    @property
    def marks_viewers2d(self):
        if self.active_step == 'bg':
            return self.bg_dataset.viewers_with_selected_visible
        return self.trace_dataset.viewers_with_selected_visible

    @property
    def marks_viewers1d(self):
        return self.ext_add_results.results_viewers

    def marks_info(self, include_mark_obj=True):
        """
        A dictionary containing each marker name, the viewer(s) (2d/1d spectral)
        it belongs in, which step (bg, trace, extract) and plotting style kwargs.
        """

        markers = {'trace': {'viewer': '2d', 'steps': ['trace', 'bg', 'ext']},
                   'extract': {'viewer': '1d', 'steps': ['trace', 'bg', 'ext']},
                   'bg1_lower': {'viewer': '2d', 'steps': ['bg']},
                   'bg1_upper': {'viewer': '2d', 'steps': ['bg']},
                   'bg1_center': {'viewer': '2d', 'steps': ['bg'], 'kw': {'line_style': 'dotted'}},
                   'bg2_lower': {'viewer': '2d', 'steps': ['bg']},
                   'bg2_upper': {'viewer': '2d', 'steps': ['bg']},
                   'bg2_center': {'viewer': '2d', 'steps': ['bg'], 'kw': {'line_style': 'dotted'}},
                   'bg_spec': {'viewer': '1d', 'steps': ['bg'], 'kw': {'stroke_width': 1}},
                   'ext_lower': {'viewer': '2d', 'steps': ['ext']},
                   'ext_upper': {'viewer': '2d', 'steps': ['ext']}}

        if include_mark_obj:  # add PluginMarkCollection
            for key, d in markers.items():
                kwargs = {'visible': self.is_active} | d.get('kw', {})
                d['mark'] = PluginMarkCollection(PluginLine, **kwargs)

        return markers

    @cached_property
    def marks(self):
        """
        Access the marks created by this plugin in both the spectrum-viewer
        and spectrum-2d-viewer.
        """
        if not self._tray_instance:
            return {}

        return {k: v['mark'] for k, v in self.marks_info().items()}

    @observe('interactive_extract')
    @skip_if_no_updates_since_last_active()
    @skip_if_not_tray_instance()
    @skip_if_not_relevant()
    def _update_interactive_extract(self, event={}):
        # also called by any of the _interaction_in_*_step
        if self.interactive_extract:
            try:
                sp1d = self.export_extract_spectrum(add_data=False)
            except Exception as e:
                # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
                # NOTE: FitTrace or manual background are often giving a
                # "background regions overlapped" error from specreduce
                self.ext_specreduce_err = repr(e)
                self.marks['extract'].clear()
            else:
                self.ext_specreduce_err = ''
                self.marks['extract'].update_xy(sp1d.spectral_axis.value,
                                                sp1d.flux.value,
                                                viewers=self.marks_viewers1d)
        else:
            self.marks['extract'].clear()

        if self.interactive_extract and self.active_step == 'bg':
            try:
                spec = self.export_bg_spectrum()
            except Exception:
                self.marks['bg_spec'].clear()
            else:
                self.marks['bg_spec'].update_xy(spec.spectral_axis,
                                                spec.flux,
                                                viewers=self.marks_viewers1d)
        else:
            self.marks['bg_spec'].clear()

    @observe('is_active', 'trace_dataset_selected', 'trace_type_selected',
             'trace_trace_selected', 'trace_offset', 'trace_order',
             'trace_pixel', 'trace_peak_method_selected',
             'trace_do_binning', 'trace_bins', 'trace_window', 'active_step')
    @skip_if_not_tray_instance()
    @skip_if_no_updates_since_last_active()
    @skip_if_not_relevant()
    def _interaction_in_trace_step(self, event={}):
        if ((event.get('name', '') in ('active_step', 'is_active') and self.active_step != 'trace')
                or not self.is_active):
            return

        try:
            trace = self.export_trace(add_data=False)
        except Exception:
            # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
            self.marks['trace'].clear()
        else:
            self.marks['trace'].update_xy(range(len(trace.trace)),
                                          trace.trace,
                                          viewers=self.marks_viewers2d)
            self.marks['trace'].line_style = 'solid'

        self._update_interactive_extract(event)

        self.active_step = 'trace'

    @observe('is_active', 'bg_dataset_selected', 'bg_type_selected',
             'bg_trace_selected', 'bg_trace_pixel',
             'bg_separation', 'bg_width', 'bg_statistic_selected', 'active_step')
    @skip_if_not_tray_instance()
    @skip_if_no_updates_since_last_active()
    @skip_if_not_relevant()
    def _interaction_in_bg_step(self, event={}):
        if ((event.get('name', '') in ('active_step', 'is_active') and self.active_step != 'bg')
                or not self.is_active):
            return

        try:
            trace = self._get_bg_trace()
        except Exception:
            # NOTE: ignore error, but will be raised when clicking ANY of the export buttons
            for mark in ['trace', 'bg1_center', 'bg1_lower', 'bg1_upper',
                         'bg2_center', 'bg2_lower', 'bg2_upper', 'bg_spec']:
                self.marks[mark].clear()
        else:
            xs = range(len(trace.trace))
            self.marks['trace'].update_xy(xs,
                                          trace.trace,
                                          viewers=self.marks_viewers2d)
            self.marks['trace'].line_style = 'dashed'

            if self.bg_type_selected in ['OneSided', 'TwoSided']:
                self.marks['bg1_center'].update_xy(xs,
                                                   trace.trace+self.bg_separation,
                                                   viewers=self.marks_viewers2d)
                self.marks['bg1_lower'].update_xy(xs,
                                                  trace.trace+self.bg_separation-self.bg_width/2,
                                                  viewers=self.marks_viewers2d)
                self.marks['bg1_upper'].update_xy(xs,
                                                  trace.trace+self.bg_separation+self.bg_width/2,
                                                  viewers=self.marks_viewers2d)
            else:
                self.marks['bg1_center'].clear()
                self.marks['bg1_lower'].update_xy(xs,
                                                  trace.trace-self.bg_width/2,
                                                  viewers=self.marks_viewers2d)
                self.marks['bg1_upper'].update_xy(xs,
                                                  trace.trace+self.bg_width/2,
                                                  viewers=self.marks_viewers2d)

            if self.bg_type_selected == 'TwoSided':
                self.marks['bg2_center'].update_xy(xs,
                                                   trace.trace-self.bg_separation,
                                                   viewers=self.marks_viewers2d)
                self.marks['bg2_lower'].update_xy(xs,
                                                  trace.trace-self.bg_separation-self.bg_width/2,
                                                  viewers=self.marks_viewers2d)
                self.marks['bg2_upper'].update_xy(xs,
                                                  trace.trace-self.bg_separation+self.bg_width/2,
                                                  viewers=self.marks_viewers2d)
            else:
                for mark in ['bg2_center', 'bg2_lower', 'bg2_upper']:
                    self.marks[mark].clear()

        self._update_interactive_extract(event)

        self.active_step = 'bg'

    @observe('is_active', 'ext_dataset_selected', 'ext_trace_selected',
             'ext_type_selected', 'ext_width', 'active_step',
             'horne_ext_profile_selected', 'self_prof_n_bins',
             'self_prof_interp_degree_x', 'self_prof_interp_degree_y')
    @skip_if_not_tray_instance()
    @skip_if_no_updates_since_last_active()
    @skip_if_not_relevant()
    def _interaction_in_ext_step(self, event={}):
        if ((event.get('name', '') in ('active_step', 'is_active') and self.active_step not in ('ext', ''))  # noqa
                or not self.is_active):
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
                                          trace.trace,
                                          viewers=self.marks_viewers2d)
            self.marks['trace'].line_style = 'dashed'
            if self.ext_type_selected == 'Boxcar':
                self.marks['ext_lower'].update_xy(xs,
                                                  trace.trace-self.ext_width/2,
                                                  viewers=self.marks_viewers2d)
                self.marks['ext_upper'].update_xy(xs,
                                                  trace.trace+self.ext_width/2,
                                                  viewers=self.marks_viewers2d)
            else:
                for mark in ['ext_lower', 'ext_upper']:
                    self.marks[mark].clear()

        self._update_interactive_extract(event)

        self.active_step = 'ext'

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
        elif isinstance(trace, tracing.FitTrace):
            self.trace_type_selected = trace.trace_model.__class__.__name__.strip('1D')
            self.trace_pixel = trace.guess
            self.trace_window = trace.window
            self.trace_bins = trace.bins
            self.trace_do_binning = True
            if hasattr(trace.trace_model, 'degree'):
                self.trace_order = trace.trace_model.degree
        elif isinstance(trace, tracing.ArrayTrace):  # pragma: no cover
            raise NotImplementedError(f"cannot import ArrayTrace into plugin.  Use viz.load instead")  # noqa
        else:  # pragma: no cover
            raise NotImplementedError(f"trace of type {trace.__class__.__name__} not supported")

    @with_spinner('trace_spinner')
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
                trace = tracing.FlatTrace(self.trace_dataset.selected_obj,
                                          orig_trace.trace_pos+self.trace_offset)
            else:
                trace = tracing.ArrayTrace(self.trace_dataset.selected_obj,
                                           self.trace_trace.selected_obj.trace+self.trace_offset)

        elif self.trace_type_selected == 'Flat':
            trace = tracing.FlatTrace(self.trace_dataset.selected_obj,
                                      self.trace_pixel)

        elif self.trace_type_selected in _model_cls:
            trace_model = _model_cls[self.trace_type_selected](degree=self.trace_order)
            trace = tracing.FitTrace(self.trace_dataset.selected_obj,
                                     guess=self.trace_pixel,
                                     bins=int(self.trace_bins) if self.trace_do_binning else None,
                                     window=self.trace_window,
                                     peak_method=self.trace_peak_method_selected.lower(),
                                     trace_model=trace_model)

        else:
            raise NotImplementedError(f"trace_type={self.trace_type_selected} not implemented")

        if add_data:
            self.trace_add_results.add_results_from_plugin(trace, replace=False)

        return trace

    def vue_create_trace(self, *args):
        self.export_trace(add_data=True)

    def _get_bg_trace(self):
        if self.bg_type_selected == 'Manual':
            trace = tracing.FlatTrace(self.trace_dataset.get_selected_spectrum(
                                      use_display_units=True),
                                      self.bg_trace_pixel)
        elif self.bg_trace_selected == 'From Plugin':
            trace = self.export_trace(add_data=False)
        else:
            trace = self.bg_trace.get_selected_spectrum(use_disaply_units=True)

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

    @with_spinner('bg_spinner')
    def export_bg(self, **kwargs):
        """
        Create a specreduce Background object from the input parameters defined in the plugin.
        """
        self._set_create_kwargs(**kwargs)
        if len(kwargs) and self.active_step != 'bg':
            self.update_marks(step='bg')

        trace = self._get_bg_trace()

        if self.bg_type_selected == 'Manual':
            bg = background.Background(self.bg_dataset.get_selected_spectrum(
                                       use_display_units=True),
                                       [trace], width=self.bg_width,
                                       statistic=self.bg_statistic.selected.lower())
        elif self.bg_type_selected == 'OneSided':
            bg = background.Background.one_sided(self.bg_dataset.get_selected_spectrum(
                                                 use_display_units=True),
                                                 trace,
                                                 self.bg_separation,
                                                 width=self.bg_width,
                                                 statistic=self.bg_statistic.selected.lower())
        elif self.bg_type_selected == 'TwoSided':
            bg = background.Background.two_sided(self.bg_dataset.get_selected_spectrum(
                                                 use_display_units=True),
                                                 trace,
                                                 self.bg_separation,
                                                 width=self.bg_width,
                                                 statistic=self.bg_statistic.selected.lower())
        else:  # pragma: no cover
            raise NotImplementedError(f"bg_type={self.bg_type_selected} not implemented")

        return bg

    @with_spinner('bg_img_spinner')
    def export_bg_img(self, add_data=False, **kwargs):
        """
        Create a background 2D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting image to the application, according to the options
            defined in the plugin.
        """
        bg_spec = self.export_bg(**kwargs).bkg_image()

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

    @with_spinner('bg_spec_spinner')
    def export_bg_spectrum(self, add_data=False, **kwargs):
        """
        Create a background 1D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting spectrum to the application, according to the options
            defined in the plugin.
        """
        spec = self.export_bg(**kwargs).bkg_spectrum()

        if add_data:
            self.bg_spec_add_results.add_results_from_plugin(spec, replace=False)

        return spec

    def vue_create_bg_spec(self, *args):
        self.export_bg_spectrum(add_data=True)

    @with_spinner('bg_sub_spinner')
    def export_bg_sub(self, add_data=False, **kwargs):
        """
        Create a background-subtracted 2D spectrum from the input parameters defined in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting image to the application, according to the options
            defined in the plugin.
        """
        bg_sub_spec = self.export_bg(**kwargs).sub_image()

        if add_data:
            self.bg_sub_add_results.add_results_from_plugin(bg_sub_spec, replace=True)

        return bg_sub_spec

    def vue_create_bg_sub(self, *args):
        self.export_bg_sub(add_data=True)

    def _get_ext_trace(self):
        if self.ext_trace_selected == 'From Plugin':
            return self.export_trace(add_data=False)
        else:
            return self.ext_trace.get_selected_spectrum(use_display_units=True)

    def _get_ext_input_spectrum(self):
        if self.ext_dataset_selected == 'From Plugin':
            return self.export_bg_sub(add_data=False)
        else:
            return self.ext_dataset.get_selected_spectrum(use_display_units=True)

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
            ext = extract.BoxcarExtract(inp_sp2d, trace, width=self.ext_width)
        elif self.ext_type_selected == 'Horne':
            spatial_profile = None
            if inp_sp2d.uncertainty is None:
                inp_sp2d.uncertainty = VarianceUncertainty(np.ones_like(inp_sp2d.data))

            if not hasattr(inp_sp2d.uncertainty, 'uncertainty_type'):
                inp_sp2d.uncertainty = StdDevUncertainty(inp_sp2d.uncert)

            if self.horne_ext_profile_selected == 'Self (interpolated)':

                # check inputs
                if self.self_prof_n_bins <= 0:
                    raise ValueError('`self_prof_n_bins` must be greater than 0.')
                if self.self_prof_interp_degree_x <= 0:
                    raise ValueError('`self_prof_interp_degree_x` must be greater than 0.')
                if self.self_prof_interp_degree_y <= 0:
                    raise ValueError('`self_prof_interp_degree_y` must be greater than 0.')

                # setup dict of interpolation options
                n_bins_interpolated_profile = self.self_prof_n_bins
                interp_degree = (self.self_prof_interp_degree_x, self.self_prof_interp_degree_y)
                spatial_profile = {'name': 'interpolated_profile',
                                   'n_bins_interpolated_profile': n_bins_interpolated_profile,
                                   'interp_degree': interp_degree}

            elif self.horne_ext_profile_selected == 'Gaussian':
                spatial_profile = 'gaussian'

            else:
                raise ValueError("Horne extraction profile must either be 'Gaussian' or 'Self (interpolated)'")  # noqa

            ext = extract.HorneExtract(inp_sp2d, trace, spatial_profile=spatial_profile)
        else:
            raise NotImplementedError(f"extraction type '{self.ext_type_selected}' not supported")  # noqa

        return ext

    @with_spinner('spinner')
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

        if add_data:
            # TODO: eventually generalize this logic into add_results_from_plugin
            if not len(self.marks_viewers1d):
                # no spectrum1d viewer, create one now and set the default viewer
                viewer_ref = self.app.return_unique_name('1D Spectrum',
                                                         typ='viewer')
                self.app._on_new_viewer(NewViewerMessage(Spectrum1DViewer,
                                                         data=None,
                                                         sender=self.app),
                                        vid=viewer_ref, name=viewer_ref,
                                        open_data_menu_if_empty=False)
                self.ext_add_results.viewer = viewer_ref

            self.ext_add_results.add_results_from_plugin(spectrum, replace=False)

        return spectrum

    def vue_extract_spectrum(self, *args):
        self.export_extract_spectrum(add_data=True)
