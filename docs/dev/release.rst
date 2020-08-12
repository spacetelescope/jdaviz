****************************
Package Release Instructions
****************************

This document outlines the steps for releasing a versioned JDAViz package to
PyPI. Currently, these do not cover submitting package updates to the
``astroconda`` channel.

This process currently requires high-level access to the JDAViz repository,
as it relies on the ability to commit to master directly.

.. note::
    These instructions are adapted from the Astropy package template releasing
    instructions.

#. Ensure Travis and any other continuous integration is passing in the main
   repository.

#. Update the ``CHANGES.rst`` file to make sure that all the changes are listed,
   and update the release date, which should currently be set to
   ``unreleased``, to the current date in ``yyyy-mm-dd`` format.

#. Run ``git clean -fxd`` to remove any untracked files (WARNING: this will
   permanently remove any files that have not been previously committed, so
   make sure that you don't need to keep any of these files).

#. Generate the source distribution tar file by first making sure the
   `pep517 <https://pypi.org/project/pep517/>`_ package is installed and
   up-to-date::

        pip install pep517 --upgrade

   then creating the source distribution with::

        python -m pep517.build --source .

   Make sure that generated file is good to go by going inside ``dist``,
   expanding the tar file, going inside the expanded directory, and
   running the tests with::

        pip install -e .[test]
        pytest

   You may need to add the ``--remote-data`` flag or any other flags that you
   normally add when fully testing your package.

#. Go back to the root of the directory and remove the generated files with::

        git clean -fxd

#. Add the changes to ``CHANGES.rst``::

        git add CHANGES.rst

   and commit with message::

        git commit -m "Preparing release <version>"

#. Update the version number to the version you're about to release by creating
   a git tag, optionally signing with the ``-s`` option::

        git tag v<version>

#. Add a new section to ``CHANGES.rst`` for next version, with a single entry
   ``No changes yet``, e.g.::

       0.2 (unreleased)
       ----------------

       - No changes yet

#. Add the changes to ``CHANGES.rst``, where ``<next_version`` would be e.g.
   ``v0.2.dev``::

        git add CHANGES.rst

   and commit with message::

        git commit -m "Back to development: <next_version>"

#. Check out the release commit with ``git checkout v<version>``.
   Run ``git clean -fxd`` to remove any non-committed files.

#. (optional) Run the tests in an environment that mocks up a "typical user"
   scenario. This is not strictly necessary because you ran the tests above, but
   it can sometimes be useful to catch subtle bugs that might come from you
   using a customized developer environment.  For more on setting up virtual
   environments, see :ref:`virtual_envs`, but for the sake of example we will
   assume you're using `Anaconda <https://conda.io/docs/>`_. Do::

       conda create -n myaffilpkg_rel_test astropy <any more dependencies here>
       source activate myaffilpkg_rel_test
       python setup.py sdist
       cd dist
       pip install myaffilpkg-version.tar.gz
       python -c 'import myaffilpkg; myaffilpkg.test()'
       source deactivate
       cd <back to your source>

   You may want to repeat this for other combinations of dependencies if you think
   your users might have other relevant packages installed.  Assuming the tests
   all pass, you can proceed on.

#. If you did the previous step, do ``git clean -fxd`` again to remove anything
   you made there.  Run ``python setup.py build sdist --format=gztar`` to
   create the files for upload.  Then you can upload to PyPI via ``twine``::

        twine upload dist/*

   as described in `these <https://packaging.python.org/tutorials/distributing-packages/#uploading-your-project-to-pypi>`_
   instructions. Check that the entry on PyPI is correct, and that
   the tarfile is present.

#. Go back to the master branch and push your changes to github::

        git checkout master
        git push --tags origin master

   Once you have done this, if you use Read the Docs, trigger a ``latest`` build
   then go to the project settings, and under **Versions** you should see the
   tag you just pushed. Select the tag to activate it, and save.
