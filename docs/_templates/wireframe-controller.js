// Wireframe controller initialization function - supports multiple instances
// This demo-wireframe made entirely possible by vibe coding
function initializeWireframeController(container) {
    // If no container provided, find all uninitialized containers
    if (!container) {
        const containers = document.querySelectorAll('.wireframe-container:not([data-initialized])');
        containers.forEach(function(c) {
            initializeWireframeController(c);
        });
        return;
    }

    // Skip if already initialized
    if (container.dataset.initialized) {
        return;
    }

    // Mark as initialized
    container.dataset.initialized = 'true';

    // Get configuration from container's data attribute or window fallback
    let config = {};
    const configAttr = container.dataset.wireframeConfig;
    if (configAttr) {
        try {
            config = JSON.parse(configAttr);
        } catch (e) {
            console.error('Failed to parse wireframe config:', e);
            config = window.wireframeConfig || {};
        }
    } else {
        config = window.wireframeConfig || {};
    }

    const initialState = config.initialState || null;
    const customDemo = config.customDemo || null;
    const enableOnly = config.enableOnly || null;
    const showScrollTo = config.showScrollTo !== undefined ? config.showScrollTo : true;
    const demoRepeat = config.demoRepeat !== undefined ? config.demoRepeat : true;
    const pluginName = config.pluginName || 'Data Analysis Plugin';
    const pluginPanelOpened = config.pluginPanelOpened !== undefined ? config.pluginPanelOpened : true;
    const customContentMapJson = config.customContentMap || null;

    // Helper function to create a legend item with reverse alphabetical letter
    function createLegendItem(layerName, index, total) {
        // Reverse alphabetical: first item gets highest letter, last item gets A
        var letter = String.fromCharCode(65 + ((total - 1 - index) % 26)); // B, A for 2 items; C, B, A for 3 items
        var div = document.createElement('div');
        div.className = 'legend-item data-menu-trigger';
        div.innerHTML = '<span class="legend-letter">' + letter + '</span><div class="legend-text">' + layerName + '</div>';
        return div;
    }

    // Viewer toolbar icon data URIs
    var VIEWER_TOOLBAR_ICONS = {
        home: 'bqplot:home',
        panZoom: 'data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBHZW5lcmF0b3I6IEFkb2JlIElsbHVzdHJhdG9yIDI3LjUuMCwgU1ZHIEV4cG9ydCBQbHVnLUluIC4gU1ZHIFZlcnNpb246IDYuMDAgQnVpbGQgMCkgIC0tPgo8c3ZnIHZlcnNpb249IjEuMSIgaWQ9IkxheWVyXzEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IgoJIHZpZXdCb3g9IjAgMCAyMi45IDIzIiBzdHlsZT0iZW5hYmxlLWJhY2tncm91bmQ6bmV3IDAgMCAyMi45IDIzOyIgeG1sOnNwYWNlPSJwcmVzZXJ2ZSI+CjxzdHlsZSB0eXBlPSJ0ZXh0L2NzcyI+Cgkuc3Qwe2ZpbGw6IzAxMDEwMTt9Cjwvc3R5bGU+Cjxwb2x5Z29uIGNsYXNzPSJzdDAiIHBvaW50cz0iMjAuMSwxMy4xIDIxLDEzLjEgMjEsMS45IDkuOSwxLjkgOS45LDMuMyA3LjksMy4zIDcuOSwwIDIyLjksMCAyMi45LDE1LjEgMjAuMSwxNS4xICIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMCwyMS4xTDEuOSwyM2w1LjgtNS43di0wLjZsMC44LTAuOGMxLjIsMC45LDIuNiwxLjMsNCwxLjNjMy43LDAsNi43LTMsNi43LTYuN3MtMy02LjctNi43LTYuN3MtNi43LDMtNi43LDYuNwoJYzAsMS40LDAuNSwyLjgsMS4zLDRsLTAuOCwwLjhINS44TDAsMjEuMXogTTEyLjQsMTUuMmMtMi42LDAtNC43LTIuMS00LjctNC43bDAsMGMwLTIuNiwyLjEtNC43LDQuNy00LjdjMi42LDAsNC43LDIuMSw0LjcsNC43CglTMTUsMTUuMiwxMi40LDE1LjJDMTIuNCwxNS4yLDEyLjQsMTUuMiwxMi40LDE1LjJ6Ii8+Cjwvc3ZnPgo=',
        rectROI: 'data:image/svg+xml;base64,PHN2ZyBpZD0iTGF5ZXJfMSIgZGF0YS1uYW1lPSJMYXllciAxIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNS40NiAyNS40NiI+PGRlZnM+PHN0eWxlPi5jbHMtMXtmaWxsOiMwMTAxMDE7fTwvc3R5bGU+PC9kZWZzPjx0aXRsZT52aXogbG9nb3MgW1JlY292ZXJlZF08L3RpdGxlPjxwb2x5bGluZSBjbGFzcz0iY2xzLTEiIHBvaW50cz0iMTEuNjcgMTMuNzMgMTEuNjcgMjEuNjMgMTAuMTMgMjAuMDkgOC43MiAyMS41MSAxMi42NyAyNS40NiAxNi42MiAyMS41MSAxNS4yMSAyMC4wOSAxMy42NyAyMS42MyAxMy42NyAxMy43MyIvPjxwb2x5bGluZSBjbGFzcz0iY2xzLTEiIHBvaW50cz0iMTMuNjcgMTMuNzMgMTMuNjcgMy44MyAxNS4yMSA1LjM2IDE2LjYyIDMuOTUgMTIuNjcgMCA4LjcyIDMuOTUgMTAuMTMgNS4zNiAxMS42NyAzLjgzIDExLjY3IDEzLjczIi8+PC9zdmc+',
        circROI: 'data:image/svg+xml;base64,PHN2ZyBpZD0iTGF5ZXJfMSIgZGF0YS1uYW1lPSJMYXllciAxIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMi43NiAyNCI+PGRlZnM+PHN0eWxlPi5jbHMtMXtmaWxsOiMyMzFmMjA7fTwvc3R5bGU+PC9kZWZzPjxyZWN0IGNsYXNzPSJjbHMtMSIgeD0iMS45NiIgeT0iMTYuMTUiIHdpZHRoPSIyLjk2IiBoZWlnaHQ9IjIuOTYiIHJ4PSIxLjQ4Ii8+PHJlY3QgY2xhc3M9ImNscy0xIiB4PSIxOCIgeT0iMTEuNzciIHdpZHRoPSIyLjk2IiBoZWlnaHQ9IjIuOTYiIHJ4PSIxLjQ4Ii8+PHBhdGggY2xhc3M9ImNscy0xIiBkPSJNNy4zMywwVjI0aDguMzNWMFptNC4yMiwxMGgwYTEuNDgsMS40OCwwLDAsMS0xLjQ4LTEuNDhoMEExLjQ4LDEuNDgsMCwwLDEsMTEuNTUsN2gwQTEuNDgsMS40OCwwLDAsMSwxMyw4LjUyaDBBMS40OCwxLjQ4LDAsMCwxLDExLjU1LDEwWiIvPjwvc3ZnPg=='
    };

    // Helper function to create a new viewer element
    function createViewerElement(viewerId) {
        var viewer = document.createElement('div');
        viewer.className = 'wireframe-viewer viewer-adding';
        viewer.dataset.viewerId = viewerId;
        viewer.innerHTML =
            '<div class="viewer-toolbar">' +
            '<div class="viewer-toolbar-spacer"></div>' +
            '<div class="viewer-toolbar-icon" data-icon="' + VIEWER_TOOLBAR_ICONS.home + '" title="Home"></div>' +
            '<div class="viewer-toolbar-icon" data-icon="' + VIEWER_TOOLBAR_ICONS.panZoom + '" title="Pan/Zoom"></div>' +
            '<div class="viewer-toolbar-icon" data-icon="' + VIEWER_TOOLBAR_ICONS.rectROI + '" title="Rectangular ROI"></div>' +
            '<div class="viewer-toolbar-icon" data-icon="' + VIEWER_TOOLBAR_ICONS.circROI + '" title="Circular ROI"></div>' +
            '</div>' +
            '<div class="viewer-content">' +
            '<div class="viewer-image-container"></div>' +
            '<span class="viewer-area-text">' + viewerId + '</span>' +
            '<div class="data-menu-legend"></div>' +
            '</div>';

        // Remove animation class after animation completes
        setTimeout(function() {
            viewer.classList.remove('viewer-adding');
        }, 300);

        return viewer;
    }

    // Helper function to generate Plot Options sidebar HTML
    function generatePlotOptionsHTML(selectedViewerId, selectedLayerIndex, selectedColor) {
        // Get all viewers from the viewer area
        var viewers = container.querySelectorAll('.wireframe-viewer');
        var viewerIds = [];
        viewers.forEach(function(v) {
            viewerIds.push(v.dataset.viewerId);
        });

        // Default to first viewer if none selected
        if (!selectedViewerId && viewerIds.length > 0) {
            selectedViewerId = viewerIds[0];
        }

        // Get layers from the selected viewer's legend
        var layers = [];
        if (selectedViewerId) {
            var viewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + selectedViewerId + '"]');
            if (viewer) {
                var legendItems = viewer.querySelectorAll('.legend-item');
                legendItems.forEach(function(item, index) {
                    var letter = String.fromCharCode(65 + (index % 26));
                    // Get color from legend-item-icon background-color
                    var icon = item.querySelector('.legend-item-icon');
                    var color = icon ? window.getComputedStyle(icon).backgroundColor : '#00FF00';
                    layers.push({ letter: letter, index: index, color: color });
                });
            }
        }

        // Default to first layer if none selected
        if (selectedLayerIndex === undefined && layers.length > 0) {
            selectedLayerIndex = 0;
        }

        // Default color
        if (!selectedColor) {
            selectedColor = '#00FF00';
        }

        var html = '';

        // Viewer dropdown
        html += '<div class="plot-options-viewer-select">';
        html += '<label>Viewer</label>';
        html += '<select class="plot-options-viewer-dropdown wireframe-select" id="plot-options-viewer">';
        if (viewerIds.length === 0) {
            html += '<option value="">No viewers available</option>';
        } else {
            viewerIds.forEach(function(id) {
                var selected = id === selectedViewerId ? ' selected' : '';
                html += '<option value="' + id + '"' + selected + '>' + id + '</option>';
            });
        }
        html += '</select>';
        html += '</div>';

        // Layer tabs (letters)
        if (layers.length > 0) {
            html += '<div class="plot-options-section-header">Layers</div>';
            html += '<div class="plot-options-layer-tabs" id="plot-options-layers">';
            layers.forEach(function(layer) {
                var active = layer.index === selectedLayerIndex ? ' active' : '';
                html += '<button class="plot-options-layer-tab' + active + '" data-layer-index="' + layer.index + '" data-layer-color="' + layer.color + '">' + layer.letter + '</button>';
            });
            html += '</div>';

            // Get selected layer's color for the color button
            var selectedLayerColor = selectedColor;
            if (layers[selectedLayerIndex]) {
                selectedLayerColor = layers[selectedLayerIndex].color;
            }

            // Color row
            html += '<div class="plot-options-color-row">';
            html += '<span class="plot-options-color-label">Color</span>';
            html += '<button class="plot-options-color-button" id="plot-options-color" style="background-color: ' + selectedLayerColor + ';" title="Click to change color"></button>';
            html += '</div>';

            // Placeholder inputs with expansion panel style bars
            html += '<div class="plot-options-section-header">Display</div>';
            html += '<div class="plot-options-input-row">';
            html += '<span class="plot-options-input-label">Opacity</span>';
            html += '<div class="plot-options-input-bar"></div>';
            html += '</div>';
            html += '<div class="plot-options-input-row">';
            html += '<span class="plot-options-input-label">Stretch</span>';
            html += '<div class="plot-options-input-bar"></div>';
            html += '</div>';
            html += '<div class="plot-options-input-row">';
            html += '<span class="plot-options-input-label">Contrast</span>';
            html += '<div class="plot-options-input-bar"></div>';
            html += '</div>';
        } else {
            html += '<div style="text-align: center; color: rgba(255,255,255,0.5); margin-top: 16px;">No layers in selected viewer</div>';
        }

        return html;
    }

    // Set up event handlers for Plot Options UI elements
    function setupPlotOptionsHandlers() {
        // Viewer dropdown change
        var viewerDropdown = container.querySelector('.plot-options-viewer-dropdown');
        if (viewerDropdown) {
            viewerDropdown.addEventListener('change', function(e) {
                stopAutoCycle();
                // Refresh the Plot Options UI for the selected viewer
                var contentDiv = container.querySelector('#sidebar-tab-content');
                if (contentDiv) {
                    var apiSnippet = sidebarContent_map['settings'].apiSnippets[0] || '';
                    contentDiv.innerHTML = apiSnippet + generatePlotOptionsHTML(this.value);
                    // Re-attach handlers
                    setupPlotOptionsHandlers();
                }
            });
        }

        // Layer tab clicks
        var layerTabs = container.querySelectorAll('.plot-options-layer-tab');
        layerTabs.forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                stopAutoCycle();
                // Update active state
                layerTabs.forEach(function(t) { t.classList.remove('active'); });
                tab.classList.add('active');

                // Could update the color button to reflect the layer's color
                var layerColor = tab.dataset.layerColor;
                var colorButton = container.querySelector('.plot-options-color-button');
                if (colorButton && layerColor) {
                    colorButton.style.backgroundColor = layerColor;
                }
            });
        });

        // Color button click (cycles through colors for demo)
        var colorButton = container.querySelector('.plot-options-color-button');
        if (colorButton) {
            colorButton.addEventListener('click', function(e) {
                stopAutoCycle();
                // Cycle through some demo colors
                var colors = ['#FF6D00', '#2979FF', '#00E676', '#FF1744', '#D500F9', '#FFEA00'];
                var currentColor = this.style.backgroundColor;
                var currentIndex = colors.findIndex(function(c) {
                    // Compare hex to rgb
                    var temp = document.createElement('div');
                    temp.style.color = c;
                    document.body.appendChild(temp);
                    var rgb = window.getComputedStyle(temp).color;
                    document.body.removeChild(temp);
                    return rgb === currentColor;
                });
                var nextIndex = (currentIndex + 1) % colors.length;
                this.style.backgroundColor = colors[nextIndex];

                // Update active layer tab color
                var activeTab = container.querySelector('.plot-options-layer-tab.active');
                if (activeTab) {
                    activeTab.dataset.layerColor = colors[nextIndex];
                }
            });
        }
    }

    // Execute viewer-add action: split a viewer and add a new one (or add first viewer)
    function executeViewerAdd(direction, newId, parentId) {
        var viewerArea = container.querySelector('.wireframe-viewer-area');
        if (!viewerArea) return;

        // Find the target viewer to split
        var targetViewer;
        if (parentId) {
            targetViewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + parentId + '"]');
        } else {
            // Default to the last viewer
            var viewers = container.querySelectorAll('.wireframe-viewer');
            targetViewer = viewers.length > 0 ? viewers[viewers.length - 1] : null;
        }

        // If no existing viewer, add the first viewer directly to the viewer area
        if (!targetViewer) {
            var newViewer = createViewerElement(newId);
            viewerArea.appendChild(newViewer);
            return;
        }

        var parent = targetViewer.parentNode;

        // Create split container
        var splitContainer = document.createElement('div');
        splitContainer.className = 'wireframe-viewer-split ' +
            (direction === 'horiz' || direction === 'h' || direction === 'horiz-before' || direction === 'hb'
                ? 'horizontal' : 'vertical');

        // Replace target with split container
        parent.insertBefore(splitContainer, targetViewer);

        // Move target into split
        splitContainer.appendChild(targetViewer);

        // Create new viewer
        var newViewer = createViewerElement(newId);

        // Add in correct position based on direction
        if (direction === 'horiz-before' || direction === 'hb' ||
            direction === 'vert-before' || direction === 'vb') {
            splitContainer.insertBefore(newViewer, targetViewer);
        } else {
            splitContainer.appendChild(newViewer);
        }
    }

    // Execute viewer-image action: set background image for a viewer
    function executeViewerImage(viewerId, imagePath) {
        var viewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + viewerId + '"]');
        if (!viewer) return;

        var content = viewer.querySelector('.viewer-content');
        var imageContainer = viewer.querySelector('.viewer-image-container');

        if (content && imageContainer) {
            if (imagePath) {
                content.classList.add('has-image');
                imageContainer.style.backgroundImage = 'url(' + imagePath + ')';
            } else {
                content.classList.remove('has-image');
                imageContainer.style.backgroundImage = '';
            }
        }
    }

    // Execute viewer-legend action: set legend layers for a viewer
    function executeViewerLegend(viewerId, layersString) {
        var viewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + viewerId + '"]');
        if (!viewer) return;

        var legend = viewer.querySelector('.data-menu-legend');
        if (!legend) return;

        // Clear existing legend items
        legend.innerHTML = '';

        // Add new legend items with reverse alphabetical letters
        var layers = layersString.split('|');
        var total = layers.filter(function(l) { return l.trim(); }).length;
        layers.forEach(function(layer, index) {
            var trimmedLayer = layer.trim();
            if (trimmedLayer) {
                legend.appendChild(createLegendItem(trimmedLayer, index, total));
            }
        });
    }

    // Execute viewer-focus action: visually emphasize a viewer
    function executeViewerFocus(viewerId) {
        // Remove focus from all viewers
        var viewers = container.querySelectorAll('.wireframe-viewer');
        viewers.forEach(function(v) {
            v.classList.remove('focused');
        });

        // Add focus to target viewer
        if (viewerId) {
            var viewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + viewerId + '"]');
            if (viewer) {
                viewer.classList.add('focused');
            }
        }
    }

    // Execute viewer-remove action: remove a viewer
    function executeViewerRemove(viewerId) {
        var viewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + viewerId + '"]');
        if (!viewer) return;

        var parent = viewer.parentNode;

        // Remove the viewer
        parent.removeChild(viewer);

        // If parent is a split container with only one child left, unwrap it
        if (parent.classList.contains('wireframe-viewer-split')) {
            var remainingChildren = parent.children;
            if (remainingChildren.length === 1) {
                var grandparent = parent.parentNode;
                var remaining = remainingChildren[0];
                grandparent.insertBefore(remaining, parent);
                grandparent.removeChild(parent);
            }
        }
    }

    // Execute viewer-open-data-menu action: click a legend item in the specified viewer to open data menu
    function executeViewerOpenDataMenu(viewerId) {
        // Find the trigger element
        var trigger = null;
        if (viewerId) {
            var viewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + viewerId + '"]');
            if (viewer) {
                trigger = viewer.querySelector('.data-menu-trigger');
            }
        }

        // If no specific viewer or no trigger found, find any legend item
        if (!trigger) {
            trigger = container.querySelector('.data-menu-trigger');
        }

        // Click the trigger to open data menu (uses event delegation handler)
        if (trigger) {
            trigger.click();
        }
    }

    // Execute viewer-tool-toggle action: toggle/activate a tool in a viewer's toolbar
    function executeViewerToolToggle(viewerId, toolName) {
        // Map tool names to icon keys
        var toolMap = {
            'home': VIEWER_TOOLBAR_ICONS.home,
            'panzoom': VIEWER_TOOLBAR_ICONS.panZoom,
            'pan-zoom': VIEWER_TOOLBAR_ICONS.panZoom,
            'pan_zoom': VIEWER_TOOLBAR_ICONS.panZoom,
            'rectroi': VIEWER_TOOLBAR_ICONS.rectROI,
            'rect-roi': VIEWER_TOOLBAR_ICONS.rectROI,
            'rect_roi': VIEWER_TOOLBAR_ICONS.rectROI,
            'rectangle': VIEWER_TOOLBAR_ICONS.rectROI,
            'circroi': VIEWER_TOOLBAR_ICONS.circROI,
            'circ-roi': VIEWER_TOOLBAR_ICONS.circROI,
            'circ_roi': VIEWER_TOOLBAR_ICONS.circROI,
            'circle': VIEWER_TOOLBAR_ICONS.circROI,
            'subset': VIEWER_TOOLBAR_ICONS.circROI  // alias for the circular ROI/subset tool
        };

        var viewer = container.querySelector('.wireframe-viewer[data-viewer-id="' + viewerId + '"]');
        if (!viewer) {
            // Try to find any viewer if the specified one doesn't exist
            viewer = container.querySelector('.wireframe-viewer');
        }
        if (!viewer) return null;

        var iconValue = toolMap[toolName.toLowerCase()];
        if (!iconValue) {
            console.warn('Unknown tool name:', toolName);
            return null;
        }

        // Find the toolbar icon with this data-icon value
        var toolIcon = viewer.querySelector('.viewer-toolbar-icon[data-icon="' + iconValue + '"]');
        if (toolIcon) {
            // Check if already active - if so, toggle it off
            if (toolIcon.classList.contains('active')) {
                toolIcon.classList.remove('active');
            } else {
                // Remove active from all icons in this viewer's toolbar
                var allIcons = viewer.querySelectorAll('.viewer-toolbar-icon');
                allIcons.forEach(function(icon) {
                    icon.classList.remove('active');
                });
                // Add active to the selected tool
                toolIcon.classList.add('active');
            }
            return toolIcon;
        }
        return null;
    }

    // Parse custom content map from JSON
    let customContentMap = {};
    if (customContentMapJson) {
        try {
            customContentMap = JSON.parse(customContentMapJson);
        } catch (e) {
            console.error('Failed to parse customContentMap:', e);
        }
    }

    // Helper function to parse sequence (initial or demo)
    function parseSequence(sequenceArray) {
        const sequence = [];
        if (!sequenceArray) return sequence;

        sequenceArray.forEach(function(item) {
            let delay = 2000; // Default delay
            let noHighlight = false; // Flag to skip highlighting
            let workingItem = item;

            // Check for timing syntax: sidebar@1000:action or sidebar@1000!:action (! = no highlight)
            if (item.includes('@')) {
                const atIndex = item.indexOf('@');
                const beforeAt = item.substring(0, atIndex);
                const afterAt = item.substring(atIndex + 1);

                // Extract delay (number before next : or end of string)
                const colonAfterAt = afterAt.indexOf(':');
                if (colonAfterAt !== -1) {
                    let delayPart = afterAt.substring(0, colonAfterAt);
                    // Check for ! suffix on delay (no highlight)
                    if (delayPart.endsWith('!')) {
                        noHighlight = true;
                        delayPart = delayPart.slice(0, -1);
                    }
                    delay = parseInt(delayPart, 10);
                    workingItem = beforeAt + afterAt.substring(colonAfterAt);
                } else {
                    let delayPart = afterAt;
                    if (delayPart.endsWith('!')) {
                        noHighlight = true;
                        delayPart = delayPart.slice(0, -1);
                    }
                    delay = parseInt(delayPart, 10);
                    workingItem = beforeAt;
                }
            }

            // Check if item contains action syntax (sidebar:action or sidebar:action=value)
            if (workingItem.includes(':')) {
                const colonIndex = workingItem.indexOf(':');
                const sidebar = workingItem.substring(0, colonIndex);
                const actionPart = workingItem.substring(colonIndex + 1);

                // Special handling for viewer-* actions: everything after sidebar goes into value
                if (sidebar.indexOf('viewer-') === 0) {
                    sequence.push({
                        sidebar: sidebar,
                        action: null,
                        value: actionPart,
                        delay: delay,
                        noHighlight: noHighlight
                    });
                } else if (actionPart.includes('=')) {
                    // Check if action has a value
                    const equalsIndex = actionPart.indexOf('=');
                    const action = actionPart.substring(0, equalsIndex);
                    const value = actionPart.substring(equalsIndex + 1);
                    sequence.push({
                        sidebar: sidebar,
                        action: action,
                        value: value,
                        delay: delay,
                        noHighlight: noHighlight
                    });
                } else {
                    sequence.push({
                        sidebar: sidebar,
                        action: actionPart,
                        delay: delay,
                        noHighlight: noHighlight
                    });
                }
            } else {
                // Simple sidebar activation
                sequence.push({
                    sidebar: workingItem,
                    action: 'show',
                    delay: delay,
                    noHighlight: noHighlight
                });
            }
        });
        return sequence;
    }

    // Parse demo sequence - can be simple list or actions with optional timing
    // Format: sidebar@delay:action=value or sidebar:action=value or sidebar
    let demoSequence = parseSequence(customDemo);
    let initialSequence = parseSequence(initialState);

    const sidebarOrder = demoSequence.length > 0 ? demoSequence.map(s => s.sidebar) : ['loaders', 'save', 'settings', 'info', 'plugins', 'subsets'];

    // Auto-cycling state
    let autoCycling = true;
    let cycleInterval = null;
    let currentCycleIndex = 0;
    let currentHighlightedElements = [];

    // Helper function to create API snippet with proper link/button based on showScrollTo
    function createApiSnippet(code) {
        if (showScrollTo) {
            return '<div class="api-snippet-container"><pre class="api-snippet">' + code + '</pre><button class="api-learn-more" data-scroll-target="grid-userapi">Learn about API access</button></div>';
        } else {
            return '<div class="api-snippet-container"><pre class="api-snippet">' + code + '</pre><a class="api-learn-more" href="../userapi/index.html">Learn about API access</a></div>';
        }
    }

    // Helper function to briefly highlight an element during demo
    function briefHighlight(element, stepDelay) {
        if (!element) return;
        const duration = Math.min(1000, (stepDelay || 2000) / 2);
        element.classList.add('highlighted');
        setTimeout(function() {
            element.classList.remove('highlighted');
        }, duration);
    }

    // Build plugins content dynamically based on configuration
    const pluginsPanelClass = pluginPanelOpened ? 'expansion-panel expanded' : 'expansion-panel';
    const pluginsContentClass = pluginPanelOpened ? 'expansion-panel-content expanded' : 'expansion-panel-content';
    const pluginsContent = customContentMap.plugins && customContentMap.plugins.main
        ? customContentMap.plugins.main
        : '{{ descriptions.plugins|capitalize }}.';

    // Build API snippet for plugin with actual plugin name
    const pluginApiSnippet = createApiSnippet('plg = jd.plugins[\'' + pluginName + '\']');

    const pluginsSidebarHTML = '<div class="expansion-panels">' +
        '<div class="' + pluginsPanelClass + '" data-panel-index="0">' +
        '<div class="expansion-panel-header">' +
        '<span class="expansion-panel-title">' + pluginName + '</span>' +
        '<span class="expansion-panel-arrow">▼</span>' +
        '</div>' +
        '<div class="' + pluginsContentClass + '">' +
        pluginApiSnippet +
        pluginsContent +
        '</div>' +
        '</div>' +
        '<div class="expansion-panel disabled" data-panel-index="1">' +
        '<div class="expansion-panel-header">' +
        '<div class="expansion-panel-placeholder"></div>' +
        '</div>' +
        '</div>' +
        '<div class="expansion-panel disabled" data-panel-index="2">' +
        '<div class="expansion-panel-header">' +
        '<div class="expansion-panel-placeholder"></div>' +
        '</div>' +
        '</div>' +
        '<div class="expansion-panel disabled" data-panel-index="3">' +
        '<div class="expansion-panel-header">' +
        '<div class="expansion-panel-placeholder"></div>' +
        '</div>' +
        '</div>' +
        '<div class="expansion-panel disabled" data-panel-index="4">' +
        '<div class="expansion-panel-header">' +
        '<div class="expansion-panel-placeholder"></div>' +
        '</div>' +
        '</div>' +
        '</div>';

    function stopAutoCycle() {
        if (autoCycling) {
            autoCycling = false;
            if (cycleInterval) {
                clearInterval(cycleInterval);
                cycleInterval = null;
            }
            updateCycleControlButton();
        }
    }

    function updateCycleControlButton() {
        const cycleIconPause = container.querySelector('.cycle-icon-pause');
        const cycleIconRestart = container.querySelector('.cycle-icon-restart');

        if (autoCycling) {
            // Show PAUSE icon when cycling (action that will be taken)
            if (cycleIconPause) cycleIconPause.classList.remove('hidden');
            if (cycleIconRestart) cycleIconRestart.classList.add('hidden');
        } else {
            // Show RESTART icon when stopped (action that will be taken)
            if (cycleIconRestart) cycleIconRestart.classList.remove('hidden');
            if (cycleIconPause) cycleIconPause.classList.add('hidden');
        }
    }

    // Reset demo state to initial - called when looping or manually restarting
    function resetDemoState() {
        // Clear highlights
        currentHighlightedElements.forEach(function(el) {
            el.classList.remove('highlighted');
        });
        currentHighlightedElements = [];

        // Reset API mode if active
        if (apiModeActive) {
            const apiButton = container.querySelector('.api-button');
            if (apiButton) {
                apiButton.click();
            }
        }

        // Remove all viewers and split containers from the viewer area (but keep the data-menu-popup)
        var viewerArea = container.querySelector('.wireframe-viewer-area');
        if (viewerArea) {
            // Remove split containers first (they contain viewers)
            var splits = viewerArea.querySelectorAll('.wireframe-viewer-split');
            splits.forEach(function(split) {
                split.remove();
            });
            // Remove any remaining viewers not in splits
            var viewers = viewerArea.querySelectorAll('.wireframe-viewer');
            viewers.forEach(function(viewer) {
                viewer.remove();
            });
        }

        // Close the data menu popup if open
        var dataMenuPopup = container.querySelector('#data-menu-popup');
        if (dataMenuPopup) {
            dataMenuPopup.classList.remove('visible');
        }

        // Close any open sidebar
        if (currentSidebar) {
            wireframeSidebar.classList.remove('visible');
            wireframeIcons.forEach(function(icon) {
                if (!icon.classList.contains('api-button')) {
                    icon.classList.remove('active');
                }
            });
            currentSidebar = null;
        }

        // Reset all form inputs
        const inputs = container.querySelectorAll('.wireframe-input');
        inputs.forEach(function(input) {
            input.value = '';
        });

        // Reset all checkboxes
        const checkboxes = container.querySelectorAll('.wireframe-checkbox');
        checkboxes.forEach(function(checkbox) {
            checkbox.checked = false;
        });

        // Reset all dropdowns to first option
        const selects = container.querySelectorAll('.wireframe-select');
        selects.forEach(function(select) {
            select.selectedIndex = 0;
        });

        // Reset cycle index
        currentCycleIndex = 0;
    }

    function restartAutoCycle() {
        // Stop any existing cycle
        if (cycleInterval) {
            clearInterval(cycleInterval);
            cycleInterval = null;
        }

        // Reset all demo state
        resetDemoState();

        // Apply initial state if provided
        if (initialSequence && initialSequence.length > 0) {
            applyInitialState();
            // After initial state completes, start demo immediately (manual restart)
            setTimeout(function() {
                autoCycling = true;
                currentCycleIndex = 0;
                hasStartedCycling = true;
                updateCycleControlButton();
                autoCycleSidebars();
            }, 1000);
        } else {
            // No initial state, start demo immediately (manual restart)
            autoCycling = true;
            currentCycleIndex = 0;
            hasStartedCycling = true;
            updateCycleControlButton();
            autoCycleSidebars();
        }
    }

    // Apply initial state sequence
    function applyInitialState() {
        if (!initialSequence || initialSequence.length === 0) return;

        // Apply all initial steps synchronously (no delays for initial state)
        for (var i = 0; i < initialSequence.length; i++) {
            var step = initialSequence[i];
            var sidebarType = step.sidebar;
            var action = step.action;
            var value = step.value;

            // Check if this is a viewer action
            if (sidebarType && sidebarType.indexOf('viewer-') === 0) {
                var viewerAction = sidebarType;
                var params = value ? value.split(':') : [];

                if (viewerAction === 'viewer-add') {
                    var direction = params[0] || 'horiz';
                    var newId = params[1] || 'viewer-' + Date.now();
                    var parentId = params[2] || null;
                    executeViewerAdd(direction, newId, parentId);
                } else if (viewerAction === 'viewer-image') {
                    var viewerId = params[0] || 'default';
                    var imagePath = params.slice(1).join(':');
                    executeViewerImage(viewerId, imagePath);
                } else if (viewerAction === 'viewer-legend') {
                    var viewerId = params[0] || 'default';
                    var layersString = params.slice(1).join(':');
                    executeViewerLegend(viewerId, layersString);
                } else if (viewerAction === 'viewer-focus') {
                    var viewerId = params[0] || null;
                    executeViewerFocus(viewerId);
                } else if (viewerAction === 'viewer-remove') {
                    var viewerId = params[0];
                    if (viewerId) {
                        executeViewerRemove(viewerId);
                    }
                } else if (viewerAction === 'viewer-open-data-menu') {
                    var viewerId = params[0] || null;
                    executeViewerOpenDataMenu(viewerId);
                } else if (viewerAction === 'viewer-tool-toggle') {
                    var viewerId = params[0];
                    var toolName = params[1];
                    if (viewerId && toolName) {
                        executeViewerToolToggle(viewerId, toolName);
                    }
                }
            } else if (action === 'show' || action === 'select-tab') {
                // Activate the sidebar
                if (action === 'select-tab' && value) {
                    // Find tab index by name
                    var data = sidebarContent_map[sidebarType];
                    if (data && data.tabs) {
                        var tabIndex = data.tabs.findIndex(function(t) { return t === value; });
                        if (tabIndex !== -1) {
                            activateSidebar(sidebarType, tabIndex);
                        } else {
                            activateSidebar(sidebarType);
                        }
                    } else {
                        activateSidebar(sidebarType);
                    }
                } else {
                    activateSidebar(sidebarType);
                }
            } else if (action === 'select-viewer' && sidebarType === 'settings') {
                // Select a viewer in Plot Options dropdown
                var viewerDropdown = container.querySelector('.plot-options-viewer-dropdown');
                if (viewerDropdown && value) {
                    viewerDropdown.value = value;
                    // Trigger change event to update layers
                    viewerDropdown.dispatchEvent(new Event('change'));
                }
            } else if (action === 'select-layer' && sidebarType === 'settings') {
                // Select a layer tab in Plot Options
                var layerIndex = parseInt(value) || 0;
                var layerTabs = container.querySelectorAll('.plot-options-layer-tab');
                if (layerTabs[layerIndex]) {
                    layerTabs.forEach(function(t) { t.classList.remove('active'); });
                    layerTabs[layerIndex].classList.add('active');
                    // Update color button to match layer color
                    var layerColor = layerTabs[layerIndex].dataset.layerColor;
                    var colorButton = container.querySelector('.plot-options-color-button');
                    if (colorButton && layerColor) {
                        colorButton.style.backgroundColor = layerColor;
                    }
                }
            } else if (action === 'set-color' && sidebarType === 'settings') {
                // Set color in Plot Options
                var colorButton = container.querySelector('.plot-options-color-button');
                if (colorButton && value) {
                    colorButton.style.backgroundColor = value;
                    // Update active layer tab's color
                    var activeTab = container.querySelector('.plot-options-layer-tab.active');
                    if (activeTab) {
                        activeTab.dataset.layerColor = value;
                    }
                }
            }
        }
    }

    // Extract dropdown options from grid items
    function extractDropdownOptions() {
        const options = {
            sources: [],
            formats: [],
            viewerTypes: []
        };

        // Find the loaders grid item on the page (has two-column layout with Sources and Formats)
        const loadersGrid = document.querySelector('[data-grid-id="grid-loaders"]');
        if (loadersGrid) {
            const columnContents = loadersGrid.querySelectorAll('.column-content');

            // First column should be sources, second should be formats
            if (columnContents.length >= 2) {
                // Extract sources from first column (lowercase for consistency)
                const sourceLinks = columnContents[0].querySelectorAll('.grid-item-link');
                sourceLinks.forEach(function(link) {
                    options.sources.push(link.textContent.trim().toLowerCase());
                });

                // Extract formats from second column
                const formatLinks = columnContents[1].querySelectorAll('.grid-item-link');
                formatLinks.forEach(function(link) {
                    options.formats.push(link.textContent.trim());
                });
            }
        }

        // Find viewers grid item on the page
        const viewersGrid = document.querySelector('[data-grid-id="grid-viewers"]');
        if (viewersGrid) {
            const links = viewersGrid.querySelectorAll('.grid-item-link');
            links.forEach(function(link) {
                options.viewerTypes.push(link.textContent.trim());
            });
        }

        return options;
    }

    // Populate dropdowns dynamically
    const dropdownOptions = extractDropdownOptions();

    // Handle description toggle
    const descToggle = container.querySelector('#description-toggle');
    const descMore = container.querySelector('#description-more');

    if (descToggle && descMore) {
        descToggle.addEventListener('click', function() {
            stopAutoCycle();
            descMore.classList.toggle('expanded');
            descToggle.textContent = descMore.classList.contains('expanded') ? 'Show Less' : 'Show More';
        });
    }

    // Handle wireframe toolbar interactions - scoped to container
    const wireframeIcons = container.querySelectorAll('.wireframe-toolbar-icon, .api-button');
    const wireframeSidebar = container.querySelector('.wireframe-sidebar');

    // SVG icon data (embedded directly as background-image) - matching grid item icons
    const iconSvgs = {
        'play': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M8,5.14V19.14L19,12.14L8,5.14Z\" /></svg>')",
        'pause': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M14,19H18V5H14M6,19H10V5H6V19Z\" /></svg>')",
        'restart': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M12,4C14.1,4 16.1,4.8 17.6,6.3C20.7,9.4 20.7,14.5 17.6,17.6C15.8,19.5 13.3,20.2 10.9,19.9L11.4,17.9C13.1,18.1 14.9,17.5 16.2,16.2C18.5,13.9 18.5,10.1 16.2,7.7C15.1,6.6 13.5,6 12,6V10.6L7,5.6L12,0.6V4M6.3,17.6C3.7,15 3.3,11 5.1,7.9L6.6,9.4C5.5,11.6 5.9,14.4 7.8,16.2C8.3,16.7 8.9,17.1 9.6,17.4L9,19.4C8,19 7.1,18.4 6.3,17.6Z\" /></svg>')",
        'database-import': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M19,19V5H5V19H19M19,3A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5A2,2 0 0,1 3,19V5C3,3.89 3.9,3 5,3H19M11,7H13V11H17V13H13V17H11V13H7V11H11V7Z\" /></svg>')",
        'download': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z\" /></svg>')",
        'tune': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z\" /></svg>')",
        'information': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z\" /></svg>')",
        'wrench': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M8 13C6.14 13 4.59 14.28 4.14 16H2V18H4.14C4.59 19.72 6.14 21 8 21S11.41 19.72 11.86 18H22V16H11.86C11.41 14.28 9.86 13 8 13M8 19C6.9 19 6 18.1 6 17C6 15.9 6.9 15 8 15S10 15.9 10 17C10 18.1 9.1 19 8 19M19.86 6C19.41 4.28 17.86 3 16 3S12.59 4.28 12.14 6H2V8H12.14C12.59 9.72 14.14 11 16 11S19.41 9.72 19.86 8H22V6H19.86M16 9C14.9 9 14 8.1 14 7C14 5.9 14.9 5 16 5S18 5.9 18 7C18 8.1 17.1 9 16 9Z\" /></svg>')",
        'selection': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M2 2H8V4H4V8H2V2M2 16H4V20H8V22H2V16M16 2H22V8H20V4H16V2M20 16H22V22H16V20H20V16Z\" /></svg>')",
        'help-circle': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M15.07,11.25L14.17,12.17C13.45,12.89 13,13.5 13,15H11V14.5C11,13.39 11.45,12.39 12.17,11.67L13.41,10.41C13.78,10.05 14,9.55 14,9C14,7.89 13.1,7 12,7A2,2 0 0,0 10,9H8A4,4 0 0,1 12,5A4,4 0 0,1 16,9C16,9.88 15.64,10.67 15.07,11.25M13,19H11V17H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12C22,6.47 17.5,2 12,2Z\" /></svg>')",
        'auto-fix': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M7.5,5.6L5,7L6.4,4.5L5,2L7.5,3.4L10,2L8.6,4.5L10,7L7.5,5.6M19.5,15.4L22,14L20.6,16.5L22,19L19.5,17.6L17,19L18.4,16.5L17,14L19.5,15.4M22,2L20.6,4.5L22,7L19.5,5.6L17,7L18.4,4.5L17,2L19.5,3.4L22,2M13.34,12.78L15.78,10.34L13.66,8.22L11.22,10.66L13.34,12.78M14.37,7.29L16.71,9.63C17.1,10 17.1,10.65 16.71,11.04L5.04,22.71C4.65,23.1 4,23.1 3.63,22.71L1.29,20.37C0.9,20 0.9,19.35 1.29,18.96L12.96,7.29C13.35,6.9 14,6.9 14.37,7.29Z\" /></svg>')",
        'api': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 67 47\"><g><path fill=\"white\" d=\"M11.6,19.5c0-.3,0-.7,0-1.1,2.1-1.1,4.3-1.7,6.6-1.7s4.1.4,5.1,1.3c1,.9,1.5,2.4,1.5,4.5v7.1c.8.2,1.4.3,1.8.6v2.9c-1.1.5-2.7.8-4.8.8-.2-.6-.4-1.3-.6-2.1-1,1.4-2.7,2.1-5.2,2.1s-2.8-.4-3.8-1.3-1.6-2-1.6-3.5.5-2.7,1.5-3.5c1-.9,2.5-1.3,4.4-1.3h3.6v-1.6c0-1.7-.9-2.6-2.8-2.6s-1.3,0-1.7.2c0,.9-.2,1.6-.4,2.2h-3.3c-.4-.8-.6-1.8-.6-3ZM17.6,30.5c1.1,0,2-.3,2.7-1v-2.7h-2.3c-1.6,0-2.4.6-2.4,1.8s.2,1,.5,1.4c.3.4.8.5,1.5.5Z\"/><path fill=\"white\" d=\"M27.9,17c1.2-.3,2.3-.4,3.3-.4s1.8,0,2.4,0v1.6c1.5-1,3.1-1.6,4.7-1.6s3.8.6,4.8,1.9c1,1.3,1.5,3.4,1.5,6.3s-.2,3-.7,4.1c-.5,1.2-1.1,2.1-1.9,2.8-1.5,1.3-3.3,2-5.4,2s-1.8,0-2.6-.3v2.9c1.3.4,2.1.8,2.5,1.2l-.3,2.6h-8.3l-.3-2.6c.3-.4.9-.8,1.8-1.1v-15.9c-.8-.3-1.4-.6-1.8-1.1l.3-2.6ZM36.3,30.5c1.1,0,2-.5,2.6-1.5.6-1,1-2.3,1-4.1s-.2-2.9-.5-3.6c-.4-.6-1-1-1.9-1-1.4,0-2.5.3-3.4,1v8.8c.7.2,1.4.3,2.3.3Z\"/><path fill=\"white\" d=\"M46.8,17c1.2-.3,2.4-.4,3.5-.4s2,0,2.7,0v13.2c.9.3,1.5.7,1.8,1.1l-.3,2.6h-7.6l-.3-2.6c.3-.4.9-.8,1.8-1.1v-9.2c-.8-.3-1.4-.6-1.8-1.1l.3-2.6ZM50.6,14.7c-1.8,0-2.8-.8-2.8-2.5s.9-2.5,2.8-2.5,2.8.8,2.8,2.5-.9,2.5-2.8,2.5Z\"/></g></svg>')"
    };

    // Apply SVG backgrounds to icons
    wireframeIcons.forEach(function(icon) {
        const iconName = icon.dataset.icon;
        if (iconName && iconSvgs[iconName]) {
            icon.style.backgroundImage = iconSvgs[iconName];
        }
    });

    // Apply SVG backgrounds to cycle control icons
    const cycleIconPause = container.querySelector('.cycle-icon-pause');
    const cycleIconRestart = container.querySelector('.cycle-icon-restart');

    if (cycleIconPause) cycleIconPause.style.backgroundImage = iconSvgs['pause'];
    if (cycleIconRestart) cycleIconRestart.style.backgroundImage = iconSvgs['restart'];

    // Handle search bar click - trigger Sphinx search
    const wireframeSearchInput = container.querySelector('#wireframe-search-input');
    if (wireframeSearchInput) {
        wireframeSearchInput.addEventListener('click', function() {
            stopAutoCycle();
            // Try multiple selectors to find the Sphinx search trigger
            const searchButton = document.querySelector('button.search-button, .search-button, button[aria-label="Search"], button[data-bs-toggle="search"]');
            if (searchButton) {
                searchButton.click();
            } else {
                // If no button found, try to focus the search input field
                const searchInput = document.querySelector('input[type="search"], input.search-input, #searchbox input');
                if (searchInput) {
                    searchInput.focus();
                }
            }
        });
    }

    const sidebarContent_map = {
        'loaders': {
            tabs: ['Data', 'Viewer'],
            content: [
                '{{ descriptions.loaders|capitalize }}.<br>' +
                '<div class="wireframe-form-group">' +
                '<label class="wireframe-form-label">Source</label>' +
                '<select class="wireframe-select" id="source-select"></select>' +
                '</div>' +
                '<div class="wireframe-form-group">' +
                '<label class="wireframe-form-label">Format</label>' +
                '<select class="wireframe-select" id="format-select"></select>' +
                '</div>' +
                '<button class="wireframe-button">Load</button>',
                '{{ descriptions.viewers|capitalize }}.<br>' +
                '<div class="wireframe-form-group">' +
                '<label class="wireframe-form-label">Viewer Type</label>' +
                '<select class="wireframe-select" id="viewer-type-select"></select>' +
                '</div>' +
                '<button class="wireframe-button">Create Viewer</button>'
            ],
            apiSnippets: [
                createApiSnippet('ldr = jd.loaders[\'<i>source</i>\']\nldr.load()'),
                createApiSnippet('vc = jd.new_viewers[\'<i>viewer_type</i>\']\nvc()')
            ],
            learnMore: [
                { text: 'Learn more about data import →', target: 'grid-loaders' },
                { text: 'Explore viewer options →', target: 'grid-loaders' }
            ],
            scrollId: 'grid-loaders'
        },
        'save': {
            tabs: null,
            content: '{{ descriptions.export|capitalize }}.',
            apiSnippet: createApiSnippet('plg = jd.plugins[\'Export\']'),
            learnMore: { text: 'See export options →', target: 'grid-export' },
            scrollId: 'grid-export'
        },
        'settings': {
            tabs: ['Plot Options', 'Units'],
            content: [
                'dynamic:plot-options',  // Special marker for dynamic content
                '{{ descriptions.settings_units }}'
            ],
            apiSnippets: [
                createApiSnippet('plg = jd.plugins[\'Plot Options\']'),
                createApiSnippet('plg = jd.plugins[\'Display Units\']')
            ],
            learnMore: [
                { text: 'View plot customization →', target: 'grid-settings' },
                { text: 'Learn about units →', target: 'grid-settings' }
            ],
            scrollId: 'grid-settings'
        },
        'info': {
            tabs: ['Metadata', 'Markers', 'Logger'],
            content: [
                '{{ descriptions.info_metadata }}',
                '{{ descriptions.info_markers|capitalize }}.',
                '{{ descriptions.info_logger }}'
            ],
            apiSnippets: [
                createApiSnippet('plg = jd.plugins[\'Metadata\']'),
                createApiSnippet('plg = jd.plugins[\'Plot Options\']\nplg.export_table()'),
                createApiSnippet('plg = jd.plugins[\'Logger\']\nplg.history')
            ],
            learnMore: [
                { text: 'Explore metadata tools →', target: 'grid-info' },
                { text: 'Learn about markers →', target: 'grid-info' },
                { text: 'View logging options →', target: 'grid-info' }
            ],
            scrollId: 'grid-info'
        },
        'plugins': {
            tabs: null,
            content: pluginsSidebarHTML,
            apiSnippet: createApiSnippet('plg = jd.plugins[\'' + pluginName + '\']'),
            learnMore: { text: 'Browse analysis plugins →', target: 'grid-plugins' },
            scrollId: 'grid-plugins'
        },
        'subsets': {
            tabs: null,
            content: '{{ descriptions.subsets|capitalize }}.',
            apiSnippet: createApiSnippet('plg = jd.plugins[\'Subset Tools\']'),
            learnMore: { text: 'Learn about subsets →', target: 'grid-subsets' },
            scrollId: 'grid-subsets'
        },
        'help': {
            tabs: null,
            content: 'Access documentation, tutorials, API reference, and interactive help. Links to user guides, example notebooks, and the jdaviz community support forum.',
            scrollId: null
        }
    };

    let currentSidebar = null;
    let apiModeActive = false;

    // Show the API toggle button (it's hidden by default in HTML) and apply its icon
    const apiButton = container.querySelector('.api-button');
    if (apiButton) {
        apiButton.style.display = 'block';
        const iconName = apiButton.dataset.icon;
        if (iconName && iconSvgs[iconName]) {
            apiButton.style.backgroundImage = iconSvgs[iconName];
        }
    }

    // Helper function to update Jupyter cell API snippet
    function updateJupyterApiSnippet(data, tabIndex) {
        if (!apiModeActive) return;

        const jupyterApiSnippet = container.querySelector('#jupyter-api-snippet');
        const jupyterApiContent = container.querySelector('#jupyter-api-snippet-content');

        if (!jupyterApiSnippet || !jupyterApiContent) return;

        let apiText = '';

        if (data.apiSnippets && tabIndex !== undefined) {
            // Multi-tab sidebar
            const apiHtml = data.apiSnippets[tabIndex];
            if (apiHtml) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = apiHtml;
                const preElement = tempDiv.querySelector('pre.api-snippet');
                if (preElement) {
                    apiText = preElement.textContent;
                }
            }
        } else if (data.apiSnippet) {
            // Single content sidebar
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = data.apiSnippet;
            const preElement = tempDiv.querySelector('pre.api-snippet');
            if (preElement) {
                apiText = preElement.textContent;
            }
        }

        jupyterApiContent.textContent = apiText || '# No API snippet available for this section';
    }

    function activateSidebar(sidebarType, tabIndex) {
        const icon = container.querySelector('.wireframe-toolbar-icon[data-sidebar="' + sidebarType + '"]');

        if (!icon) return;

        // Remove active from all icons (except API button)
        wireframeIcons.forEach(function(i) {
            if (!i.classList.contains('api-button')) {
                i.classList.remove('active');
            }
        });

        // Update sidebar content
        if (sidebarContent_map[sidebarType]) {
            const data = sidebarContent_map[sidebarType];

            // Clear and rebuild sidebar with tabs as header (if available) or just content
            let sidebarHtml = '';

            if (data.tabs) {
                const activeIndex = tabIndex !== undefined ? tabIndex : 0;

                // Build tabs
                sidebarHtml += '<div class="wireframe-sidebar-tabs">' +
                    data.tabs.map((tab, i) =>
                        '<button class="wireframe-sidebar-tab' + (i === activeIndex ? ' active' : '') + '" data-tab-index="' + i + '">' + tab + '</button>'
                    ).join('') +
                    '</div>';

                // Start sidebar body wrapper
                sidebarHtml += '<div class="wireframe-sidebar-body">';

                // Build content with API snippet before content if available
                const apiSnippet = data.apiSnippets && data.apiSnippets[activeIndex] ? data.apiSnippets[activeIndex] : '';
                let contentHtml = data.content[activeIndex];

                // Check for dynamic content markers
                if (contentHtml === 'dynamic:plot-options') {
                    contentHtml = generatePlotOptionsHTML();
                }

                sidebarHtml += '<div class="wireframe-sidebar-content" id="sidebar-tab-content">' + apiSnippet + contentHtml + '</div>';

                // Build footer with learn more button
                const learnMoreData = data.learnMore && data.learnMore[activeIndex] ? data.learnMore[activeIndex] : null;
                if (learnMoreData && showScrollTo) {
                    sidebarHtml += '<div class="wireframe-sidebar-footer">' +
                        '<button class="wireframe-sidebar-footer-button" data-scroll-target="' + learnMoreData.target + '">' + learnMoreData.text + '</button>' +
                        '</div>';
                }

                // Close sidebar body wrapper
                sidebarHtml += '</div>';

                // Set all HTML at once
                wireframeSidebar.innerHTML = sidebarHtml;

                // Update Jupyter cell API snippet
                updateJupyterApiSnippet(data, activeIndex);

                // Add click handlers to tabs
                const tabs = wireframeSidebar.querySelectorAll('.wireframe-sidebar-tab');
                tabs.forEach(function(tab) {
                    tab.addEventListener('click', function(e) {
                        // Only stop auto-cycle for real user clicks, not programmatic demo clicks
                        if (e.isTrusted) {
                            stopAutoCycle();
                        }
                        const tabIndex = parseInt(tab.dataset.tabIndex);

                        // Update active state
                        tabs.forEach(t => t.classList.remove('active'));
                        tab.classList.add('active');

                        // Update content
                        const contentDiv = container.querySelector('#sidebar-tab-content');
                        if (contentDiv && data.content[tabIndex]) {
                            const apiSnippet = data.apiSnippets && data.apiSnippets[tabIndex] ? data.apiSnippets[tabIndex] : '';
                            let contentHtml = data.content[tabIndex];

                            // Check for dynamic content markers
                            if (contentHtml === 'dynamic:plot-options') {
                                contentHtml = generatePlotOptionsHTML();
                            }

                            contentDiv.innerHTML = apiSnippet + contentHtml;

                            // Update footer learn more button
                            const footerButton = wireframeSidebar.querySelector('.wireframe-sidebar-footer-button');
                            const learnMoreData = data.learnMore && data.learnMore[tabIndex] ? data.learnMore[tabIndex] : null;
                            if (footerButton && learnMoreData) {
                                footerButton.textContent = learnMoreData.text;
                                footerButton.setAttribute('data-scroll-target', learnMoreData.target);
                            }

                            // Repopulate dropdowns for loaders sidebar
                            if (sidebarType === 'loaders') {
                                setTimeout(function() {
                                    const sourceSelect = container.querySelector('#source-select');
                                    const formatSelect = container.querySelector('#format-select');
                                    const viewerTypeSelect = container.querySelector('#viewer-type-select');

                                    // Populate source dropdown (only if empty - not populated from registry)
                                    if (sourceSelect && sourceSelect.options.length === 0) {
                                        if (dropdownOptions.sources.length > 0) {
                                            sourceSelect.innerHTML = dropdownOptions.sources.map(function(source) {
                                                return '<option>' + source + '</option>';
                                            }).join('');
                                        } else {
                                            sourceSelect.innerHTML = '<option>file</option><option>file drop</option><option>url</option><option>object</option><option>astroquery</option><option>virtual observatory</option>';
                                        }
                                    }

                                    // Populate format dropdown (only if empty - not populated from registry)
                                    if (formatSelect && formatSelect.options.length === 0) {
                                        if (dropdownOptions.formats.length > 0) {
                                            formatSelect.innerHTML = dropdownOptions.formats.map(function(format) {
                                                return '<option>' + format + '</option>';
                                            }).join('');
                                        } else {
                                            formatSelect.innerHTML = '<option>1D Spectrum</option><option>2D Spectrum</option>';
                                        }
                                    }

                                    // Populate viewer type dropdown (only if empty - not populated from registry)
                                    if (viewerTypeSelect && viewerTypeSelect.options.length === 0) {
                                        if (dropdownOptions.viewerTypes.length > 0) {
                                            viewerTypeSelect.innerHTML = dropdownOptions.viewerTypes.map(function(type) {
                                                return '<option>' + type + '</option>';
                                            }).join('');
                                        } else {
                                            viewerTypeSelect.innerHTML = '<option>1D Spectrum</option><option>2D Spectrum</option><option>Histogram</option><option>Scatter</option>';
                                        }
                                    }
                                }, 50);
                            }

                            // Re-attach scroll behavior for footer button
                            setTimeout(function() {
                                const footerButton = wireframeSidebar.querySelector('.wireframe-sidebar-footer-button');
                                if (footerButton) {
                                    footerButton.addEventListener('click', function(e) {
                                        stopAutoCycle();
                                        const targetId = footerButton.getAttribute('data-scroll-target');
                                        const targetElement = document.querySelector('[data-grid-id="' + targetId + '"]');
                                        if (targetElement) {
                                            // Always scroll, even if already at the target
                                            targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });

                                            // Highlight the target grid item
                                            setTimeout(function() {
                                                // Remove highlight from any previously highlighted items
                                                document.querySelectorAll('.grid-item.highlighted').forEach(function(el) {
                                                    el.classList.remove('highlighted');
                                                });

                                                // Add highlight to current target
                                                targetElement.classList.add('highlighted');

                                                // Remove highlight after 3 seconds
                                                setTimeout(function() {
                                                    targetElement.classList.remove('highlighted');
                                                }, 3000);
                                            }, 500);
                                        }
                                    });
                                }
                            }, 100);
                        }

                        // Update Jupyter cell API snippet
                        updateJupyterApiSnippet(data, tabIndex);
                    });
                });
            } else {
                // No tabs, build HTML string then set all at once
                let sidebarHtml = '';

                // Start sidebar body wrapper
                sidebarHtml += '<div class="wireframe-sidebar-body">';

                // Build content with API snippet before content if available
                // Skip API snippet for plugins sidebar since it's embedded in the expansion panel
                const apiSnippet = (sidebarType !== 'plugins' && data.apiSnippet) ? data.apiSnippet : '';
                sidebarHtml += '<div class="wireframe-sidebar-content">' + apiSnippet + data.content + '</div>';

                // Build footer with learn more button
                const learnMoreData = data.learnMore || null;
                if (learnMoreData && showScrollTo) {
                    sidebarHtml += '<div class="wireframe-sidebar-footer">' +
                        '<button class="wireframe-sidebar-footer-button" data-scroll-target="' + learnMoreData.target + '">' + learnMoreData.text + '</button>' +
                        '</div>';
                }

                // Close sidebar body wrapper
                sidebarHtml += '</div>';

                // Set all HTML at once
                wireframeSidebar.innerHTML = sidebarHtml;

                // Update Jupyter cell API snippet
                updateJupyterApiSnippet(data);
            }

            // Populate dropdowns for loaders sidebar
            if (sidebarType === 'loaders') {
                setTimeout(function() {
                    const sourceSelect = container.querySelector('#source-select');
                    const formatSelect = container.querySelector('#format-select');
                    const viewerTypeSelect = container.querySelector('#viewer-type-select');

                    // Populate source dropdown
                    if (sourceSelect && dropdownOptions.sources.length > 0) {
                        sourceSelect.innerHTML = dropdownOptions.sources.map(function(source) {
                            return '<option>' + source + '</option>';
                        }).join('');
                    } else if (sourceSelect) {
                        // Fallback options
                        sourceSelect.innerHTML = '<option>file</option><option>file drop</option><option>url</option><option>object</option><option>astroquery</option><option>virtual observatory</option>';
                    }

                    // Populate format dropdown
                    if (formatSelect && dropdownOptions.formats.length > 0) {
                        formatSelect.innerHTML = dropdownOptions.formats.map(function(format) {
                            return '<option>' + format + '</option>';
                        }).join('');
                    } else if (formatSelect) {
                        // Fallback options
                        formatSelect.innerHTML = '<option>1D Spectrum</option><option>2D Spectrum</option>';
                    }

                    // Populate viewer type dropdown
                    if (viewerTypeSelect && dropdownOptions.viewerTypes.length > 0) {
                        viewerTypeSelect.innerHTML = dropdownOptions.viewerTypes.map(function(type) {
                            return '<option>' + type + '</option>';
                        }).join('');
                    } else if (viewerTypeSelect) {
                        // Fallback options
                        viewerTypeSelect.innerHTML = '<option>1D Spectrum</option><option>2D Spectrum</option><option>Histogram</option><option>Scatter</option>';
                    }
                }, 50);
            }

            // Add event handlers for Plot Options UI
            if (sidebarType === 'settings') {
                setTimeout(function() {
                    setupPlotOptionsHandlers();
                }, 50);
            }

            // Add scroll behavior for footer button and any other scroll links
            setTimeout(function() {
                const links = wireframeSidebar.querySelectorAll('[data-scroll-target]');
                links.forEach(function(link) {
                    link.addEventListener('click', function(e) {
                        stopAutoCycle();
                        const targetId = link.getAttribute('data-scroll-target');
                        const targetElement = document.querySelector('[data-grid-id="' + targetId + '"]');
                        if (targetElement) {
                            // Always scroll, even if already at the target
                            targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });

                            // Highlight the target grid item
                            setTimeout(function() {
                                // Remove highlight from any previously highlighted items
                                document.querySelectorAll('.grid-item.highlighted').forEach(function(el) {
                                    el.classList.remove('highlighted');
                                });

                                // Add highlight to current target
                                targetElement.classList.add('highlighted');

                                // Remove highlight after 3 seconds
                                setTimeout(function() {
                                    targetElement.classList.remove('highlighted');
                                }, 3000);
                            }, 500);
                        }
                    });
                });

                // Add expansion panel click handlers
                const expansionPanels = wireframeSidebar.querySelectorAll('.expansion-panel:not(.disabled)');
                expansionPanels.forEach(function(panel) {
                    const header = panel.querySelector('.expansion-panel-header');
                    const content = panel.querySelector('.expansion-panel-content');

                    if (header && content) {
                        header.addEventListener('click', function() {
                            stopAutoCycle();

                            // Toggle expanded state
                            const isExpanded = panel.classList.contains('expanded');

                            if (isExpanded) {
                                panel.classList.remove('expanded');
                                content.classList.remove('expanded');
                            } else {
                                // Close all other panels (accordion behavior)
                                expansionPanels.forEach(function(p) {
                                    p.classList.remove('expanded');
                                    const c = p.querySelector('.expansion-panel-content');
                                    if (c) c.classList.remove('expanded');
                                });

                                // Open this panel
                                panel.classList.add('expanded');
                                content.classList.add('expanded');
                            }
                        });
                    }
                });
            }, 100);
        }

        // Show sidebar and activate icon
        wireframeSidebar.classList.add('visible');
        icon.classList.add('active');
        currentSidebar = sidebarType;
    }

    wireframeIcons.forEach(function(icon) {
        // Disable icons not in enableOnly list
        if (enableOnly) {
            const sidebarType = icon.dataset.sidebar;
            if (sidebarType && !enableOnly.includes(sidebarType)) {
                icon.style.opacity = '0.3';
                icon.style.cursor = 'not-allowed';
                icon.style.pointerEvents = 'none';
            }
        }

        // Disable mouseover button if scroll-to is hidden
        if (!showScrollTo && icon.classList.contains('mouseover-button')) {
            icon.style.opacity = '0.3';
            icon.style.cursor = 'not-allowed';
            icon.style.pointerEvents = 'none';
            icon.classList.add('disabled');
        }

        icon.addEventListener('click', function(e) {
            // Only stop auto-cycle for real user clicks, not programmatic demo clicks
            if (e.isTrusted) {
                stopAutoCycle();
            }

            // Handle API button separately
            if (icon.classList.contains('api-button')) {
                apiModeActive = !apiModeActive;
                const jupyterApiSnippet = container.querySelector('#jupyter-api-snippet');
                const jupyterApiContent = container.querySelector('#jupyter-api-snippet-content');
                const dataMenuApiSnippets = container.querySelectorAll('.data-menu-api-snippet');

                if (apiModeActive) {
                    icon.classList.add('active');
                    container.classList.add('api-mode-active');

                    // Show API snippet in Jupyter cell and update content based on current sidebar
                    if (jupyterApiSnippet && jupyterApiContent) {
                        jupyterApiSnippet.classList.add('visible');

                        // Get current sidebar API snippet if available
                        if (currentSidebar && sidebarContent_map[currentSidebar]) {
                            const data = sidebarContent_map[currentSidebar];
                            let apiText = '';

                            if (data.apiSnippet) {
                                // Extract text from HTML
                                const tempDiv = document.createElement('div');
                                tempDiv.innerHTML = data.apiSnippet;
                                const preElement = tempDiv.querySelector('pre.api-snippet');
                                if (preElement) {
                                    apiText = preElement.textContent;
                                }
                            }

                            jupyterApiContent.textContent = apiText || '# Select a sidebar to see API snippets';
                        } else {
                            jupyterApiContent.textContent = '# Select a sidebar to see API snippets';
                        }
                    }
                } else {
                    icon.classList.remove('active');
                    container.classList.remove('api-mode-active');

                    // Hide API snippet in Jupyter cell
                    if (jupyterApiSnippet) {
                        jupyterApiSnippet.classList.remove('visible');
                    }
                }

                // Don't re-activate sidebar - just let CSS show/hide API snippets
                return;
            }

            // Handle Mouseover button separately - scroll to section
            if (icon.classList.contains('mouseover-button')) {
                const targetElement = document.querySelector('[data-grid-id="grid-mouseover"]');
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    // Highlight effect
                    setTimeout(function() {
                        document.querySelectorAll('.grid-item.highlighted').forEach(function(el) {
                            el.classList.remove('highlighted');
                        });
                        targetElement.classList.add('highlighted');
                        setTimeout(function() {
                            targetElement.classList.remove('highlighted');
                        }, 3000);
                    }, 500);
                }
                return;
            }

            // Get the sidebar type
            const sidebarType = icon.dataset.sidebar;

            if (!sidebarType) return;

            if (currentSidebar === sidebarType) {
                // Close sidebar if clicking the same icon
                wireframeSidebar.classList.remove('visible');
                icon.classList.remove('active');
                currentSidebar = null;
            } else {
                activateSidebar(sidebarType);
            }
        });
    });

    // Auto-cycle function
    function autoCycleSidebars() {
        if (!autoCycling) return;

        // Handle custom demo sequence with actions
        if (demoSequence.length > 0 && currentCycleIndex < demoSequence.length) {
            const step = demoSequence[currentCycleIndex];
            const sidebarType = step.sidebar;
            const action = step.action;
            const value = step.value;
            const data = sidebarContent_map[sidebarType];

            // Check if this is a standalone action (no sidebar needed)
            const standaloneActions = ['open-data-menu', 'highlight'];
            const isStandaloneAction = standaloneActions.indexOf(action) !== -1;
            const isViewerAction = sidebarType && sidebarType.indexOf('viewer-') === 0;

            // Helper function to move to the next step
            function moveToNextStep() {
                // Use typeof check to allow delay of 0 (since 0 is falsy)
                const currentDelay = typeof step.delay === 'number' ? step.delay : 2000;
                currentCycleIndex++;
                if (currentCycleIndex < demoSequence.length) {
                    setTimeout(autoCycleSidebars, currentDelay);
                } else {
                    // Demo sequence complete
                    if (demoRepeat) {
                        // Loop back to start - full reset including viewers
                        setTimeout(function() {
                            resetDemoState();
                            autoCycleSidebars();
                        }, currentDelay + 1000);
                    } else {
                        // Stop and show restart button
                        autoCycling = false;
                        updateCycleControlButton();
                    }
                }
            }

            // Handle pause action - just wait without doing anything
            if (sidebarType === 'pause') {
                moveToNextStep();
                return;
            }

            // Handle viewer-* actions immediately (no setTimeout needed)
            if (isViewerAction) {
                const viewerAction = sidebarType;
                const params = value ? value.split(':') : [];

                if (viewerAction === 'viewer-add') {
                    const direction = params[0] || 'horiz';
                    const newId = params[1] || 'viewer-' + Date.now();
                    const parentId = params[2] || null;
                    executeViewerAdd(direction, newId, parentId);
                } else if (viewerAction === 'viewer-image') {
                    const viewerId = params[0] || 'default';
                    const imagePath = params.slice(1).join(':');
                    executeViewerImage(viewerId, imagePath);
                } else if (viewerAction === 'viewer-legend') {
                    const viewerId = params[0] || 'default';
                    const layersString = params.slice(1).join(':');
                    executeViewerLegend(viewerId, layersString);
                } else if (viewerAction === 'viewer-focus') {
                    const viewerId = params[0] || null;
                    executeViewerFocus(viewerId);
                } else if (viewerAction === 'viewer-remove') {
                    const viewerId = params[0];
                    if (viewerId) {
                        executeViewerRemove(viewerId);
                    }
                } else if (viewerAction === 'viewer-open-data-menu') {
                    const viewerId = params[0] || null;
                    executeViewerOpenDataMenu(viewerId);
                } else if (viewerAction === 'viewer-tool-toggle') {
                    const viewerId = params[0];
                    const toolName = params[1];
                    if (viewerId && toolName) {
                        var toolIcon = executeViewerToolToggle(viewerId, toolName);
                        if (toolIcon && !step.noHighlight) {
                            briefHighlight(toolIcon, step.delay);
                        }
                    }
                }

                moveToNextStep();
                return;
            }

            // Only activate the sidebar if it's not a standalone action and either:
            // - There's no action specified, OR
            // - The sidebar is different from the current one
            var needsSidebarChange = !isStandaloneAction && (!action || currentSidebar !== sidebarType);
            if (needsSidebarChange) {
                activateSidebar(sidebarType);
            }

            // Determine delay needed - if sidebar already open, execute immediately
            // Otherwise wait for sidebar animation (300ms CSS transition + small buffer)
            var actionDelay = needsSidebarChange ? 350 : 0;

            // Execute action after sidebar is shown (if needed)
            setTimeout(function() {
                if (!autoCycling) return;

                // Clear previous highlights at start of new step
                currentHighlightedElements.forEach(function(el) {
                    el.classList.remove('highlighted');
                });
                currentHighlightedElements = [];

                if (action === 'open-panel') {
                    // Open expansion panel
                    const panel = wireframeSidebar.querySelector('.expansion-panel');
                    if (panel && !panel.classList.contains('expanded')) {
                        panel.classList.add('expanded');
                        const content = panel.querySelector('.expansion-panel-content');
                        if (content) {
                            content.classList.add('expanded');
                        }
                        if (!step.noHighlight) briefHighlight(panel, step.delay);
                    }
                } else if (action === 'api-toggle') {
                    // Toggle API mode
                    const apiButton = container.querySelector('.api-button');
                    if (apiButton) {
                        apiButton.click();
                        if (!step.noHighlight) briefHighlight(apiButton, step.delay);
                    }
                } else if (action === 'select-tab') {
                    // Select a specific tab
                    const tabs = wireframeSidebar.querySelectorAll('.wireframe-sidebar-tab');
                    tabs.forEach(function(tab) {
                        if (tab.textContent.trim() === value) {
                            tab.click();
                            if (!step.noHighlight) briefHighlight(tab, step.delay);
                        }
                    });
                } else if (action === 'select-dropdown') {
                    // Select a dropdown value by label - format: label:value
                    if (value && value.includes(':')) {
                        const parts = value.split(':');
                        const targetLabel = parts[0].trim().toLowerCase();
                        const targetValue = parts.slice(1).join(':').trim().toLowerCase(); // Handle values with colons

                        const dropdowns = wireframeSidebar.querySelectorAll('select');
                        dropdowns.forEach(function(dropdown) {
                            const label = dropdown.previousElementSibling;
                            if (label && label.textContent) {
                                const labelText = label.textContent.trim().toLowerCase();
                                if (labelText === targetLabel || labelText.includes(targetLabel)) {
                                    // Find option by value (case-insensitive)
                                    const options = dropdown.querySelectorAll('option');
                                    options.forEach(function(option, index) {
                                        const optionText = option.textContent.trim().toLowerCase();
                                        const optionValue = (option.value || '').trim().toLowerCase();
                                        if (optionText === targetValue || optionValue === targetValue) {
                                            dropdown.selectedIndex = index;
                                            // Trigger visual feedback
                                            dropdown.style.background = 'rgba(199, 93, 44, 0.3)';
                                            setTimeout(function() {
                                                dropdown.style.background = '';
                                            }, 800);
                                            briefHighlight(dropdown, step.delay);
                                        }
                                    });
                                }
                            }
                        });
                    }
                } else if (action === 'select-data' || action === 'select-aperture') {
                    // Select a dropdown value
                    const dropdowns = wireframeSidebar.querySelectorAll('select');
                    dropdowns.forEach(function(dropdown) {
                        const label = dropdown.previousElementSibling;
                        if (label && label.textContent) {
                            const labelText = label.textContent.trim().toLowerCase();
                            if ((action === 'select-data' && labelText.includes('data')) ||
                                (action === 'select-aperture' && labelText.includes('aperture'))) {
                                // Find option by value
                                const options = dropdown.querySelectorAll('option');
                                options.forEach(function(option, index) {
                                    if (option.textContent === value || option.value === value) {
                                        dropdown.selectedIndex = index;
                                        // Trigger visual feedback
                                        dropdown.style.background = 'rgba(199, 93, 44, 0.3)';
                                        setTimeout(function() {
                                            dropdown.style.background = '';
                                        }, 800);
                                        if (!step.noHighlight) if (!step.noHighlight) briefHighlight(dropdown, step.delay);
                                    }
                                });
                            }
                        }
                    });
                } else if (action === 'open-data-menu') {
                    // Open the data menu popup - scoped to this wireframe
                    const dataMenuTrigger = container.querySelector('.data-menu-trigger');
                    if (dataMenuTrigger) {
                        dataMenuTrigger.click();
                    }
                } else if (action === 'highlight') {
                    // Highlight an element by selector
                    if (value) {
                        const targetElements = container.querySelectorAll(value);
                        targetElements.forEach(function(el) {
                            el.classList.add('highlighted');
                            currentHighlightedElements.push(el);
                        });
                    }
                } else if (action === 'click-button') {
                    // Click a button by its text content
                    if (value) {
                        const buttons = wireframeSidebar.querySelectorAll('button.wireframe-button');
                        buttons.forEach(function(button) {
                            if (button.textContent.trim().toLowerCase() === value.toLowerCase()) {
                                // Visual feedback for button click
                                button.style.background = 'rgba(199, 93, 44, 0.8)';
                                setTimeout(function() {
                                    button.style.background = '';
                                }, 400);
                                if (!step.noHighlight) briefHighlight(button, step.delay);
                            }
                        });
                    }
                } else if (action === 'select-viewer' && sidebarType === 'settings') {
                    // Select a viewer in Plot Options dropdown
                    var viewerDropdown = container.querySelector('.plot-options-viewer-dropdown');
                    if (viewerDropdown && value) {
                        viewerDropdown.value = value;
                        if (!step.noHighlight) briefHighlight(viewerDropdown, step.delay);
                        // Trigger change event to update layers
                        viewerDropdown.dispatchEvent(new Event('change'));
                    }
                } else if (action === 'select-layer' && sidebarType === 'settings') {
                    // Select a layer tab in Plot Options
                    var layerIndex = parseInt(value) || 0;
                    var layerTabs = container.querySelectorAll('.plot-options-layer-tab');
                    if (layerTabs[layerIndex]) {
                        layerTabs.forEach(function(t) { t.classList.remove('active'); });
                        layerTabs[layerIndex].classList.add('active');
                        if (!step.noHighlight) briefHighlight(layerTabs[layerIndex], step.delay);
                        // Update color button to match layer color
                        var layerColor = layerTabs[layerIndex].dataset.layerColor;
                        var colorButton = container.querySelector('.plot-options-color-button');
                        if (colorButton && layerColor) {
                            colorButton.style.backgroundColor = layerColor;
                        }
                    }
                } else if (action === 'set-color' && sidebarType === 'settings') {
                    // Set color in Plot Options
                    var colorButton = container.querySelector('.plot-options-color-button');
                    if (colorButton && value) {
                        colorButton.style.backgroundColor = value;
                        if (!step.noHighlight) briefHighlight(colorButton, step.delay);
                        // Update active layer tab's color
                        var activeTab = container.querySelector('.plot-options-layer-tab.active');
                        if (activeTab) {
                            activeTab.dataset.layerColor = value;
                        }
                    }
                }

                moveToNextStep();
            }, actionDelay);

            return;
        }

        // Check if auto-cycling is still enabled
        if (!autoCycling) return;

        // Original logic for simple sidebar order
        const sidebarType = sidebarOrder[currentCycleIndex];
        const data = sidebarContent_map[sidebarType];

        // Special handling for loaders sidebar with animations
        if (sidebarType === 'loaders' && data && data.tabs) {
            const numTabs = data.tabs.length;
            let animationStep = 0;

            // Step 0: Show Data tab
            activateSidebar(sidebarType, 0);

            const loaderAnimation = setInterval(function() {
                if (!autoCycling) {
                    clearInterval(loaderAnimation);
                    return;
                }

                animationStep++;

                if (animationStep === 1) {
                    // Step 1: Change format select to "2D Spectrum"
                    const formatSelect = container.querySelector('#format-select');
                    if (formatSelect) {
                        // Find the option with "2D Spectrum" (case-insensitive)
                        const options = formatSelect.querySelectorAll('option');
                        let found = false;
                        options.forEach(function(option, index) {
                            if (option.textContent.toLowerCase().includes('2d spectrum')) {
                                formatSelect.selectedIndex = index;
                                found = true;
                            }
                        });
                        // If "2D Spectrum" not found, try to select second option
                        if (!found && options.length > 1) {
                            formatSelect.selectedIndex = 1;
                        }
                    }
                } else if (animationStep === 2) {
                    // Step 2: Flash Load button orange
                    const loadButton = wireframeSidebar.querySelector('.wireframe-button');
                    if (loadButton) {
                        loadButton.style.background = '#c75d2c';
                        loadButton.style.opacity = '1';
                        loadButton.style.transform = 'scale(0.98)';
                        setTimeout(function() {
                            if (loadButton) {
                                loadButton.style.background = '';
                                loadButton.style.opacity = '';
                                loadButton.style.transform = '';
                            }
                        }, 800);
                    }
                } else if (animationStep === 3) {
                    // Step 3: Switch to Viewer tab
                    activateSidebar(sidebarType, 1);
                } else {
                    // Done with loaders, move to next sidebar
                    clearInterval(loaderAnimation);
                    currentCycleIndex = (currentCycleIndex + 1) % sidebarOrder.length;
                    setTimeout(autoCycleSidebars, 2000);
                }
            }, 2000);

        } else if (data && data.tabs) {
            // Regular sidebar with tabs, cycle through them
            const numTabs = data.tabs.length;
            let tabCycleIndex = 0;

            // Activate first tab
            activateSidebar(sidebarType, 0);

            // Set up tab cycling
            const tabCycleInterval = setInterval(function() {
                if (!autoCycling) {
                    clearInterval(tabCycleInterval);
                    return;
                }

                tabCycleIndex++;
                if (tabCycleIndex < numTabs) {
                    activateSidebar(sidebarType, tabCycleIndex);
                } else {
                    // Done with tabs, move to next sidebar
                    clearInterval(tabCycleInterval);
                    currentCycleIndex = (currentCycleIndex + 1) % sidebarOrder.length;
                    setTimeout(autoCycleSidebars, 2000);
                }
            }, 2000);
        } else {
            // No tabs, just show the sidebar
            activateSidebar(sidebarType);
            currentCycleIndex = (currentCycleIndex + 1) % sidebarOrder.length;
            setTimeout(autoCycleSidebars, 3000);
        }
    }

    // Start auto-cycling only when wireframe is in view
    let hasStartedCycling = false;

    function checkWireframeInView() {
        if (!autoCycling || hasStartedCycling) {
            return;
        }

        const rect = container.getBoundingClientRect();
        const windowHeight = window.innerHeight || document.documentElement.clientHeight;

        // Check if entire wireframe is fully visible in viewport
        const isFullyVisible = (
            rect.top >= 0 &&
            rect.bottom <= windowHeight
        );

        if (isFullyVisible) {
            hasStartedCycling = true;

            // Apply initial state first (if any)
            if (initialSequence && initialSequence.length > 0) {
                applyInitialState();
            }

            // Then start the demo sequence
            autoCycleSidebars();
        }
    }

    // Check on scroll and initial load
    window.addEventListener('scroll', checkWireframeInView);
    window.addEventListener('resize', checkWireframeInView);
    setTimeout(function() {
        checkWireframeInView();
    }, 1000);

    // Handle cycle control button
    const cycleControlButton = container.querySelector('.wireframe-cycle-control');
    if (cycleControlButton) {
        // Hover: only update flyout text, don't change icons
        cycleControlButton.addEventListener('mouseenter', function() {
            if (autoCycling) {
                cycleControlButton.setAttribute('data-flyout-text', 'pause demo');
            } else {
                cycleControlButton.setAttribute('data-flyout-text', 'restart demo');
            }
        });

        cycleControlButton.addEventListener('mouseleave', function() {
            // No icon changes needed on mouse leave
        });

        // Click: pause when playing, restart when paused
        cycleControlButton.addEventListener('click', function() {
            if (autoCycling) {
                // Pause/cancel the cycle
                stopAutoCycle();
                // Update hover state immediately - show restart since now paused
                const cycleIconPause = container.querySelector('.cycle-icon-pause');
                const cycleIconRestart = container.querySelector('.cycle-icon-restart');
                if (cycleIconPause) cycleIconPause.classList.add('hidden');
                if (cycleIconRestart) cycleIconRestart.classList.remove('hidden');
                cycleControlButton.setAttribute('data-flyout-text', 'restart demo');
            } else {
                // Restart the cycle
                restartAutoCycle();
                // Update hover state immediately - show pause since now playing
                const cycleIconPause = container.querySelector('.cycle-icon-pause');
                const cycleIconRestart = container.querySelector('.cycle-icon-restart');
                if (cycleIconRestart) cycleIconRestart.classList.add('hidden');
                if (cycleIconPause) cycleIconPause.classList.remove('hidden');
                cycleControlButton.setAttribute('data-flyout-text', 'pause demo');
            }
        });
    }

    // Stop cycling on any user interaction within THIS container
    container.addEventListener('click', function(e) {
        // Only stop if clicking on interactive elements within this container
        // AND if it's a real user click (not programmatic from the demo)
        if (e.isTrusted && e.target.closest('.wireframe-toolbar-icon, .wireframe-sidebar-tab, .wireframe-sidebar-link')) {
            stopAutoCycle();
        }
    });

    // Data menu popup handler - using event delegation for dynamic legend items
    const dataMenuPopup = container.querySelector('#data-menu-popup');
    const dataMenuClose = container.querySelector('#data-menu-close');

    // Helper function to position data menu popup based on trigger element
    function positionDataMenuPopup(triggerElement) {
        if (!dataMenuPopup) return;

        var viewerArea = container.querySelector('.wireframe-viewer-area');
        if (!viewerArea) return;

        var viewerAreaRect = viewerArea.getBoundingClientRect();

        // Get popup dimensions (use actual if visible, otherwise estimate)
        var popupWidth = dataMenuPopup.offsetWidth || 350;
        var popupHeight = dataMenuPopup.offsetHeight || 300;

        var top, left;

        // Always use trigger element position for consistent behavior
        if (triggerElement) {
            // Position based on the trigger element
            var triggerRect = triggerElement.getBoundingClientRect();
            top = triggerRect.top - viewerAreaRect.top;
            left = triggerRect.left - viewerAreaRect.left - popupWidth - 8;
        } else {
            // Fallback to center of viewer area
            top = (viewerAreaRect.height - popupHeight) / 2;
            left = (viewerAreaRect.width - popupWidth) / 2;
        }

        // Make sure popup stays within viewer area bounds
        if (top < 8) top = 8;
        if (top + popupHeight > viewerAreaRect.height - 8) {
            top = viewerAreaRect.height - popupHeight - 8;
            if (top < 8) top = 8;
        }

        // If popup would go off left edge, show it to the right of trigger instead
        if (left < 8) {
            if (triggerElement) {
                var triggerRect = triggerElement.getBoundingClientRect();
                left = triggerRect.right - viewerAreaRect.left + 8;
            } else {
                left = 8;
            }
        }

        dataMenuPopup.style.top = top + 'px';
        dataMenuPopup.style.left = left + 'px';
    }

    if (dataMenuPopup && dataMenuClose) {
        // Use event delegation on the container for dynamically created .data-menu-trigger elements
        container.addEventListener('click', function(e) {
            var trigger = e.target.closest('.data-menu-trigger');
            if (trigger && container.contains(trigger)) {
                e.stopPropagation();

                // Pause any running demo when user clicks on legend
                if (e.isTrusted) {
                    stopAutoCycle();
                }

                // If popup is already visible, just hide it
                if (dataMenuPopup.classList.contains('visible')) {
                    dataMenuPopup.classList.remove('visible');
                } else {
                    // Position popup based on trigger element
                    positionDataMenuPopup(trigger);
                    dataMenuPopup.classList.add('visible');
                }
            }
        });

        dataMenuClose.addEventListener('click', function() {
            dataMenuPopup.classList.remove('visible');
        });

        // Add scroll behavior for buttons inside the data menu popup
        const dataMenuScrollLinks = dataMenuPopup.querySelectorAll('[data-scroll-target]');

        // Hide scroll-to buttons if showScrollTo is false
        if (!showScrollTo) {
            dataMenuScrollLinks.forEach(function(link) {
                link.style.display = 'none';
            });
        }

        dataMenuScrollLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                stopAutoCycle();
                const targetId = link.getAttribute('data-scroll-target');
                const targetElement = document.querySelector('[data-grid-id="' + targetId + '"]');
                if (targetElement) {
                    // Close the popup
                    dataMenuPopup.classList.remove('visible');

                    // Scroll to target
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });

                    // Highlight the target grid item
                    setTimeout(function() {
                        // Remove highlight from any previously highlighted items
                        document.querySelectorAll('.grid-item.highlighted').forEach(function(el) {
                            el.classList.remove('highlighted');
                        });

                        // Add highlight to current target
                        targetElement.classList.add('highlighted');

                        // Remove highlight after 3 seconds
                        setTimeout(function() {
                            targetElement.classList.remove('highlighted');
                        }, 3000);
                    }, 100);
                }
            });
        });

        // Close popup when clicking outside (use dynamic check for triggers)
        document.addEventListener('click', function(e) {
            var isClickInsidePopup = dataMenuPopup.contains(e.target);
            var isClickOnTrigger = e.target.closest('.data-menu-trigger') !== null;

            if (!isClickInsidePopup && !isClickOnTrigger) {
                dataMenuPopup.classList.remove('visible');
            }
        });
    }
}

// Initialize on DOMContentLoaded (for directive-embedded wireframes)
document.addEventListener('DOMContentLoaded', function() {
    initializeWireframeController();
});

// Initialize on custom event (for dynamically loaded wireframes in index.html)
document.addEventListener('wireframe-loaded', function() {
    initializeWireframeController();
});

// Initialize grid item toggle buttons for landing page
function initializeGridItemToggles() {
    const gridItems = document.querySelectorAll('.grid-item');

    gridItems.forEach(function(item) {
        const content = item.querySelector('.grid-item-content');
        if (!content) return;

        // Check if content is taller than a threshold (e.g., 300px)
        const contentHeight = content.scrollHeight;
        const threshold = 300;

        if (contentHeight > threshold) {
            // Add has-toggle class
            item.classList.add('has-toggle');

            // Create toggle button
            const toggleButton = document.createElement('button');
            toggleButton.className = 'toggle-more';
            toggleButton.textContent = 'Show More';

            // Initially collapse the content
            content.style.maxHeight = threshold + 'px';
            content.style.overflow = 'hidden';

            // Add click handler
            toggleButton.addEventListener('click', function(e) {
                e.stopPropagation();
                const isExpanded = item.classList.contains('expanded');

                if (isExpanded) {
                    // Collapse
                    item.classList.remove('expanded');
                    content.style.maxHeight = threshold + 'px';
                    toggleButton.textContent = 'Show More';
                } else {
                    // Expand
                    item.classList.add('expanded');
                    content.style.maxHeight = 'none';
                    toggleButton.textContent = 'Show Less';
                }
            });

            // Append button to grid item
            item.appendChild(toggleButton);
        }
    });
}

// Initialize grid toggles when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeGridItemToggles);
