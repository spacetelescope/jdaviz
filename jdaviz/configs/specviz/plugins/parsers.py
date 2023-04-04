import pathlib
from collections import defaultdict

import numpy as np
from astropy.io.registry import IORegistryError
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum1D, SpectrumList, SpectrumCollection

from jdaviz.core.registries import data_parser_registry
from jdaviz.utils import standardize_metadata

__all__ = ["specviz_spectrum1d_parser"]


@data_parser_registry("specviz-spectrum1d-parser")
def specviz_spectrum1d_parser(app, data, data_label=None, format=None, show_in_viewer=True,
                              concat_by_file=False):
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
    concat_by_file : bool
        If True and there is more than one available extension, concatenate
        the extensions within each spectrum file passed to the parser and
        add a concatenated spectrum to the data collection.
    """
    spectrum_viewer_reference_name = app._jdaviz_helper._default_spectrum_viewer_reference_name
    # If no data label is assigned, give it a unique name
    if not data_label:
        data_label = app.return_data_label(data, alt_name="specviz_data")

    if isinstance(data, SpectrumCollection):
        raise TypeError("SpectrumCollection detected."
                        " Please provide a Spectrum1D or SpectrumList")
    elif isinstance(data, Spectrum1D):
        data = [data]
        data_label = [app.return_data_label(data_label, alt_name="specviz_data")]
    # No special processing is needed in this case, but we include it for completeness
    elif isinstance(data, SpectrumList):
        pass
    elif isinstance(data, list):
        data = SpectrumList.read(data, format=format)
    else:
        path = pathlib.Path(data)

        if path.is_file():
            try:
                data = [Spectrum1D.read(str(path), format=format)]
                data_label = [app.return_data_label(data_label, alt_name="specviz_data")]
            except IORegistryError:
                # Multi-extension files may throw a registry error
                data = SpectrumList.read(str(path), format=format)
        elif path.is_dir():
            data = SpectrumList.read(str(path), format=format)
            if data == []:
                raise ValueError(f"`specutils.SpectrumList.read('{str(path)}')` "
                                 "returned an empty list")
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

    with app.data_collection.delay_link_manager_update():
        # these are used to build a combined spectrum with all
        # input spectra included (taken from https://github.com/spacetelescope/
        # dat_pyinthesky/blob/main/jdat_notebooks/MRS_Mstar_analysis/
        # JWST_Mstar_dataAnalysis_analysis.ipynb)
        wlallorig = []
        fnuallorig = []
        dfnuallorig = []

        for i, spec in enumerate(data):

            wave_units = spec.spectral_axis.unit
            flux_units = spec.flux.unit

            # Make metadata layout conform with other viz.
            spec.meta = standardize_metadata(spec.meta)

            app.add_data(spec, data_label[i])

            # handle display, with the SpectrumList special case in mind.
            if show_in_viewer:
                if isinstance(data, SpectrumList):

                    # add spectrum to combined result
                    for wlind in range(len(spec.spectral_axis)):
                        wlallorig.append(spec.spectral_axis[wlind].value)
                        fnuallorig.append(spec.flux[wlind].value)
                        dfnuallorig.append(spec.uncertainty[wlind].array)

                elif i == 0:
                    app.add_data_to_viewer(spectrum_viewer_reference_name, data_label[i])

        if concat_by_file and isinstance(data, SpectrumList):
            # If >1 spectra in the list were opened from the same FITS file,
            # group them by their original FITS filenames and add their combined
            # 1D spectrum to the DataCollection.
            unique_files = group_spectra_by_filename(app.data_collection)
            for filename, datasets in unique_files.items():
                if len(datasets) > 1:
                    spec = combine_lists_to_1d_spectrum(wlallorig, fnuallorig, dfnuallorig,
                                                        wave_units, flux_units)

                    # Make metadata layout conform with other viz.
                    spec.meta = standardize_metadata(spec.meta)

                    label = f"Combined [{filename}]"
                    app.add_data(spec, label)

                    if show_in_viewer:
                        app.add_data_to_viewer(spectrum_viewer_reference_name, label)


def group_spectra_by_filename(datasets):
    """
    Organize the elements of a `~glue.core.data_collection.DataCollection` by the name of
    the FITS file they came from, if available via the header card "FILENAME".

    Parameters
    ----------
    datasets : `~glue.core.data_collection.DataCollection`
        Collection of datasets.

    Returns
    -------
    spectra_to_combine : dict
        Datasets of spectra organized by their filename.
    """
    spectra_to_combine = defaultdict(list)

    for data in datasets:
        filename = data.meta.get("FILENAME")
        spectra_to_combine[filename].append(data)

    return spectra_to_combine


def combine_lists_to_1d_spectrum(wl, fnu, dfnu, wave_units, flux_units):
    """
    Combine lists of 1D spectra into a composite `~specutils.Spectrum1D` object.

    Parameters
    ----------
    wl : list of `~astropy.units.Quantity`s
        Wavelength in each spectral channel
    fnu : list of `~astropy.units.Quantity`s
        Flux in each spectral channel
    dfnu : list of `~astropy.units.Quantity`s
        Uncertainty on each flux

    Returns
    -------
    spec : `~specutils.Spectrum1D`
        Composite 1D spectrum.
    """
    wlallarr = np.array(wl)
    fnuallarr = np.array(fnu)
    dfnuallarr = np.array(dfnu)
    srtind = np.argsort(wlallarr)
    wlall = wlallarr[srtind]
    fnuall = fnuallarr[srtind]
    fnuallerr = dfnuallarr[srtind]

    # units are not being handled properly yet.
    unc = StdDevUncertainty(fnuallerr * flux_units)
    spec = Spectrum1D(flux=fnuall * flux_units, spectral_axis=wlall * wave_units,
                      uncertainty=unc)
    return spec
