import os.path

# settings for dmgbuild

# Define information

# application location
application = defines.get("app", "./standalone/dist/Jdaviz.app")  # noqa: F821
appname = os.path.basename(application)

# Volume format (see hdiutil create -help)
format = defines.get("format", "UDZO")

# Volume size
size = defines.get("size", None)  # noqa: F821

# Files to include
files = [application]

# Symlinks to create
symlinks = {"Applications": "/Applications"}

# Files to hide
# hide = [ 'Secret.data' ]

# Volume icon
icon = './assets/app.icns'

# Where to put the icons
icon_locations = {appname: (140, 120), "Applications": (500, 120)}

# Window configuration

background = "./standalone/background.tiff"

show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
sidebar_width = 180

# Window position in ((x, y), (w, h)) format
window_rect = ((100, 100), (640, 280))

# Select the default view; must be one of
default_view = "icon-view"

# General view configuration
show_icon_preview = False

# Set these to True to force inclusion of icon/list view settings (otherwise
# we only include settings for the default view)
include_icon_view_settings = "auto"
include_list_view_settings = "auto"

# Icon view configuration
arrange_by = None
grid_offset = (0, 0)
grid_spacing = 100
scroll_position = (0, 0)
label_pos = "bottom"
text_size = 16
icon_size = 128

# List view configuration
list_icon_size = 16
list_text_size = 12
list_scroll_position = (0, 0)
list_sort_by = "name"
list_use_relative_dates = True
list_calculate_all_sizes = (False,)
list_columns = ("name", "date-modified", "size", "kind", "date-added")
list_column_widths = {
    "name": 300,
    "date-modified": 181,
    "date-created": 181,
    "date-added": 181,
    "date-last-opened": 181,
    "size": 97,
    "kind": 115,
    "label": 100,
    "version": 75,
    "comments": 300,
}
list_column_sort_directions = {
    "name": "ascending",
    "date-modified": "descending",
    "date-created": "descending",
    "date-added": "descending",
    "date-last-opened": "descending",
    "size": "descending",
    "kind": "ascending",
    "label": "ascending",
    "version": "ascending",
    "comments": "ascending",
}
