import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()

from pathlib import Path
import os

from qtpy import QtCore
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


_STARTUP_APP = None
_STARTUP_SPLASH = None


def _show_early_splash():
    global _STARTUP_APP, _STARTUP_SPLASH
    _STARTUP_APP = QApplication.instance() or QApplication([])
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        source_root = Path(sys._MEIPASS)
    else:
        source_root = Path(__file__).resolve().parent.parent
    pixmap = QPixmap(str(source_root / "jdaviz/data/icons/jdaviz_logo.png"))

    _STARTUP_SPLASH = QWidget()
    _STARTUP_SPLASH.setObjectName("jdavizStartupSplash")
    _STARTUP_SPLASH.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint |
                                   QtCore.Qt.FramelessWindowHint)
    _STARTUP_SPLASH.setWindowTitle("Setting up Jdaviz")

    layout = QVBoxLayout(_STARTUP_SPLASH)
    logo = QLabel()

    logo.setAlignment(QtCore.Qt.AlignCenter)
    logo.setPixmap(pixmap.scaled(320, 320, QtCore.Qt.KeepAspectRatio,
                                 QtCore.Qt.SmoothTransformation))
    _STARTUP_SPLASH.setStyleSheet("background-color: white")
    message = QLabel("Jdaviz is being set up...")
    font = message.font()
    font.setPointSize(20)
    message.setFont(font)
    message.setAlignment(QtCore.Qt.AlignCenter)

    message2 = QLabel("(JAY-dee-a-viz)")
    font = message2.font()
    font.setPointSize(14)
    message2.setFont(font)
    message2.setAlignment(QtCore.Qt.AlignCenter)

    layout.addWidget(message)
    layout.addWidget(message2)
    layout.addWidget(logo)
    _STARTUP_SPLASH.show()
    _STARTUP_APP.processEvents()


if __name__ == "__main__":

    _show_early_splash()

    # This avoids a backend error when the CLI imports pyplot. Importing the
    # backend here also makes PyInstaller include and register it.
    import matplotlib_inline
    import matplotlib_inline.backend_inline

    # PyInstaller recommends explicitly selecting the inline backend.
    import matplotlib
    matplotlib.use("module://matplotlib_inline.backend_inline")
    # Since matplotlib 3.9, this backend is aliased to "inline".
    matplotlib.use("inline")

    # Delay importing the CLI until after the splash is visible.
    import jdaviz.cli

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):

        # Define a safe user-writable path (e.g., user's home folder)
        user_home = Path.home()

        # create jdaviz_cache directory to save downloaded files
        jdaviz_cache = user_home / ".cache" / "jdaviz"
        jdaviz_cache.mkdir(exist_ok=True)
        os.environ['JDAVIZ_CACHE_DIR'] = str(jdaviz_cache)

        # create astropy_cache directory to save downloaded files
        # (backup in case it had been deleted or astropy not installed)
        astropy_cache = user_home / ".cache" / "astropy"
        astropy_cache.mkdir(exist_ok=True)
        os.environ['ASTROPY_CACHE_DIR'] = str(astropy_cache)

        # Change Python's working directory to a writable directory
        # This prevents Jdaviz from defaulting download_uri_to_path to the read-only _MEIPASS path
        os.chdir(user_home)

    args = sys.argv.copy()
    if not any(arg == "--browser" or arg.startswith("--browser=") for arg in args):
        args.append("--browser")
        args.append("qt")
    if not any(arg == "--layout" or arg.startswith("--layout=") for arg in args):
        args.append("--layout")
        args.append("flexible")
    sys.argv = args
    jdaviz.cli._main()
