from functools import cached_property
import asdf
from pathlib import Path

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True

__all__ = ['ASDFParser']


@loader_parser_registry('asdf')
class ASDFParser(BaseParser):

    def _check_is_valid(self):
        # generalized jdaviz isn't the valid config name, but we can
        # drop it here for the string output.
        accepted_configs = ['imviz', 'specviz', 'specviz2d', 'rampviz', 'generalized jdaviz']
        if self._app.config not in ['deconfigged'] + accepted_configs:
            # NOTE: temporary during deconfig process
            return f"asdf format is only supported in {', '.join(accepted_configs)}."

        _ = self.output
        return ''

    @cached_property
    def output(self):
        if HAS_ROMAN_DATAMODELS:
            try:
                return rdd.open(self.input)
            except (ImportError, TypeError) as e:
                msg_txt = (f"{Path(self.input).name} could not be opened with the "
                           f"`roman_datamodels` package: {e} "
                           f"This file will be loaded with the `asdf` package directly.")
                self._loader_message(msg_txt, color='warning', raise_msg=True, traceback=e)

        output = asdf.open(self.input)

        try:
            # attempting to access the data triggers the error
            _ = hasattr(output['roman']['data'], '_')
        except (ModuleNotFoundError, ImportError) as e:
            msg_txt = f"{Path(self.input).name} could not be opened: {e} "
            # the input is asdf, but requires optional dependencies (e.g., lz4) which is/are
            # dependencies of roman_datamodels
            if not HAS_ROMAN_DATAMODELS:
                msg_txt += f"To install optional jdaviz dependencies for Roman, you can run: "\
                           f"pip install -U jdaviz[roman]"
            self._loader_message(msg_txt, color='error', traceback=e, raise_msg=True)
        return output

    def _cleanup(self):
        if 'output' not in self.__dict__:
            return
        try:
            self.output.close()
        except Exception:  # nosec
            pass
        self._clear_cache('output')
