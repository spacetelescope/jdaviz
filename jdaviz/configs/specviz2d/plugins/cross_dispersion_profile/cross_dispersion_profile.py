import math

import astropy.units as u
import numpy as np
from bqplot import LinearScale
from specreduce.tracing import FlatTrace
from specreduce.utils import measure_cross_dispersion_profile
from traitlets import Bool, Float, Integer, List, Unicode, observe

from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.marks import PluginLine, PluginScatter
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (DatasetSelect, PluginTemplateMixin,
                                        PlotMixin)
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               flux_conversion_general)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['CrossDispersionProfile']


@tray_registry('cross-dispersion-profile', label="Cross Dispersion Profile")
class CrossDispersionProfile(PluginTemplateMixin, PlotMixin):
    """
    The Cross Dispersion Profile plugin allows for visualizaion of the
    cross-dispersion profile of 2d spectra, at a specified wavelength / pixel
    and window.

    The following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * :meth:`measure_cross_dispersion_profile`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
        Dataset used to calculate and plot cross-dispersion profile.
    * ``pixel``
        Pixel on spectral axis used to compute and plot profile.
    * ``y_pixel``
        Center of profile on cross-dispersion axis.
    * ``use_full_width``
        If true, full cross-dispersion axis will be used to compute the profile.
    * ``width``
        If use_full_with is False, this value will set the size of the window
        for the profile on the cross-dispersion axis, centered at y_pixel.
    * ``profile``
        Computed profile, as a Quantity array.

    """

    template_file = __file__, "cross_dispersion_profile.vue"

    uses_active_status = Bool(True).tag(sync=True)

    dataset_items = List().tag(sync=True)
    dataset_selected = Unicode().tag(sync=True)

    # pixel on cross dispersion axis where profile will be centered. a FlatTrace
    # at y_pixel will be created to measure the profile.
    y_pixel = Integer().tag(sync=True)

    # pixel on spectral axis to measure profile
    pixel = Integer().tag(sync=True)
    wav = Float(allow_none=True).tag(sync=True)  # corresponding wavelength, if available

    # set maximum values for slider limits
    max_pix = Integer().tag(sync=True)
    max_y_pix = Integer().tag(sync=True)

    # traitlets for size of window in cross-dispersion axis. If 'use_full_width'
    # is True, then the full cross dispersion axis around y_pixel will be used.
    # If False, then 'width' will be used.
    use_full_width = Bool(True).tag(sync=True)
    width = Integer().tag(sync=True)

    # app-wide flux display unit. 'profile' will always be in this unit
    flux_display_unit = Unicode("").tag(sync=True)

    # app-wide unit for spectral axis, for plot title
    sa_display_unit = Unicode("").tag(sync=True)

    # to avoid calculating profile and updating plot when profile parameters
    # are being set for the first time when new data selected
    setting_defaults = Bool().tag(sync=True)

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

        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_display_units_changed)

        # attribute to access computed profile, will be a quantity array
        self._profile = None

        # override default plot styling
        self.plot.figure.fig_margin = {'top': 60, 'bottom': 60, 'left': 65,
                                       'right': 15}
        self.plot.viewer.axis_y.tick_format = '0.1e'
        self.plot.viewer.axis_y.label_offset = '50px'

    @property
    def user_api(self):
        expose = ('dataset', 'pixel', 'y_pixel', 'use_full_width', 'width',
                  'profile', 'measure_cross_dispersion_profile')
        return PluginUserApi(self, expose=expose)

    @observe("dataset_selected")
    def _set_defaults(self, event={}):
        """
        When a dataset is selected, re-calculate the default values for pixel,
        y_pixel, width, and the slider limits for selecting row/column where
        the profile will be measured.
        """
        # self.dataset might not exist when app is setting itself up.
        if hasattr(self, "dataset") and self.dataset.selected_obj is not None:
            # to avoid entering methods that observe any of these traitlets
            # while they're being set for the first time
            self.setting_defaults = True

            try:
                data = self.dataset.selected_obj
                # default value for 'y_pixel' is middle of cross dispersion axis
                self.y_pixel = math.floor(data.shape[0] / 2)
                # default value for 'pixel' is middle of spectral axis
                self.pixel = math.floor(data.shape[1] / 2)
                # slider limits
                self.max_y_pix = data.shape[0]
                self.max_pix = data.shape[1]
                # default use_full_width=True
                self.use_full_width = True
                # set appropriate default 'width' if use_full_width=False
                self.width = data.shape[0]
            finally:
                # finally, trigger to update plot/profile/marks
                self.setting_defaults = False

    @observe('pixel', 'sa_display_unit')
    def _pixel_to_wav(self, event={}):
        """
        Calculate the corresponding wavelength for ``pixel``, if wcs is present,
        when ``pixel`` is changed (or new dataset selected, in case the previous one
        had a wcs and the new one doesn't or vice versa).
        """
        data = self.dataset.selected_obj
        if data is not None:
            if hasattr(data, 'wcs') and self.sa_display_unit != '':
                wcs = self.dataset.selected_obj.wcs
                # wcs / gwcs don't necessarily have ndim attribute, so try
                # to detect 2d/1d wcs with try / except
                try:  # dataset selected wcs is 1d
                    wav = wcs.pixel_to_world(self.pixel)
                except ValueError:  # dataset selected wcs is 2d
                    if data.spectral_axis_index == 0:
                        wav = wcs.pixel_to_world(0, self.pixel)[0]
                    else:
                        # It's 2D, so this is the only option
                        wav = wcs.pixel_to_world(self.pixel, 0)[0]
                self.wav = wav.to(u.Unit(self.sa_display_unit), u.spectral()).value
            else:
                self.wav = None

    def _on_display_units_changed(self, event={}):
        """
        On flux display unit change from Unit Conversion plugin, re-compute
        profile in new unit and update plot.

        Note: re-measure profile in native data units rather than converting
        currently computed profile so repeated conversions don't accumulate
        precision errors.
        """
        if event.axis == 'flux':
            if self.flux_display_unit != event.unit:
                self.flux_display_unit = event.unit.to_string()

        if event.axis == 'spectral':
            if self.sa_display_unit != event.unit:
                self.sa_display_unit = event.unit.to_string()

    @property
    def profile(self):
        return self._profile

    @property
    def marks(self):
        """
        Access the marks created by this plugin in the spectrum-2d-viewer.
        """
        if self._marks:
            return self._marks

        if not self._tray_instance:
            return {}

        v2d = self.spectrum_2d_viewers[0]
        v1d = self.spectrum_1d_viewers[0]

        if not v2d.state.reference_data:
            return {}

        self._marks = {'2d': {'pix': PluginLine(v2d,
                                                visible=self.is_active,
                                                line_style='solid'),
                              'y_pix': PluginScatter(v2d, marker='diamond',
                                                     stroke_width=1)},
                       '1d': {'pix': PluginLine(v1d,
                                                x=[0, 0], y=[0, 1],
                                                scales={'x': v1d.scales['x'],
                                                        'y': LinearScale(min=0,
                                                                         max=1)},
                                                visible=self.is_active,
                                                line_style='solid')}}

        v2d.figure.marks = v2d.figure.marks + list(self._marks['2d'].values())
        v1d.figure.marks = v1d.figure.marks + list(self._marks['1d'].values())

        return self._marks

    @observe('dataset_selected', 'is_active', 'pixel', 'y_pixel', 'width',
             'use_full_width', 'setting_defaults')  # noqa
    def _pixel_selected_mark(self, event={}):
        """
        Update drawn marks (synced vertical lines in 2d and 1d spectrum viewers,
        scatter mark to mark center of profile on y axis) for current selected
        pixel, when any relevant parameter is changed or plugin is made active.
        """
        if self.setting_defaults:
            return

        data = self.dataset.selected_obj
        if data is not None:

            if self.use_full_width is True:
                ymax = data.shape[0]
                ymin = 0
            else:
                ymax = self.y_pixel + int(self.width/2)
                ymin = self.y_pixel - int(self.width/2)

            self.marks['2d']['pix'].update_xy(np.full(data.shape[1],
                                              self.pixel), range(ymin, ymax+1))
            self.marks['2d']['pix'].visible = self.is_active
            self.marks['2d']['y_pix'].update_xy((self.pixel, self.pixel),
                                                (self.y_pixel, self.y_pixel))
            self.marks['2d']['y_pix'].visible = self.is_active

            # plot line in 1d viewer when possible, unit conversion is handled
            # inside of Marks so we don't need to convert the limits here
            if self.wav is not None and self.sa_display_unit != '':
                self.marks['1d']['pix'].update_xy([self.wav, self.wav], [0, 1])
                self.marks['1d']['pix'].visible = self.is_active

    @observe('is_active', 'pixel', 'y_pixel', 'width', 'use_full_width',
             'flux_display_unit', 'setting_defaults')
    def _measure_cross_dispersion_profile(self, event={}):

        if self.setting_defaults:
            return

        self.measure_cross_dispersion_profile(update_plot=self.is_active)

    def measure_cross_dispersion_profile(self, update_plot=True):
        """
        Measure the cross-dispersion profile and update plugin plot.

        Calculates the cross-dispersion profile for the currently
        selected dataset at column ``pixel``. If ``use_full_width`` is True,
        the profile is computed over the entire detector width, otherwise,
        a user-defined ``width`` and center ``y_pixel`` are used. The profile
        is returned and plotted in the app-wide flux display unit, as set in
        the Unit Conversion plugin. If update_plot is True, the plugin plot
        will be updated with the computed profile.

        Parameters
        ----------
        update_plot : bool, optional
            If True, update the plugin plot with the profile (default True).

        Returns
        -------
        profile : array-like
            The computed cross-dispersion profile.

        """

        data = self.dataset.selected_obj
        if data is None:
            return

        if self.use_full_width:
            width = None
        else:
            width = self.width

        # create a FlatTrace at y_pixel
        trace = FlatTrace(data, self.y_pixel)

        profile = measure_cross_dispersion_profile(data,
                                                   trace=trace,
                                                   crossdisp_axis=0,
                                                   width=width,
                                                   pixel=self.pixel,
                                                   pixel_range=None,
                                                   align_along_trace=False)

        # convert profile, which was computed in data units, to display unit
        if self.sa_display_unit != '':
            if self.wav is not None:
                wav = self.wav * u.Unit(self.sa_display_unit)
            else:
                wav = None
            eqv = all_flux_unit_conversion_equivs(data.meta.get('PIXAR_SR', 1.0),
                                                  wav)
            profile = flux_conversion_general(profile.value, profile.unit,
                                              self.flux_display_unit, eqv)

        self._profile = profile

        if update_plot:
            self.update_plot()

    @observe('sa_display_unit')
    def update_plot(self, event={}):
        """Update plugin plot with self.profile."""

        if self.profile is None:
            return

        x = np.arange(len(self.profile))

        if not self.use_full_width:
            # translate x-axis of plot to image y-axis coordinates so plot
            # is centered on y_pixel
            x += int(self.y_pixel - (self.width / 2))

        self.plot._update_data('profile', x=x, y=self.profile, reset_lims=True)
        self.plot.update_style('profile', line_visible=True, color='gray',
                               size=32)

        title = f'Cross dispersion profile for pixel {self.pixel}'

        # include wavelength in plot title, if available
        if self.wav is not None:
            title += f' ({round(self.wav, 3)} {self.sa_display_unit})'
        self.plot.figure.title = title

        self.plot.figure.axes[0].label = 'pixel'
        self.plot.figure.axes[1].label = f'Value ({self.flux_display_unit})'

        self.plot_available = True
