import base64
import pathlib
import uuid

from jdaviz.core.registries import data_parser_registry
from specutils import Spectrum1D, SpectrumCollection

__all__ = ["specviz_spectrum1d_parser"]


@data_parser_registry("specviz-spectrum1d-parser")
def specviz_spectrum1d_parser(app, data, data_label=None, format=None, show_in_viewer=True):
    """
    Loads a data file or `~specutils.Spectrum1D` object into SpecViz.

    Parameters
    ----------
    data : str or `~specutils.Spectrum1D`
        Spectrum1D spectra, or path to compatible data file.
    data_label : str
        The Glue data label found in the ``DataCollection``.
    format : str
        Loader format specification used to indicate data format in
        `~specutils.Spectrum1D.read` io method.
    """

    # If no data label is assigned, give it a unique identifier
    if not data_label:
        data_label = "specviz_data|" + str(
            base64.b85encode(uuid.uuid4().bytes), "utf-8"
        )

    # If data provided is a path, try opening into a Spectrum1D object
    try:
        path = pathlib.Path(data)

        if path.is_file():
            data = Spectrum1D.read(str(path), format=format)
        else:
            raise FileNotFoundError("No such file: " + str(path))
    # If not, it must be a Spectrum1D object. Otherwise, it's unsupported
    except TypeError:
        if type(data) is SpectrumCollection:
            raise TypeError(
                "SpectrumCollection detected. Please provide a Spectrum1D"
            )
        elif type(data) is not Spectrum1D:
            raise TypeError("Data is not a Spectrum1D object or compatible file")

    # If there's already data in the viewer, convert units if needed
    current_spec = app.get_data_from_viewer("spectrum-viewer", data_label=data_label)
    if current_spec != {} and current_spec is not None:
        spec_key = list(current_spec.keys())[0]
        current_unit = current_spec[spec_key].spectral_axis.unit
        if data.spectral_axis.unit != current_unit:
            data = Spectrum1D(flux=data.flux,
                              spectral_axis=data.spectral_axis.to(current_unit))

    app.add_data(data, data_label)
    if show_in_viewer:
        app.add_data_to_viewer("spectrum-viewer", data_label)
