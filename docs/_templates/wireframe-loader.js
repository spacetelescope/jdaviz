// Wireframe Dynamic Loader
// This script loads and injects the wireframe components into the page

(function() {
    'use strict';
    
    // Function to load CSS
    function loadCSS(href) {
        return new Promise(function(resolve, reject) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            link.onload = resolve;
            link.onerror = reject;
            document.head.appendChild(link);
        });
    }
    
    // Function to load HTML and inject into target
    function loadHTML(url, targetSelector) {
        return fetch(url)
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                return response.text();
            })
            .then(function(html) {
                const target = document.querySelector(targetSelector);
                if (target) {
                    target.innerHTML = html;
                } else {
                    console.error('Target element not found:', targetSelector);
                }
            });
    }
    
    // Function to load and execute JavaScript
    function loadScript(src) {
        return new Promise(function(resolve, reject) {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.body.appendChild(script);
        });
    }
    
    // Main initialization function
    function initWireframe() {
        // Get the base path for template files
        const basePath = '_templates/';
        
        // Load CSS first
        loadCSS(basePath + 'wireframe-demo.css')
            .then(function() {
                // Then load HTML
                return loadHTML(basePath + 'wireframe-base.html', '#wireframe-container-placeholder');
            })
            .then(function() {
                // Finally load and execute JavaScript
                return loadScript(basePath + 'wireframe-controller.js');
            })
            .catch(function(error) {
                console.error('Error loading wireframe components:', error);
            });
    }
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWireframe);
    } else {
        initWireframe();
    }
})();
