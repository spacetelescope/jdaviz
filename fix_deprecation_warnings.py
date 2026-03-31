#!/usr/bin/env python
"""
Script to add @pytest.mark.filterwarnings decorator to test functions that need it.
This adds the decorator to test functions and classes that use load_data.
"""

import re
import sys
from pathlib import Path

# Decorator to add
DECORATOR = '@pytest.mark.filterwarnings("ignore:.*show_in_viewer.*:DeprecationWarning")'

# List of test files that need fixing (from failure list)
TEST_FILES = [
    "jdaviz/configs/default/plugins/markers/tests/test_markers_plugin.py",
    "jdaviz/configs/imviz/tests/test_parser.py",
    "jdaviz/tests/test_subsets.py",
    "jdaviz/core/loaders/tests/test_loaders.py",
    "jdaviz/tests/test_app.py",
    "jdaviz/configs/default/plugins/subset_tools/tests/test_subset_tools.py",
    "jdaviz/core/tests/test_launcher.py",
    "jdaviz/configs/imviz/tests/test_viewers.py",
    "jdaviz/configs/imviz/tests/test_regions.py",
    "jdaviz/configs/default/plugins/export/tests/test_export.py",
    "jdaviz/configs/default/plugins/plot_options/tests/test_plot_options.py",
    "jdaviz/configs/imviz/tests/test_catalogs.py",
    "jdaviz/core/loaders/resolvers/virtual_observatory/tests/test_vo_imviz.py",
    "jdaviz/configs/default/tests/test_aida.py",
    "jdaviz/core/tests/test_tools.py",
    "jdaviz/configs/imviz/tests/test_tools.py",
    "jdaviz/configs/imviz/tests/test_line_profile_xy.py",
    "jdaviz/configs/default/plugins/metadata_viewer/tests/test_metadata_viewer.py",
    "jdaviz/configs/imviz/tests/test_parser_asdf.py",
    "jdaviz/configs/imviz/tests/test_astrowidgets_api.py",
    "jdaviz/configs/imviz/tests/test_wcs_utils.py",
    "jdaviz/configs/imviz/tests/test_linking.py",
    "jdaviz/configs/imviz/tests/test_delete_data.py",
    "jdaviz/configs/imviz/tests/test_subset_centroid.py",
    "jdaviz/configs/imviz/tests/test_viewer_tools.py",
]

def add_decorator_to_function(content, func_pattern):
    """Add decorator to function if not already present."""
    # Check if decorator already exists
    if DECORATOR in func_pattern:
        return func_pattern
    
    # Find the indentation and function definition
    match = re.search(r'(^\s*)(@pytest\.\S+\s+)?(def |class )', func_pattern, re.MULTILINE)
    if match:
        indent = match.group(1)
        existing_decorators = match.group(2) or ''
        definition = match.group(3)
        
        # Add our decorator before the function/class definition
        if existing_decorators:
            # There are existing decorators, add ours before them
            return func_pattern.replace(
                existing_decorators + definition,
                f"{DECORATOR}\n{indent}{existing_decorators}{definition}"
            )
        else:
            # No existing decorators, add before def/class
            return func_pattern.replace(
                f"{indent}{definition}",
                f"{indent}{DECORATOR}\n{indent}{definition}"
            )
    return func_pattern

def process_file(filepath):
    """Process a single test file."""
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return
        
    print(f"Processing: {filepath}")
    
    with open(path, 'r') as f:
        content = f.read()
    
    original = content
    
    # Find all test functions and setup_class methods that might use load_data
    # Pattern: def test_... or class Test... or def setup_class
    pattern = r'((?:^\s*@[\w.]+.*\n)*^\s*(?:def test_\w+|class Test\w+|def setup_class)\([^)]*\):.*?(?=\n(?:def |class |$)))'
    
    matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))
    
    # Process in reverse order to maintain correct offsets
    for match in reversed(matches):
        func_text = match.group(1)
        # Only add decorator if function contains load_data
        if 'load_data' in func_text and DECORATOR not in func_text:
            new_text = add_decorator_to_function(content, func_text)
            if new_text != content:
                content = new_text
    
    if content != original:
        with open(path, 'w') as f:
            f.write(content)
        print(f"  Updated: {filepath}")
    else:
        print(f"  No changes: {filepath}")

def main():
    for test_file in TEST_FILES:
        process_file(test_file)
    print("Done!")

if __name__ == "__main__":
    main()
