.. _plugins-model-fitting:
.. rst-class:: section-icon-mdi-tune-variant

*************
Model Fitting
*************

.. plugin-availability::

Fit analytical models to spectroscopic data.

Overview
========

The Model Fitting plugin allows you to fit various analytical models to 1D spectra,
including Gaussian, Lorentzian, and polynomial models.

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"plugins","delay":1500},{"action":"open-panel","value":"Model Fitting","delay":1000}]

Details
=======

Astropy models can be fit to a spectrum via the Model Fitting plugin.
Model components are selected via the :guilabel:`Model Component` pulldown menu.
The :guilabel:`Add Component` button adds a Model Components block.

Model Parameters are automatically initialized with a guess.
These starting values can be edited by the user.
They may also be fixed by selecting the checkbox,
so that they are not fit or changed by the model fitting.

A mathematical expression must be entered into the
:guilabel:`Equation Editor` to specify the mathematical
combination of models.
This is also necessary even if there is only one model component.
The model components are specified by their labels and the equation
defaults to the sum of all created components, but can be modified to
exclude some of components without needing to delete them entirely
or to change to subtraction, for example. The user can also select
a different fitter to use for the model and adjust the corresponding
parameters that appear in the :guilabel:`Fitter Parameters`
accordion menu. The default fitter used is
`astropy.modeling.fitting.TRFLSQFitter <https://docs.astropy.org/en/latest/api/astropy.modeling.fitting.TRFLSQFitter.html#astropy.modeling.fitting.TRFLSQFitter>`_.
The fitter can be changed to any of the available Astropy fitters,
which can be found here `<https://docs.astropy.org/en/latest/modeling/reference_api.html#id6>`_.

After fitting, the expandable menu for each component model will update to
show the fitted value of each parameter rather than the initial value, and
will additionally show the standard deviation uncertainty of the fitted
parameter value if the parameter was not set to be fixed to the initial value
and if the spectrum uncertainty was loaded.

.. note::

   When a `1D Spline Models <https://docs.astropy.org/en/stable/modeling/spline_models.html>`_. model is selected, the plugin uses
   `astropy.modeling.spline.SplineSmoothingFitter <https://docs.astropy.org/en/stable/api/astropy.modeling.spline.SplineSmoothingFitter.html#astropy.modeling.spline.SplineSmoothingFitter>`_. to compute the fit.
   The initial value of the smoothing factor is automatically set to:
   (``len(data) * (standard_deviation(data))**2``).

   Refer to the section of the Scipy spline modeling documentation explaining
   the ``s`` parameter for advice on setting the smoothing factor/condition manually:
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.UnivariateSpline.html#scipy.interpolate.UnivariateSpline


From the API
------------

The model fitting plugin can be run from the API:

.. code-block:: python

    # Open model fitting plugin
    plugin_mf = jd.plugins['Model Fitting']
    plugin_mf.open_in_tray()
    # Input the appropriate dataset and subset
    plugin_mf.dataset = 'my spectrum'
    plugin_mf.spectral_subset = 'Subset 1'
    # Input the model components
    plugin_mf.create_model_component(model_component='Linear1D',
                                     model_component_label='L')
    plugin_mf.create_model_component(model_component='Gaussian1D',
                                     model_component_label='G')
    # Set the initial guess of some model parameters
    plugin_mf.set_model_component('G', 'stddev', 0.002)
    plugin_mf.set_model_component('G', 'mean', 2.2729)
    # Model equation gets populated automatically, but can be overwritten
    plugin_mf.equation = 'L+G'
    # Set fitter
    plugin_mf.fitter.selected = 'TRFLSQFitter'
    # Calculate fit
    plugin_mf.calculate_fit()

Customizing Fitter Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The fitter parameters (such as maximum iterations, filtering non-finite values, etc.)
can be accessed and modified programmatically using the
:meth:`~jdaviz.configs.default.plugins.model_fitting.model_fitting.ModelFitting.get_fitter_parameter`
and :meth:`~jdaviz.configs.default.plugins.model_fitting.model_fitting.ModelFitting.set_fitter_parameter`
methods. The available parameters depend on the selected fitter.

Common parameters include:

* ``maxiter``: Maximum number of iterations (available for most fitters)
* ``filter_non_finite``: Whether to filter non-finite values like NaNs (available for most fitters)
* ``calc_uncertainties``: Whether to calculate parameter uncertainties (available for most fitters)

.. code-block:: python

    # Get the current value of a fitter parameter
    max_iterations = plugin_mf.get_fitter_parameter('maxiter')
    print(f"Current max iterations: {max_iterations}")

    # Set a new value for a fitter parameter
    plugin_mf.set_fitter_parameter('maxiter', 200)
    plugin_mf.set_fitter_parameter('filter_non_finite', False)

    # Verify the change
    new_max_iterations = plugin_mf.get_fitter_parameter('maxiter')
    print(f"New max iterations: {new_max_iterations}")

Note that different fitters support different parameters. For example, ``LinearLSQFitter``
does not support the ``maxiter`` parameter. If you attempt to get a parameter that doesn't
exist for the selected fitter, the method will return ``None``.

Exporting Fit Results
^^^^^^^^^^^^^^^^^^^^^^

Parameter values for each fitting run are stored in the plugin table.
To export the table into the notebook, call
:meth:`~jdaviz.core.template_mixin.TableMixin.export_table`
(see :ref:`plugin-apis`).

.. seealso::

    :ref:`Export Models <specviz-export-model>`
        Documentation on exporting model fitting results.
