from contextlib import nullcontext
from pathlib import Path

import numpy as np
import pytest
from asdf import AsdfFile

from jdaviz.core.loaders.parsers.asdf.asdf import ASDFParser, HAS_ROMAN_DATAMODELS


def _write_lz4_asdf(path, tree):
    """
    lz4 is a roman datamodels dependency that triggers an error when reading roman asdf
    files without it being installed. It may be worth switching this for a real/sim
    roman data file at some point.
    """
    # data is a plain, lazily loaded array, not a Quantity,
    # which asdf would convert on open and re-emit the lz4 ImportError as a warning instead.
    tree = {k: getattr(v, 'value', v) for k, v in tree.items()}
    af = AsdfFile({'roman': tree})
    af.write_to(path, all_array_compression='zlib')
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

    @pytest.mark.parametrize('from_file', [True, False])
    def test_output(self, from_file):
        if from_file:
            if HAS_ROMAN_DATAMODELS:
                from roman_datamodels.datamodels import ImageModel
                assert isinstance(self.parser.output, ImageModel)
            else:
                assert isinstance(self.parser.output, AsdfFile)
                # the wcs isn't compared since gwcs objects don't support equality
                for key in ('name', 'telescope'):
                    assert (self.parser.output['roman']['meta'][key] ==
                            self.roman_asdf_tree['meta'][key])
            assert self.parser.loader_message_items == []

            # cleanup closes and clears the cached output, and is safe to call repeatedly
            self.parser._cleanup()
            assert 'output' not in self.parser.__dict__
            self.parser._cleanup()

            inp = self.roman_asdf_file
        else:
            # in-memory AsdfFile objects are handled by the object parser
            inp = AsdfFile({'roman': self.roman_asdf_tree})

        # roman_asdf_file isn't a roman_datamodels model, but should load with units
        # with or without roman_datamodels installed. Keys are sorted when read from file,
        # so request the data extension explicitly.
        self.helper.load(inp, extension='data')
        out_component = self.helper._app.data_collection[0].get_component('DATA')
        in_data = self.roman_asdf_tree['data']
        np.testing.assert_array_equal(in_data.value, out_component.data)
        assert out_component.units == str(in_data.unit)

    # The lz4-compressed gwcs fails to convert on open, which asdf
    # only warns about before the parser raises on accessing the data.
    @pytest.mark.filterwarnings('ignore::asdf.exceptions.AsdfConversionWarning')
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

    @pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason='roman_datamodels is not installed')
    def test_load_asdf_via_rdm(self, roman_imagemodel):
        # roman_datamodels ImageModels are loaded without units
        self.helper.load(roman_imagemodel)
        out_component = self.helper._app.data_collection[0].get_component('DATA')
        np.testing.assert_array_equal(roman_imagemodel.data, out_component.data)
