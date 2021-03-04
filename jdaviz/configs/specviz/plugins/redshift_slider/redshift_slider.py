from traitlets import Bool, Float, observe, Any, Int
import astropy.units as u
from astropy.constants import c
import numpy as np

from jdaviz.core.events import AddDataMessage, RedshiftMessage
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from glue_jupyter.bqplot.profile import BqplotProfileView

__all__ = ['RedshiftSlider']


@tool_registry('g-redshift-slider')
class RedshiftSlider(TemplateMixin):
    template = load_template("redshift_slider.vue", __file__).tag(sync=True)
    slider = Any(0).tag(sync=True)
    slider_textbox = Any(0).tag(sync=True)
    slider_type = Any("Redshift").tag(sync=True)
    min_value = Float(0).tag(sync=True)
    max_value = Float(0.1).tag(sync=True)
    slider_step = Float(0.00001).tag(sync=True)
    linked = Bool(True).tag(sync=True)
    wait = Int(100).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._watched_viewers = []

        # Watch for new data to grab its redshift if it has one
        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_data_added)
        # Watch for messages from Specviz helper redshift functions
        self.session.hub.subscribe(self, RedshiftMessage,
                                   handler=self._parse_redshift_msg)

        self._update_bounds = {"Redshift": self._update_bounds_redshift,
                               "RV (km/s)": self._update_bounds_rv}

    def _on_data_added(self, msg):
        if isinstance(msg.viewer, BqplotProfileView):
            label = msg.data.label
            temp_data = self.app.get_data_from_viewer("spectrum-viewer")[label]
            if self.slider_type == "Redshift":
                new_z = temp_data.redshift.value
                if new_z < self.min_value or new_z > self.max_value:
                    self._update_bounds_redshift(new_z)
                self.slider = new_z
            else:
                new_rv = temp_data.radial_velocity.to("km/s").value
                if new_rv < self.min_value or new_rv > self.max_value:
                    self._update_bounds_rv(new_rv)
                self.slider = new_rv

    def _parse_redshift_msg(self, msg):
        '''
        Handle incoming redshift messages from the app hub. Generally these
        will be created by Specviz helper methods.
        '''
        if msg.sender == self:
            return

        param = msg.param
        val = float(msg.value)

        if param == "slider_min":
            self.min_value = val
        elif param == "slider_max":
            self.max_value = val
        elif param == "slider_step":
            self.slider_step = val
        elif param == "redshift":
            if val > self.max_value or val < self.min_value:
                self._update_bounds[self.slider_type](val)
            self.slider = val

    def _velocity_to_redshift(self, velocity):
        """
        Convert a velocity to a relativistic redshift.
        """
        beta = velocity / c
        return np.sqrt((1 + beta) / (1 - beta)) - 1

    def _redshift_to_velocity(self, redshift):
        """
        Convert a relativistic redshift to a velocity.
        """
        zponesq = (1 + redshift) ** 2
        return c * (zponesq - 1) / (zponesq + 1)

    def _propagate_redshift(self):
        """
        When the redshift is changed with the slider, send the new value to
        the line list and spectrum viewer data.
        """
        if self.slider == "" or self.slider == "-":
            return
        if self.slider_type == "Redshift":
            z = u.Quantity(self.slider)
        else:
            z = self._velocity_to_redshift(u.Quantity(self.slider, "km/s"))

        line_list = self.app.get_viewer('spectrum-viewer').spectral_lines
        if line_list is not None:
            line_list["redshift"] = z
            # Replot with the new redshift
            line_list = self.app.get_viewer('spectrum-viewer').plot_spectral_lines()

        # Send the redshift back to the Specviz helper
        msg = RedshiftMessage("redshift", z.value, sender=self)
        self.app.hub.broadcast(msg)

        '''
        for data_item in self.app.data_collection:
            if type(data_item.coords.spectral_axis) == SpectralAxis:
                if self.slider_type == "Redshift":
                    new_axis = SpectralAxis(data_item.coords.spectral_axis,
                                            redshift = self.slider)
                else:
                    new_axis = SpectralAxis(data_item.coords.spectral_axis,
                                radial_velocity = u.Quantity(self.slider, "km/s"))
                data_item.coords = SpectralCoordinates(new_axis)
        '''

    # def _slider_value_updated(self, value):
    #     if len(value) > 0:
    #         self.slider = float(value[0])

    def _set_bounds_orderly(self, new_min, new_max, new_val):
        '''Have to do this in the right order so our slider value is never out of bounds'''
        if new_val > self.max_value:
            self.max_value = new_max
            self.slider = new_val
            self.min_value = new_min
        elif new_val < self.min_value:
            self.min_value = new_min
            self.slider = new_val
            self.max_value = new_max
        else:
            self.min_value = new_min
            self.max_value = new_max

    def _update_bounds_redshift(self, new_val):
        '''Set reasonable slider parameters based on manually set redshift'''
        if new_val >= 0 and new_val - 0.5 < 0:
            new_min = 0
        else:
            new_min = new_val - 0.5
        new_max = new_val + 0.5

        self._set_bounds_orderly(new_min, new_max, new_val)

        self.slider_step = 0.001

    def _update_bounds_rv(self, new_val):
        '''Set reasonable slider parameters based on manually set radial velocity'''
        if new_val >= 0 and new_val < 100000:
            new_min = 0
            new_max = new_val + 100000
            step = 500
        elif new_val < 0 and new_val > -100000:
            new_min = new_val-100000
            new_max = 0
            step = 500
        else:
            new_min = new_val - (new_val / 100.0)
            new_max = new_val + (new_val / 100.0)
            step = new_val / 10000.0

        self._set_bounds_orderly(new_min, new_max, new_val)

        self.slider_step = step

    @observe('slider_textbox')
    def _on_textbox_change(self, event):
        try:
            val = float(event["new"])
        except ValueError:
            return

        if val > self.max_value or val < self.min_value:
            self._update_bounds[self.slider_type](val)

        if self.slider != val:
            self.slider = val

    @observe('slider')
    def _on_slider_updated(self, event):
        if not event['new']:
            value = 0
        else:
            value = float(event['new'])

        if value > self.max_value or value < self.min_value:
            self._update_bounds[self.slider_type](value)
            self.slider = value
        else:
            self.slider = value

        if self.slider != float(self.slider_textbox):
            self.slider_textbox = self.slider

        self._propagate_redshift()

    @observe('slider_type')
    def _on_type_updated(self, event):
        if event['new'] == "Redshift":
            new_val = self._velocity_to_redshift(u.Quantity(self.slider, "km/s")).value
            self._update_bounds_redshift(new_val)
            self.slider = new_val
        else:
            new_val = self._redshift_to_velocity(self.slider).to('km/s').value
            self._update_bounds_rv(new_val)
            self.slider = new_val
