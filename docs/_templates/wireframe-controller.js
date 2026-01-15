// Wireframe controller initialization function - supports multiple instances
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
            let workingItem = item;

            // Check for timing syntax: sidebar@1000:action
            if (item.includes('@')) {
                const atIndex = item.indexOf('@');
                const beforeAt = item.substring(0, atIndex);
                const afterAt = item.substring(atIndex + 1);

                // Extract delay (number before next : or end of string)
                const colonAfterAt = afterAt.indexOf(':');
                if (colonAfterAt !== -1) {
                    delay = parseInt(afterAt.substring(0, colonAfterAt), 10);
                    workingItem = beforeAt + afterAt.substring(colonAfterAt);
                } else {
                    delay = parseInt(afterAt, 10);
                    workingItem = beforeAt;
                }
            }

            // Check if item contains action syntax (sidebar:action or sidebar:action=value)
            if (workingItem.includes(':')) {
                const colonIndex = workingItem.indexOf(':');
                const sidebar = workingItem.substring(0, colonIndex);
                const actionPart = workingItem.substring(colonIndex + 1);

                // Check if action has a value
                if (actionPart.includes('=')) {
                    const equalsIndex = actionPart.indexOf('=');
                    const action = actionPart.substring(0, equalsIndex);
                    const value = actionPart.substring(equalsIndex + 1);
                    sequence.push({
                        sidebar: sidebar,
                        action: action,
                        value: value,
                        delay: delay
                    });
                } else {
                    sequence.push({
                        sidebar: sidebar,
                        action: actionPart,
                        delay: delay
                    });
                }
            } else {
                // Simple sidebar activation
                sequence.push({
                    sidebar: workingItem,
                    action: 'show',
                    delay: delay
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

    // Helper function to create API snippet with proper link/button based on showScrollTo
    function createApiSnippet(code) {
        if (showScrollTo) {
            return '<div class="api-snippet-container"><pre class="api-snippet">' + code + '</pre><button class="api-learn-more" data-scroll-target="grid-userapi">Learn about API access</button></div>';
        } else {
            return '<div class="api-snippet-container"><pre class="api-snippet">' + code + '</pre><a class="api-learn-more" href="../userapi/index.html">Learn about API access</a></div>';
        }
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

    function restartAutoCycle() {
        // Stop any existing cycle
        if (cycleInterval) {
            clearInterval(cycleInterval);
            cycleInterval = null;
        }

        // Reset API mode if active
        if (apiModeActive) {
            const apiButton = container.querySelector('.api-button');
            if (apiButton) {
                apiButton.click();
            }
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

        let currentStep = 0;

        function applyStep() {
            if (currentStep >= initialSequence.length) return;

            const step = initialSequence[currentStep];
            const sidebarType = step.sidebar;
            const action = step.action;
            const value = step.value;

            // Activate the sidebar
            if (action === 'show' || action === 'select-tab') {
                if (action === 'select-tab' && value) {
                    // Find tab index by name
                    const data = sidebarContent_map[sidebarType];
                    if (data && data.tabs) {
                        const tabIndex = data.tabs.findIndex(t => t === value);
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
            }

            currentStep++;
            if (currentStep < initialSequence.length) {
                setTimeout(applyStep, step.delay || 500);
            }
        }

        applyStep();
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
                '{{ descriptions.settings_plot }}',
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
                sidebarHtml += '<div class="wireframe-sidebar-content" id="sidebar-tab-content">' + apiSnippet + data.content[activeIndex] + '</div>';

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
                            contentDiv.innerHTML = apiSnippet + data.content[tabIndex];

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

            // Only activate the sidebar if it's different from the current one or if there's no action
            // (actions can be performed on the already-active sidebar without reactivating)
            if (!action || currentSidebar !== sidebarType) {
                activateSidebar(sidebarType);
            }

            // Execute action after sidebar is shown
            setTimeout(function() {
                if (!autoCycling) return;

                if (action === 'open-panel') {
                    // Open expansion panel
                    const panel = wireframeSidebar.querySelector('.expansion-panel');
                    if (panel && !panel.classList.contains('expanded')) {
                        panel.classList.add('expanded');
                        const content = panel.querySelector('.expansion-panel-content');
                        if (content) {
                            content.classList.add('expanded');
                        }
                    }
                } else if (action === 'api-toggle') {
                    // Toggle API mode
                    const apiButton = container.querySelector('.api-button');
                    if (apiButton) {
                        apiButton.click();
                    }
                } else if (action === 'select-tab') {
                    // Select a specific tab
                    const tabs = wireframeSidebar.querySelectorAll('.wireframe-sidebar-tab');
                    tabs.forEach(function(tab) {
                        if (tab.textContent.trim() === value) {
                            tab.click();
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
                }

                // Move to next step
                currentCycleIndex++;
                if (currentCycleIndex < demoSequence.length) {
                    const nextStep = demoSequence[currentCycleIndex];
                    const nextDelay = nextStep.delay || 2000;
                    setTimeout(autoCycleSidebars, nextDelay);
                } else {
                    // Demo sequence complete
                    if (demoRepeat) {
                        // Loop back to start
                        currentCycleIndex = 0;
                        const firstStep = demoSequence[0];
                        const firstDelay = firstStep.delay || 2000;
                        setTimeout(autoCycleSidebars, firstDelay + 1000);
                    } else {
                        // Stop and show restart button
                        autoCycling = false;
                        updateCycleControlButton();
                    }
                }
            }, 1000);

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

    // Data menu popup handler
    const dataMenuTriggers = container.querySelectorAll('.data-menu-trigger');
    const dataMenuPopup = container.querySelector('#data-menu-popup');
    const dataMenuClose = container.querySelector('#data-menu-close');

    if (dataMenuTriggers.length > 0 && dataMenuPopup && dataMenuClose) {
        dataMenuTriggers.forEach(function(trigger) {
            trigger.addEventListener('click', function(e) {
                e.stopPropagation();
                dataMenuPopup.classList.toggle('visible');
            });
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

        // Close popup when clicking outside
        document.addEventListener('click', function(e) {
            const isClickInsidePopup = dataMenuPopup.contains(e.target);
            const isClickOnTrigger = Array.from(dataMenuTriggers).some(trigger => trigger.contains(e.target));

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
