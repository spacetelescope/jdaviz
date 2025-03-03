from functools import cached_property

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


@loader_parser_registry('object')
class ObjectParser(BaseParser):
    # pass through an object from the object resolver directly to the importers
    @property
    def is_valid(self):
        return self.input is not None

    @cached_property
    def output(self):
        return self.input
