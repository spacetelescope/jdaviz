import pathlib

from astropy.nddata import CCDData

from jdaviz.core.registries import data_parser_registry

__all__ = ["imviz_image_parser"]


@data_parser_registry("imviz-image-parser")
def imviz_image_parser(app, data, data_label=None, show_in_viewer=True):
    """Loads an image into Imviz"""
    # If no data label is assigned, give it a unique identifier
    if not data_label:
        from astrowidgets.glupyter import _gen_random_label
        data_label = _gen_random_label(prefix="imviz_data|")

    path = pathlib.Path(data)
    if path.is_file():
        # TODO: Support other image formats
        data = CCDData.read(path)
    else:
        raise FileNotFoundError(f"No such file: {path}")

    app.add_data(data, data_label)
    if show_in_viewer:
        app.add_data_to_viewer("imviz-image-viewer", data_label, clear_other_data=True)
