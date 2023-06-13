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

    @property
    def specviz(self):
        """
        A Specviz helper (`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Specviz2d.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz

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

    def get_data(self, data_label=None, spectral_subset=None, cls=None):
        """
        Returns data with name equal to data_label of type cls with subsets applied from
        spectral_subset.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spectral_subset : str, optional
            Spectral subset applied to data.
        cls : `~specutils.Spectrum1D`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        return self._get_data(data_label=data_label, spectral_subset=spectral_subset, cls=cls)
