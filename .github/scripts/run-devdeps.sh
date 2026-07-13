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
# Stage 1: a consistent base -- jdaviz + its test extra, with the core
# scientific stack bumped to nightly/dev wheels (resolved normally).
# --index-strategy unsafe-best-match makes uv consider all of the extra index
# URLs (like pip does); without it uv only looks at the first index that
# contains a package, so dev wheels split across the astropy/liberfa/nightly
# indexes (e.g. pyerfa) are not found.
uv pip install --python .venv-devdeps --prerelease allow --upgrade \
  --index-strategy unsafe-best-match \
  "${DEV_INDEXES[@]}" \
  "${project_spec}" \
  "${NIGHTLY[@]}"

# Stage 2: layer the git-main dev versions on top WITHOUT their dependencies.
# --no-deps is the uv equivalent of pip's tolerant/incremental install: it swaps
# in the dev versions of these packages without re-resolving (and therefore
# without failing on) their intentionally-conflicting requirements.
uv pip install --python .venv-devdeps --no-deps --upgrade \
  "${GIT_MAIN[@]}"

# Run pytest from an isolated temporary directory so that the source-tree
# `jdaviz/` package is NOT discovered. `--pyargs jdaviz` imports the *installed*
# copy from site-packages, but pytest's rootdir-based conftest collection would
# otherwise also pick up ./jdaviz/conftest.py from the source tree, and the two
# `jdaviz.conftest` modules at different paths trigger an ImportPathMismatchError.
# This mirrors the old tox `changedir = .tmp/{envname}` behavior.
REPO_ROOT="$(pwd)"
PYTEST="${REPO_ROOT}/.venv-devdeps/bin/pytest"
JDAVIZ_INSTALLED="$("${REPO_ROOT}/.venv-devdeps/bin/python" -c 'import jdaviz, os; print(os.path.dirname(jdaviz.__file__))')"

RUN_DIR="$(mktemp -d)"
cd "${RUN_DIR}"

"${PYTEST}" -n auto --dist loadfile --pyargs jdaviz "${REPO_ROOT}/docs" \
  --ignore="${JDAVIZ_INSTALLED}/qt.py" --durations=30 --memlog "$@"
