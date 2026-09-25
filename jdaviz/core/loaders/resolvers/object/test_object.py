from jdaviz.core.loaders.resolvers.object.object import ObjectResolver

import numpy as np


def test_object_resolver_is_valid(deconfigged_helper, tmp_path):
    """Test _check_is_valid for ObjectResolver: success and failure cases."""
    resolver = ObjectResolver(app=deconfigged_helper._app)

    # Success: plain Python object (not a path, URI, or Path)
    resolver._object = {'key': 'value'}
    assert resolver._check_is_valid() == ''

    # Failure: existing file path string
    filepath = tmp_path / 'test.fits'
    filepath.write_text('data')
    resolver._object = str(filepath)
    assert resolver._check_is_valid() == 'Object is a file path.'

    # Failure: URI strings
    for uri in ('http://example.com/data.fits', 'https://x.com/d.fits',
                'ftp://x.com/d.fits', 's3://bucket/data.fits',
                'mast://example/data.fits'):
        resolver._object = uri
        assert resolver._check_is_valid() == 'Object is an uri.'

    # Failure: Path objects
    resolver._object = filepath
    assert resolver._check_is_valid() == 'Path objects should be treated as files.'


def test_object_resolver_list_is_multiple_outputs(deconfigged_helper):
    """A top-level list/tuple passed to the object resolver is treated as multiple outputs."""
    ldr = deconfigged_helper.loaders['object']
    images = [np.zeros((3, 3)), np.zeros((4, 4))]
    ldr.object = images

    resolver = ldr._obj
    assert resolver.output == images
    assert resolver.object_repr == '<list of 2 objects>'

    fmt = resolver.format
    image_item = next(item for item in fmt.items if item['label'] == 'Image')
    assert image_item['n_total'] == 2
    assert image_item['n_valid'] == 2
    assert isinstance(resolver.importer, list)
    assert len(resolver.importer) == len(resolver.output)
    assert isinstance(resolver.parser, list)
    assert len(resolver.parser) == len(resolver.output)
    assert '(2/2)' in repr(fmt)


def test_object_resolver_list_partial_format_validity(deconfigged_helper):
    """Only outputs valid for the selected format should count towards n_valid."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = [np.zeros((3, 3)), 'not an image']

    resolver = ldr._obj
    image_item = next(item for item in resolver.format.items if item['label'] == 'Image')
    assert image_item['n_total'] == 2
    assert image_item['n_valid'] == 1

    resolver.format.selected = 'Image'
    assert not isinstance(resolver.importer, list)


def test_object_resolver_hdulist_is_single_output(deconfigged_helper, image_hdu_wcs):
    """HDUList subclasses list but should still be treated as a single output."""
    from astropy.io import fits
    hdul = fits.HDUList([fits.PrimaryHDU(), image_hdu_wcs])

    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdul

    resolver = ldr._obj
    image_item = next(item for item in resolver.format.items if item['label'] == 'Image')
    assert image_item['n_total'] == 1


def test_object_resolver_load_multiple_outputs(deconfigged_helper):
    """Loading a format valid for a subset of outputs imports the valid ones and reports
    the number skipped via a snackbar message."""
    from unittest.mock import patch
    from jdaviz.core.events import SnackbarMessage

    ldr = deconfigged_helper.loaders['object']
    ldr.object = [np.zeros((3, 3)), np.zeros((4, 4)), 'not an image']
    ldr.format = 'Image'

    messages = []
    orig_broadcast = deconfigged_helper._app.hub.broadcast

    def _capture(msg, *args, **kwargs):
        if isinstance(msg, SnackbarMessage):
            messages.append(msg.text)
        return orig_broadcast(msg, *args, **kwargs)

    with patch.object(deconfigged_helper._app.hub, 'broadcast', side_effect=_capture):
        ldr.load()

    assert len(deconfigged_helper._app.data_collection) == 2
    assert any('2 of 3 outputs imported' in text and '1 skipped' in text for text in messages)


def test_object_resolver_multiple_outputs_labels_match_preview(deconfigged_helper):
    """The data label shown in the importer widget must match the label actually created
    for that output, and each output must get its own distinct label."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = [np.zeros((3, 3)), np.zeros((4, 4))]
    ldr.format = 'Image'

    resolver = ldr._obj
    importers = resolver.importer
    # the widget the user sees/configures corresponds to the first output
    previewed_label = importers[0].data_label_value
    expected_labels = [imp.data_label_value for imp in importers]
    assert expected_labels == ['Image_ndarray_0', 'Image_ndarray_1']

    ldr.load()

    created_labels = [data.label for data in deconfigged_helper._app.data_collection]
    assert sorted(created_labels) == sorted(expected_labels)
    assert previewed_label in created_labels


def test_multiple_outputs_resolver_suffix_precedes_extension_suffix(deconfigged_helper):
    """The per-output suffix must be folded into the base label *before* an importer's
    own extension suffix, and must not be applied twice."""
    from astropy.io import fits

    def _make_hdul(value):
        hdul = fits.HDUList([fits.PrimaryHDU()])
        hdul.append(fits.ImageHDU(data=np.zeros((5, 5)) + value, name='SCI', ver=1))
        hdul.append(fits.ImageHDU(data=np.zeros((5, 5)) + value, name='ERR', ver=1))
        return hdul

    ldr = deconfigged_helper.loaders['object']
    ldr.object = [_make_hdul(1), _make_hdul(2)]
    ldr.format = 'Image'

    ldr.load()

    created_labels = [data.label for data in deconfigged_helper._app.data_collection]
    assert created_labels == ['Image_hdulist_0[SCI,1]', 'Image_hdulist_1[SCI,1]']
