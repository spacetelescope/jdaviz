#!/usr/bin/env bash
#
# Run the test suite against the latest development versions of jdaviz's key
# dependencies using uv (the tox "devdeps" factor equivalent).
#
# These jobs are intentionally NOT managed by pixi: they pull nightly wheels and
# git main branches, which are inherently unlocked/unreproducible and can break
# on any given day (hence they are allow_failure in CI). Keeping them out of the
# pixi workspace ensures a broken upstream dev build cannot poison the pixi lock
# used by the stable environments.
#
# Environment variables:
#   PYTHON_VERSION  Python version for the virtual environment (default: 3.13)
#   EXTRAS          Extra jdaviz optional-dependency groups, comma separated
#                   (e.g. "roman"). The "test" extra is always included.
#
# Any arguments passed to this script are forwarded to pytest.
set -euo pipefail

# Match the old tox `[testenv] setenv`: force a non-interactive matplotlib
# backend so headless CI never tries to open a GUI, and opt in to the new
# jupyter_core path layout to silence its migration DeprecationWarning (which
# filterwarnings=error would otherwise escalate to a test failure).
export MPLBACKEND="${MPLBACKEND:-agg}"
export JUPYTER_PLATFORM_DIRS="${JUPYTER_PLATFORM_DIRS:-1}"

PYTHON_VERSION="${PYTHON_VERSION:-3.13}"
EXTRAS="${EXTRAS:-}"

# Nightly / dev wheels for the core scientific stack.
DEV_INDEXES=(
  --extra-index-url https://pypi.anaconda.org/astropy/simple
  --extra-index-url https://pypi.anaconda.org/liberfa/simple
  --extra-index-url https://pypi.anaconda.org/scientific-python-nightly-wheels/simple
)

NIGHTLY=(
  "numpy>=0.0.dev0"
  "scipy>=0.0.dev0"
  "matplotlib>=0.0.dev0"
  "pandas>=0.0.dev0"
  "scikit-image>=0.0.dev0"
  "pyerfa>=0.0.dev0"
  "astropy>=0.0.dev0"
  "photutils>=0.0.dev0"
  "bqplot>=0.12,<0.13"
)

# git main branches for the astropy / glue ecosystem packages, written as
# `name @ git+url`. These are layered on top of the base install with
# `--no-deps` (see below) rather than resolved together with jdaviz.
GIT_MAIN=(
  "regions @ git+https://github.com/astropy/regions.git"
  "specutils @ git+https://github.com/astropy/specutils.git"
  "gwcs @ git+https://github.com/spacetelescope/gwcs.git"
  "asdf @ git+https://github.com/asdf-format/asdf.git"
  "asdf-astropy @ git+https://github.com/astropy/asdf-astropy.git"
  "stdatamodels @ git+https://github.com/spacetelescope/stdatamodels.git"
  "echo @ git+https://github.com/glue-viz/echo.git"
  "glue-core @ git+https://github.com/glue-viz/glue.git"
  # NOTE: bqplot-image-gl is intentionally NOT built from git here. Its git
  # main build-system.requires pins jupyterlab>=3.6,<4, which drags in an old
  # jupyter-ydoc / y-py that has no Python 3.13 wheels and unbuildable sdists,
  # so `uv`/`pip` cannot build it on 3.13 (upstream breakage). It is still
  # installed as a normal PyPI wheel via glue-jupyter; only its git-main build
  # is skipped. Re-add the line below once the upstream build is fixed:
  #   "bqplot-image-gl @ git+https://github.com/glue-viz/bqplot-image-gl.git"
  "glue-jupyter @ git+https://github.com/glue-viz/glue-jupyter.git"
  "glue-astronomy @ git+https://github.com/glue-viz/glue-astronomy.git"
  # NOTE: solara is intentionally NOT overridden to git main. The solara repo is
  # a monorepo whose root builds `solara-ui` (name mismatch for `solara`), and
  # jdaviz already pins solara/solara-ui/solara-server to 2.0.0a0 alpha wheels,
  # so it is bleeding-edge already. Overriding only `solara` would also be
  # inconsistent with the pinned solara-ui / solara-server.
  "specreduce @ git+https://github.com/astropy/specreduce.git"
  "spectral-cube @ git+https://github.com/radio-astro-tools/spectral-cube.git"
)

project_spec=".[test]"
if [ -n "${EXTRAS}" ]; then
  project_spec=".[test,${EXTRAS}]"
fi

uv venv --python "${PYTHON_VERSION}" .venv-devdeps

# The install is done in two stages, which reproduces how the old tox+pip
# devdeps job behaved. uv (unlike pip) performs a single strict resolution and
# refuses to build an inconsistent environment; jdaviz currently pins deps that
# are *ahead* of some packages' git main (e.g. it needs ipyvuetify>=3.0.0a4 via
# glue-jupyter PR #519, while glue-jupyter main still requires ipyvuetify<2), so
# a one-shot resolve is unsatisfiable. pip only "worked" by installing the
# pieces incrementally and tolerating the resulting conflict.
#
# Stage 1: a consistent base -- jdaviz (installed EDITABLE) + its test extra,
# with the core scientific stack bumped to nightly/dev wheels (resolved
# normally). The editable install matches the pixi environments
# (`jdaviz = { path = ".", editable = true }`) so that this job behaves like the
# rest of CI: `--pyargs jdaviz` then resolves to the source tree that pytest
# also collects from repo root (avoiding the conftest ImportPathMismatchError a
# non-editable/site-packages install would cause), and remote-data tests can
# find MAST cache files that `cached_uri()` looks for in the working directory.
# --index-strategy unsafe-best-match makes uv consider all of the extra index
# URLs (like pip does); without it uv only looks at the first index that
# contains a package, so dev wheels split across the astropy/liberfa/nightly
# indexes (e.g. pyerfa) are not found.
uv pip install --python .venv-devdeps --prerelease allow --upgrade \
  --index-strategy unsafe-best-match \
  "${DEV_INDEXES[@]}" \
  --editable "${project_spec}" \
  "${NIGHTLY[@]}" \
  boto3 botocore

# boto3/botocore are required by the remote-data tests against *dev* astroquery.
# Dev astroquery's Observations.download_file now uses the MAST S3 public dataset
# (cloud) path unconditionally, where stable (<=0.4.11) only did so after an
# explicit enable_cloud_dataset(). Without boto3/botocore it raises "Please
# install the boto3 and botocore packages ..." before it can return an ERROR
# status, which breaks tests that expect jdaviz's "Failed query for URI" message
# (e.g. test_uri_to_download_nonexistent_mast_file, test_resolver_url). botocore
# already comes in transitively via s3fs; boto3 is the one genuinely-new package.

# Stage 2: layer the git-main dev versions on top WITHOUT their dependencies.
# --no-deps is the uv equivalent of pip's tolerant/incremental install: it swaps
# in the dev versions of these packages without re-resolving (and therefore
# without failing on) their intentionally-conflicting requirements.
uv pip install --python .venv-devdeps --no-deps --upgrade \
  "${GIT_MAIN[@]}"

# Run pytest from the repository root, exactly like the pixi `test` task. Because
# jdaviz is installed editable (above), `--pyargs jdaviz` resolves to the source
# tree that pytest's rootdir-based conftest discovery also collects, so there is
# no ImportPathMismatchError, and any MAST *.fits cache files restored into the
# working directory are picked up by `cached_uri()` in the remote-data tests.
.venv-devdeps/bin/pytest -n auto --dist loadfile --pyargs jdaviz docs \
  --ignore=jdaviz/qt.py --durations=30 --memlog "$@"
