from functools import cached_property
from skimage.io import imread
from skimage.color import rgb2gray, rgba2rgb
from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['JPGPNGParser']


@loader_parser_registry('jpgpng')
class JPGPNGParser(BaseParser):

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d', 'lcviz', 'imviz'):
            # NOTE: temporary during deconfig process
            return False
        return isinstance(self.input, str) and self.input.endswith(('.jpg', '.jpeg', '.png'))

    @cached_property
    def output(self):
        im = imread(self.input)
        if im.shape[2] == 4:
            pf = rgb2gray(rgba2rgb(im))
        else:  # Assume RGB
            pf = rgb2gray(im)
        return pf[::-1, :]  # Flip it
