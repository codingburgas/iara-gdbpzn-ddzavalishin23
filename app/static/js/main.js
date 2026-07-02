// ============================================================================
// MAIN.JS – Navigation, dropdown, and mobile interactions
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {

    // ---- Hamburger menu toggle ----
    const toggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (toggle && navLinks) {
        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            navLinks.classList.toggle('open');
        });

        // Close hamburger menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navLinks.contains(e.target) && !toggle.contains(e.target)) {
                navLinks.classList.remove('open');
            }
        });
    }

    // ---- User dropdown toggle (mobile only) ----
    const dropdownToggle = document.querySelector('.dropdown-toggle');
    const dropdownMenu = document.querySelector('.dropdown-menu');

    if (dropdownToggle && dropdownMenu) {
        // Toggle dropdown on click
        dropdownToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            // Only toggle on mobile (screen width <= 768px)
            if (window.innerWidth <= 768) {
                dropdownMenu.classList.toggle('mobile-open');
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                if (!dropdownToggle.contains(e.target) && !dropdownMenu.contains(e.target)) {
                    dropdownMenu.classList.remove('mobile-open');
                }
            }
        });

        // Also close dropdown when a link inside it is clicked (on mobile)
        const dropdownItems = dropdownMenu.querySelectorAll('.dropdown-item');
        dropdownItems.forEach(function(item) {
            item.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    dropdownMenu.classList.remove('mobile-open');
                }
            });
        });
    }

    // ---- Close dropdown on resize (if screen becomes desktop) ----
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && dropdownMenu) {
            dropdownMenu.classList.remove('mobile-open');
        }
        if (window.innerWidth > 768 && navLinks) {
            navLinks.classList.remove('open');
        }
    });

});