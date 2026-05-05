from functools import cached_property
from skimage.io import imread
from skimage.color import rgb2gray, rgba2rgb
from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['JPGPNGParser']


@loader_parser_registry('jpgpng')
class JPGPNGParser(BaseParser):

    def _check_is_valid(self):
        # generalized jdaviz isn't the valid config name, but we can
        # drop it here for the string output.
        accepted_configs = ['specviz2d', 'lcviz', 'imviz', 'generalized jdaviz']
        if self._app.config not in ['deconfigged'] + accepted_configs:
            # NOTE: temporary during deconfig process
            return f"jpg/png format is only supported in {', '.join(accepted_configs)}."

        if not (isinstance(self.input, str) and self.input.endswith(('.jpg', '.jpeg', '.png'))):
            return 'Input must be a string path ending in .jpg, .jpeg, or .png.'

        return ''

    @cached_property
    def output(self):
        im = imread(self.input)
        if im.shape[2] == 4:
            pf = rgb2gray(rgba2rgb(im))
        else:  # Assume RGB
            pf = rgb2gray(im)
        return pf[::-1, :]  # Flip it
