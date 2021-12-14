import sys
import base64
import pathlib
import uuid

import numpy as np

from astropy.io.registry import IORegistryError
from specutils import Spectrum1D, SpectrumList, SpectrumCollection

from jdaviz.core.registries import data_parser_registry

__all__ = ["specviz_spectrum1d_parser"]


@data_parser_registry("specviz-spectrum1d-parser")
def specviz_spectrum1d_parser(app, data, data_label=None, format=None, show_in_viewer=True):
    """
    Loads a data file or `~specutils.Spectrum1D` object into Specviz.

    Parameters
    ----------
    data : str, `~specutils.Spectrum1D`, or `~specutils.SpectrumList`
        Spectrum1D, SpectrumList, or path to compatible data file.
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

    if isinstance(data, SpectrumCollection):
        raise TypeError("SpectrumCollection detected."
                        " Please provide a Spectrum1D or SpectrumList")
    elif isinstance(data, Spectrum1D):
        data = [data]
        data_label = [data_label]
    elif isinstance(data, SpectrumList):
        pass
    elif isinstance(data, list):
        data = SpectrumList.read(data, format=format)
    else:
        path = pathlib.Path(data)

        if path.is_file():
            try:
                data = [Spectrum1D.read(str(path), format=format)]
                data_label = [data_label]
            except IORegistryError:
                # Multi-extension files may throw a registry error
                data = SpectrumList.read(str(path), format=format)
        elif path.is_dir():
            data = SpectrumList.read(str(path), format=format)
        else:
            raise FileNotFoundError("No such file: " + str(path))

    if isinstance(data, SpectrumList):
        if not isinstance(data_label, (list, tuple)):
            temp_labels = []
            for i in range(len(data)):
                temp_labels.append(f"{data_label} {i}")
            data_label = temp_labels
        elif len(data_label) != len(data):
            raise ValueError(f"Length of data labels list ({len(data_label)}) is different"
                             f" than length of list of data ({len(data)})")

    # If there's already data in the viewer, convert units if needed
    current_unit = None
    current_spec = app.get_data_from_viewer("spectrum-viewer")
    if current_spec != {} and current_spec is not None:
        spec_key = list(current_spec.keys())[0]
        current_unit = current_spec[spec_key].spectral_axis.unit
    with app.data_collection.delay_link_manager_update():

        # these are used to reset the display range
        # when SpectrumList objects are displayed.
        x_min = sys.float_info.max
        x_max = -sys.float_info.max
        y_min = sys.float_info.max
        y_max = -sys.float_info.max

        for i in range(len(data)):
            spec = data[i]
            if current_unit is not None and spec.spectral_axis.unit != current_unit:
                spec = Spectrum1D(flux=spec.flux,
                                  spectral_axis=spec.spectral_axis.to(current_unit))

            app.add_data(spec, data_label[i])

            # Only auto-show the first spectrum in a list, except if it is a SpectrumList
            if show_in_viewer:
                if isinstance(data, SpectrumList):
                    app.add_data_to_viewer("spectrum-viewer", data_label[i])

                    x_min = min(x_min, np.min(spec.spectral_axis.value))
                    x_max = max(x_max, np.max(spec.spectral_axis.value))

                    y_min = min(y_min, np.min(spec.flux.value))
                    y_max = max(y_max, np.max(spec.flux.value))

                elif i == 0:
                    app.add_data_to_viewer("spectrum-viewer", data_label[i])

        # reset display ranges for SpectrumList
        if isinstance(data, SpectrumList):

            scale = app.get_viewer("spectrum-viewer").scale_x
            scale.min = float(x_min)
            scale.max = float(x_max)

            scale = app.get_viewer("spectrum-viewer").scale_y
            scale.min = float(y_min)
            scale.max = float(y_max)
