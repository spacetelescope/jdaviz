from traitlets import Bool, Float, observe, Any, Int
import astropy.units as u

from jdaviz.core.events import AddDataMessage
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from glue_jupyter.bqplot.image import BqplotImageView

__all__ = ['RedshiftSlider']


@tool_registry('g-redshift-slider')
class RedshiftSlider(TemplateMixin):
    template = load_template("redshift_slider.vue", __file__).tag(sync=True)
    slider = Any(0).tag(sync=True)
    min_value = Float(-1).tag(sync=True)
    max_value = Float(1).tag(sync=True)
    slider_step = Float(0.01).tag(sync=True)
    linked = Bool(True).tag(sync=True)
    wait = Int(100).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._watched_viewers = []

        # Probably don't need a new data watcher here
        #self.session.hub.subscribe(self, AddDataMessage,
        #                           handler=self._on_data_added)

    def _propagate_redshift(self):
        """
        When the redshift is changed with the slider, send the new value to
        the line list and spectrum viewer data.
        """
        line_list = self.app.get_viewer('spectrum-viewer').spectral_lines
        line_list["redshift"]= u.Quantity(self.slider)
        # Replot with the new redshift
        line_list = self.app.get_viewer('spectrum-viewer').plot_spectral_lines()

    def _slider_value_updated(self, value):
        if len(value) > 0:
            self.slider = float(value[0])

    @observe('slider')
    def _on_slider_updated(self, event):
        if not event['new']:
            value = 0
        else:
            value = event['new']
        self._propagate_redshift()
