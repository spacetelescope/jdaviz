import sys
# this avoids:
# ValueError: Key backend: 'module://matplotlib_inline.backend_inline' is not a valid value for backend; supported values are [...]
# Although not 100% why, it has two effects:
#  1. PyInstaller picks it up as a module to include
#  2. It registers the backend, maybe earlier than it would be otherwise
import matplotlib_inline
import matplotlib_inline.backend_inline

# We still see the above error on CI on jdaviz, and the PyInstaller
# output recommends the following:
import matplotlib
matplotlib.use("module://matplotlib_inline.backend_inline")
# since matplotlib 3.9 (see https://github.com/matplotlib/matplotlib/pull/27948),
# it seems that matplotlib_inline.backend_inline is an alias for inline
# so we make sure to communicate that to PyInstaller
matplotlib.use("inline")

import jdaviz.cli


if __name__ == "__main__":
    # should change this to _main, but now it doesn't need arguments
    args = sys.argv.copy()
    # change the browser to qt if not specified
    if "--browser" not in args:
        args.append("--browser")
        args.append("qt")
    sys.argv = args
    jdaviz.cli._main()
