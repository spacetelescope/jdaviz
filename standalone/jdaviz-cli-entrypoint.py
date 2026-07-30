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
from pathlib import Path
import os
import jdaviz.cli


if __name__ == "__main__":

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):

        # Define a safe user-writable path (e.g., user's home folder)
        user_home = Path.home() 
        user_downloads = user_home / "Downloads"

        # if the Downloads directory is found, set the JDAVIZ_CACHE_DIR to put mast downloaded data in Downloads
        if user_downloads.is_dir():
            os.environ['JDAVIZ_CACHE_DIR'] = str(user_downloads)

        # if Downloads is not easily discoverable, create a directory in the home directory to save the data. 
        else:
            writable_cache_dir = user_home / "jdaviz_downloads"
            writable_cache_dir.mkdir(exist_ok=True)
            os.environ['JDAVIZ_CACHE_DIR'] = str(writable_cache_dir)

        os.environ['ASTROPY_CACHE_DIR'] = str(user_home / ".cache" / "astropy")

        # Change Python's working directory to a writable directory
        # This prevents Jdaviz from defaulting download_uri_to_path to the read-only _MEIPASS path
        os.chdir(user_home)


    # should change this to _main, but now it doesn't need arguments
    args = sys.argv.copy()
    # change the browser to qt if not specified
    if "--browser" not in args:
        args.append("--browser")
        args.append("qt")
    sys.argv = args
    jdaviz.cli._main()
