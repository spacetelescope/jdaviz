/**
 * Jdaviz Wireframe Demo — Custom Actions
 *
 * Registers jdaviz-specific actions with the docs-wireframe-demo
 * infrastructure via WireframeDemo.registerAction().
 *
 * This file should be loaded AFTER wireframe-demo-controller.js
 * but BEFORE any wireframe-demo containers are auto-discovered.
 * If the controller hasn't loaded yet (e.g. deferred scripts),
 * registrations are queued and applied when 'wireframe-demo-ready' fires.
 */
(function () {
    'use strict';

    // ── Icon SVGs (Material Design Icons as data URIs) ──────────────────

    var ICON_SVGS = {
        'database-import': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M19,19V5H5V19H19M19,3A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5A2,2 0 0,1 3,19V5C3,3.89 3.9,3 5,3H19M11,7H13V11H17V13H13V17H11V13H7V11H11V7Z\" /></svg>')",
        'download': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z\" /></svg>')",
        'tune': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z\" /></svg>')",
        'information': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z\" /></svg>')",
        'wrench': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M8 13C6.14 13 4.59 14.28 4.14 16H2V18H4.14C4.59 19.72 6.14 21 8 21S11.41 19.72 11.86 18H22V16H11.86C11.41 14.28 9.86 13 8 13M8 19C6.9 19 6 18.1 6 17C6 15.9 6.9 15 8 15S10 15.9 10 17C10 18.1 9.1 19 8 19M19.86 6C19.41 4.28 17.86 3 16 3S12.59 4.28 12.14 6H2V8H12.14C12.59 9.72 14.14 11 16 11S19.41 9.72 19.86 8H22V6H19.86M16 9C14.9 9 14 8.1 14 7C14 5.9 14.9 5 16 5S18 5.9 18 7C18 8.1 17.1 9 16 9Z\" /></svg>')",
        'selection': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M2 2H8V4H4V8H2V2M2 16H4V20H8V22H2V16M16 2H22V8H20V4H16V2M20 16H22V22H16V20H20V16Z\" /></svg>')",
        'auto-fix': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M7.5,5.6L5,7L6.4,4.5L5,2L7.5,3.4L10,2L8.6,4.5L10,7L7.5,5.6M19.5,15.4L22,14L20.6,16.5L22,19L19.5,17.6L17,19L18.4,16.5L17,14L19.5,15.4M22,2L20.6,4.5L22,7L19.5,5.6L17,7L18.4,4.5L17,2L19.5,3.4L22,2M13.34,12.78L15.78,10.34L13.66,8.22L11.22,10.66L13.34,12.78M14.37,7.29L16.71,9.63C17.1,10 17.1,10.65 16.71,11.04L5.04,22.71C4.65,23.1 4,23.1 3.63,22.71L1.29,20.37C0.9,20 0.9,19.35 1.29,18.96L12.96,7.29C13.35,6.9 14,6.9 14.37,7.29Z\" /></svg>')",
        'home': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z\"/></svg>')",
        'pan-zoom': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M13,7H11V11H7V13H11V17H13V13H17V11H13V7Z\"/></svg>')",
        'rect-roi': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M4,6H2V20A2,2 0 0,0 4,22H18V20H4V6M20,2H8A2,2 0 0,0 6,4V16A2,2 0 0,0 8,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H8V4H20V16Z\"/></svg>')",
        'circ-roi': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z\"/></svg>')",
        'subset': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M2 2H8V4H4V8H2V2M2 16H4V20H8V22H2V16M16 2H22V8H20V4H16V2M20 16H22V22H16V20H20V16Z\"/></svg>')"
    };

    // Viewer toolbar icons
    var VIEWER_TOOLBAR_ICONS = ['home', 'pan-zoom', 'rect-roi', 'circ-roi'];

    // ── Sidebar content map ─────────────────────────────────────────────

    // Form element helper
    function formSelect(label, id, options) {
        var opts = options.map(function(o) { return '<option>' + o + '</option>'; }).join('');
        return '<div class="jdaviz-form-group">' +
            '<label class="jdaviz-form-label">' + label + '</label>' +
            '<select class="jdaviz-select" id="' + id + '">' + opts + '</select>' +
            '</div>';
    }

    function formButton(label) {
        return '<button class="jdaviz-button">' + label + '</button>';
    }

    function formInput(label, placeholder) {
        return '<div class="jdaviz-form-group">' +
            '<label class="jdaviz-form-label">' + label + '</label>' +
            '<input type="text" class="jdaviz-input" placeholder="' + (placeholder || '') + '" />' +
            '</div>';
    }

    function formCheckbox(label) {
        return '<div class="jdaviz-form-group">' +
            '<label class="jdaviz-checkbox-label"><input type="checkbox" /> ' + label + '</label>' +
            '</div>';
    }

    // Plugin list for expansion panels
    var PLUGIN_LIST = [
        'Gaussian Smooth', 'Model Fitting', 'Line Lists', 'Line Analysis',
        'Aperture Photometry', 'Moment Maps', 'Collapse',
        '2D Spectral Extraction', '3D Spectral Extraction', 'Ramp Extraction',
        'Orientation', 'Footprints', 'Compass', 'Catalog Search',
        'Data Quality', 'Sonify Data'
    ];

    function generatePluginPanelsHTML() {
        return PLUGIN_LIST.map(function(name) {
            return '<div class="jdaviz-expansion-panel" data-plugin-name="' + name + '">' +
                '<div class="jdaviz-expansion-header">' +
                '<span>' + name + '</span><span class="jdaviz-expansion-chevron">\u25B6</span>' +
                '</div>' +
                '<div class="jdaviz-expansion-body">' +
                '<div style="padding:8px 0;color:rgba(255,255,255,0.6);">' +
                'Configure ' + name.toLowerCase() + ' settings.' +
                '</div>' +
                '</div></div>';
        }).join('');
    }

    // Default sidebar content (can be overridden via config.customContentMap)
    var confSettings = (typeof window !== 'undefined' && window.__confSettings) || {};
    var loaderFormats = confSettings.loaderFormats ||
        ['auto', 'image', 'spectrum', 'catalog', 'cube'];

    var SIDEBAR_CONTENT = {
        'loaders': {
            tabs: ['Data', 'Viewer'],
            content: [
                'Load data into the application.<br>' +
                formSelect('Source', 'source-select', ['file', 'astroquery', 'url']) +
                formSelect('Format', 'format-select', loaderFormats) +
                formButton('Load') +
                '<div class="jdaviz-api-snippet">from jdaviz import Specviz\nviz = Specviz()\nviz.load_data("spectrum.fits")</div>',
                'Create and configure viewers.<br>' +
                formSelect('Viewer Type', 'viewer-type-select', ['image', 'scatter', '1D spectrum', '2D spectrum', 'histogram']) +
                formButton('Create Viewer') +
                '<div class="jdaviz-api-snippet">viz.app.add_viewer("spectrum-viewer")</div>'
            ],
            learnMore: ['Learn more about data import \u2192', 'Explore viewer options \u2192'],
            scrollTarget: 'grid-loaders'
        },
        'save': {
            tabs: null,
            content: 'Export data, plots, and subsets to various formats.' +
                '<div class="jdaviz-api-snippet">viz.app.get_viewer("spectrum-viewer").figure.save_png("plot.png")</div>',
            learnMore: 'See export options \u2192',
            scrollTarget: 'grid-export'
        },
        'settings': {
            tabs: ['Plot Options', 'Units'],
            content: [
                'dynamic:plot-options',
                'Configure display units for spectral and flux axes.<br>' +
                formSelect('Spectral Unit', 'spectral-unit-select', ['Angstrom', 'nm', 'micron']) +
                formSelect('Flux Unit', 'flux-unit-select', ['Jy', 'erg/s/cm\u00B2/\u00C5']) +
                '<div class="jdaviz-api-snippet">viz.plugins["Unit Conversion"].spectral_unit = "micron"</div>'
            ],
            learnMore: ['View plot customization \u2192', 'Learn about units \u2192'],
            scrollTarget: 'grid-settings'
        },
        'info': {
            tabs: ['Metadata', 'Markers', 'Logger'],
            content: [
                'Display file metadata and header information.' +
                '<div class="jdaviz-api-snippet">viz.app.get_viewer("spectrum-viewer").data()</div>',
                'Interactive table of markers placed on the viewer.',
                'View history of operations and messages.'
            ],
            learnMore: ['Explore metadata tools \u2192', 'Learn about markers \u2192', 'View logging options \u2192'],
            scrollTarget: 'grid-info'
        },
        'plugins': {
            tabs: null,
            content: 'dynamic:plugin-panels',
            learnMore: 'Browse analysis plugins \u2192',
            scrollTarget: 'grid-plugins'
        },
        'subsets': {
            tabs: null,
            content: 'Create and manage spatial and spectral subsets for targeted analysis.<br>' +
                formSelect('Subset', 'subset-select', ['Subset 1', 'Subset 2']) +
                formButton('Recenter') +
                formButton('Delete') +
                '<div class="jdaviz-api-snippet">viz.get_subsets()</div>',
            learnMore: 'Learn about subsets \u2192',
            scrollTarget: 'grid-subsets'
        }
    };

    // ── Per-instance state ──────────────────────────────────────────────

    function getState(instance) {
        if (!instance._jdaviz) {
            instance._jdaviz = {
                currentSidebar: null,
                currentTabIndex: 0
            };
        }
        return instance._jdaviz;
    }

    // ── Helper: apply toolbar icons ─────────────────────────────────────

    function applyToolbarIcons(contentRoot) {
        var icons = contentRoot.querySelectorAll('.jdaviz-toolbar-icon');
        icons.forEach(function(icon) {
            var name = icon.getAttribute('data-icon');
            if (name && ICON_SVGS[name]) {
                icon.style.backgroundImage = ICON_SVGS[name];
            }
        });
    }

    // ── Helper: create a viewer element ─────────────────────────────────

    function createViewerElement(viewerId) {
        var viewer = document.createElement('div');
        viewer.className = 'jdaviz-viewer viewer-adding';
        viewer.dataset.viewerId = viewerId;

        var toolbarHtml = '<div class="jdaviz-viewer-toolbar"><div class="jdaviz-viewer-toolbar-spacer"></div>';
        VIEWER_TOOLBAR_ICONS.forEach(function(iconName) {
            toolbarHtml += '<div class="jdaviz-viewer-toolbar-icon" data-tool="' + iconName + '" title="' + iconName + '"></div>';
        });
        toolbarHtml += '</div>';

        viewer.innerHTML = toolbarHtml +
            '<div class="jdaviz-viewer-content">' +
            '<div class="jdaviz-viewer-image-container"></div>' +
            '<span class="jdaviz-viewer-area-text">' + viewerId + '</span>' +
            '<div class="jdaviz-viewer-legend"></div>' +
            '</div>';

        // Apply viewer toolbar icons
        var toolIcons = viewer.querySelectorAll('.jdaviz-viewer-toolbar-icon');
        toolIcons.forEach(function(icon) {
            var name = icon.getAttribute('data-tool');
            if (name && ICON_SVGS[name]) {
                icon.style.backgroundImage = ICON_SVGS[name];
            }
        });

        setTimeout(function() { viewer.classList.remove('viewer-adding'); }, 300);

        return viewer;
    }

    // ── Helper: generate Plot Options HTML ──────────────────────────────

    function generatePlotOptionsHTML(contentRoot, selectedViewerId, selectedLayerIndex, selectedColor) {
        var viewers = contentRoot.querySelectorAll('.jdaviz-viewer');
        var viewerIds = [];
        viewers.forEach(function(v) { viewerIds.push(v.dataset.viewerId); });

        if (!selectedViewerId && viewerIds.length > 0) selectedViewerId = viewerIds[0];

        var layers = [];
        if (selectedViewerId) {
            var viewer = contentRoot.querySelector('.jdaviz-viewer[data-viewer-id="' + selectedViewerId + '"]');
            if (viewer) {
                var legendItems = viewer.querySelectorAll('.jdaviz-legend-item');
                legendItems.forEach(function(item, idx) {
                    layers.push({ letter: String.fromCharCode(65 + idx), index: idx });
                });
            }
        }
        if (selectedLayerIndex === undefined && layers.length > 0) selectedLayerIndex = 0;
        if (!selectedColor) selectedColor = '#00FF00';

        var html = '';
        // Viewer dropdown
        html += '<div class="jdaviz-form-group"><label class="jdaviz-form-label">Viewer</label>';
        html += '<select class="jdaviz-select jdaviz-plot-options-viewer">';
        viewerIds.forEach(function(id) {
            var sel = id === selectedViewerId ? ' selected' : '';
            html += '<option value="' + id + '"' + sel + '>' + id + '</option>';
        });
        if (viewerIds.length === 0) html += '<option>No viewers</option>';
        html += '</select></div>';

        // Layer tabs
        if (layers.length > 0) {
            html += '<div class="jdaviz-form-group"><label class="jdaviz-form-label">Layer</label>';
            html += '<div class="jdaviz-plot-options-layers">';
            layers.forEach(function(l) {
                var cls = l.index === selectedLayerIndex ? ' active' : '';
                html += '<button class="jdaviz-button jdaviz-layer-tab' + cls + '" data-layer-index="' + l.index + '" style="display:inline-block;width:auto;margin:0 4px 0 0;padding:4px 12px;">' + l.letter + '</button>';
            });
            html += '</div></div>';

            // Color
            html += '<div class="jdaviz-form-group"><label class="jdaviz-form-label">Color</label>';
            html += '<button class="jdaviz-button jdaviz-color-btn" style="background:' + selectedColor + ';width:40px;height:24px;padding:0;"></button>';
            html += '</div>';

            // Placeholder controls
            html += '<div class="jdaviz-form-group"><label class="jdaviz-form-label">Display</label>';
            html += '<div style="height:8px;background:rgba(255,255,255,0.1);border-radius:4px;margin:6px 0;"></div>';
            html += '<div style="height:8px;background:rgba(255,255,255,0.1);border-radius:4px;margin:6px 0;"></div>';
            html += '</div>';
        } else {
            html += '<div style="text-align:center;color:rgba(255,255,255,0.5);margin-top:16px;">No layers in selected viewer</div>';
        }

        return html;
    }

    // ── Helper: render sidebar content ──────────────────────────────────

    function renderSidebar(instance, sidebarType, tabIndex) {
        var state = getState(instance);
        var root = instance._contentRoot;
        var sidebar = root.querySelector('.jdaviz-sidebar');
        var tabsEl = root.querySelector('.jdaviz-sidebar-tabs');
        var contentEl = root.querySelector('.jdaviz-sidebar-content');
        var footerEl = root.querySelector('.jdaviz-sidebar-footer');

        if (!sidebar || !contentEl) return;

        // Get content map (allow override via config)
        var contentMap = SIDEBAR_CONTENT;
        if (instance.config.customContentMap) {
            var custom = instance.config.customContentMap;
            if (typeof custom === 'string') {
                try { custom = JSON.parse(custom); } catch(e) { custom = {}; }
            }
            contentMap = Object.assign({}, SIDEBAR_CONTENT, custom);
        }

        var data = contentMap[sidebarType];
        if (!data) return;

        state.currentSidebar = sidebarType;
        state.currentTabIndex = tabIndex || 0;

        // Remove active from all toolbar icons
        var icons = root.querySelectorAll('.jdaviz-toolbar-icon[data-sidebar]');
        icons.forEach(function(i) { i.classList.remove('active'); });

        // Activate the clicked icon
        var activeIcon = root.querySelector('.jdaviz-toolbar-icon[data-sidebar="' + sidebarType + '"]');
        if (activeIcon) activeIcon.classList.add('active');

        // Build tabs
        if (data.tabs && data.tabs.length > 0) {
            var tabsHtml = '';
            data.tabs.forEach(function(tabName, idx) {
                var cls = idx === state.currentTabIndex ? ' active' : '';
                tabsHtml += '<button class="jdaviz-sidebar-tab' + cls + '" data-tab-index="' + idx + '">' + tabName + '</button>';
            });
            tabsEl.innerHTML = tabsHtml;

            // Tab click handlers
            tabsEl.querySelectorAll('.jdaviz-sidebar-tab').forEach(function(tab) {
                tab.addEventListener('click', function(e) {
                    if (e.isTrusted) instance.pause();
                    var idx = parseInt(tab.dataset.tabIndex, 10);
                    renderSidebar(instance, sidebarType, idx);
                });
            });
        } else {
            tabsEl.innerHTML = '';
        }

        // Build content
        var contentHtml = '';
        if (data.tabs && Array.isArray(data.content)) {
            contentHtml = data.content[state.currentTabIndex] || '';
        } else {
            contentHtml = data.content || '';
        }

        // Handle dynamic content
        if (contentHtml === 'dynamic:plot-options') {
            contentHtml = generatePlotOptionsHTML(root);
        } else if (contentHtml === 'dynamic:plugin-panels') {
            contentHtml = generatePluginPanelsHTML();
        }

        contentEl.innerHTML = contentHtml;

        // Wire up expansion panel clicks
        contentEl.querySelectorAll('.jdaviz-expansion-header').forEach(function(hdr) {
            hdr.addEventListener('click', function(ev) {
                if (ev.isTrusted) instance.pause();
                var panel = hdr.parentElement;
                panel.classList.toggle('open');
            });
        });

        // Build footer
        var learnMoreText = '';
        if (data.tabs && Array.isArray(data.learnMore)) {
            learnMoreText = data.learnMore[state.currentTabIndex] || '';
        } else {
            learnMoreText = data.learnMore || '';
        }
        if (learnMoreText) {
            var scrollAttr = data.scrollTarget
                ? ' data-scroll-target="' + data.scrollTarget + '"'
                : '';
            footerEl.innerHTML = '<button class="jdaviz-sidebar-footer-button"' + scrollAttr + '>' + learnMoreText + '</button>';
            // Wire up scroll-to click
            var footerBtn = footerEl.querySelector('.jdaviz-sidebar-footer-button[data-scroll-target]');
            if (footerBtn) {
                footerBtn.addEventListener('click', function(ev) {
                    var targetId = footerBtn.dataset.scrollTarget;
                    var targetEl = document.querySelector('[data-grid-id="' + targetId + '"]');
                    if (targetEl) {
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            }
        } else {
            footerEl.innerHTML = '';
        }

        // Show sidebar
        sidebar.classList.add('visible');
    }

    // ── Register custom actions ─────────────────────────────────────────

    function registerAll() {

    /**
     * show-sidebar: Open a sidebar panel.
     * step.value = sidebar type name (e.g. "loaders", "settings")
     */
    WireframeDemo.registerAction('show-sidebar', function(step, el, contentRoot) {
        var sidebarType = step.value;
        applyToolbarIcons(contentRoot);
        renderSidebar(this, sidebarType, 0);

        // Highlight the toolbar icon
        if (!step.noHighlight) {
            var icon = contentRoot.querySelector('.jdaviz-toolbar-icon[data-sidebar="' + sidebarType + '"]');
            if (icon) this._highlight(icon, step.delay);
        }
    });

    /**
     * hide-sidebar: Close the sidebar.
     */
    WireframeDemo.registerAction('hide-sidebar', function(step, el, contentRoot) {
        var sidebar = contentRoot.querySelector('.jdaviz-sidebar');
        if (sidebar) sidebar.classList.remove('visible');
        var icons = contentRoot.querySelectorAll('.jdaviz-toolbar-icon[data-sidebar]');
        icons.forEach(function(i) { i.classList.remove('active'); });
        var state = getState(this);
        state.currentSidebar = null;
    });

    /**
     * select-tab: Select a tab within the current sidebar by name.
     * step.value = tab name (e.g. "Viewer", "Units")
     */
    WireframeDemo.registerAction('select-tab', function(step, el, contentRoot) {
        var state = getState(this);
        if (!state.currentSidebar) return;

        var data = SIDEBAR_CONTENT[state.currentSidebar];
        if (!data || !data.tabs) return;

        var targetIndex = -1;
        data.tabs.forEach(function(name, idx) {
            if (name === step.value) targetIndex = idx;
        });

        if (targetIndex >= 0) {
            renderSidebar(this, state.currentSidebar, targetIndex);

            if (!step.noHighlight) {
                var tab = contentRoot.querySelector('.jdaviz-sidebar-tab[data-tab-index="' + targetIndex + '"]');
                if (tab) this._highlight(tab, step.delay);
            }
        }
    });

    /**
     * select-dropdown: Select a dropdown value by label text.
     * step.value = "label:option" (e.g. "source:file", "format:image")
     */
    WireframeDemo.registerAction('select-dropdown', function(step, el, contentRoot) {
        if (!step.value) return;
        var parts = step.value.split(':');
        var targetLabel = parts[0].trim().toLowerCase();
        var targetValue = parts.slice(1).join(':').trim().toLowerCase();

        var dropdowns = contentRoot.querySelectorAll('.jdaviz-select');
        var self = this;
        dropdowns.forEach(function(dropdown) {
            var label = dropdown.previousElementSibling;
            if (label && label.textContent.trim().toLowerCase().indexOf(targetLabel) !== -1) {
                var options = dropdown.querySelectorAll('option');
                options.forEach(function(option, idx) {
                    if (option.textContent.trim().toLowerCase() === targetValue) {
                        dropdown.selectedIndex = idx;
                        if (!step.noHighlight) self._highlight(dropdown, step.delay);
                    }
                });
            }
        });
    });

    /**
     * click-button: Click a button by text content.
     * step.value = button label (e.g. "Load", "Create Viewer")
     */
    WireframeDemo.registerAction('click-button', function(step, el, contentRoot) {
        if (!step.value) return;
        var target = step.value.toLowerCase();
        var self = this;
        var buttons = contentRoot.querySelectorAll('.jdaviz-button');
        buttons.forEach(function(btn) {
            if (btn.textContent.trim().toLowerCase() === target) {
                btn.style.background = 'rgba(199, 93, 44, 0.8)';
                setTimeout(function() { btn.style.background = ''; }, 400);
                if (!step.noHighlight) self._highlight(btn, step.delay);
            }
        });
    });

    /**
     * viewer-add: Add a new viewer.
     * step.value = "direction:newId" or "direction:newId:parentId"
     */
    WireframeDemo.registerAction('viewer-add', function(step, el, contentRoot) {
        if (!step.value) return;
        var params = step.value.split(':');
        var direction = params[0] || 'horiz';
        var newId = params[1] || 'viewer-' + Date.now();
        var parentId = params[2] || null;

        var viewerArea = contentRoot.querySelector('.jdaviz-viewer-area');
        if (!viewerArea) return;

        // Apply toolbar icons on first viewer add
        applyToolbarIcons(contentRoot);

        var targetViewer;
        if (parentId) {
            targetViewer = contentRoot.querySelector('.jdaviz-viewer[data-viewer-id="' + parentId + '"]');
        } else {
            var viewers = contentRoot.querySelectorAll('.jdaviz-viewer');
            targetViewer = viewers.length > 0 ? viewers[viewers.length - 1] : null;
        }

        if (!targetViewer) {
            viewerArea.appendChild(createViewerElement(newId));
            return;
        }

        var parent = targetViewer.parentNode;
        var splitContainer = document.createElement('div');
        var isHoriz = direction === 'horiz' || direction === 'h' || direction === 'horiz-before' || direction === 'hb';
        splitContainer.className = 'jdaviz-viewer-split ' + (isHoriz ? 'horizontal' : 'vertical');

        parent.insertBefore(splitContainer, targetViewer);
        splitContainer.appendChild(targetViewer);

        var newViewer = createViewerElement(newId);
        if (direction === 'horiz-before' || direction === 'hb' || direction === 'vert-before' || direction === 'vb') {
            splitContainer.insertBefore(newViewer, targetViewer);
        } else {
            splitContainer.appendChild(newViewer);
        }
    });

    /**
     * viewer-image: Set background image for a viewer.
     * step.value = "viewerId:imagePath"
     */
    WireframeDemo.registerAction('viewer-image', function(step, el, contentRoot) {
        if (!step.value) return;
        var params = step.value.split(':');
        var viewerId = params[0];
        var imagePath = params.slice(1).join(':');

        var viewer = contentRoot.querySelector('.jdaviz-viewer[data-viewer-id="' + viewerId + '"]');
        if (!viewer) return;

        var content = viewer.querySelector('.jdaviz-viewer-content');
        var imageContainer = viewer.querySelector('.jdaviz-viewer-image-container');

        if (content && imageContainer) {
            if (imagePath) {
                content.classList.add('has-image');
                imageContainer.style.backgroundImage = 'url(' + imagePath + ')';
            } else {
                content.classList.remove('has-image');
                imageContainer.style.backgroundImage = '';
            }
        }
    });

    /**
     * viewer-legend: Set legend layers for a viewer.
     * step.value = "viewerId:layer1|layer2"
     */
    WireframeDemo.registerAction('viewer-legend', function(step, el, contentRoot) {
        if (!step.value) return;
        var params = step.value.split(':');
        var viewerId = params[0];
        var layersString = params.slice(1).join(':');

        var viewer = contentRoot.querySelector('.jdaviz-viewer[data-viewer-id="' + viewerId + '"]');
        if (!viewer) return;

        var legend = viewer.querySelector('.jdaviz-viewer-legend');
        if (!legend) return;

        legend.innerHTML = '';
        var layers = layersString.split('|');
        var total = layers.filter(function(l) { return l.trim(); }).length;
        layers.forEach(function(layer, idx) {
            var name = layer.trim();
            if (!name) return;
            var letter = String.fromCharCode(65 + ((total - 1 - idx) % 26));
            var item = document.createElement('div');
            item.className = 'jdaviz-legend-item';
            item.innerHTML = '<span class="jdaviz-legend-letter">' + letter + '</span><span class="jdaviz-legend-text">' + name + '</span>';
            legend.appendChild(item);
        });
    });

    /**
     * viewer-focus: Visually emphasize a viewer.
     * step.value = viewerId
     */
    WireframeDemo.registerAction('viewer-focus', function(step, el, contentRoot) {
        var viewers = contentRoot.querySelectorAll('.jdaviz-viewer');
        viewers.forEach(function(v) { v.classList.remove('focused'); });
        if (step.value) {
            var viewer = contentRoot.querySelector('.jdaviz-viewer[data-viewer-id="' + step.value + '"]');
            if (viewer) viewer.classList.add('focused');
        }
    });

    /**
     * viewer-remove: Remove a viewer.
     * step.value = viewerId
     */
    WireframeDemo.registerAction('viewer-remove', function(step, el, contentRoot) {
        if (!step.value) return;
        var viewer = contentRoot.querySelector('.jdaviz-viewer[data-viewer-id="' + step.value + '"]');
        if (!viewer) return;

        var parent = viewer.parentNode;
        viewer.remove();

        // If parent is a split container with only one child, unwrap it
        if (parent && parent.classList.contains('jdaviz-viewer-split')) {
            var remaining = parent.children;
            if (remaining.length === 1) {
                var child = remaining[0];
                parent.parentNode.insertBefore(child, parent);
                parent.remove();
            } else if (remaining.length === 0) {
                parent.remove();
            }
        }
    });

    /**
     * viewer-tool-toggle: Toggle a viewer toolbar tool.
     * step.value = "viewerId:toolName"
     */
    WireframeDemo.registerAction('viewer-tool-toggle', function(step, el, contentRoot) {
        if (!step.value) return;
        var params = step.value.split(':');
        var viewerId = params[0];
        var toolName = params[1];

        var viewer = contentRoot.querySelector('.jdaviz-viewer[data-viewer-id="' + viewerId + '"]');
        if (!viewer) return;

        var toolIcon = viewer.querySelector('.jdaviz-viewer-toolbar-icon[data-tool="' + toolName + '"]');
        if (toolIcon) {
            toolIcon.classList.toggle('active');
            if (!step.noHighlight) this._highlight(toolIcon, step.delay);
        }
    });

    /**
     * select-layer: Select a layer tab in Plot Options.
     * step.value = layer index (e.g. "1")
     */
    WireframeDemo.registerAction('select-layer', function(step, el, contentRoot) {
        var layerIndex = parseInt(step.value, 10) || 0;
        var tabs = contentRoot.querySelectorAll('.jdaviz-layer-tab');
        if (tabs[layerIndex]) {
            tabs.forEach(function(t) { t.classList.remove('active'); });
            tabs[layerIndex].classList.add('active');
            if (!step.noHighlight) this._highlight(tabs[layerIndex], step.delay);
        }
    });

    /**
     * set-color: Set the color button in Plot Options.
     * step.value = color string (e.g. "#FF0000")
     */
    WireframeDemo.registerAction('set-color', function(step, el, contentRoot) {
        var colorBtn = contentRoot.querySelector('.jdaviz-color-btn');
        if (colorBtn && step.value) {
            colorBtn.style.background = step.value;
            if (!step.noHighlight) this._highlight(colorBtn, step.delay);
        }
    });

    /**
     * open-data-menu: Open the data menu popup.
     */
    WireframeDemo.registerAction('open-data-menu', function(step, el, contentRoot) {
        var popup = contentRoot.querySelector('.jdaviz-data-menu-popup');
        if (popup) popup.classList.add('visible');
    });

    /**
     * open-panel: Open a plugin expansion panel by name.
     * step.value = plugin name (e.g. "Gaussian Smooth")
     */
    WireframeDemo.registerAction('open-panel', function(step, el, contentRoot) {
        var panels = contentRoot.querySelectorAll('.jdaviz-expansion-panel');
        panels.forEach(function(panel) {
            if (panel.dataset.pluginName === step.value) {
                panel.classList.add('open');
            }
        });
    });

    /**
     * api-toggle: Toggle the API hints display in the sidebar.
     */
    WireframeDemo.registerAction('api-toggle', function(step, el, contentRoot) {
        var sidebar = contentRoot.querySelector('.jdaviz-sidebar');
        if (sidebar) sidebar.classList.toggle('api-hints-visible');
        var btn = contentRoot.querySelector('.jdaviz-api-toggle-btn');
        if (btn) btn.classList.toggle('active');
    });

    } // end registerAll

    // ── Register actions: immediately if controller is loaded, else wait ─
    if (typeof WireframeDemo !== 'undefined' && WireframeDemo.registerAction) {
        registerAll();
    } else {
        document.addEventListener('wireframe-demo-ready', function() {
            registerAll();
        }, { once: true });
    }

    // ── Initialization hook ─────────────────────────────────────────────
    // Apply toolbar icons when any wireframe-demo finishes loading HTML.
    // This listens for the event dispatched by the docs-wireframe-demo controller.

    document.addEventListener('wireframe-demo-loaded', function(e) {
        if (e.detail && e.detail.container) {
            var root = e.detail.container.querySelector('.wfd-content');
            if (root && root.querySelector('.jdaviz-toolbar')) {
                applyToolbarIcons(root);

                // Wire up interactive toolbar clicks (for manual user interaction)
                root.querySelectorAll('.jdaviz-toolbar-icon[data-sidebar]').forEach(function(icon) {
                    icon.addEventListener('click', function(ev) {
                        if (!ev.isTrusted) return;
                        var instance = e.detail.instance;
                        if (instance) {
                            instance.pause();
                            var sidebarType = icon.dataset.sidebar;
                            var state = getState(instance);
                            if (state.currentSidebar === sidebarType) {
                                // Toggle off
                                var sidebar = root.querySelector('.jdaviz-sidebar');
                                if (sidebar) sidebar.classList.remove('visible');
                                icon.classList.remove('active');
                                state.currentSidebar = null;
                            } else {
                                renderSidebar(instance, sidebarType, 0);
                            }
                        }
                    });
                });

                // Wire up data menu close button
                var closeBtn = root.querySelector('.jdaviz-data-menu-close');
                if (closeBtn) {
                    closeBtn.addEventListener('click', function() {
                        var popup = root.querySelector('.jdaviz-data-menu-popup');
                        if (popup) popup.classList.remove('visible');
                    });
                }

                // Populate version from conf settings
                var versionEl = root.querySelector('.jdaviz-toolbar-version');
                if (versionEl && confSettings.version) {
                    versionEl.textContent = 'v' + confSettings.version;
                }

                // Wire up search bar to open Sphinx search
                var searchInput = root.querySelector('.jdaviz-toolbar-search');
                if (searchInput) {
                    searchInput.removeAttribute('readonly');
                    searchInput.addEventListener('keydown', function(ev) {
                        if (ev.key === 'Enter' && searchInput.value.trim()) {
                            var searchLink = document.querySelector('link[rel="search"]');
                            var searchUrl = searchLink ? searchLink.href : 'search.html';
                            window.location.href = searchUrl + '?q=' + encodeURIComponent(searchInput.value.trim());
                        }
                    });
                }

                // Wire up API toggle button
                var apiBtn = root.querySelector('.jdaviz-api-toggle-btn');
                if (apiBtn) {
                    apiBtn.addEventListener('click', function(ev) {
                        var instance = e.detail.instance;
                        if (instance && ev.isTrusted) instance.pause();
                        var sidebar = root.querySelector('.jdaviz-sidebar');
                        if (sidebar) sidebar.classList.toggle('api-hints-visible');
                        apiBtn.classList.toggle('active');
                    });
                }

                // Apply initial classes from config (e.g. "show-scroll-to")
                var instance = e.detail.instance;
                if (instance && instance.config && instance.config.initialClass) {
                    var classes = instance.config.initialClass.split(/\s+/);
                    var section = root.querySelector('.jdaviz-wireframe-section') || root;
                    classes.forEach(function(cls) {
                        if (cls) section.classList.add(cls);
                    });
                }
            }
        }
    });

})();
