from jdaviz.core.helpers import ConfigHelper
from specutils import Spectrum1D, SpectrumCollection


class MosViz(ConfigHelper):
    """MosViz Helper class"""
    _default_configuration = 'mosviz'

    def load_1d_spectra(self, data_obj, data_labels=None):
        """
        Load one-dimensional spectral objects into the mosviz application.

        Parameters
        ----------
        data_obj : ~`specutils.Spectrum1D` or ~`specutils.SpectrumCollection`
            The spectral data object to load.
        data_labels : string or list, optional
            A list of string values representing the data label used to assign
            the spectrum object. In the case of a ~`SpectrumCollection`,
            each element of the list will represent the data label of a
            ~`Spectrum1D` object extracted from the collection.
        """
        if isinstance(data_labels, str):
            data_labels = [data_labels]

        if isinstance(data_obj, Spectrum1D):
            data_label = data_labels[0] if len(data_labels) > 0 else "New 1D Spectrum"

            self.app.add_data(data_obj, data_label)
            self.app.add_data_to_viewer('spectrum-viewer', data_label)

        # TODO: we parse out the internal `Spectrum1D` objects manually
        #  because glue-astronomy does not currently have a
        #  `SpectrumCollection` translator.
        elif isinstance(data_obj, SpectrumCollection):
            for i in range(len(data_obj)):
                if len(data_labels) >= i + 1:
                    data_label = data_labels[i]
                else:
                    data_label = f"New 1D Spectrum {i}"

                self.app.add_data(data_obj[i], data_label)

                # Given a spectrum collection, only plot the last item in the
                #  spectrum list
                if i == len(data_obj) - 1:
                    self.app.add_data_to_viewer('spectrum-viewer', data_label)
        else:
            raise ValueError("Data object must be either `Spectrum1D` or "
                             f"`SpectrumCollection`, got {type(data_obj)}.")


    def load_2d_spectra(self, data_obj):
        pass

    def load_image(self, data_obj, data_labels=None):
        pass

