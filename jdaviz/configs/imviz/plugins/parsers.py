import base64
import pathlib
import uuid

from astropy.nddata import CCDData

from jdaviz.core.registries import data_parser_registry

__all__ = ["imviz_image_parser"]


@data_parser_registry("imviz-image-parser")
def imviz_image_parser(app, data, data_label=None, show_in_viewer=True):
    """Loads an image into Imviz"""
    # If no data label is assigned, give it a unique identifier
    if not data_label:
        data_label = "imviz_data|" + str(
            base64.b85encode(uuid.uuid4().bytes), "utf-8")

    path = pathlib.Path(data)
    if path.is_file():
        # TODO: Support other image formats
        data = CCDData.read(path)
    else:
        raise FileNotFoundError(f"No such file: {path}")

    app.add_data(data, data_label)
    if show_in_viewer:
        app.add_data_to_viewer("image-viewer", data_label)
