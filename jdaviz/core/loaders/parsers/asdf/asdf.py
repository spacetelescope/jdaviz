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
        accepted_configs = ['imviz', 'specviz', 'specviz2d', 'rampviz']
        # NOTE: temporary during deconfig process
        if self._app.config not in ['deconfigged'] + accepted_configs:
            # generalized jdaviz isn't the valid config name, but we can
            # drop it here for the string output.
            accepted_configs += ['and generalized jdaviz']
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
                self._loader_message(msg_txt, color='warning', traceback=msg_txt, raise_msg=True)

        output = None
        try:
            # opening or accessing the data may require optional dependencies
            # from roman_datamodels, e.g., lz4 for decompression
            output = asdf.open(self.input)
            # requesting 'roman' matches the check in the image importer
            _ = hasattr(output['roman']['data'], '_')

        except ImportError as e:
            # output isn't cached when raising, so _cleanup can't close it later
            if output is not None:
                output.close()

            msg_txt = f"{Path(self.input).name} could not be opened: {e}"
            if not HAS_ROMAN_DATAMODELS:
                msg_txt += " To install optional jdaviz dependencies for Roman, you can run: "\
                           "pip install -U jdaviz[roman]"
            self._loader_message(msg_txt, color='error', traceback=msg_txt, raise_msg=True)

        return output

    def _cleanup(self):
        if 'output' not in self.__dict__:
            return
        try:
            self.output.close()
        except Exception:  # nosec
            pass
        self._clear_cache('output')
