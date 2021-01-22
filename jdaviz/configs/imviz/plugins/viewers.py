from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry

__all__ = ['ImvizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(BqplotImageView):
    """Image widget for Imviz."""

    default_class = None
