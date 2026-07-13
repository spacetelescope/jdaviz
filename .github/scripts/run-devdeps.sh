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

# git main branches for the astropy / glue ecosystem packages.
GIT_MAIN=(
  "git+https://github.com/astropy/regions.git"
  "git+https://github.com/astropy/specutils.git"
  "git+https://github.com/spacetelescope/gwcs.git"
  "git+https://github.com/asdf-format/asdf.git"
  "git+https://github.com/astropy/asdf-astropy.git"
  "git+https://github.com/spacetelescope/stdatamodels.git"
  "git+https://github.com/glue-viz/echo.git"
  "git+https://github.com/glue-viz/glue.git"
  "git+https://github.com/glue-viz/bqplot-image-gl.git"
  "git+https://github.com/glue-viz/glue-jupyter.git"
  "git+https://github.com/glue-viz/glue-astronomy.git"
  "git+https://github.com/widgetti/solara.git"
  "git+https://github.com/astropy/specreduce.git"
  "git+https://github.com/radio-astro-tools/spectral-cube.git"
)

project_spec=".[test]"
if [ -n "${EXTRAS}" ]; then
  project_spec=".[test,${EXTRAS}]"
fi

uv venv --python "${PYTHON_VERSION}" .venv-devdeps

uv pip install --python .venv-devdeps --prerelease allow --upgrade \
  "${DEV_INDEXES[@]}" \
  "${project_spec}" \
  "${NIGHTLY[@]}" \
  "${GIT_MAIN[@]}"

.venv-devdeps/bin/pytest -n auto --dist loadfile --pyargs jdaviz docs \
  --ignore=jdaviz/qt.py --durations=30 --memlog "$@"
