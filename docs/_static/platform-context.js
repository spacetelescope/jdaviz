/**
 * Platform Context Manager for Jdaviz Documentation
 *
 * This script maintains platform context (desktop, mast, jupyter, platform) across
 * documentation pages using a hybrid approach:
 * 1. Query parameters for shareable URLs
 * 2. sessionStorage for persistence across navigation
 * 3. Automatic link interception to maintain context
 */

(function() {
    'use strict';

    // Get platform from query parameter or sessionStorage
    const urlParams = new URLSearchParams(window.location.search);
    const platformFromUrl = urlParams.get('platform');
    const platformFromStorage = sessionStorage.getItem('jdaviz-platform');

    // URL parameter takes precedence over storage
    const currentPlatform = platformFromUrl || platformFromStorage || null;

    // Store platform if detected
    if (currentPlatform) {
        sessionStorage.setItem('jdaviz-platform', currentPlatform);

        // Add platform class to body for CSS targeting (when DOM is ready)
        if (document.body) {
            document.body.classList.add('platform-' + currentPlatform);
            document.body.setAttribute('data-jdaviz-platform', currentPlatform);
        } else {
            // DOM not ready yet, wait for it
            document.addEventListener('DOMContentLoaded', function() {
                document.body.classList.add('platform-' + currentPlatform);
                document.body.setAttribute('data-jdaviz-platform', currentPlatform);
            });
        }
    }

    // Function to append platform parameter to URL
    function appendPlatformParam(url) {
        if (!currentPlatform) return url;

        try {
            const urlObj = new URL(url, window.location.origin);

            // Only modify internal links
            if (urlObj.origin !== window.location.origin) {
                return url;
            }

            // Don't modify if already has platform parameter
            if (urlObj.searchParams.has('platform')) {
                return url;
            }

            urlObj.searchParams.set('platform', currentPlatform);
            return urlObj.toString();
        } catch (e) {
            // If URL parsing fails, return original
            return url;
        }
    }

    // Intercept internal links when page loads
    function interceptLinks() {
        if (!currentPlatform) return;

        // Get all internal links
        const internalLinks = document.querySelectorAll('a[href^="/"], a[href^="./"], a[href^="../"], a:not([href^="http"]):not([href^="#"]):not([target="_blank"])');

        internalLinks.forEach(function(link) {
            // Skip if it's an anchor link only
            if (link.getAttribute('href').startsWith('#')) return;

            // Skip if it's already modified
            if (link.hasAttribute('data-platform-modified')) return;

            const originalHref = link.getAttribute('href');
            const newHref = appendPlatformParam(originalHref);

            if (newHref !== originalHref) {
                link.setAttribute('href', newHref);
                link.setAttribute('data-platform-modified', 'true');
            }
        });
    }

    // Run on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', interceptLinks);
    } else {
        interceptLinks();
    }

    // Also intercept dynamically added links
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    interceptLinks();
                }
            });
        });

        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
        } else {
            document.addEventListener('DOMContentLoaded', function() {
                observer.observe(document.body, { childList: true, subtree: true });
            });
        }
    }

    // Expose utility function globally for manual use
    window.jdavizPlatform = {
        get: function() {
            return currentPlatform;
        },
        set: function(platform) {
            if (platform) {
                sessionStorage.setItem('jdaviz-platform', platform);
                window.location.reload();
            }
        },
        clear: function() {
            sessionStorage.removeItem('jdaviz-platform');
            document.body.className = document.body.className.replace(/platform-\w+/g, '');
            document.body.removeAttribute('data-jdaviz-platform');
        },
        appendToUrl: appendPlatformParam
    };

})();
