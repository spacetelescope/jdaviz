# Wireframe Component Architecture

This document describes the refactored wireframe demonstration system.

## Overview

The wireframe demonstration code has been extracted from `index.html` into separate, modular components:

- `wireframe-base.html` - HTML structure
- `wireframe-demo.css` - All styling
- `wireframe-controller.js` - Interactive behavior and data

## Files

### wireframe-base.html
Contains the complete HTML structure for the interactive wireframe demonstration, including:
- Wireframe container and toolbar
- Sidebar panel
- Viewer area with data menu
- Cycle control button

### wireframe-demo.css
Contains all CSS styles for the wireframe, including:
- Layout and positioning
- Color schemes and theming (dark/light mode)
- Responsive design (media queries)
- Animation and transitions
- Component-specific styles (toolbar, sidebar, viewer, etc.)

### wireframe-controller.js
Contains all JavaScript functionality:
- Auto-cycling through different sidebars
- Sidebar content management
- Interactive toolbar controls
- Data menu popup behavior
- Platform tab integration
- API snippet toggling

## Usage

### In index.html

The main landing page (`index.html`) loads the wireframe components externally:

```html
<!-- CSS -->
<link rel="stylesheet" href="_templates/wireframe-demo.css">

<!-- JavaScript -->
<script src="_templates/wireframe-controller.js"></script>

<!-- HTML (loaded dynamically) -->
<div id="wireframe-placeholder"></div>
<script>
    fetch("_templates/wireframe-base.html")
        .then(response => response.text())
        .then(html => {
            const version = "{{ jdaviz_version }}";
            html = html.replace("{{ jdaviz_version }}", version);
            document.getElementById("wireframe-placeholder").innerHTML = html;
        });
</script>
```

### In RST Documentation Files

Use the `wireframe-demo` Sphinx directive to embed the wireframe in any RST file:

```rst
.. wireframe-demo::
```

This directive is defined in `conf.py` and automatically:
1. Loads all three component files
2. Processes Jinja2 variables (e.g., `{{ jdaviz_version }}`)
3. Embeds the complete wireframe as raw HTML

### Example: aperture_photometry.rst

The aperture photometry plugin documentation includes a wireframe at the top:

```rst
.. _plugins-aperture_photometry:

********************
Aperture Photometry
********************

.. wireframe-demo::

.. plugin-availability::

...rest of documentation...
```

## Benefits

1. **Modularity**: Each component (HTML, CSS, JS) is in its own file
2. **Maintainability**: Easier to edit and update specific parts
3. **Reusability**: Can be used in multiple places (landing page, plugin docs, etc.)
4. **Reduced File Size**: `index.html` reduced from 3382 to 967 lines
5. **Better Organization**: Clearer separation of concerns

## Technical Details

### Jinja2 Variable Handling

The wireframe HTML includes a Jinja2 template variable `{{ jdaviz_version }}` that needs to be replaced at runtime:

- In `index.html`: Replaced via JavaScript fetch and string replacement
- In RST files: Replaced by the Sphinx directive before embedding

### Sidebar Content

The `wireframe-controller.js` file includes a complete `sidebarContent_map` object that defines:
- Sidebar content for each toolbar icon
- Tab structures for multi-tab sidebars
- API snippets for each feature
- "Learn more" links to documentation sections

This data is dynamically used to populate the sidebar when users interact with the wireframe.

## Future Enhancements

Potential improvements:
- Add more sidebar content types
- Enhance mobile responsiveness
- Add keyboard navigation
- Improve accessibility (ARIA labels, focus management)
- Support for different wireframe configurations
