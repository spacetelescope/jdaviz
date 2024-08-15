*********************
Developing on Windows
*********************

On some Windows OS versions, symbolic links cannot be created without
using a terminal started with administrative priviledge, which is not
recommended for security reasons. Therefore, ``setup.py`` instead
creates a copy of the data files instead of using symbolic links.
As a result, if you are changing the contents in ``share`` folder
under the source checkout's root directory, you will need to rebuild
the package even in editable install mode. Otherwise, this should not
affect your development experience.