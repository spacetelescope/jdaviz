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

    function formRange(label, min, max, val) {
        return '<div class="jdaviz-form-group"><label class="jdaviz-form-label">' + label +
            '</label><input type="range" class="jdaviz-range" min="' + min + '" max="' + max +
            '" value="' + val + '" /></div>';
    }

    function formToggle(label, checked) {
        return '<div class="jdaviz-toggle-group"><span class="jdaviz-form-label" style="margin:0">' + label +
            '</span><label class="jdaviz-toggle"><input type="checkbox"' +
            (checked ? ' checked' : '') + ' /><span class="jdaviz-toggle-track"></span></label></div>';
    }

    function formModes(options, activeIdx) {
        var html = '<div class="jdaviz-mode-row">';
        options.forEach(function(o, i) {
            html += '<button class="jdaviz-mode-btn' + (i === activeIdx ? ' active' : '') + '">' + o + '</button>';
        });
        return html + '</div>';
    }

    function formResults(text) {
        return '<div class="jdaviz-results-box">' + (text || 'No results yet') + '</div>';
    }

    function formDesc(text) {
        return '<p class="jdaviz-plugin-desc">' + text + '</p>';
    }

    // ── Per-plugin content definitions ──────────────────────────────────

    var PLUGINS = {
        'Gaussian Smooth': {
            html: formDesc('Smooth data with a Gaussian kernel.') +
                formSelect('Dataset', 'gs-data', ['Spectrum1D[flux]', 'Spectrum1D[uncertainty]']) +
                formInput('Std Dev', '2.0') +
                formSelect('Mode', 'gs-mode', ['Spectral', 'Spatial']) +
                formButton('Apply'),
            api: "plg = jd.plugins['Gaussian Smooth']\nplg.stddev = 2.0\nplg.smooth()"
        },
        'Model Fitting': {
            html: formDesc('Fit spectral models to data.') +
                formSelect('Dataset', 'mf-data', ['Spectrum1D[flux]']) +
                formSelect('Spectral Subset', 'mf-subset', ['Entire Spectrum', 'Subset 1']) +
                formSelect('Model', 'mf-model', ['Gaussian1D', 'Lorentz1D', 'Polynomial1D', 'Voigt1D']) +
                formInput('Center', '2.95') +
                formInput('Amplitude', '3.5e6') +
                formInput('Std Dev', '0.15') +
                formButton('Fit Model') +
                formResults('Fit not yet run'),
            api: "plg = jd.plugins['Model Fitting']\nplg.model_component = 'Gaussian1D'\nplg.calculate_fit()"
        },
        'Line Lists': {
            html: formDesc('Overlay spectral line identifications.') +
                formSelect('Preset', 'll-preset', ['Custom', 'SDSS-III/IV', 'H-alpha', 'Common Stellar']) +
                formInput('Redshift', '0.0') +
                formInput('Radial Velocity (km/s)', '0.0') +
                formCheckbox('Show line labels') +
                formButton('Load Lines'),
            api: "plg = jd.plugins['Line Lists']\nplg.rs_redshift = 0.0"
        },
        'Line Analysis': {
            html: formDesc('Compute line measurements: flux, EW, FWHM, centroid.') +
                formSelect('Dataset', 'la-data', ['Spectrum1D[flux]']) +
                formSelect('Spectral Subset', 'la-subset', ['Subset 1', 'Subset 2']) +
                formToggle('Continuum Subtracted', true) +
                formButton('Calculate') +
                formResults('Flux: \u2014\nEq. Width: \u2014\nCentroid: \u2014\nFWHM: \u2014'),
            api: "plg = jd.plugins['Line Analysis']\nplg.get_results()"
        },
        'Unit Conversion': {
            html: formDesc('Convert spectral and flux units globally.') +
                formSelect('Spectral Unit', 'uc-spec', ['Angstrom', 'nm', 'um', 'Hz', 'eV']) +
                formSelect('Flux Unit', 'uc-flux', ['Jy', 'MJy', 'erg/s/cm\u00B2/\u00C5', 'W/m\u00B2/Hz']) +
                formSelect('Angle Unit', 'uc-angle', ['sr', 'pix\u00B2']),
            api: "plg = jd.plugins['Unit Conversion']\nplg.spectral_unit = 'um'"
        },
        'Plot Options': {
            html: formDesc('Customize plot appearance.') +
                formSelect('Viewer', 'po-viewer', ['Viewer 1', 'Viewer 2']) +
                formSelect('Layer', 'po-layer', ['Layer A', 'Layer B']) +
                '<div class="jdaviz-form-group"><label class="jdaviz-form-label">Color</label>' +
                '<input type="color" class="jdaviz-input" value="#00FF00" style="height:28px;padding:2px" /></div>' +
                formSelect('Stretch', 'po-stretch', ['Linear', 'Sqrt', 'Log', 'Power', 'Squared']) +
                formRange('Contrast', 0, 100, 50) +
                formRange('Bias', 0, 100, 50) +
                formRange('Opacity', 0, 100, 100),
            api: "plg = jd.plugins['Plot Options']\nplg.stretch_function = 'sqrt'"
        },
        'Subset Tools': {
            html: formDesc('Create and manage spatial/spectral regions of interest.') +
                formSelect('Subset', 'st-sub', ['Create New', 'Subset 1', 'Subset 2']) +
                '<label class="jdaviz-form-label">Shape</label>' +
                formModes(['Circle', 'Rect', 'Ellipse', 'Annulus'], 0) +
                '<label class="jdaviz-form-label" style="margin-top:10px">Mode</label>' +
                formModes(['New', 'Replace', 'Or', 'And', 'Xor', 'Not'], 0) +
                formButton('Recenter') +
                formButton('Delete'),
            api: "plg = jd.plugins['Subset Tools']"
        },
        'Aperture Photometry': {
            html: formDesc('Aperture photometry on images.') +
                formSelect('Dataset', 'ap-data', ['Image[SCI]']) +
                formSelect('Aperture', 'ap-aper', ['Subset 1 (Circle)', 'Subset 2 (Annulus)']) +
                formSelect('Flux Unit', 'ap-unit', ['count', 'Jy', 'erg/s/cm\u00B2/\u00C5']) +
                formButton('Calculate') +
                formResults('Aperture sum: \u2014\nMean: \u2014\nStd: \u2014\nS/N: \u2014'),
            api: "plg = jd.plugins['Aperture Photometry']\nplg.calculate_photometry()"
        },
        'Moment Maps': {
            html: formDesc('Compute moment maps from data cubes.') +
                formSelect('Dataset', 'mm-data', ['Spectrum1D[flux]']) +
                formSelect('Spectral Subset', 'mm-sub', ['Entire Spectrum', 'Subset 1']) +
                formSelect('Moment', 'mm-order', ['0 (Integrated Flux)', '1 (Velocity)', '2 (Velocity Dispersion)', '3 (Skewness)']) +
                formToggle('Continuum subtraction', false) +
                formButton('Calculate'),
            api: "plg = jd.plugins['Moment Maps']\nplg.n_moment = 0\nplg.calculate_moment()"
        },
        'Collapse': {
            html: formDesc('Collapse a data cube along the spectral axis.') +
                formSelect('Dataset', 'col-data', ['Spectrum1D[flux]']) +
                formSelect('Spectral Subset', 'col-sub', ['Entire Spectrum', 'Subset 1']) +
                formSelect('Function', 'col-func', ['Sum', 'Mean', 'Median', 'Min', 'Max']) +
                formButton('Collapse'),
            api: "plg = jd.plugins['Collapse']\nplg.collapse()"
        },
        '2D Spectral Extraction': {
            html: formDesc('Extract 1D spectra from 2D spectral images.') +
                formSelect('Dataset', 'se2-data', ['Spectrum2D[SCI]']) +
                formSelect('Trace Model', 'se2-trace', ['Spline', 'Polynomial', 'Legendre']) +
                formSelect('Background', 'se2-bg', ['None', 'Manual', 'Fit']) +
                formButton('Extract'),
            api: "plg = jd.plugins['Spectral Extraction']\nplg.extract()"
        },
        '3D Spectral Extraction': {
            html: formDesc('Extract 1D spectra from 3D data cubes.') +
                formSelect('Dataset', 'se-data', ['Spectrum1D[flux]']) +
                formSelect('Aperture', 'se-aper', ['Entire Cube', 'Subset 1', 'Subset 2']) +
                '<label class="jdaviz-form-label">Aperture Shape</label>' +
                formModes(['Circle', 'Rect', 'Annulus'], 0) +
                formSelect('Function', 'se-func', ['Sum', 'Mean', 'Median', 'Min', 'Max']) +
                formToggle('Background subtraction', false) +
                formButton('Extract'),
            api: "plg = jd.plugins['Spectral Extraction']\nplg.extract()"
        },
        'Ramp Extraction': {
            html: formDesc('Extract data from JWST ramp observations.') +
                formSelect('Dataset', 're-data', ['Ramp[SCI]']) +
                formSelect('Extraction Mode', 're-mode', ['Integration', 'Group', 'Slope']) +
                formButton('Extract'),
            api: "plg = jd.plugins['Ramp Extraction']"
        },
        'Orientation': {
            html: formDesc('Link images by WCS or pixel coordinates.') +
                formSelect('Viewer', 'or-viewer', ['Image Viewer']) +
                '<label class="jdaviz-form-label">Alignment</label>' +
                formModes(['Pixels', 'WCS'], 1) +
                formButton('Link'),
            api: "plg = jd.plugins['Orientation']"
        },
        'Footprints': {
            html: formDesc('Overlay instrument footprint regions.') +
                formSelect('Viewer', 'fp-viewer', ['Image Viewer']) +
                formInput('Region File', 'footprint.reg') +
                formToggle('Visible', true) +
                formButton('Import Region'),
            api: "plg = jd.plugins['Footprints']"
        },
        'Compass': {
            html: formDesc('Display compass, data label, and zoom box.') +
                formSelect('Viewer', 'cp-viewer', ['Image Viewer']) +
                '<div style="text-align:center;padding:12px;color:rgba(255,255,255,0.5)">' +
                '<div style="font-size:24px;margin-bottom:6px">\u2191 N&emsp;\u2192 E</div>' +
                '<div style="font-size:11px">Zoom: 4.2\u00D7</div></div>',
            api: "plg = jd.plugins['Compass']"
        },
        'Catalog Search': {
            html: formDesc('Query online astronomical catalogs.') +
                formSelect('Viewer', 'cs-viewer', ['Image Viewer']) +
                formSelect('Catalog', 'cs-cat', ['SDSS', 'Gaia DR3', '2MASS', 'WISE']) +
                formInput('Search Radius (arcsec)', '60') +
                formInput('Max Sources', '100') +
                formButton('Search') +
                formResults('No catalog results yet'),
            api: "plg = jd.plugins['Catalog Search']\nplg.search()"
        },
        'Data Quality': {
            html: formDesc('Visualize data quality flags.') +
                formSelect('Viewer', 'dq-viewer', ['Viewer 1', 'Viewer 2']) +
                formSelect('Science Layer', 'dq-sci', ['Spectrum1D[flux]']) +
                formSelect('DQ Layer', 'dq-dq', ['Spectrum1D[dq]']) +
                formRange('Opacity', 0, 100, 80) +
                formCheckbox('DO_NOT_USE') +
                formCheckbox('SATURATED') +
                formCheckbox('JUMP_DET') +
                formCheckbox('NON_SCIENCE'),
            api: "plg = jd.plugins['Data Quality']"
        },
        'Sonify Data': {
            html: formDesc('Convert spectral data to audio.') +
                formSelect('Dataset', 'son-data', ['Spectrum1D[flux]']) +
                formSelect('Spectral Subset', 'son-sub', ['Entire Spectrum']) +
                formInput('Min Frequency (Hz)', '200') +
                formInput('Max Frequency (Hz)', '2000') +
                formButton('Play'),
            api: "plg = jd.plugins['Sonify Data']"
        },
        'Export': {
            html: formDesc('Export data, subsets, and viewers in various formats.') +
                formSelect('Format', 'export-fmt', ['FITS', 'CSV', 'ECSV', 'PNG', 'SVG']) +
                formInput('Filename', 'export.fits') +
                formCheckbox('Custom size') +
                formButton('Export'),
            api: "plg = jd.plugins['Export']\nplg.export()"
        },
        'Markers': {
            html: formDesc('Create markers and measure positions.') +
                formSelect('Viewer', 'mk-viewer', ['Viewer 1', 'Viewer 2']) +
                formResults('No markers created\n\nClick in a viewer to create markers.') +
                formButton('Export Table') +
                formButton('Clear All'),
            api: "plg = jd.plugins['Markers']\nplg.export_table()"
        },
        'Metadata Viewer': {
            html: formDesc('View FITS header and metadata.') +
                formSelect('Dataset', 'mv-data', ['Spectrum1D[flux]', 'Spectrum1D[uncertainty]']) +
                formCheckbox('Show primary header') +
                formInput('Filter', 'keyword...') +
                formResults('SIMPLE  = T\nBITPIX  = -64\nNAXIS   = 3\nCRVAL3  = 0.6\nCDELT3  = 0.001\nCTYPE3  = WAVE'),
            api: "plg = jd.plugins['Metadata Viewer']"
        },
        'Logger': {
            html: formDesc('System messages and operation history.') +
                formSelect('Popup Verbosity', 'log-popup', ['Error', 'Warning', 'Info', 'Debug']) +
                formSelect('History Verbosity', 'log-hist', ['Info', 'Debug', 'Warning', 'Error']) +
                formResults('[INFO] Data loaded successfully\n[INFO] Cube shape: (30, 40, 2048)\n[WARN] NaN values detected in flux') +
                formButton('Clear History'),
            api: "plg = jd.plugins['Logger']\nplg.history"
        },
        'Slice': {
            html: formDesc('Select a spectral slice of the data cube.') +
                formSelect('Viewer', 'sl-viewer', ['Viewer 1', 'Viewer 2']) +
                formRange('Slice', 0, 2047, 1024) +
                '<div style="text-align:center;font-size:12px;color:rgba(255,255,255,0.5)">' +
                '\u03bb = 2.9486 \u03bcm (slice 1024 / 2048)</div>' +
                formToggle('Snap to slice', true) +
                formToggle('Show indicator', true),
            api: "plg = jd.plugins['Slice']\nplg.slice = 1024\nplg.wavelength"
        },
        'Image Profiles (XY)': {
            html: formDesc('Plot line profiles across images.') +
                formSelect('Viewer', 'xy-viewer', ['Image Viewer']) +
                formInput('X Pixel', '512') +
                formInput('Y Pixel', '512') +
                formButton('Plot Profiles'),
            api: "plg = jd.plugins['Image Profiles (XY)']"
        },
        'Cross Dispersion Profile': {
            html: formDesc('Measure cross-dispersion profile at a wavelength.') +
                formInput('Wavelength / Pixel', '1024') +
                formInput('Window Width (px)', '10') +
                formCheckbox('Use full width') +
                formButton('Measure'),
            api: "plg = jd.plugins['Cross Dispersion Profile']"
        }
    };

    // Plugin list for expansion panels (ordered for display)
    var PLUGIN_LIST = Object.keys(PLUGINS);

    function generatePluginPanelsHTML(pluginName) {
        var name = pluginName || PLUGIN_LIST[0];
        // Only use rich per-plugin content when a specific plugin is explicitly requested
        var plugin = pluginName ? PLUGINS[name] : null;
        var pluginContent = plugin
            ? plugin.html + '<div class="jdaviz-api-snippet">' + plugin.api + '</div>'
            : 'Do basic data reduction and analysis tasks for specific science use-cases.' +
              '<div class="jdaviz-api-snippet">plg = jd.plugins[\'' + name + '\']</div>';
        return '<div class="jdaviz-expansion-panels">' +
            '<div class="jdaviz-expansion-panel expanded" data-panel-index="0" data-plugin-name="' + name + '">' +
            '<div class="jdaviz-expansion-panel-header">' +
            '<span class="jdaviz-expansion-panel-title">' + name + '</span>' +
            '<span class="jdaviz-expansion-panel-arrow">\u25BC</span>' +
            '</div>' +
            '<div class="jdaviz-expansion-panel-content expanded">' +
            pluginContent +
            '</div>' +
            '</div>' +
            '<div class="jdaviz-expansion-panel disabled" data-panel-index="1">' +
            '<div class="jdaviz-expansion-panel-header">' +
            '<div class="jdaviz-expansion-panel-placeholder"></div>' +
            '</div>' +
            '</div>' +
            '<div class="jdaviz-expansion-panel disabled" data-panel-index="2">' +
            '<div class="jdaviz-expansion-panel-header">' +
            '<div class="jdaviz-expansion-panel-placeholder"></div>' +
            '</div>' +
            '</div>' +
            '<div class="jdaviz-expansion-panel disabled" data-panel-index="3">' +
            '<div class="jdaviz-expansion-panel-header">' +
            '<div class="jdaviz-expansion-panel-placeholder"></div>' +
            '</div>' +
            '</div>' +
            '<div class="jdaviz-expansion-panel disabled" data-panel-index="4">' +
            '<div class="jdaviz-expansion-panel-header">' +
            '<div class="jdaviz-expansion-panel-placeholder"></div>' +
            '</div>' +
            '</div>' +
            '</div>';
    }

    // Default sidebar content (can be overridden via config.customContentMap)
    // Read confSettings lazily so that jdaviz-conf-settings.js can load in any order
    function getConfSettings() {
        return (typeof window !== 'undefined' && window.__confSettings) || {};
    }

    var _sidebarContentCache = null;
    function getSidebarContent() {
        if (_sidebarContentCache) return _sidebarContentCache;
        var loaderFormats = getConfSettings().loaderFormats ||
            ['Auto', 'Image', 'Spectrum', 'Catalog', 'Cube'];
        _sidebarContentCache = {
        'loaders': {
            tabs: ['Data', 'Viewer'],
            content: [
                'Import data of multiple formats and from multiple sources into jdaviz.<br>' +
                formSelect('Source', 'source-select', ['File', 'Astroquery', 'URL']) +
                formSelect('Format', 'format-select', loaderFormats) +
                formButton('Load') +
                '<div class="jdaviz-api-snippet">ldr = jd.loaders[\'<i>source</i>\']\nldr.load()</div>',
                'Show data in a variety of different viewers custom built for exploring astronomical data.<br>' +
                formSelect('Viewer Type', 'viewer-type-select', ['Image', 'Scatter', '1D Spectrum', '2D Spectrum', 'Histogram']) +
                formButton('Create Viewer') +
                '<div class="jdaviz-api-snippet">vc = jd.new_viewers[\'<i>viewer_type</i>\']\nvc()</div>'
            ],
            learnMore: ['Learn more about data import \u2192', 'Explore viewer options \u2192'],
            scrollTarget: 'grid-loaders'
        },
        'save': {
            tabs: null,
            content: 'Export generated data, selected subsets, and viewers.' +
                '<div class="jdaviz-api-snippet">plg = jd.plugins[\'Export\']</div>',
            learnMore: 'See export options \u2192',
            scrollTarget: 'grid-export'
        },
        'settings': {
            tabs: ['Plot Options', 'Units'],
            content: [
                'dynamic:plot-options',
                'Convert and display data in different unit systems. Choose spectral units (wavelength, frequency, energy) and flux units appropriate for your analysis.<br>' +
                formSelect('Spectral Unit', 'spectral-unit-select', ['Angstrom', 'nm', 'micron']) +
                formSelect('Flux Unit', 'flux-unit-select', ['Jy', 'erg/s/cm\u00B2/\u00C5']) +
                '<div class="jdaviz-api-snippet">plg = jd.plugins[\'Display Units\']</div>'
            ],
            learnMore: ['View plot customization \u2192', 'Learn about units \u2192'],
            scrollTarget: 'grid-settings'
        },
        'info': {
            tabs: ['Metadata', 'Markers', 'Logger'],
            content: [
                'View FITS header information, WCS coordinates, and other metadata for loaded datasets.' +
                '<div class="jdaviz-api-snippet">plg = jd.plugins[\'Metadata\']</div>',
                'Interactively create markers in any viewer and information about the underlying data will be exposed and available to export into the notebook.' +
                '<div class="jdaviz-api-snippet">plg = jd.plugins[\'Markers\']\nplg.export_table()</div>',
                'System messages, warnings, and operation history. Monitor plugin execution, data loading status, and any issues that arise during analysis.' +
                '<div class="jdaviz-api-snippet">plg = jd.plugins[\'Logger\']\nplg.history</div>'
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
            content: 'Select regions of interest in your data, see that synced across all viewers, and use as inputs to data analysis tasks.<br>' +
                formSelect('Subset', 'subset-select', ['Subset 1', 'Subset 2']) +
                formButton('Recenter') +
                formButton('Delete') +
                '<div class="jdaviz-api-snippet">plg = jd.plugins[\'Subset Tools\']</div>',
            learnMore: 'Learn about subsets \u2192',
            scrollTarget: 'grid-subsets'
        }
        };
        return _sidebarContentCache;
    }

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

        html += '<div class="jdaviz-api-snippet">plg = jd.plugins[\'Plot Options\']</div>';

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
        var contentMap = getSidebarContent();
        if (instance.config.customContentMap) {
            var custom = instance.config.customContentMap;
            if (typeof custom === 'string') {
                try { custom = JSON.parse(custom); } catch(e) { custom = {}; }
            }
            contentMap = Object.assign({}, getSidebarContent(), custom);
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
            var panelName = state.openPanel || null;
            state.openPanel = null;
            contentHtml = generatePluginPanelsHTML(panelName);
        }

        contentEl.innerHTML = contentHtml;

        // Wire up expansion panel clicks (both old and new style)
        contentEl.querySelectorAll('.jdaviz-expansion-panel:not(.disabled) .jdaviz-expansion-panel-header').forEach(function(hdr) {
            hdr.addEventListener('click', function(ev) {
                if (ev.isTrusted) instance.pause();
                var panel = hdr.closest('.jdaviz-expansion-panel');
                panel.classList.toggle('expanded');
                var contentDiv = panel.querySelector('.jdaviz-expansion-panel-content');
                if (contentDiv) contentDiv.classList.toggle('expanded');
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
        // Clear openPanel so the animated show-sidebar always shows the generic plugin list;
        // set-plugin / open-panel steps are responsible for revealing specific plugin content.
        if (sidebarType === 'plugins') {
            getState(this).openPanel = null;
        }
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

        var data = getSidebarContent()[state.currentSidebar];
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
     * Re-renders the plugin panels sidebar with the named plugin expanded.
     * step.value = plugin name (e.g. "Gaussian Smooth")
     */
    WireframeDemo.registerAction('open-panel', function(step, el, contentRoot) {
        var state = getState(this);
        state.openPanel = step.value;
        // Re-render the plugins sidebar so the correct plugin panel is expanded
        renderSidebar(this, 'plugins', 0);
    });

    /**
     * set-plugin: Pre-load the default plugin for manual sidebar interactions.
     * Used in init-steps-json to configure which plugin content appears when the
     * user manually opens the plugins sidebar (before or after the animation).
     * Does not open the sidebar — no visible change on init.
     * step.value = plugin name (e.g. "Gaussian Smooth")
     */
    WireframeDemo.registerAction('set-plugin', function(step, el, contentRoot) {
        getState(this).defaultPlugin = step.value;
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
                                // For plugins sidebar, use defaultPlugin if one was pre-loaded
                                // via the set-plugin init step (user opened manually)
                                if (sidebarType === 'plugins' && state.defaultPlugin && !state.openPanel) {
                                    state.openPanel = state.defaultPlugin;
                                }
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
                if (versionEl && getConfSettings().version) {
                    versionEl.textContent = 'v' + getConfSettings().version;
                }

                // Wire up search bar click to open Sphinx search dialog
                var searchInput = root.querySelector('.jdaviz-toolbar-search');
                if (searchInput) {
                    searchInput.addEventListener('click', function() {
                        var instance = e.detail.instance;
                        if (instance) instance.pause();
                        // Try pydata-sphinx-theme search button first
                        var searchButton = document.querySelector(
                            'button.search-button, .search-button, ' +
                            'button[aria-label="Search"], button.search-button__button'
                        );
                        if (searchButton) {
                            searchButton.click();
                        } else {
                            // Fallback: try to focus the theme search input
                            var themeInput = document.querySelector(
                                'input[type="search"], input.search-input, #searchbox input'
                            );
                            if (themeInput) themeInput.focus();
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
