# The code in this file has been forked from the ipyfilechooser package which
# was originally released under the license in licenses/IPYFILECHOOSER_LICENSE.rst
#
# This was forked to enable us to use our own buttons for the dialog and use
# this just for the file browser view, but we could switch back to using the
# main released version of ipyfilechooser if it was possible to toggle this via
# public API. However for now this is sufficient until we know whether we are
# going to try and implement a native file picker instead.


import fnmatch
import os
import string
import sys

from traitlets import Unicode

from ipywidgets import Dropdown, Select, Layout, GridBox, VBox, ValueWidget

__all__ = ['FileChooser']


def get_subpaths(path):
    """Walk a path and return a list of subpaths."""
    if os.path.isfile(path):
        path = os.path.dirname(path)

    paths = [path]
    path, tail = os.path.split(path)

    while tail:
        paths.append(path)
        path, tail = os.path.split(path)

    try:
        # Add Windows drive letters, but remove the current drive
        drives = get_drive_letters()
        drives.remove(paths[-1])
        paths.extend(drives)
    except ValueError:
        pass
    return paths


def has_parent(path):
    """Check if a path has a parent folder."""
    return os.path.basename(path) != ''


def match_item(item, filter_pattern):
    """Check if a string matches one or more fnmatch patterns."""
    if isinstance(filter_pattern, str):
        filter_pattern = [filter_pattern]

    idx = 0
    found = False

    while idx < len(filter_pattern) and not found:
        found |= fnmatch.fnmatch(item, filter_pattern[idx])
        idx += 1

    return found


def get_dir_contents(
        path,
        show_hidden=False,
        prepend_icons=False,
        filter_pattern=None):
    """Get directory contents."""
    files = list()
    dirs = list()

    if os.path.isdir(path):
        for item in os.listdir(path):
            append = True
            if item.startswith('.') and not show_hidden:
                append = False
            full_item = os.path.join(path, item)
            if append and os.path.isdir(full_item):
                dirs.append(item)
            elif append:
                if filter_pattern:
                    if match_item(item, filter_pattern):
                        files.append(item)
                else:
                    files.append(item)
        if has_parent(path):
            dirs.insert(0, '..')
    if prepend_icons:
        return prepend_dir_icons(sorted(dirs)) + sorted(files)
    else:
        return add_trailing_slash(sorted(dirs)) + sorted(files)


def add_trailing_slash(dir_list):
    return [dirname + '/' for dirname in dir_list]


def prepend_dir_icons(dir_list):
    """Prepend unicode folder icon to directory names."""
    return ['\U0001F4C1 ' + dirname for dirname in dir_list]


def get_drive_letters():
    """Get drive letters."""
    if sys.platform == 'win32':
        # Windows has drive letters
        return [
            '%s:\\' % d for d in string.ascii_uppercase
            if os.path.exists('%s:' % d)
        ]
    else:
        # Unix does not have drive letters
        return []


class FileChooser(VBox, ValueWidget):
    """FileChooser class."""

    _LBL_TEMPLATE = '<span style="margin-left:10px; color:{1};">{0}</span>'
    _LBL_NOFILE = 'No file selected'

    file_path = Unicode(allow_none=True)

    def __init__(
            self,
            path=os.getcwd(),
            filename='',
            show_hidden=False,
            use_dir_icons=False,
            filter_pattern=None,
            **kwargs):
        """Initialize FileChooser object."""
        self._default_path = path.rstrip(os.path.sep)
        self._default_filename = filename
        self._show_hidden = show_hidden
        self._use_dir_icons = use_dir_icons
        self._filter_pattern = filter_pattern

        # Widgets

        self._pathlist = Dropdown(
            description="",
            layout=Layout(
                width='auto',
                grid_area='pathlist'
            )
        )

        self._dircontent = Select(
            rows=8,
            layout=Layout(
                width='auto',
                grid_area='dircontent'
            )
        )

        # Widget observe handlers
        self._pathlist.observe(
            self._on_pathlist_select,
            names='value'
        )
        self._dircontent.observe(
            self._on_dircontent_select,
            names='value'
        )

        # Layout
        self._gb = GridBox(
            children=[
                self._pathlist,
                self._dircontent
            ],
            layout=Layout(
                width='500px',
                grid_gap='0px 0px',
                grid_template_rows='auto auto',
                grid_template_columns='60% 40%',
                grid_template_areas='''
                    'pathlist pathlist'
                    'dircontent dircontent'
                    '''
            )
        )

        # Call setter to set initial form values
        self._set_form_values(
            self._default_path,
            self._default_filename
        )

        self._initialize_form_values()

        # Call VBox super class __init__
        super().__init__(
            children=[self._gb],
            layout=Layout(width='auto'),
            **kwargs
        )

    def _set_form_values(self, path, filename):
        """Set the form values."""
        # Disable triggers to prevent selecting an entry in the Select
        # box from automatically triggering a new event.
        self._pathlist.unobserve(
            self._on_pathlist_select,
            names='value'
        )
        self._dircontent.unobserve(
            self._on_dircontent_select,
            names='value'
        )

        # Set form values
        self._pathlist.options = get_subpaths(path)
        self._pathlist.value = path

        # file/folder real names
        dircontent_real_names = get_dir_contents(
            path,
            show_hidden=self._show_hidden,
            prepend_icons=False,
            filter_pattern=self._filter_pattern
        )

        # file/folder display names
        dircontent_display_names = get_dir_contents(
            path,
            show_hidden=self._show_hidden,
            prepend_icons=self._use_dir_icons,
            filter_pattern=self._filter_pattern
        )

        # Dict to map real names to display names
        self._map_name_to_disp = {
            real_name: disp_name
            for real_name, disp_name in zip(
                dircontent_real_names,
                dircontent_display_names
            )
        }

        # Dict to map display names to real names
        self._map_disp_to_name = dict(
            reversed(item) for item in self._map_name_to_disp.items()
        )

        # Set _dircontent form value to display names
        self._dircontent.options = dircontent_display_names

        # If the value in the filename Text box equals a value in the
        # Select box and the entry is a file then select the entry.
        if ((filename in dircontent_real_names) and
                os.path.isfile(os.path.join(path, filename))):
            self._dircontent.value = self._map_name_to_disp[filename]
        else:
            self._dircontent.value = None

        # Re-enable triggers again
        self._pathlist.observe(
            self._on_pathlist_select,
            names='value'
        )
        self._dircontent.observe(
            self._on_dircontent_select,
            names='value'
        )

        self._update_file_path()

    def _on_pathlist_select(self, change):
        """Handle selecting a path entry."""
        self._set_form_values(
            change['new'],
            self._selected_filename
        )

    def _on_dircontent_select(self, change):
        """Handle selecting a folder entry."""
        new_path = os.path.realpath(
            os.path.join(
                self._selected_path,
                self._map_disp_to_name[change['new']]
            )
        )

        # Check if folder or file
        if os.path.isdir(new_path):
            path = new_path
            filename = None
        elif os.path.isfile(new_path):
            path = self._selected_path
            filename = self._map_disp_to_name[change['new']]

        self._set_form_values(
            path,
            filename
        )

    def _initialize_form_values(self):
        """Show the dialog."""

        # Show the form with the correct path and filename
        if ((self._selected_path is not None) and
                (self._selected_filename is not None)):
            path = self._selected_path
            filename = self._selected_filename
        else:
            path = self._default_path
            filename = self._default_filename

        self._set_form_values(path, filename)

    @property
    def _selected_path(self):
        return self._pathlist.value

    @property
    def _selected_filename(self):
        if self._dircontent.value is None:
            return None
        else:
            return self._map_disp_to_name[self._dircontent.value]

    def _update_file_path(self):
        if self._selected_filename is not None and self._selected_path is not None:
            self.file_path = os.path.join(self._selected_path,
                                          self._selected_filename)

    def refresh(self):
        """Re-render the form."""
        self._set_form_values(
            self._selected_path,
            self._selected_filename
        )

    @property
    def show_hidden(self):
        """Get _show_hidden value."""
        return self._show_hidden

    @show_hidden.setter
    def show_hidden(self, hidden):
        """Set _show_hidden value."""
        self._show_hidden = hidden
        self.refresh()

    @property
    def use_dir_icons(self):
        """Get _use_dir_icons value."""
        return self._use_dir_icons

    @use_dir_icons.setter
    def use_dir_icons(self, dir_icons):
        """Set _use_dir_icons value."""
        self._use_dir_icons = dir_icons
        self.refresh()

    @property
    def rows(self):
        """Get current number of rows."""
        return self._dircontent.rows

    @rows.setter
    def rows(self, rows):
        """Set number of rows."""
        self._dircontent.rows = rows

    @property
    def default_path(self):
        """Get the default_path value."""
        return self._default_path

    @default_path.setter
    def default_path(self, path):
        """Set the default_path."""
        self._default_path = path.rstrip(os.path.sep)
        self._set_form_values(
            self._default_path,
            self._selected_filename
        )

    @property
    def default_filename(self):
        """Get the default_filename value."""
        return self._default_filename

    @default_filename.setter
    def default_filename(self, filename):
        """Set the default_filename."""
        self._default_filename = filename
        self._set_form_values(
            self._selected_path,
            self._default_filename
        )

    @property
    def filter_pattern(self):
        """Get file name filter pattern."""
        return self._filter_pattern

    @filter_pattern.setter
    def filter_pattern(self, filter_pattern):
        """Set file name filter pattern."""
        self._filter_pattern = filter_pattern
        self.refresh()

    @property
    def selected(self):
        """Get selected value."""
        try:
            return os.path.join(
                self._selected_path,
                self._selected_filename
            )
        except TypeError:
            return None
