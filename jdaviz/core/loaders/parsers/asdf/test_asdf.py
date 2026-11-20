from contextlib import nullcontext
from pathlib import Path

import pytest
from asdf import AsdfFile

from jdaviz.core.loaders.parsers.asdf.asdf import ASDFParser, HAS_ROMAN_DATAMODELS


def _write_lz4_asdf(path, tree):
    # lz4 is a roman datamodels dependency that triggers an error when reading roman asdf
    # files without it being installed. It may be worth switching this for a real/sim
    # roman data file at some point.
    af = AsdfFile({'roman': tree})
    af.set_array_compression(af['roman']['data'], 'zlib')
    af.write_to(path)
    path.write_bytes(path.read_bytes().replace(b'zlib', b'lz4\x00'))
    return str(path)


class TestASDFParser:

    @pytest.fixture(autouse=True)
    def _setup(self, deconfigged_helper, roman_imagemodel, roman_asdf_tree, roman_asdf_file,
               tmp_path):
        self.helper = deconfigged_helper
        self.roman_asdf_tree = roman_asdf_tree
        self.roman_asdf_file = roman_asdf_file

        # Create a roman imagemodel file for testing if roman_datamodels is installed,
        # otherwise use the existing roman asdf file
        if HAS_ROMAN_DATAMODELS:
            valid_file = tmp_path / 'roman_imagemodel.asdf'
            roman_imagemodel.save(str(valid_file))
        else:
            valid_file = roman_asdf_file
        self.parser = ASDFParser(self.helper._app, str(valid_file))

    def test_is_valid(self, cubeviz_helper):
        assert self.parser.is_valid
        self.parser._cleanup()

        parser = ASDFParser(cubeviz_helper._app, self.parser.input)
        assert not parser.is_valid
        assert parser.is_valid.message == ("asdf format is only supported in imviz, "
                                           "specviz, specviz2d, rampviz, and generalized "
                                           "jdaviz.")

        assert parser.loader_message_items == []

    def test_output(self):
        if HAS_ROMAN_DATAMODELS:
            from roman_datamodels.datamodels import ImageModel
            assert isinstance(self.parser.output, ImageModel)
        else:
            assert isinstance(self.parser.output, AsdfFile)
            assert self.parser.output['roman']['meta'] == self.roman_asdf_tree['meta']
        assert self.parser.loader_message_items == []

        # cleanup closes and clears the cached output, and is safe to call repeatedly
        self.parser._cleanup()
        assert 'output' not in self.parser.__dict__
        self.parser._cleanup()

    def test_loader_message(self, tmp_path):
        if HAS_ROMAN_DATAMODELS:
            path = self.roman_asdf_file
            color, match = 'warning', 'could not be opened with the `roman_datamodels` package'
        else:
            path = _write_lz4_asdf(tmp_path / 'roman_lz4.asdf', self.roman_asdf_tree)
            color, match = 'error', 'pip install -U jdaviz[roman]'
        parser = ASDFParser(self.helper._app, path)

        # warnings fall back to the asdf package, errors invalidate the parser
        with pytest.warns(UserWarning, match=match) if color == 'warning' else nullcontext():
            assert bool(parser.is_valid) == (color == 'warning')

        assert len(parser.loader_message_items) == 1
        msg = parser.loader_message_items[0]
        assert msg['color'] == color
        assert msg['text'].startswith(f'{Path(path).name} could not be opened')
        assert match in msg['text']
        assert msg['traceback'] is not None
        parser._cleanup()

        if not HAS_ROMAN_DATAMODELS:
            ldr = self.helper.loaders['file']
            ldr.filepath = path
            resolver = ldr._obj

            # nothing can be loaded, so all parsers are exposed to the frontend to explain why
            # NOTE: this is only currently used by asdf so care must be taken if messages are
            #   added to other parsers
            assert resolver.format_selected == ''
            asdf_parser = resolver.format._parsers['asdf']
            assert f"IPY_MODEL_{asdf_parser.model_id}" in resolver.parser_widgets
            assert [m['color'] for m in asdf_parser.loader_message_items] == ['error']
