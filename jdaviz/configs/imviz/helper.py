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
        if filename.endswith(('.fits', '.fit', '.fits.gz')):
            self.load_fits(filename, **kwargs)
        else:
            raise NotImplementedError(f'Format for {filename} not supported')
