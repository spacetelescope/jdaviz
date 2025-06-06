import math

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetSelect,
                                        SelectPluginComponent, PlotMixin)
from jdaviz.core.events import GlobalDisplayUnitChanged, SnackbarMessage
from traitlets import Bool, List, Integer, Unicode, observe, Any
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               flux_conversion_general)
from jdaviz.core.marks import PluginLine


import astropy.units as u
import numpy as np
from specreduce.utils import measure_cross_dispersion_profile

__all__ = ['CrossDispersionProfile']


@tray_registry('cross-dispersion-profile', label="Cross Dispersion Profile",
               viewer_requirements=['spectrum', 'spectrum-2d'])
class CrossDispersionProfile(PluginTemplateMixin, PlotMixin):
    
    template_file = __file__, "cross_dispersion_profile.vue"

    uses_active_status = Bool(True).tag(sync=True)

    dataset_items = List().tag(sync=True)
    dataset_selected = Unicode().tag(sync=True)

    trace_items = List().tag(sync=True)
    trace_selected = Unicode().tag(sync=True)

    # pixel on spectral axis to measure profile
    pixel = Integer().tag(sync=True)

    # allowed range of pixel value based on image size, to set slider limit
    max_pix = Integer().tag(sync=True)

    # size of window in cross-dispersion axis to measure profile
    use_full_width = Bool(False).tag(sync=True)
    width = Integer(1).tag(sync=True)

    # app-wide flux display unit. 'profile' will always be in this unit
    flux_display_unit = Unicode("").tag(sync=True)

    # app-wide unit for spectral axis
    sa_display_unit = Unicode("").tag(sync=True)

    plot_available = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._marks = {}

        # description displayed under plugin title in tray
        self._plugin_description = 'Visualize cross-dispersion profile.'

        self.dataset = DatasetSelect(self,
                                    'dataset_items',
                                    'dataset_selected',
                                     filters=['layer_in_spectrum_2d_viewer',
                                              'not_trace'])

        self.trace = DatasetSelect(self,
                                   'trace_items',
                                   'trace_selected',
                                    default_text='Select Trace',
                                    filters=['is_trace'])

        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_display_units_changed)

        # attribute to access computed profile, will be a quantity array
        self.profile = None

    @observe('trace_selected')
    def _set_defaults(self, msg=None):
        """
        Listens to `trace_selected` to set the default of parameters for
        computing the cross dispersion profile. 'width', the window
        size in the cross-disperions axis, will by default use the whole image.
        The default for 'pixel' will be the center of the image on the spectral
        axis, rounded to the nearest integer.

        """
        # trace_selected gets triggered when app initializes
        # (for default extraction?) with no data so this check is necessary
        if hasattr(self, 'dataset'):
            data = self.dataset.selected_obj
            if data is not None:
                # default profile parameters
                self.use_full_width = True
                self.pixel = math.floor(data.shape[1] / 2)
                # slider limit
                self.max_pix = data.shape[1]

    def _on_display_units_changed(self, event={}):

        """
        On flux display unit change from Unit Conversion plugin, re-compute
        profile in new unit and update plot.

        Note: re-measure profile in native data units rather than converting
        currently computed profile so repeated conversions don't accumulate
        precision errors.
        """
        if event.axis == 'flux':
            if self.flux_display_unit == event.unit:
                return
            self.flux_display_unit = event.unit.to_string()

        # if event.axis == 'spectral_y':
        #     if self.sa_display_unit == event.unit:
        #         return
        #     self.sa_display_unit = event.unit.to_string()

        # re-compute profile, which will then be converted to the unit
        # self.flux_display_unit was just set to, and update plot
        self.measure_cross_dispersion_profile(update_plot=True)

    @property
    def marks(self):
        """
        Access the marks created by this plugin in the spectrum-2d-viewer.
        """
        if self._marks:
            # TODO: replace with cache property?
            return self._marks

        if not self._tray_instance:
            return {}

        # NOTE fix this, why can't i access _default_spectrum_2d_viewer_reference_name???
        #viewer2d = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)
        viewer2d = self.app.get_viewer('spectrum-2d-viewer')
        spectrum_viewer = self.app.get_viewer('spectrum-viewer')

        if not viewer2d.state.reference_data:
            # we don't have data yet for scales, defer initializing
            return {}

        self._marks = {'pixel': PluginLine(viewer2d, visible=self.is_active,
                                                     line_style='dotted'),
                       'pixel_on_spectrum_viewer': PluginLine(spectrum_viewer,
                                                   visible=self.is_active,
                                                   line_style='dotted')}

        viewer2d.figure.marks = viewer2d.figure.marks + list(self._marks.values())

        return self._marks

    @observe('pixel', 'trace_selected', 'is_active', 'width', 'use_full_width')
    def _pixel_selected_mark(self, event={}):
        """
        Update drawn mark (vertical line) for current selected pixel,
        when changed.
        """

        data = self.dataset.selected_obj
        if data is not None:

            # remove line if trace is un-selected
            if self.trace_selected == 'Select Trace':
                self.marks['pixel'].clear()
                return

            # plot vertical line at 'pixel' that extends +/- 'width'
            # y min / max are 'width' around trace at 'pixel'
            trace_at_pixel = self.trace.selected_obj.trace[self.pixel]
            if self.use_full_width is True:
                ymax = data.shape[1]
                ymin = 0
            else:
                ymax = int(trace_at_pixel + self.width)
                ymin = int(trace_at_pixel - self.width)

            self.marks['pixel'].update_xy(np.full(data.shape[1], self.pixel),
                                          range(ymin, ymax))

            self.marks['pixel'].visible = self.is_active

            if hasattr(data, 'wcs'):  # also plot line in spectrum viewer
                wcs = self.dataset.selected_obj.wcs
                loc = wcs.pixel_to_world(self.pixel).value

                # # convert to display spectral axis unit
                # current = loc * u.Unit(data.unit)
                # target = u.Unit(self.sa_display_unit)
                # loc = current.to(target, u.spectral()).value

                self.marks['pixel_on_spectrum_viewer'].update_xy(np.full(data.shape[1], loc),
                                                                 range(0, data.shape[0]))
                self.marks['pixel_on_spectrum_viewer'].visible = self.is_active


    def vue_measure_cross_dispersion_profile(self):
        self.measure_cross_dispersion_profile()

    @observe('pixel', 'trace_selected', 'width', 'use_full_width')
    def measure_cross_dispersion_profile(self, update_plot=True,
                                         use_display_units=True):

        data = self.dataset.selected_obj

        if data is None:
            return

        if self.use_full_width:
            width = None
        else:
            width = self.width

        profile = measure_cross_dispersion_profile(data,
                                                   trace=self.trace.selected_obj,
                                                   crossdisp_axis=0,
                                                   width=width,
                                                   pixel=self.pixel,
                                                   pixel_range=None,
                                                   align_along_trace=False)
        # convert profile, which was computed in data units, to display unit
        # if they differ
        if use_display_units:
            eqv = all_flux_unit_conversion_equivs(data.meta.get('PIXAR_SR', 1.0),
                                                  data.spectral_axis)
            profile = flux_conversion_general(profile.value, profile.unit,
                                              self.flux_display_unit, eqv)


        self.profile = profile.value

        if update_plot:
            self.update_plot()

    def update_plot(self):
        """Update plot with current self.profile."""

        if self.use_full_width:
            x = range(len(self.profile))
        else:
            x = self.width + 1

        self.plot._update_data('profile', x=x, y=self.profile, reset_lims=True)
        self.plot.update_style('profile', line_visible=True, color='gray',
                                size=32)

        self.plot.figure.title = f'Cross dispersion profile for pixel {self.pixel}'

        self.plot.figure.axes[1].label = f'Value ({self.flux_display_unit})'

        self.plot_available = True
