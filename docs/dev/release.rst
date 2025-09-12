****************************
Package Release Instructions
****************************

This document outlines the steps for releasing a versioned Jdaviz package to
PyPI. Currently, these do not cover submitting package updates to other
distribution outlets, such as ``conda-forge``.

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

But wait, there's more:

* :ref:`release-milestones`
* :ref:`manual-backport`

.. _release-feature:

Releasing a minor or major version
==================================

The automated release infrastructure has proven to be reliable for a good number
of releases now, so we've been using this faster version as the default release
procedure.

You can do a release from your fork directly without a clean code check-out.

1. Ensure `CI on Actions for main <https://github.com/spacetelescope/jdaviz/actions/workflows/ci_workflows.yml?query=branch%3Amain>`_
   and `readthedocs (RTD) build for latest <https://readthedocs.org/projects/jdaviz/builds/>`_
   are passing.

2. Optional, but recommended: Lock down the ``main`` branch of the repository by setting the
   `branch protection <https://github.com/spacetelescope/jdaviz/settings/branches>`_
   rule for ``main`` (note: only available to Jdaviz admins) to some high number
   required to merge, so that more PRs don't get merged while you're releasing.
   At the very least, give a heads up to the team that you are working on a release
   and that they should hold off merging any PRs until the release is done.

3. Create a new local 'vX.Y.x' branch and make sure you have updated tags too. Note
   that the "x" here should actually be the letter "x", whereas the upper case "X"
   and "Y" should be replace by your major and minor version numbers:

.. code-block:: bash

     git fetch upstream main
     git fetch upstream --tags
     git checkout upstream/main -b vX.Y.x

4. Update the ``CHANGES.rst`` file to make sure that all the user-facing changes are listed,
   and update the release date from ``unreleased`` to current date in the ``yyyy-mm-dd`` format.
   Remove any empty subsections.

   NOTE: You may encounter the case where there is a populated bugfix section
   below the current feature release section, but this bugfix release is being skipped
   in favor of a major release. If this happens, you will need to move those entries
   to the appropriate location(s) in the newest 'released' section, and remove that
   bugfix section since that release is being skipped.

5. Update the ``CITATION.cff`` file's ``date-released`` and ``version`` fields.
   If there are new contributors to the project, add them in the ``authors``
   section.

6. Do not forget to commit your changes from the last two steps:

.. code-block:: bash

     git add CHANGES.rst
     git add CITATION.cff
     git commit -m "Preparing release vX.Y.0"

7. Push the ``vX.Y.x`` branch to upstream.
   Make sure the CI passes. If any of the CI fails,
   stop here; do not continue! Contact the maintainers
   for information on how to proceed.
   Otherwise, go to the next step.

8. Go to `Releases on GitHub <https://github.com/spacetelescope/jdaviz/releases>`_
   and `create a new GitHub release <https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository>`_
   targeting the new branch you created (not ``main``!), and give it a new ``vX.Y.Z``
   tag (do not choose any existing tags). Copy the relevant section from CHANGES.rst
   into the release notes section and clean up any formatting problems.

9. The most important step: Click the ``Publish Release`` button!

10. Check `Release on Actions <https://github.com/spacetelescope/jdaviz/actions/workflows/publish.yml>`_
    to make sure that the new GitHub release triggered PyPI upload successfully.
    Also check that `files on PyPI <https://pypi.org/project/jdaviz/#files>`_ contain
    both the source tarball and the wheel for that release.

11. Check `RTD builds <https://readthedocs.org/projects/jdaviz/builds/>`_ to make sure
    that documentation built successfully for both ``latest`` and the new ``vX.Y.Z`` tag.

12. Check `Zenodo page for Jdaviz <https://doi.org/10.5281/zenodo.5513927>`_.
    It should have picked up the GitHub Release automatically.

13. The release is basically done, but now you have to set it up for the
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

14. Checkout ``main`` and update ``CHANGES.rst`` and ``CITATIONS.cff`` directly
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

15. Commit your changes of the, uh, change log with a message, "Back to development: A.C.dev"
    and push directly to ``main``.

16. For this commit, if you are doing a "major" release, also do this so ``setuptools-scm``
    is able to report the dev version properly. This is needed because it cannot grab
    the new release tag from a release branch:

.. code-block:: bash

     git tag -a vA.C.dev -m "Back to development: A.C.dev"
     git push upstream vA.C.dev

17. Follow procedures for :ref:`release-milestones`.

18. For your own sanity (unrelated to the release), grab the new tag for your fork:

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

1. Optional but recommended: Lock down the ``vX.Y.x`` branch of the repository by setting the
   `branch protection <https://github.com/spacetelescope/jdaviz/settings/branches>`_
   rule for ``v*.x`` (note: only available to Jdaviz admins) to some high number required to merge,
   so that more PRs don't get merged while you're releasing. At the very least,
   give a heads up to the team that you are working on a release
   and that they should hold off merging any PRs to the bugfix branch (including
   tagging PRs to main to the bugfix branch) until the release is done.

2. Review the appropriate `Milestone <https://github.com/spacetelescope/jdaviz/milestones>`_
   to see which PRs should be released in this version, and double check that any open
   backport PRs intended for this release have been merged.

3. Checkout the upstream ``vX.Y.x`` branch corresponding to the last feature release.
   Alternatively you can create a new local branch from ``vX.Y.x`` and make sure
   it is up to date with the upstream ``vX.Y.x`` branch, in which case you will
   eventually open a PR to ``vX.Y.x`` with changes for the release from your fork 
   instead of pushing directly to upstream.

4. The ``CHANGES.rst`` file should have all of the bug fixes to be released. Delete the
   unreleased feature version section at the top of the changelog if it exists and update
   the release date of the bugfix release section from ``unreleased`` to current date in
   the ``yyyy-mm-dd`` format. Remove any empty subsections.

5. Update the ``CITATION.cff`` file's ``date-released`` and ``version`` fields.
   If there are new contributors to the project, add them in the ``authors``
   section.

6. Do not forget to commit your changes from the last two steps:

.. code-block:: bash

     git add CHANGES.rst
     git add CITATION.cff
     git commit -m "Preparing release vX.Y.Z"

7. Push the ``vX.Y.x`` branch to upstream. Alternatively, you can open a PR to
   the ``vX.Y.x`` branch from your fork if you do not have direct push access or
   prefer to not push directly to upstream. Make sure the CI passes. If any of
   the CI fails, stop here; do not continue! Contact the maintainers for
   information on how to proceed. Otherwise,
   go to the next step.

8. Go to `Releases on GitHub <https://github.com/spacetelescope/jdaviz/releases>`_
   and `create a new GitHub release <https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository>`_
   targeting the release branch ``vX.Y.x`` (not ``main``!), and give it a new ``vX.Y.Z``
   tag (do not choose any existing tags). Copy the relevant section from CHANGES.rst
   into the release notes section and clean up any formatting problems.

9. The most important step: Click the ``Publish Release`` button!

10. Check `Release on Actions <https://github.com/spacetelescope/jdaviz/actions/workflows/publish.yml>`_
    to make sure that the new GitHub release triggered PyPI upload successfully.
    Also check that `files on PyPI <https://pypi.org/project/jdaviz/#files>`_ contain
    both the source tarball and the wheel for that release.

11. Check `RTD builds <https://readthedocs.org/projects/jdaviz/builds/>`_ to make sure
    that documentation built successfully for both ``latest`` and the new ``vX.Y.Z`` tag.

12. Check `Zenodo page for Jdaviz <https://doi.org/10.5281/zenodo.5513927>`_.
    It should have picked up the GitHub Release automatically.

13. The release is basically done, but now you have to set up the main branch for the
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

    Update the ``CITATION.cff`` file's ``date-released``, ``version`` and
    ``authors`` (if any new) sections to match the release branch.

14. Commit your changes of the, uh, change log with a message, "Back to development: A.B.dev"

15. Finally, you will need to set up the vX.Y.x branch for the next (potential)
    bugfix release. To do this (either through a direct commit using admin power,
    or via pull request to vX.Y.x), add a new bugfix section to the top of the
    change log. For example, if the bugfix release you just made was 3.6.2,
    add a 3.6.3 (unreleased) section (see step 7, but no need for a feature
    release section). Commit these changes with a message along the lines of
    "Back to development, vX.Y.x".

16. Follow procedures for :ref:`release-milestones`.

17. For your own sanity (unrelated to the release), grab the new tag for your fork::

     git fetch upstream --tags

Congratulations, you have just released a new version of Jdaviz!

.. _release-milestones:

Milestones bookkeeping
======================

1. Go to `Milestones <https://github.com/spacetelescope/jdaviz/milestones>`_.

2. If you are doing a bugfix release, create a new milestone for the next bugfix release.
   If you are doing a feature release, create a new milestone for **both**
   feature and bugfix releases. Change the ``description`` field for the new
   milestone(s) to include ONLY "on-merge: backport to vX.Y.x", with X and Y
   being the major and minor version of these milestones. For example, if you are
   creating a new 1.2.3 bugfix milestone after a 1.2.2 bugfix release, the description
   for the 1.2.3 milestone should be "on-merge: backport to v1.2.x". This text in
   the milestone description is used by the auto-backport bot to trigger automatic
   backport on merge for PRs with this milestone. You can leave the due date field
   empty.

3. If there are any open issues or pull requests still attached to the current release,
   move their milestones to the next feature or bugfix milestone as appropriate.

4. Make sure the milestone of this release ends up with "0 open" and then close it.

5. Remind the other devs of the open pull requests with milestone moved that they
   will need to move their change log entries to the new release section that you
   have created in ``CHANGES.rst`` during the release process.


.. _manual-backport:

Manual backport
===============

Situations where a pull request might need to be manually backported
after being merged into ``main`` branch:

* Auto-backport failed.
* Maintainer forgot to apply relevant milestone to trigger auto-backport
  *before* merging the pull request.

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
