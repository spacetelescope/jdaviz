from astrowidgets.core import ImageWidget
from ginga.misc.log import get_logger

__all__ = ['Imviz']


class Imviz(ImageWidget):
    def __init__(self, **kwargs):
        if 'logger' not in kwargs:
            kwargs['logger'] = get_logger('Imviz', log_stderr=True,
                                          log_file=None, level=30)
        super().__init__(**kwargs)

    def load_data(self, filename, **kwargs):
        try:
            # TODO: Support different file formats.
            # File downloaded with download_file does not have extension
            # to check.
            self.load_fits(filename, **kwargs)
        except Exception as e:
            raise NotImplementedError(
                f'Format for {filename} not supported: {repr(e)}') from None
