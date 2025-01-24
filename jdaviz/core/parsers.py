import os
#import numpy as np
from functools import cached_property

from jdaviz.core.registries import resolver_registry, parser_registry, loader_registry
from jdaviz.utils import download_uri_to_path

from specutils import Spectrum1D

__all__ = ['parse']


"""
Three registries for 3 steps:
1. Resolver: for resolving string to a path or object(s)
    input: string
    output: path to file or directory or object itself (skip parsing step)
2. Parser: for parsing a file into an object(s)
    input: string or path to file or directory
    output: python object
3. Loader: for manipulating the object(s) and passing to glue (potentially in a loop)
    input: python object
    output: glue data or python object able to directly be input to glue parsers
"""


class BaseParsingStep:
    def __init__(self, input):
        self._input = input

    @property
    def input(self):
        return self._input

#    def validate_call_kwargs(self, kwargs):
#        # hmmm not sure where this belongs (in original is_valid or while calling)
#        import inspect
#        allowed_kwargs = inspect.signature(self.__call__).parameters.keys()
#        valid = np.all([k in allowed_kwargs for k in kwargs])
#        if not valid:
#            raise ValueError(f"Invalid keyword arguments passed to __call__, allowed: {allowed_kwargs}")

    @property
    def is_valid(self):
        # override by subclass
        return False

    def __call__(self):
        return self.input


class BaseParsingStepLoader(BaseParsingStep):
    @property
    def default_data_label(self):
        return self.registry_name


class ParsingStepSearch:
    valid = {}

    def __init__(self, registry, parser, input, kwargs):
        self._step = registry._step
        self._input = input
        self._kwargs = kwargs

        if isinstance(parser, BaseParsingStep):
            all_parsers = {parser.__name__: parser}
        if isinstance(parser, str):
            if parser not in registry.members:
                raise ValueError(f"\'{parser}\' not one of {list(registry.members.keys())}")
            all_parsers = {parser: registry.members.get(parser)}
        else:
            all_parsers = registry.members
        self.all_parsers = all_parsers

        # loop through all registered parsers to see which can parse the file
        valid_parsers = {}
        for parser_name, Parser in all_parsers.items():
            this_parser = Parser(input)
            if this_parser.is_valid:
                valid_parsers[parser_name] = this_parser
        self.valid_parsers = valid_parsers

    @cached_property
    def single_match(self):
        if not len(self.valid_parsers):
            all_parsers_str = ', '.join(list(self.all_parsers.keys()))
            raise ValueError(f"No valid {self._step}s found for input, tried {all_parsers_str}.")
        if len(self.valid_parsers) > 1:
            valid_parsers_str = ', '.join(list(self.valid_parsers.keys()))
            raise ValueError(f"Multiple valid {self._step}s found, please pass {self._step} as one of: {valid_parsers_str}")  # noqa
        return list(self.valid_parsers.values())[0]

    def __call__(self):
        print(f"{self._step} using {self.single_match.registry_name}")
        return self.single_match(**self._kwargs)


@resolver_registry('Local Path')
class LocalFileResolver(BaseParsingStep):
    @property
    def is_valid(self):
        return os.path.exists(self.input)

    def __call__(self):
        return self.input


@resolver_registry('URL')
class URLResolver(BaseParsingStep):
    @property
    def is_valid(self):
        return not os.path.exists(self.input)

    def __call__(self, cache=True, local_path=None, timeout=60):
        return download_uri_to_path(self.input, cache=cache,
                                    local_path=local_path, timeout=timeout)


@parser_registry('specutils.Spectrum')
class SpecutilsSpectrumParser(BaseParsingStep):
    def is_valid(self):
        if isinstance(self.input, Spectrum1D):
            return True
        if not isinstance(self.input, str):
            return False
        try:
            self.spectrum1d
        except Exception as e:
            print("spectrum1d read failed", str(e))
            return False
        return True

    @cached_property
    def spectrum1d(self):
        return Spectrum1D.read(self.input)

    def __call__(self):
        if isinstance(self.input, Spectrum1D):
            return self.input
        return self.spectrum1d


@loader_registry('1D Spectrum')
class Spectrum1DLoader(BaseParsingStepLoader):
    @property
    def is_valid(self):
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 1


@loader_registry('2D Spectrum')
class Spectrum2DLoader(BaseParsingStepLoader):
    @property
    def is_valid(self):
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 2


@loader_registry('Specreduce Trace')
class SpecreduceTraceLoader(BaseParsingStepLoader):
    @property
    def is_valid(self):
        from specreduce.tracing import Trace
        return isinstance(self.input, Trace)

    @property
    def default_data_label(self):
        return 'Trace'


def parse(input,
          resolver=None, parser=None, loader=None,
          resolver_kwargs={}, parser_kwargs={}, loader_kwargs={}):

    if isinstance(input, str) or resolver is not None:
        resolver_search = ParsingStepSearch(resolver_registry, resolver, input, resolver_kwargs)
        input = resolver_search()

    if isinstance(input, str) or parser is not None:
        parser_search = ParsingStepSearch(parser_registry, parser, input, parser_kwargs)
        input = parser_search()

    loader_search = ParsingStepSearch(loader_registry, loader, input, loader_kwargs)
    # need access to the loader itself for viewer/data_label defaults
    loader = loader_search.single_match
    # identical to loader(**loader_kwargs)
    objects = loader_search()
    if not isinstance(objects, list):
        objects = [objects]
    return objects, loader


# TODO: concept of "only_if_requested" for spectrum2d loaded as list