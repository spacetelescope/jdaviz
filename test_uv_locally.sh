#!/bin/bash
# Test UV locally to compare with current pip/tox setup
# This helps validate UV before rolling it out in CI

set -eo pipefail

echo "============================================"
echo "UV Local Test Script"
echo "============================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
fi

echo "UV version: $(uv --version)"
echo ""

# Create a test venv
TEST_DIR=".uv_test_env"
if [ -d "$TEST_DIR" ]; then
    echo "Removing existing test environment..."
    rm -rf "$TEST_DIR"
fi

echo "Creating UV virtual environment..."
mkdir -p "$TEST_DIR"

# Time the dependency resolution
echo ""
echo "--- Timing UV Dependency Resolution ---"
time_resolution_start=$(date +%s)

echo "Installing jdaviz with test dependencies..."
uv venv "$TEST_DIR/venv"
source "$TEST_DIR/venv/bin/activate" 2>/dev/null || . "$TEST_DIR/venv/Scripts/activate"

# Install with UV
uv pip install -e ".[test]"

time_resolution_end=$(date +%s)
time_resolution_s=$(( time_resolution_end - time_resolution_start ))

echo ""
echo "Resolution + Install Time: ${time_resolution_s}s"
echo ""

# Verify installation
echo "Verifying installation..."
python -c "import jdaviz; print(f'jdaviz version: {jdaviz.__version__}')"
python -c "import pytest; print(f'pytest installed: {pytest.__version__}')"

# Run a quick subset of tests
echo ""
echo "--- Running Quick Test Suite ---"
echo "Running a few quick tests to validate..."
MPLBACKEND=agg JUPYTER_PLATFORM_DIRS=1 pytest jdaviz/tests/test_utils.py -xvs

echo ""
echo "============================================"
echo "Test Environment Location: $TEST_DIR"
echo "To activate: source $TEST_DIR/venv/bin/activate"
echo "To clean up: rm -rf $TEST_DIR"
echo "============================================"
