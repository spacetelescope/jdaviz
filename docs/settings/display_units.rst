.. _settings-display_units:
.. rst-class:: section-icon-mdi-cog

*************
Display Units
*************

This plugin gives access to changing global spectral axis and flux units. Changing the units in the plugin
will change them across all viewers and all layers where applicable.  

.. note::
   This does not change the underlying units of the datasets loaded into ``jdaviz``.  If you export the dataset
   into a notebook from ``jdaviz``, it will be in the original units.  This only changes the units displayed
   in the viewers.  

.. _settings-display_units-units:

Units
=====
Spectral Unit (spectrum viewers)
--------------------------------
Change the global display unit for spectral axes for a spectrum viewer. 
See :py:class:`astropy.units` for more details.

+--------------+---------------+------------------------+
| Jdaviz Name  | Full Name     | Unit definition        | 
+==============+===============+========================+
| Angstrom     | angstrom      | 1e-10 m                |
+--------------+---------------+------------------------+
| nm           | nanometer     | 1e-9 m                 |
+--------------+---------------+------------------------+
| um, micron   | micrometer    | 1e-6 m                 |
+--------------+---------------+------------------------+
| cm           | centimeter    | 1e-2 m                 |
+--------------+---------------+------------------------+
| m            | meter         | 1 m                    |
+--------------+---------------+------------------------+
| Hz           | Hertz         | 1 / s                  |
+--------------+---------------+------------------------+
| Ci           | Curie         | 3.7e10 / s             |
+--------------+---------------+------------------------+
| eV           | electronvolt  | 1.60218e-19 m2 kg / s2 |
+--------------+---------------+------------------------+
| Ry           | Rydberg       | 2.17987e-18 m2 kg/s2   |
+--------------+---------------+------------------------+
| erg          | erg           | 1e-7 m2 kg / s2        |
+--------------+---------------+------------------------+
| J            | Joule         | 1 m2 kg / s2           |
+--------------+---------------+------------------------+
| foe          | Bethe         | 1e+44 m2 kg / s2       |
+--------------+---------------+------------------------+
| k            | Kayser        | 100 / m                |
+--------------+---------------+------------------------+


Flux Unit
---------

Change the global display unit for flux axes. This changes the flux unit for *all* viewers.  
 For example, if you have a 1D spectrum viewer and an Image viewer, the flux unit will change for both viewers.

+-----------------------+-------------------------------+
| Jdaviz Name           | Full Name/meaning             | 
+=======================+===============================+
| Jy                    | Jansky                        | 
+-----------------------+-------------------------------+
| MJy                   | Mega Jansky                   | 
+-----------------------+-------------------------------+
| W / (Hz m2)           | flux density                  | 
+-----------------------+-------------------------------+
| eV / (Hz s m2)        | flux density                  |         
+-----------------------+-------------------------------+
| erg / (Angstrom s cm2)| flux density                  |                
+-----------------------+-------------------------------+
| erg / (Hz s cm2)      | flux density                  | 
+-----------------------+-------------------------------+
| mJy                   | milli Jansky                  | 
+-----------------------+-------------------------------+
| ph / (Angstrom s cm2) | photon flux density           |
+-----------------------+-------------------------------+
| ph / (Hz s cm2)       | photon flux density           | 
+-----------------------+-------------------------------+
| uJy                   | micro Jansky                  | 
+-----------------------+-------------------------------+


Angle Unit
----------

Change the display unit for solid angle.  

+-----------------------+---------------+
| Jdaviz Name           | Full Name     | 
+=======================+===============+
| sr                    | steradian     | 
+-----------------------+---------------+
| pix^2                 | square pixel  | 
+-----------------------+---------------+

Surface Brightness Unit (spectrum viewers)
------------------------------------------

If the physical type of the y-axis for a spectrum viewer is set to ``Surface Brightness``, the surface brightness
unit will display the selected flux unit and angle unit. 

Spectral Y-type Type (spectrum viewers)
---------------------------------------
Change the y-axis physical type for the spectrum viewer. Choices are ``Surface Brightness`` and ``Flux``. 

.. _settings-display_units-api:

API Access 
==========

.. code-block:: python

   plg = jd.plugins['Unit Conversion']
   plg.spectral_axis = 'um'
   plg.flux_unit = 'MJy'
   plg.angle_unit = 'str'
   plg.spectral_y_type = 'Flux'

.. _settings-display_units-ui:

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"show-sidebar","value":"settings"},{"action":"select-tab","value":"Units"},{"action":"disable-toolbar-except","value":"settings"}]

