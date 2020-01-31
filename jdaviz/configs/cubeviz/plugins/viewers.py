from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewers


viewers.add("g-profile-viewer", label="Profile 1D", cls=BqplotProfileView)
viewers.add("g-image-viewer", label="Image 2D", cls=BqplotImageView)
