# Wireframe Template Assets

This directory contains jdaviz-specific assets that override the defaults bundled in the
[`docs-wireframe-demo`](https://github.com/kecnry/docs-wireframe-demo) Sphinx extension.

## How it works

The `docs-wireframe-demo` package provides:
- The `.. wireframe-demo::` Sphinx directive
- A generic `wireframe-engine.js` (the interactive JS runtime — not overridable)
- Fallback `wireframe-base.html` and `wireframe-demo.css` defaults

jdaviz points `wireframe_assets_dir` at this directory in `docs/conf.py`, so the directive
loads jdaviz's custom HTML and CSS instead of the package defaults.  The engine JS is always
loaded from the package bundle.

## Files

### wireframe-base.html

The jdaviz-specific HTML structure for the interactive wireframe, including:

- Toolbar with jdaviz's toolbar icons (`loaders`, `save`, `settings`, `info`, `plugins`,
  `subsets`, mouseover)
- All six sidebar panels (`loaders`, `save`, `settings`, `info`, `plugins`, `subsets`),
  each with their tabs and content areas
- Viewer area (dynamically populated by the engine via `viewer-*` actions)
- Cycle control button

Template variables (substituted at build time from `wireframe_variables` in `conf.py`):
- `{{ jdaviz_version }}` — displayed in the toolbar version row
- `{{ descriptions.loaders }}`, `{{ descriptions.export }}`, etc. — sidebar description text
- `{{ descriptions.settings_units }}`, `{{ descriptions.info_metadata }}`, etc.
- `{{ plugin_name }}` — expansion panel title (overridden per-directive via `:plugin-name:`)

### wireframe-demo.css

All CSS for the wireframe, including:
- Layout and positioning (flexbox-based)
- Color schemes and theming (dark/light mode via CSS variables)
- Responsive design and media queries
- Animation and transitions (expansion panels, highlights, viewer add/remove)
- Component-specific styles: toolbar, sidebar panels, tabs, viewer area, data menu popup,
  expansion panels, plot options UI

### wireframe-loader.js

Utility script for cases where inline embedding isn't used (e.g. the landing page).
Dynamically loads CSS, HTML, and JS assets from `_templates/` in sequence.

## Usage in RST

```rst
.. wireframe-demo::
   :initial: viewer-add:horiz:v1
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: Aperture Photometry
```

See `docs/dev/wireframe.rst` for full option reference.

## Sidebar names

The `data-sidebar` and `data-sidebar-panel` attribute values in `wireframe-base.html` define
the canonical sidebar names used in `:demo:` and `:initial:` step sequences:

| Name       | Toolbar icon  | Panel content                              |
|------------|---------------|--------------------------------------------|
| `loaders`  | database-import | Data tab (source/format selects) + Viewer tab |
| `save`     | download      | Export description                         |
| `settings` | tune          | Plot Options tab + Units tab               |
| `info`     | information   | Metadata tab + Markers tab + Logger tab    |
| `plugins`  | wrench        | Expansion panels                           |
| `subsets`  | selection     | Subset description                         |
