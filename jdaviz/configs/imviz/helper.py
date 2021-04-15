from jdaviz.core.helpers import ConfigHelper


class Imviz(ConfigHelper):
    """Imviz Helper class"""
    _default_configuration = 'imviz'

    def load_data(self, data, parser_reference=None, **kwargs):
        self.app.load_data(data, parser_reference=parser_reference,
                           skip_checks=True, **kwargs)
