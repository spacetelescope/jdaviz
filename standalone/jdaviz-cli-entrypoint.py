import sys
# this avoids:
# ValueError: Key backend: 'module://matplotlib_inline.backend_inline' is not a valid value for backend; supported values are [...]
# Although not 100% why, it has two effects:
#  1. PyInstaller picks it up as a module to include
#  2. It registers the backend, maybe earlier than it would be otherwise
import matplotlib_inline
import matplotlib_inline.backend_inline

import jdaviz.cli


if __name__ == "__main__":
    # should change this to _main, but now it doesn't need arguments
    jdaviz.cli.main(layout="")
