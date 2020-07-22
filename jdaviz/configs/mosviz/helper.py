from jdaviz.core.helpers import ConfigHelper


class MosViz(ConfigHelper):
    """MosViz Helper class"""
    _default_configuration = 'mosviz'

    def load_1d_spectra(self, data_obj, data_labels=None):
        self.app.load_data(data_obj, parser_reference="mosviz-spec1d-parser",
                           data_labels=data_labels)

    def load_2d_spectra(self, data_obj, data_labels=None):
        self.app.load_data(data_obj, parser_reference="mosviz-spec2d-parser",
                           data_labels=data_labels)

    def load_images(self, data_obj, data_labels=None):
        self.app.load_data(data_obj, parser_reference="mosviz-image-parser",
                           data_labels=data_labels)
