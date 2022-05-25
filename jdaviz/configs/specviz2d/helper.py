import numpy as np

from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import SnackbarMessage
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin

__all__ = ['Specviz2d']


class Specviz2d(ConfigHelper, LineListMixin):
    """Specviz2D Helper class"""

    _default_configuration = "specviz2d"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        spec1d = self.app.get_viewer("spectrum-viewer")
        spec1d.scales['x'].observe(self._update_spec2d_x_axis)

        spec2d = self.app.get_viewer("spectrum-2d-viewer")
        spec2d.scales['x'].observe(self._update_spec1d_x_axis)

    def _extend_world(self, spec1d, ext):
        # Extend 1D spectrum world axis to enable panning (within reason) past
        # the bounds of data
        world = self.app.data_collection[spec1d]["World 0"].copy()
        dw = world[1]-world[0]
        prepend = np.linspace(world[0]-dw*ext, world[0]-dw, ext)
        dw = world[-1]-world[-2]
        append = np.linspace(world[-1]+dw, world[-1]+dw*ext, ext)
        world = np.hstack((prepend, world, append))
        return world

    def _update_spec2d_x_axis(self, change):
        # This assumes the two spectrum viewers have the same x-axis shape and
        # wavelength solution, which should always hold
        if change['old'] is None:
            pass
        else:
            name = change['name']
            if name not in ['min', 'max']:
                return
            new_val = change['new']
            spec1d = self.app.get_viewer('spectrum-viewer').state.reference_data.label
            extend_by = int(self.app.data_collection[spec1d]["World 0"].shape[0])
            world = self._extend_world(spec1d, extend_by)

            # Warn the user if they've panned far enough away from the data
            # that the viewers will desync
            if new_val > world[-1] or new_val < world[0]:
                msg = "Warning: panning too far away from the data may desync\
                      the 1D and 2D spectrum viewers"
                msg = SnackbarMessage(msg, color='warning', sender=self)
                self.app.hub.broadcast(msg)

            idx = float((np.abs(world - new_val)).argmin()) - extend_by
            scales = self.app.get_viewer('spectrum-2d-viewer').scales
            old_idx = getattr(scales['x'], name)
            if idx != old_idx:
                setattr(scales['x'], name, idx)

    def _update_spec1d_x_axis(self, change):
        if self.app.get_viewer('spectrum-viewer').state.reference_data is None:
            return

        # This assumes the two spectrum viewers have the same x-axis shape and
        # wavelength solution, which should always hold
        if change['old'] is None:
            pass
        else:
            name = change['name']
            if name not in ['min', 'max']:
                return
            new_idx = int(np.around(change['new']))
            spec1d = self.app.get_viewer('spectrum-viewer').state.reference_data.label
            extend_by = int(self.app.data_collection[spec1d]["World 0"].shape[0])
            world = self._extend_world(spec1d, extend_by)

            scales = self.app.get_viewer('spectrum-viewer').scales
            old_val = getattr(scales['x'], name)

            # Warn the user if they've panned far enough away from the data
            # that the viewers will desync
            try:
                val = world[new_idx+extend_by]
            except IndexError:
                val = old_val
                msg = "Warning: panning too far away from the data may desync \
                       the 1D and 2D spectrum viewers"
                msg = SnackbarMessage(msg, color='warning', sender=self)
                self.app.hub.broadcast(msg)
            if val != old_val:
                setattr(scales['x'], name, val)

    def load_data(self, spectrum_2d=None, spectrum_1d=None, spectrum_1d_label=None,
                  spectrum_2d_label=None, show_in_viewer=True):
        """
        Load and parse a pair of corresponding 1D and 2D spectra

        Parameters
        ----------
        spectrum_1d: str or Spectrum1D
            A spectrum as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        spectrum_2d: str
            A spectrum as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        spectrum_1d_label : str
            String representing the label for the data item loaded via
            ``spectrum_1d``.

        spectrum_2d_label : str
            String representing the label for the data item loaded via
            ``spectrum_2d``.

        """
        if spectrum_2d_label is None:
            spectrum_2d_label = "Spectrum 2D"
        elif spectrum_2d_label[-2:] != "2D":
            spectrum_2d_label = "{} 2D".format(spectrum_2d_label)

        if spectrum_1d_label is None:
            spectrum_1d_label = spectrum_2d_label.replace("2D", "1D")

        if spectrum_2d is not None:
            self.app.load_data(spectrum_2d, parser_reference="mosviz-spec2d-parser",
                               data_labels=spectrum_2d_label,
                               show_in_viewer=False,
                               add_to_table=False)

            # Passing show_in_viewer into app.load_data does not work anymore,
            # so we force it to show here.
            if show_in_viewer:
                self.app.add_data_to_viewer("spectrum-2d-viewer", spectrum_2d_label)

            # Collapse the 2D spectrum to 1D if no 1D spectrum provided
            if spectrum_1d is None:
                self.app.load_data(spectrum_2d,
                                   parser_reference="spec2d-1d-parser",
                                   data_label=spectrum_1d_label,
                                   show_in_viewer=show_in_viewer)

                # Warn that this shouldn't be used for science
                msg = ("The collapsed 1D spectrum is for quicklook"
                       " purposes only. A robust extraction should be used for"
                       " scientific use cases.")
                msg = SnackbarMessage(msg, color='warning', sender=self,
                                      timeout=10000)
                self.app.hub.broadcast(msg)

        else:
            self.app.load_data(spectrum_1d, data_label=spectrum_1d_label,
                               parser_reference="specviz-spectrum1d-parser",
                               show_in_viewer=show_in_viewer)
