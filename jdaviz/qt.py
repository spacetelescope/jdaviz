# this module is based on solara/server/qt.py
import sys
from typing import List
import webbrowser
try:
    from qtpy.QtWidgets import QApplication, QMessageBox, QAction, QMenuBar, QVBoxLayout, QWidget
    from qtpy.QtWebEngineWidgets import QWebEngineView
    from qtpy.QtWebChannel import QWebChannel
    from qtpy import QtCore, QtGui
except ModuleNotFoundError as e:
    raise ModuleNotFoundError("""Qt browser requires Qt dependencies, run:
$ pip install jdaviz[qt]
to install.""") from e
import signal
from pathlib import Path
from importlib.metadata import version
import os
import shutil
import time
import re
import requests

HERE = Path(__file__).parent


# setUrlRequestInterceptor, navigationRequested and acceptNavigationRequest
# all trigger the websocket to disconnect, so we need to block cross origin
# requests on the frontend/browser side by intercepting clicks on links

cross_origin_block_js = """
var script = document.createElement('script');
script.src = 'qrc:///qtwebchannel/qwebchannel.js';
document.head.appendChild(script);
script.onload = function() {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        let py_callback = channel.objects.py_callback;

        document.addEventListener('click', function(event) {
            let target = event.target;
            while (target && target.tagName !== 'A') {
                target = target.parentNode;
            }

            if (target && target.tagName === 'A') {
                const linkOrigin = new URL(target.href).origin;
                const currentOrigin = window.location.origin;

                if (linkOrigin !== currentOrigin) {
                    event.preventDefault();
                    console.log("Blocked cross-origin navigation to:", target.href);
                    py_callback.open_link(target.href);  // Call Python method
                }
            }
        }, true);
    });
};
"""


class PyCallback(QtCore.QObject):
    @QtCore.Slot(str)
    def open_link(self, url):
        webbrowser.open(url)


class QWebEngineViewWithPopup(QWebEngineView):
    # keep a strong reference to all windows
    windows: List = []

    def __init__(self):
        super().__init__()
        self.page().newWindowRequested.connect(self.handle_new_window_request)

        # Set up WebChannel and py_callback object
        self.py_callback = PyCallback()
        self.channel = QWebChannel()
        self.channel.registerObject("py_callback", self.py_callback)
        self.page().setWebChannel(self.channel)

        self.loadFinished.connect(self._inject_javascript)

    def _inject_javascript(self, ok):
        self.page().runJavaScript(cross_origin_block_js)

    def handle_new_window_request(self, info):
        webview = QWebEngineViewWithPopup()
        geometry = info.requestedGeometry()
        width = geometry.width()
        parent_size = self.size()
        if width == 0:
            width = parent_size.width()
        height = geometry.height()
        if height == 0:
            height = parent_size.height()
        print("new window", info.requestedUrl(), width, height)
        webview.resize(width, height)
        webview.setUrl(info.requestedUrl())
        webview.show()
        QWebEngineViewWithPopup.windows.append(webview)
        return webview


def clear_cache(clear_all=False):
    cache_dir = os.environ['JDAVIZ_CACHE_DIR']
    # Clear after 4 weeks
    seconds_in_two_weeks = 28 * 24 * 60 * 60
    cutoff_time = time.time() - seconds_in_two_weeks
    if os.path.exists(cache_dir):
        try:
            # clear all if button clicked
            if clear_all:
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir, exist_ok=True)
                print("Cache cleared successfully.")
            else:
                # go through all files and folders (inc. subfolders).
                # files will be deleted first then folder checked to see if it is empty.
                for fil in list(Path(cache_dir).rglob("*"))[::-1]:
                    # delete files > 4 weeks AND hidden files
                    if fil.is_file():
                        file_modified_time = os.path.getmtime(fil)
                        if file_modified_time < cutoff_time:
                            os.remove(fil)
                        elif str(fil.name).startswith('.'):
                            os.remove(fil)
                    # delete empty folders (inc. subfolders)
                    elif fil.is_dir() and not any(fil.iterdir()):
                        shutil.rmtree(fil)
                print("Files/folders cleared successfully.")

        except Exception as e:
            print(f"Failed to delete cache folders: {e}")


def run_qt(url, app_name="Jdaviz"):
    app = QApplication([])
    window_container = QWidget()
    web = QWebEngineViewWithPopup()
    web.setUrl(QtCore.QUrl(url))

    layout = QVBoxLayout(window_container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    ############
    # Menu
    ############

    menu_bar = QMenuBar(window_container)

    # Create Menu Bar menus
    file_menu = menu_bar.addMenu("&File")
    cache_menu = menu_bar.addMenu("&Cache")
    window_menu = menu_bar.addMenu("&Window")
    help_menu = menu_bar.addMenu("&Help")

    # About menu
    # ----------
    about_action = QAction(f"&About {app_name}", window_container)
    about_action.setMenuRole(QAction.MenuRole.AboutRole)
    file_menu.addAction(about_action)

    def show_about_dialog():
        about_text = (
            f"<h3>{app_name}</h3>"
            f"<p>Version: {version('jdaviz')}</p>"
            "<hr>"
            "<p><small>© 2026 JDADF Developers</small></p>")
        # Spawns a modal, native popup window
        QMessageBox.about(
            window_container,
            f"About {app_name}",
            about_text)
    # Connect the button click to our popup trigger function
    about_action.triggered.connect(show_about_dialog)

    # Update dropdown
    # ----------
    update_action = QAction("&Check for Update...", window_container)
    update_action.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)

    def _parse_version_nums(s: str):
        # Extract numeric groups for a simple version comparison, e.g. 'v1.2.3' -> (1,2,3)
        # this covers both releases and dev versions for testing
        parts = re.findall(r"\d+", str(s).split('+g')[0])
        return tuple(int(p) for p in parts) if parts else ()

    def check_for_updates(show_up_to_date_message=True):
        try:
            api_url = "https://api.github.com/repos/spacetelescope/jdaviz/releases/latest"
            response = requests.get(api_url, timeout=10,
                                    headers={"User-Agent": "jdaviz-check-updates"})
            response.raise_for_status()
            data = response.json()

            latest_tag = data.get("tag_name") or data.get("name")
            release_html = data.get("html_url")
            installed = version("jdaviz")

            msg_utd = QMessageBox(window_container)
            icon_path = str(HERE / "data/icons/jdaviz_logo_transparent.png")
            pixmap = QtGui.QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(
                100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation)
            msg_utd.setIconPixmap(scaled_pixmap)

            if not latest_tag:
                msg_utd.setText("Error")
                msg_utd.setInformativeText("Could not determine the latest release for Jdaviz.")
                process_btn = msg_utd.addButton("File GitHub Issue",
                                                QMessageBox.ButtonRole.AcceptRole)
                msg_utd.addButton(QMessageBox.StandardButton.Cancel)

                ret = msg_utd.exec()
                if msg_utd.clickedButton() == process_btn:
                    QtGui.QDesktopServices.openUrl(
                        QtCore.QUrl('https://github.com/spacetelescope/jdaviz/issues')
                        )
                return

            if _parse_version_nums(latest_tag) > _parse_version_nums(installed):
                msg_utd.setText("Update Available")
                msg = (f"There is a new version of Jdaviz available to download: {latest_tag}\n\n"
                       "Press OK to open the download page in your browser.")
                msg_utd.setInformativeText(msg)
                msg_utd.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                ret = msg_utd.exec()
                # Convert the menu item into a direct link to the release page
                if release_html:
                    update_action.setText("Update Available")
                    update_action.setToolTip(release_html)

                    if ret == QMessageBox.Ok:
                        QtGui.QDesktopServices.openUrl(QtCore.QUrl(release_html))

            elif show_up_to_date_message:
                msg_utd.setText("You're up to date!")
                msg = f"Jdaviz {installed} is currently the newest version available."
                msg_utd.setInformativeText(msg)
                msg_utd.setStandardButtons(QMessageBox.Ok)
                ret = msg_utd.exec()

        except requests.exceptions.HTTPError:
            QMessageBox.warning(window_container, "Check for updates...",
                                "Failed to check updates: GitHub request failed")

        except requests.exceptions.RequestException as e:
            QMessageBox.warning(window_container, "Check for updates...",
                                f"Failed to check updates: {e}")

        except Exception as e:
            QMessageBox.warning(window_container, "Check for updates...",
                                f"Failed to check updates: {e}")

    update_action.triggered.connect(lambda: check_for_updates(show_up_to_date_message=True))
    ## Uncomment if we want to trigger an update message when the app opens if
    ## an update is available.  Does NOT have a way to stop popups reopening the app
    ## so it could get very annoying if you don't want an update. 
    # QtCore.QTimer.singleShot(0, lambda: check_for_updates(show_up_to_date_message=False))
    file_menu.addAction(update_action)

    # Window menu dropdowns
    # ----------

    # Minimize
    minimize_action = QAction("Minimize", window_container)
    minimize_action.setShortcut("Ctrl+M")
    minimize_action.triggered.connect(window_container.showMinimized)
    window_menu.addAction(minimize_action)

    # Toggle zoom
    zoom_action = QAction("Zoom", window_container)

    def toggle_zoom():
        if window_container.isMaximized():
            window_container.showNormal()
        else:
            window_container.showMaximized()
    zoom_action.triggered.connect(toggle_zoom)
    window_menu.addAction(zoom_action)

    # Fill Screen
    fill_action = QAction("Fill", window_container)
    fill_action.setShortcut("Ctrl+Meta+F")

    def fill_screen():
        # Grabs monitor dimensions excluding the global top menu bar and system dock
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_container.setGeometry(screen_geometry)
    fill_action.triggered.connect(fill_screen)
    window_menu.addAction(fill_action)

    # Center Window
    center_action = QAction("Center", window_container)
    center_action.setShortcut("Ctrl+Meta+C")

    def center_window():
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_geometry = window_container.frameGeometry()
        # Find center coordinates matching the target frame size
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        window_container.move(window_geometry.topLeft())
    center_action.triggered.connect(center_window)
    window_menu.addAction(center_action)

    # Full Screen
    fullscreen_action = QAction("Enter Full Screen", window_container)
    fullscreen_action.setShortcut("Ctrl+F")

    def toggle_fullscreen():
        if window_container.isFullScreen():
            window_container.showNormal()
        else:
            window_container.showFullScreen()
    fullscreen_action.triggered.connect(toggle_fullscreen)
    window_menu.addAction(fullscreen_action)

    window_menu.addSeparator()

    # Zoom in/out
    current_zoom = [1.0]

    # Zoom In Control
    zoom_in_action = QAction("Zoom In", window_container)
    zoom_in_action.setShortcut("Ctrl++")  # Maps to Cmd++ on macOS

    def zoom_in():
        if current_zoom[0] < 3.0:  # Enforce safe ceiling multiplier limit
            current_zoom[0] += 0.1
            web.setZoomFactor(current_zoom[0])
    zoom_in_action.triggered.connect(zoom_in)
    window_menu.addAction(zoom_in_action)

    # Zoom Out Control
    zoom_out_action = QAction("Zoom Out", window_container)
    zoom_out_action.setShortcut("Ctrl+-")  # Maps to Cmd+- on macOS

    def zoom_out():
        if current_zoom[0] > 0.5:  # Enforce safe basement floor multiplier limit
            current_zoom[0] -= 0.1
            web.setZoomFactor(current_zoom[0])
    zoom_out_action.triggered.connect(zoom_out)
    window_menu.addAction(zoom_out_action)

    # Reset Zoom Target
    zoom_reset_action = QAction("Reset Zoom", window_container)
    zoom_reset_action.setShortcut("Ctrl+0")

    def zoom_reset():
        current_zoom[0] = 1.0
        web.setZoomFactor(1.0)
    zoom_reset_action.triggered.connect(zoom_reset)
    window_menu.addAction(zoom_reset_action)

    # Help Menu
    # ----------

    # ReadTheDocs
    rtd_action = QAction("Jdaviz Documentation", window_container)
    rtd_action.triggered.connect(
        lambda: QtGui.QDesktopServices.openUrl(
            QtCore.QUrl("https://jdaviz.readthedocs.io/en/latest/index.html")
        )
    )
    help_menu.addAction(rtd_action)

    # Zenodo
    zenodo_action = QAction("Jdaviz Zenodo", window_container)
    zenodo_action.triggered.connect(
        lambda: QtGui.QDesktopServices.openUrl(
            QtCore.QUrl("https://doi.org/10.5281/zenodo.5513927")
        )
    )
    help_menu.addAction(zenodo_action)

    # Github
    git_action = QAction("Jdaviz GitHub", window_container)
    git_action.triggered.connect(
        lambda: QtGui.QDesktopServices.openUrl(
            QtCore.QUrl("https://github.com/spacetelescope/jdaviz")
        )
    )
    help_menu.addAction(git_action)

    # JWST Help Desk
    jwst_action = QAction("JWST Help Desk", window_container)
    jwst_action.triggered.connect(
        lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://stsci.service-now.com/jwst"))
    )
    help_menu.addAction(jwst_action)

    # Cache Menu
    # ----------
    clear_action = cache_menu.addAction("Empty Jdaviz Cache")
    clear_action.triggered.connect(lambda: clear_cache(True))

    ############
    ############

    layout.addWidget(menu_bar)
    layout.addWidget(web)

    window_container.resize(1024, 1024)
    window_container.show()

    app.setApplicationDisplayName(app_name)
    app.setApplicationName(app_name)
    window_container.setWindowTitle(app_name)
    if sys.platform.startswith("darwin"):
        # Set app name, if PyObjC is installed
        # Python 2 has PyObjC preinstalled
        # Python 3: pip3 install pyobjc-framework-Cocoa
        try:
            from Foundation import NSBundle

            bundle = NSBundle.mainBundle()
            if bundle:
                app_info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if app_info is not None:
                    app_info["CFBundleName"] = app_name
                    app_info["CFBundleDisplayName"] = app_name
        except ModuleNotFoundError:
            pass
    else:
        # on macs, the .icns set in jdaviz.spec handles the window icon, while
        # qt.setWindowIcon handles it in windows/linux
        app.setWindowIcon(QtGui.QIcon(str(HERE / "data/icons/jdaviz_logo.png")))

    # empty folders in cache on close
    app.aboutToQuit.connect(clear_cache)

    # without this, ctrl-c does not work in the terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.exec_()
