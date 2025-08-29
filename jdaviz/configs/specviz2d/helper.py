from astropy.utils.decorators import deprecated
from specutils import Spectrum

from jdaviz.configs.specviz import Specviz

__all__ = ['Specviz2d']


class Specviz2d(Specviz):
    """Specviz2D Helper class"""

    _default_configuration = "specviz2d"
    _default_spectrum_viewer_reference_name = "spectrum-viewer"
    _default_spectrum_2d_viewer_reference_name = "spectrum-2d-viewer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Temporary during deconfigging (until _load exposed to all configs)
        self.load = self._load

    @property
    def specviz(self):
        """
        A Specviz helper (`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Specviz2d.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz

    @deprecated(since="4.3", alternative="load")
    def load_data(self, spectrum_2d=None, spectrum_1d=None, spectrum_1d_label=None,
                  spectrum_2d_label=None, show_in_viewer=True, ext=1,
                  transpose=False, cache=None, local_path=None, timeout=None):
        """
        Load and parse a pair of corresponding 1D and 2D spectra.

        Parameters
        ----------
        spectrum_2d: str
            A spectrum as translatable container objects (e.g.,
            ``Spectrum``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        spectrum_1d: str or Spectrum
            A spectrum as translatable container objects (e.g.,
            ``Spectrum``) that can be read by glue-jupyter. Alternatively,
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

        cache : None, bool, or str
            Cache the downloaded file if the data are retrieved by a query
            to a URL or URI.

        local_path : str, optional
            Cache remote files to this path. This is only used if data is
            requested from `astroquery.mast`.

        timeout : float, optional
            If downloading from a remote URI, set the timeout limit for
            remote requests in seconds (passed to
            `~astropy.utils.data.download_file` or
            `~astroquery.mast.Conf.timeout`).
        """
        if spectrum_2d is None and spectrum_1d is None:
            raise ValueError('Must provide spectrum_2d or spectrum_1d but none given.')

        if spectrum_2d_label is None:
            spectrum_2d_label = "Spectrum 2D"
        elif spectrum_2d_label[-2:] != "2D":
            spectrum_2d_label = "{} 2D".format(spectrum_2d_label)

        if spectrum_1d_label is None:
            spectrum_1d_label = spectrum_2d_label.replace("2D", "1D")

        load_kwargs = {}
        if cache is not None:
            load_kwargs['cache'] = cache
        if timeout is not None:
            load_kwargs['timeout'] = timeout
        if local_path is not None:
            load_kwargs['local_path'] = local_path

        if spectrum_2d is not None:
            if spectrum_2d_label is not None:
                spectrum_2d_label = self.app.return_unique_name(spectrum_2d_label)
            self.load(spectrum_2d, format='2D Spectrum',
                      data_label=spectrum_2d_label,
                      ext_data_label=spectrum_1d_label,
                      auto_extract=spectrum_1d is None,
                      viewer='*' if show_in_viewer else [],
                      extension=ext,
                      **load_kwargs)
        if spectrum_1d is not None:
            if spectrum_1d_label is not None:
                spectrum_1d_label = self.app.return_unique_name(spectrum_1d_label)
            self.load(spectrum_1d, format='1D Spectrum',
                      data_label=spectrum_1d_label,
                      viewer='*' if show_in_viewer else [],
                      **load_kwargs)

    @deprecated(since="4.3", alternative="load")
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
        self.load(trace, format='trace', data_label=data_label,
                  viewer='*' if show_in_viewer else [])

    def get_data(self, data_label=None, spectral_subset=None,
                 cls=Spectrum, use_display_units=False):
        """
        Returns data with name equal to data_label of type cls with subsets applied from
        spectral_subset.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spectral_subset : str, optional
            Spectral subset applied to data.
        cls : `~specutils.Spectrum`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.
        use_display_units : bool, optional
            Specify whether the returned data is in native units or the current display units.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        return self._get_data(data_label=data_label, spectral_subset=spectral_subset,
                              cls=cls, use_display_units=use_display_units)
