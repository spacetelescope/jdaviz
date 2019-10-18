from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewers


viewers.add("profile-1d", label="Profile 1D", cls=BqplotProfileView)
viewers.add("imshow", label="Image 2D", cls=BqplotImageView)
