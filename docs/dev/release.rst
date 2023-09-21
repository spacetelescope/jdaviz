****************************
Package Release Instructions
****************************

This document outlines the steps for releasing a versioned Jdaviz package to
PyPI. Currently, these do not cover submitting package updates to other
distribution outlets, such as ``astroconda`` or ``conda-forge``.

This process currently requires you (the release manager) to have sufficient GitHub
permissions to tag, push, and create a GitHub release on Jdaviz repository. These
instructions assume that the ``origin`` remote points to your personal fork,
and that ``upstream`` points to the
`STScI repository <https://github.com/spacetelescope/jdaviz.git>`_.

It is recommended that you lock the ``main`` branch after the "feature freeze"
for the release and only unlock it when release is out on PyPI. Any urgent
pull request that needs to go in after the freeze needs your blessing.
A lock can be as simple as bumping the "reviews required" protection rule
for the ``main`` branch to a very high number; Any rule that will prevent
co-maintainers from merging pull requests without your blessing would do.

If you deem it necessary, you may choose to release a Release Candidate (RC)
first before the actual release. In that case, instead of "vX.Y.Z", it would
be "vX.YrcN" (also see `PEP 440 <https://www.python.org/dev/peps/pep-0440/>`_).

.. note::
    These instructions are adapted from the Astropy package template releasing
    instructions. Replace "vX.Y.Z" with the actual version tag of the release you
    are about to make.

Choose your adventure:

* :ref:`release-feature`
* :ref:`release-bugfix`
* :ref:`release-old`


.. _release-feature:

Releasing a minor or major version
==================================

The automated release infrastructure has proven to be reliable for a good number
of releases now, so we've been using this faster version as the default release
procedure. The longer procedure we previously used is still available in the
:ref:`release-old` section.

You can do a release from your fork directly without a clean code check-out.

#. Ensure `CI on Actions for main <https://github.com/spacetelescope/jdaviz/actions/workflows/ci_workflows.yml?query=branch%3Amain>`_
   and `RTD build for latest <https://readthedocs.org/projects/jdaviz/builds/>`_
   are passing.

#. Lock down the ``main`` branch of the repository by setting the
   `branch protection <https://github.com/spacetelescope/jdaviz/settings/branches>`_
   rule for ``main`` to some high number required to merge, so that more PRs don't
   get merged while you're releasing.

#. Create a new local branch and make sure you have updated tags too. Note
   that the "x" here should actually be the letter "x", whereas the upper case "X"
   and "Y" should be replace by your major and minor version numbers:

.. code-block:: bash

     git fetch upstream main
     git fetch upstream --tags
     git checkout upstream/main -b vX.Y.x

#. Update the ``CHANGES.rst`` file to make sure that all the user-facing changes are listed,
   and update the release date from ``unreleased`` to current date in the ``yyyy-mm-dd`` format.
   Remove any empty subsections.

   NOTE: You may encounter the case where there is a populated bugfix section
   below the current feature release section, but this bugfix release is being skipped
   in favor of a major release. If this happens, you will need to move those entries
   to the appropriate location(s) in the newest 'released' section, and remove that
   bugfix section since that release is being skipped.

#. Update the ``CITATION.cff`` file's ``date-released`` and ``version`` fields.
   If there are new contributors to the project, add them in the ``authors``
   section.

#. Do not forget to commit your changes from the last two steps:

.. code-block:: bash

     git add CHANGES.rst
     git add CITATION.cff
     git commit -m "Preparing release vX.Y.0"

#. Push the ``vX.Y.x`` branch to upstream.
   Make sure the CI passes. If any of the CI fails, especially the job that
   says "Release", abandon this way. Stop here; do not continue! Otherwise,
   go to the next step.

#. Go to `Releases on GitHub <https://github.com/spacetelescope/jdaviz/releases>`_
   and `create a new GitHub release <https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository>`_
   targeting the new branch you created (not ``main``!), and give it a new ``vX.Y.Z``
   tag (do not choose any existing tags). Copy the relevant section from CHANGES.rst
   into the release notes section and clean up any formatting problems.

#. The most important step: Click the ``Publish Release`` button!

#. Check `Release on Actions <https://github.com/spacetelescope/jdaviz/actions/workflows/publish.yml>`_
   to make sure that the new GitHub release triggered PyPI upload successfully.
   Also check that `files on PyPI <https://pypi.org/project/jdaviz/#files>`_ contain
   both the source tarball and the wheel for that release.

#. Check `RTD builds <https://readthedocs.org/projects/jdaviz/builds/>`_ to make sure
   that documentation built successfully for both ``latest`` and the new ``vX.Y.Z`` tag.

#. Check `Zenodo page for Jdaviz <https://doi.org/10.5281/zenodo.5513927>`_.
   It should have picked up the GitHub Release automatically.

#. The release is basically done, but now you have to set it up for the
   *next* release cycle. In your release branch, add a new section above the
   current release section for the next bugfix release and push it to the
   new release branch::

     A.B.1 (unreleased)
     ==================

     Bug Fixes
     ---------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

#. Checkout ``main`` and update ``CHANGES.rst`` and ``CITATIONS.cff`` directly
   in that branch using your admin power. If you do not have sufficient access to
   do that, you will have to update it via a pull request from your fork. Make
   sure the section for the version just released matches the finalized change
   log from the release branch you created, and add a new section to the top of
   ``CHANGES.rst`` as follows, replacing ``A.C`` with the next non-bugfix version,
   and ``A.B`` with the version you just released::

     A.C (unreleased)
     ================

     New Features
     ------------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

     API Changes
     -----------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

     Bug Fixes
     ---------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

     Other Changes and Additions
     ---------------------------

     A.B.1 (unreleased)
     ==================

     Bug Fixes
     ---------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

#. Commit your changes of the, uh, change log with a message, "Back to development: A.C.dev"
   and push directly to ``main``.

#. For this commit, if you are doing a "major" release, also do this so ``setuptools-scm``
   is able to report the dev version properly. This is needed because it cannot grab
   the new release tag from a release branch:

.. code-block:: bash

     git tag -a vA.C.dev -m "Back to development: A.C.dev"
     git push upstream vA.C.dev

#. Follow procedures for :ref:`release-milestones` and :ref:`release-labels`.

#. For your own sanity unrelated to the release, grab the new tag for your fork:

.. code-block:: bash

     git fetch upstream --tags

Congratulations, you have just released a new version of Jdaviz!

.. _release-bugfix:

Releasing a bugfix version
==========================

.. note::

    Make sure all necessary backports to ``vX.Y.x`` are done before releasing.
    Most should have been automatically backported. If you need to manually
    backport something still, see :ref:`manual-backport`.

The procedure for a bugfix release is a little different from a feature release - you will
be releasing from an existing release branch, and will also need to do some
cleanup on the ``main`` branch. In the following, X and Y refer to the minor release for
which you're doing a bugfix release. For example, if you are releasing v3.5.2, replace all
instances of ``vX.Y.x`` with ``v3.5.x``. 

#. Lock down the ``vX.Y.x`` branch of the repository by setting the
   `branch protection <https://github.com/spacetelescope/jdaviz/settings/branches>`_
   rule for ``v*.x`` to some high number required to merge, so that more PRs don't
   get merged while you're releasing.

#. Review the appropriate `Milestone <https://github.com/spacetelescope/jdaviz/milestones>`_
   to see which PRs should be released in this version, and double check that any open
   backport PRs intended for this release have been merged.

#. Checkout the ``vX.Y.x`` branch corresponding to the last feature release.

#. The ``CHANGES.rst`` file should have all of the bug fixes to be released. Delete the
   unreleased feature version section at the top of the changelog if it exists and update
   the release date of the bugfix release section from ``unreleased`` to current date in
   the ``yyyy-mm-dd`` format. Remove any empty subsections.

#. Update the ``CITATION.cff`` file's ``date-released`` and ``version`` fields.
   If there are new contributors to the project, add them in the ``authors``
   section.

#. Do not forget to commit your changes from the last two steps:

.. code-block:: bash

     git add CHANGES.rst
     git add CITATION.cff
     git commit -m "Preparing release vX.Y.Z"

#. Push the ``vX.Y.x`` branch to upstream.
   Make sure the CI passes. If any of the CI fails, especially the job that
   says "Release", abandon this way. Stop here; do not continue! Otherwise,
   go to the next step.

#. Go to `Releases on GitHub <https://github.com/spacetelescope/jdaviz/releases>`_
   and `create a new GitHub release <https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository>`_
   targeting the release branch ``vX.Y.x`` (not ``main``!), and give it a new ``vX.Y.Z``
   tag (do not choose any existing tags). Copy the relevant section from CHANGES.rst
   into the release notes section and clean up any formatting problems.

#. The most important step: Click the ``Publish Release`` button!

#. Check `Release on Actions <https://github.com/spacetelescope/jdaviz/actions/workflows/publish.yml>`_
   to make sure that the new GitHub release triggered PyPI upload successfully.
   Also check that `files on PyPI <https://pypi.org/project/jdaviz/#files>`_ contain
   both the source tarball and the wheel for that release.

#. Check `RTD builds <https://readthedocs.org/projects/jdaviz/builds/>`_ to make sure
   that documentation built successfully for both ``latest`` and the new ``vX.Y.Z`` tag.

#. Check `Zenodo page for Jdaviz <https://doi.org/10.5281/zenodo.5513927>`_.
   It should have picked up the GitHub Release automatically.

#. The release is basically done, but now you have to set up the main branch for the
   *next* release cycle. Checkout the ``main`` branch and update ``CHANGES.rst``
   using your admin power. If you do not have sufficient access to do that,
   you will have to update it via a pull request from your fork. Make sure the
   section for the version just released matches the finalized change log from
   the release branch (be sure to change ``unreleased`` to the appropriate date),
   and add a new bugfix release section below the next feature
   release section as follows, replacing ``X.Y.Z`` with the next minor release
   number. For example, if you just released ``3.0.2``, a section for ``3.0.3``
   would go below the section for ``3.1``::

     X.Y.Z (unreleased)
     ==================

     Bug Fixes
     ---------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

#. Commit your changes of the, uh, change log with a message, "Back to development: A.B.dev"

#. Finally, you will need to set up the vX.Y.x branch for the next (potential)
   bugfix release. To do this (either through a direct commit using admin power,
   or via pull request to vX.Y.x), add a new bugfix section to the top of the
   change log. For example, if the bugfix release you just made was 3.6.2,
   add a 3.6.3 (unreleased) section (see step 7, but no need for a feature
   release section). Commit these changes with a message along the lines of
   "Back to development, vX.Y.x".

#. Follow procedures for :ref:`release-milestones`.

#. For your own sanity unrelated to the release, grab the new tag for your fork::

     git fetch upstream --tags

Congratulations, you have just released a new version of Jdaviz!

.. _release-milestones:

Milestones bookkeeping
======================

#. Go to `Milestones <https://github.com/spacetelescope/jdaviz/milestones>`_.

#. Create a new milestone for the next release and the next bugfix release, if
   doing a feature release, or for just the next bugfix release if you just did
   one. You do not need to fill in the description and due date fields.

#. For the milestone of this release, if there are any open issues or pull requests
   still milestoned to it, move their milestones to the next feature or bugfix
   milestone as appropriate.

#. Make sure the milestone of this release ends up with "0 open" and then close it.

#. Remind the other devs of the open pull requests with milestone moved that they
   will need to move their change log entries to the new release section that you
   have created in ``CHANGES.rst`` during the release process.

.. _release-labels:

Labels bookkeeping
==================

This is only applicable if you are doing a new branched release.
In the instructions below, ``A.B`` is the old release and ``A.C`` is
the new release:

#. Go to `Labels <https://github.com/spacetelescope/jdaviz/labels>`_.

#. Find the old ``backport-vA.B.x`` label. Click its "Edit" button and
   add ``:zzz:`` in front of it. This would send it all the way to the
   end of labels listing and indicate that it has been retired from usage.

#. Click "New label" (big green button on top right). Enter ``backport-vA.C.x``
   as the label name, ``on-merge: backport to vA.C.x`` as the description, and
   ``#5319E7`` as the color. Then click "Create label".

Going forward, any PR that needs backporting to the ``vA.C.x`` branch can
have this label applied *before* merge to trigger the auto-backport bot on merge.
For more info on the bot, see https://meeseeksbox.github.io/ .

.. _manual-backport:

Manual backport
===============

Situations where a pull request might need to be manually backported
after being merged into ``main`` branch:

* Auto-backport failed.
* Maintainer forgot to apply relevant label to trigger auto-backport
  (see :ref:`release-labels`) *before* merging the pull request.

To manually backport pull request ``NNNN`` to a ``vX.Y.x`` branch;
``abcdef`` should be replaced by the actual *merge commit hash*
of that pull request that you can copy from ``main`` branch history:

.. code-block:: bash

    git fetch upstream vX.Y.x
    git checkout upstream/vX.Y.x -b backport-of-pr-NNNN-on-vX.Y.x
    git cherry-pick -x -m1 abcdef

You will likely have some merge/cherry-pick conflict here, fix them and commit.
Then push the branch out to your fork:

.. code-block:: bash

    git commit -am "Backport PR #NNNN: Original PR title"
    git push origin backport-of-pr-NNNN-on-vX.Y.x

Create a backport pull request from that ``backport-of-pr-NNNN-on-vX.Y.x``
branch you just pushed against ``upstream/vX.Y.x`` (not ``upstream/main``).
Title it::

    Backport PR #NNNN on branch vX.Y.x (Original PR title)

Also apply the correct label(s) and milestone. If the original pull request
has a ``Still Needs Manual Backport`` label attached to it, you can also
remove that label now.

.. _release-old:

The old, long way
=================

.. note::
   This section is kept mainly for historical purposes, and to show how many of the
   things that are now automated can be done manually. Note that it is not up-to-date
   with the change to a branched release strategy.

This way is recommended if you are new to the process or wish to manually run
some automated steps locally. It takes longer but has a smaller risk factor.
It also gives you a chance to test things out on a machine that is different
from the one used for deployment on GitHub Actions.

It is recommended for you to have a clean checkout of the Jdaviz repository
(not the fork), especially if you also do a lot of development work.
You can create a clean checkout as follows (requires
`SSH setup <https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh>`_):

.. code-block:: bash

    mkdir jdaviz_for_release
    cd jdaviz_for_release
    git clone git@github.com:spacetelescope/jdaviz.git .
    git fetch origin --tags

#. Ensure `CI on Actions for main <https://github.com/spacetelescope/jdaviz/actions/workflows/ci_workflows.yml?query=branch%3Amain>`_
   and `RTD build for latest <https://readthedocs.org/projects/jdaviz/builds/>`_
   are passing.

#. Update the ``CHANGES.rst`` file to make sure that all the user-facing changes are listed,
   and update the release date from ``unreleased`` to current date in the ``yyyy-mm-dd`` format.
   Remove any empty subsections.

#. Update the ``CITATION.cff`` file's ``date-released`` and ``version`` fields.
   If there are new contributors to the project, add them in the ``authors``
   section. Do not forget to commit your changes from the last two steps:

.. code-block:: bash

     git add CHANGES.rst
     git add CITATION.cff
     git commit -m "Preparing release vX.Y.Z"

#. Remove any untracked files. (WARNING: This will
   permanently remove any files that have not been previously committed, so
   make sure that you don't need to keep any of these files.)
   This step is not needed if you have a fresh code checkout, but does not hurt either:

.. code-block:: bash

     git clean -xdf

#. Tag the version you are about to release and sign it (optional but it is a good practice).
   Signing requires
   `GPG setup <https://docs.github.com/en/github/authenticating-to-github/managing-commit-signature-verification/adding-a-new-gpg-key-to-your-github-account>`_:

.. code-block:: bash

     git tag -s "vX.Y.Z" -m "Tagging version vX.Y.Z"

#. Generate the package distribution files by first making sure the
   following packages are installed and up-to-date:

.. code-block:: bash

     pip install build twine -U

#. Creating the source distribution and its wheel with:

.. code-block:: bash

     python -m build --sdist --wheel .

#. Do a preliminary check of the generated files:

.. code-block:: bash

     python -m twine check --strict dist/*

#. Fix any errors or warnings reported. Skip this step if not applicable.

#. Run unit tests using package you are about to release. It is recommended that you
   do this in a fresh Python environment. The following example uses ``conda``,
   so if you use a non-``conda`` Python environment manager, replace the ``conda``
   commands accordingly:

.. code-block:: bash

     conda create -n testenv python=3.9
     conda activate testenv
     pip install pytest pytest-astropy pytest-tornasync dist/*.whl
     cd ..
     python -c "import jdaviz; jdaviz.test(remote_data=True)"
     cd jdaviz_for_release

#. Fix any test failures. Skip this step if not applicable.

#. Depending on the severity of the fixes above, you might need to submit the
   fixes as separate PRs and abandon the release. If that is the case, stop here,
   delete the ``vX.Y.Z`` tag, and start again from above when those fixes are in
   the ``main`` branch. If there are no fixes (yay) or if you can justify pushing
   the fixes as part of this release (not recommended), continue on.

#. Remove files generated by above steps:

.. code-block:: bash

     git clean -xdf

#. Make sure code checkout state is clean and history is correct. If not, fix accordingly:

.. code-block:: bash

     git status
     git log

#. The release is basically done locally, but now you have to set it up for the
   *next* release cycle. Add a new section to the top of ``CHANGES.rst`` as follows,
   replacing ``A.B`` with the next non-bugfix version::

     A.B (unreleased)
     ================

     New Features
     ------------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

     API Changes
     -----------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

     Bug Fixes
     ---------

     Cubeviz
     ^^^^^^^

     Imviz
     ^^^^^

     Mosviz
     ^^^^^^

     Specviz
     ^^^^^^^

     Specviz2d
     ^^^^^^^^^

     Other Changes and Additions
     ---------------------------

#. Commit your changes of the, uh, change log:

.. code-block:: bash

     git add CHANGES.rst
     git commit -m "Back to development: A.B.dev"

#. For this commit, if you are doing a "major" release, also do this so ``setuptools-scm``
   is able to report the dev version properly. This is needed because it cannot grab
   the new release tag from a release branch:

.. code-block:: bash

     git tag -a vA.B.dev -m "Back to development: A.B.dev"

#. Push out the updated code and tag. If applicable, change ``origin`` to point to
   the remote that points to the repository being released:

.. code-block:: bash

     git push origin main
     git push origin vX.Y.Z
     git push origin vA.B.dev

#. Go to `Releases on GitHub <https://github.com/spacetelescope/jdaviz/releases>`_
   and `create a new GitHub release <https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository>`_
   off the new ``vX.Y.Z`` tag.

#. Check `Release on Actions <https://github.com/spacetelescope/jdaviz/actions/workflows/publish.yml>`_
   to make sure that the new GitHub release triggered PyPI upload successfully.
   Also check that `files on PyPI <https://pypi.org/project/jdaviz/#files>`_ contain
   both the source tarball and the wheel for that release.

#. Check `RTD builds <https://readthedocs.org/projects/jdaviz/builds/>`_ to make sure
   that documentation built successfully for both ``latest`` and the new ``vX.Y.Z`` tag.

#. Check `Zenodo page for Jdaviz <https://doi.org/10.5281/zenodo.5513927>`_.
   It should have picked up the GitHub Release automatically.

#. Follow procedures for :ref:`release-milestones`.

Congratulations, you have just released a new version of Jdaviz!
