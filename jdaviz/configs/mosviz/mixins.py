__all__ = ['Matched2dSpectrumMixin']


class Matched2dSpectrumMixin:
    def _setup_xaxes_linking(self):
        spec1d = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        spec2d = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)
        for k in ('x_min', 'x_max'):
            spec1d.state.add_callback(k, self._on_spec1d_x_limits_changed)
            spec2d.state.add_callback(k, self._on_spec2d_x_limits_changed)

    def _on_spec1d_x_limits_changed(self, *args):
        spec1d = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        spec2d = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)
        if spec1d.state.reference_data is None or spec2d.state.reference_data is None:
            return

        spec1d_limits = (spec1d.state.x_min, spec1d.state.x_max)
        if spec1d.state.x_display_unit == 'pix':
            spec2d_limits = spec1d_limits
        else:
            spec2d_limits = spec2d.world_to_pixel_limits(spec1d_limits)

        spec2d_x_scales = spec2d.scales['x']
        with spec2d_x_scales.hold_sync():
            spec2d_x_scales.min, spec2d_x_scales.max = spec2d_limits

    def _on_spec2d_x_limits_changed(self, *args):
        spec1d = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        spec2d = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)
        if spec1d.state.reference_data is None or spec2d.state.reference_data is None:
            return

        spec2d_limits = (spec2d.state.x_min, spec2d.state.x_max)
        if spec1d.state.x_display_unit == 'pix':
            spec1d_limits = spec2d_limits
        else:
            spec1d_limits = spec2d.pixel_to_world_limits(spec2d_limits)

        spec1d_x_scales = spec1d.scales['x']
        with spec1d_x_scales.hold_sync():
            spec1d_x_scales.min, spec1d_x_scales.max = spec1d_limits
