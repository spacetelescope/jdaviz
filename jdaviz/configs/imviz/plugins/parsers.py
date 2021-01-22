import logging
import os

from glue.core.data_factories import fits_reader

from jdaviz.core.registries import data_parser_registry

__all__ = ["imviz_data_parser"]


@data_parser_registry("imviz-data-parser")
def imviz_data_parser(app, file_obj, data_type=None, data_label=None):
    """Loads an image into Imviz"""
    if data_type is not None and data_type.lower() != 'image':
        msg = "Data type must be 'image'."
        logging.error(msg)
        return msg

    if isinstance(file_obj, str) and os.path.exists(file_obj):
        _parse_data(app, file_obj)
    else:
        msg = f'Cannot load {file_obj}'
        logging.error(msg)
        return msg


def _parse_data(app, file_obj):
    data_list = fits_reader(file_obj)
    for data in data_list:
        app.add_data(data, data.label)
        app.add_data_to_viewer("imviz-image-viewer", data.label)
