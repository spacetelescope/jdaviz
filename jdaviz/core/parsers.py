from functools import cached_property

from jdaviz.core.registries import parser_registry

from specutils import Spectrum1D
from specutils.io.registers import identify_spectrum_format

__all__ = ['parse']


class BaseParser:
    registry_name = None  # populated by parser_registry decorator

    def __init__(self, input, shared_info={}):
        self.shared_info = shared_info  # dictionary of parsed objects to be re-used between parsers
        self._input = input
        # trigger the cached_property
        _ = self.can_parse

    @property
    def input(self):
        return self._input

    @cached_property
    def default_data_label(self):
        # optional override by subclass
        # has access to self.input and anything stored by can_parse
        return self.registry_name

    @cached_property
    def default_viewer(self):
        # override by subclass
        # has access to self.input and anything stored by can_parse
        return 'scatter'

    @cached_property
    def can_parse(self):
        # override by subclass, ONLY use self.input
        # anything that needs to be opened can be stored internally for other methods (i.e. _input_to_object)
        return False

    def _input_to_object(self):
        # override by subclass
        # has access to self.input and anything stored by can_parse
        # can return single object or list (in which case _object_to_glue_data should also handle)
        return self.input

    @cached_property
    def object(self):
        if not self.can_parse:
            raise ValueError("Cannot parse input")
        return self._input_to_object()

    def _object_to_glue_data(self):
        # override by subclass
        # has access to self.input and self.object and can return single entry or list
        return self.object

    @cached_property
    def glue_data(self):
        if not self.can_parse:
            raise ValueError("Cannot parse input")
        data = self._object_to_glue_data()
        if not isinstance(data, list):
            data = [data]
        return data


@parser_registry('1D Spectrum')
class Spectrum1DParser(BaseParser):
    def default_viewer(self):
        return 'spectrum-viewer'

    @cached_property
    def can_parse(self):
        if 'Spectrum1D' in self.shared_info:
            pass
        elif isinstance(self.input, Spectrum1D):
            self.shared_info['Spectrum1D'] = self.input
        if isinstance(self.input, str):
            if 'specutils_format' not in self.shared_info:
                try:
                    format = identify_spectrum_format(self.input, Spectrum1D)
                except ValueError:
                    return False
                else:
                    self.shared_info['specutils_format'] = format
            if self.shared_info['specutils_format'] in ('JWST x1d',):
                self.shared_info['Spectrum1D'] = Spectrum1D.read(self.input)
            else:
                return False
        else:
            return False
        return self.shared_info['Spectrum1D'].flux.ndim == 1

    def _input_to_object(self):
        # has access to self.input and anything stored by can_parse
        return self.shared_info['Spectrum1D']


@parser_registry('2D Spectrum')
class Spectrum2DParser(BaseParser):
    def default_viewer(self):
        return 'spectrum-2d-viewer'

    @cached_property
    def can_parse(self):
        if 'Spectrum1D' in self.shared_info:
            pass
        elif isinstance(self.input, str):
            if 'specutils_format' not in self.shared_info:
                try:
                    format = identify_spectrum_format(self.input, Spectrum1D)
                except ValueError:
                    return False
                else:
                    self.shared_info['specutils_format'] = format
            if self.shared_info['specutils_format'] in ('JWST s2d',):
                self.shared_info['Spectrum1D'] = Spectrum1D.read(self.input)
            else:
                return False
        elif isinstance(self.input, Spectrum1D):
            self.shared_info['Spectrum1D'] = self.input
        else:
            return False
        return self.shared_info['Spectrum1D'].flux.ndim == 2

    def _input_to_object(self):
        # has access to self.input and anything stored by can_parse
        return self.shared_info['Spectrum1D']


@parser_registry('2D Spectral Trace')
class SpectralTraceParser(BaseParser):
    def default_viewer(self):
        return 'spectrum-2d-viewer'

    @cached_property
    def can_parse(self):
        from specreduce.tracing import Trace
        return isinstance(self.input, Trace)


def parse(input, parser=None):
    # if input is a string, but not path/file, then download first

    # by default, search through all registered parsers, but also allow
    # passing a Parser class or name of registered parser.
    # could also be extended to allow pre-parsing of MOS data
    if isinstance(parser, BaseParser):
        all_parsers = {parser.__name__: parser}
    if isinstance(parser, str):
        if parser not in parser_registry.members:
            raise ValueError(f"\'{parser}\' not one of {list(parser_registry.members.keys())}")
        all_parsers = {parser: parser_registry.members.get(parser)}
    else:
        all_parsers = parser_registry.members

    # loop through all registered parsers to see which can parse the file
    valid_parsers = {}
    shared_info = {}
    for parser_name, Parser in all_parsers.items():
        this_parser = Parser(input, shared_info)
        shared_info.update(this_parser.shared_info)
        if this_parser.can_parse:
            valid_parsers[parser_name] = this_parser
    if not len(valid_parsers):
        all_parsers_str = ', '.join(list(all_parsers.keys()))
        raise ValueError(f"No valid parsers found for input, tried {all_parsers_str}.")
    if len(valid_parsers) > 1:
        valid_parsers_str = ', '.join(list(valid_parsers.keys()))
        raise ValueError(f"Multiple valid parsers found, please pass parser as one of: {valid_parsers_str}")  # noqa
    return list(valid_parsers.values())[0]