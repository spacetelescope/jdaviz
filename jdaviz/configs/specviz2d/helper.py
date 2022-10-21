import numpy as np

from jdaviz.configs.specviz import Specviz
from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import SnackbarMessage
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction import SpectralExtraction  # noqa

__all__ = ['Specviz2d']


class Specviz2d(ConfigHelper, LineListMixin):
    """Specviz2D Helper class"""

    _default_configuration = "specviz2d"
    _default_spectrum_viewer_reference_name = "spectrum-viewer"
    _default_spectrum_2d_viewer_reference_name = "spectrum-2d-viewer"
    _default_table_viewer_reference_name = "table-viewer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        spec1d = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        spec1d.scales['x'].observe(self._update_spec2d_x_axis)

        spec2d = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)
        spec2d.scales['x'].observe(self._update_spec1d_x_axis)

    @property
    def specviz(self):
        """
        A Specviz helper (`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Specviz2d.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz

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
            spec1d = self.app.get_viewer(
                self._default_spectrum_viewer_reference_name
            ).state.reference_data.label
            extend_by = int(self.app.data_collection[spec1d]["World 0"].shape[0])
            world = self._extend_world(spec1d, extend_by)

            # Warn the user if they've panned far enough away from the data
            # that the viewers will desync
            if new_val > world[-1] or new_val < world[0]:
                self.app.hub.broadcast(SnackbarMessage(
                    "Panning too far away from the data may desync the 1D and 2D spectrum viewers.",
                    color='warning', sender=self))

            idx = float((np.abs(world - new_val)).argmin()) - extend_by
            scales = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name).scales
            old_idx = getattr(scales['x'], name)
            if idx != old_idx:
                setattr(scales['x'], name, idx)

    def _update_spec1d_x_axis(self, change):
        if self.app.get_viewer(
                self._default_spectrum_viewer_reference_name
        ).state.reference_data is None:
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
            spec1d = self.app.get_viewer(
                self._default_spectrum_viewer_reference_name
            ).state.reference_data.label
            extend_by = int(self.app.data_collection[spec1d]["World 0"].shape[0])
            world = self._extend_world(spec1d, extend_by)

            scales = self.app.get_viewer(
                self._default_spectrum_viewer_reference_name
            ).scales
            old_val = getattr(scales['x'], name)

            # Warn the user if they've panned far enough away from the data
            # that the viewers will desync
            try:
                val = world[new_idx+extend_by]
            except IndexError:
                val = old_val
                self.app.hub.broadcast(SnackbarMessage(
                    "Panning too far away from the data may desync the 1D and 2D spectrum viewers.",
                    color='warning', sender=self))
            if val != old_val:
                setattr(scales['x'], name, val)

    def load_data(self, spectrum_2d=None, spectrum_1d=None, spectrum_1d_label=None,
                  spectrum_2d_label=None, show_in_viewer=True, ext=1,
                  transpose=False):
        """
        Load and parse a pair of corresponding 1D and 2D spectra.

        Parameters
        ----------
        spectrum_2d: str
            A spectrum as translatable container objects (e.g.,
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        spectrum_1d: str or Spectrum1D
            A spectrum as translatable container objects (e.g.,
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        spectrum_1d_label : str
            String representing the label for the data item loaded via
            ``spectrum_1d``.

        spectrum_2d_label : str
            String representing the label for the data item loaded via
            ``spectrum_2d``.

        show_in_viewer : bool
            Show data in viewer(s).

        ext : int, optional
            Extension of the input ``spectrum_2d`` file to load. Defaults to 1.

        transpose : bool, optional
            Flag to transpose the 2D data array before loading. Useful for uncalibrated
            data that is dispersed vertically, to change it to horizontal dispersion.
        """
        if spectrum_2d is None and spectrum_1d is None:
            raise ValueError('Must provide spectrum_2d or spectrum_1d but none given.')

        if spectrum_2d_label is None:
            spectrum_2d_label = "Spectrum 2D"
        elif spectrum_2d_label[-2:] != "2D":
            spectrum_2d_label = "{} 2D".format(spectrum_2d_label)

        if spectrum_1d_label is None:
            spectrum_1d_label = spectrum_2d_label.replace("2D", "1D")

        load_1d = False

        if spectrum_2d is not None:
            self.app.load_data(spectrum_2d, parser_reference="mosviz-spec2d-parser",
                               data_labels=spectrum_2d_label,
                               show_in_viewer=False, add_to_table=False,
                               ext=ext, transpose=transpose)

            # Passing show_in_viewer into app.load_data does not work anymore,
            # so we force it to show here.
            if show_in_viewer:
                self.app.add_data_to_viewer(
                    self._default_spectrum_2d_viewer_reference_name, spectrum_2d_label
                )
            # Collapse the 2D spectrum to 1D if no 1D spectrum provided
            if spectrum_1d is None:
                # create a non-interactive (so that it does not create duplicate marks with the
                # plugin-instance created later) instance of the SpectralExtraction plugin,
                # and use the defaults to generate the initial 1D extracted spectrum
                spext = SpectralExtraction(
                    app=self.app, interactive=False,
                    spectrum_viewer_reference_name=self._default_spectrum_viewer_reference_name,
                    spectrum_2d_viewer_reference_name=(
                        self._default_spectrum_2d_viewer_reference_name
                    )
                )
                # for some reason, the trailets are resetting to their default values even
                # though _trace_dataset_selected was called internally to set them to reasonable
                # new defaults.  We'll just call it again manually.
                spext._trace_dataset_selected()
                try:
                    spext.export_extract_spectrum(add_data=True)
                except Exception:
                    msg = SnackbarMessage(
                        "Automatic spectrum extraction failed. See the spectral extraction"
                        " plugin to perform a custom extraction",
                        color='error', sender=self, timeout=10000)
                else:
                    # Warn that this shouldn't be used for science
                    msg = SnackbarMessage(
                        "The extracted 1D spectrum was generated automatically."
                        " See the spectral extraction plugin for details or to"
                        " perform a custom extraction.",
                        color='warning', sender=self, timeout=10000)
                self.app.hub.broadcast(msg)

            else:
                load_1d = True

        else:
            load_1d = True

        if load_1d:
            self.app.load_data(
                spectrum_1d, data_label=spectrum_1d_label,
                parser_reference="specviz-spectrum1d-parser",
                show_in_viewer=show_in_viewer,
            )

    def load_trace(self, trace, data_label, show_in_viewer=True):
        """
        Load a trace object and load into the spectrum-2d-viewer

        Parameters
        ----------
        trace : Trace
            A specreduce trace object
        data_label : str
            String representing the label
        show_in_viewer : bool
            Whether to load into the spectrum-2d-viewer.
        """
        self.app.add_data(trace, data_label=data_label)
        if show_in_viewer:
            self.app.add_data_to_viewer(
                self._default_spectrum_2d_viewer_reference_name, data_label
            )
