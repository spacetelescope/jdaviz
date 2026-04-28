from functools import cached_property

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


@loader_parser_registry('object')
class ObjectParser(BaseParser):
    # pass through an object from the object resolver directly to the importers
    def _check_is_valid(self):
        if self.input is None:
            return 'Input must not be None.'
        return ''

    @cached_property
    def output(self):
        return self.input
