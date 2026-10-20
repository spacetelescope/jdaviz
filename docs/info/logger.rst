.. _info-logger:
.. rst-class:: section-icon-mdi-information-outline

******
Logger
******

View system messages, warnings, and errors from Jdaviz operations. These messages can appear
as popups on the top right of ``jdaviz`` as temporary messages, and/or will appear in the Logger plugin. 
These give information on how the underlying data changes (data being logged, changing alignment and linking).  

popup verbosity
===============

Minimum level to show a popup message.  The default is ``warning``. 


history verbosity
=================

Minimum level to show a in the :guilabel:`Logger` plugin.  The default is ``info``. 


Verbosity Levels
================

+-----------+-------------------------------------------------------------------------------+
| Verbosity | Explanation                                                                   |
+===========+===============================================================================+
| Debug     | diagnostic information, for development and troubleshooting                   | 
+-----------+-------------------------------------------------------------------------------+
| Info      | confirmation messages that the task ran as expected                           |
+-----------+-------------------------------------------------------------------------------+
| Warning   | indication of potential issue, but does not stop ``jdaviz``                   |
+-----------+-------------------------------------------------------------------------------+
| Error     | failure due to issue with specific task.  Might require restarting ``jdaviz`` |
+-----------+-------------------------------------------------------------------------------+



UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"info"}]
   :steps-json: [{"action": "show-sidebar", "value": "info", "delay": 1500, "caption": "Open the info sidebar"}, {"action": "select-tab", "value": "Logger", "delay": 1500, "caption": "Select the Logger tab"}]


API Access
==========
.. code-block:: python

   plg = jdaviz.plugins['Logger']
   logger = plg.history

The ``logger`` will return a list of dictionaries, where each dictionary gives:

- the time of the logged message
- the logged message
- the type of message (info, warning, etc)
- the traceback (if there is one)