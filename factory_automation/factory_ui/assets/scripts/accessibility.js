function enhanceAccessibility() {
    // Add ARIA labels to buttons
    document.querySelectorAll('button').forEach(btn => {
        if (btn.textContent.includes('Refresh')) {
            btn.setAttribute('aria-label', 'Refresh queue list');
        } else if (btn.textContent.includes('Approve')) {
            btn.setAttribute('aria-label', 'Approve this recommendation');
        } else if (btn.textContent.includes('Reject')) {
            btn.setAttribute('aria-label', 'Reject this recommendation');
        } else if (btn.textContent.includes('Request')) {
            btn.setAttribute('aria-label', 'Request more information');
        }
    });
    
    // Add ARIA labels to form inputs
    document.querySelectorAll('input, textarea, select').forEach(input => {
        if (!input.getAttribute('aria-label') && !input.getAttribute('aria-labelledby')) {
            const label = input.closest('label') || 
                         input.previousElementSibling || 
                         document.querySelector(`label[for="${input.id}"]`);
            if (label && label.textContent) {
                input.setAttribute('aria-label', label.textContent.trim());
            }
        }
    });
    
    // Make tables more accessible
    document.querySelectorAll('table').forEach(table => {
        if (!table.getAttribute('role')) {
            table.setAttribute('role', 'table');
        }
        
        // Add scope to headers
        table.querySelectorAll('th').forEach(th => {
            if (!th.getAttribute('scope')) {
                th.setAttribute('scope', 'col');
            }
        });
        
        // Add row headers where applicable
        table.querySelectorAll('tbody tr').forEach(row => {
            const firstCell = row.querySelector('td:first-child');
            if (firstCell && !firstCell.querySelector('input')) {
                firstCell.setAttribute('scope', 'row');
            }
        });
    });
    
    // Add keyboard navigation to queue items
    document.querySelectorAll('.queue-item').forEach(item => {
        item.setAttribute('tabindex', '0');
        item.setAttribute('role', 'button');
        
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                item.click();
            }
        });
    });
    
    // Add live region for updates
    if (!document.querySelector('[aria-live="polite"]')) {
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.id = 'live-region';
        document.body.appendChild(liveRegion);
    }
    
    // Announce changes to screen readers
    function announce(message) {
        const liveRegion = document.getElementById('live-region');
        if (liveRegion) {
            liveRegion.textContent = message;
            setTimeout(() => {
                liveRegion.textContent = '';
            }, 1000);
        }
    }
    
    // Add skip to content link
    if (!document.querySelector('.skip-to-content')) {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-to-content';
        skipLink.textContent = 'Skip to main content';
        document.body.insertBefore(skipLink, document.body.firstChild);
    }
    
    // Ensure proper heading hierarchy
    let lastLevel = 0;
    document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
        const level = parseInt(heading.tagName.charAt(1));
        if (level > lastLevel + 1) {
            console.warn(`Heading hierarchy issue: ${heading.tagName} follows h${lastLevel}`);
        }
        lastLevel = level;
    });
    
    // Add proper form labels
    document.querySelectorAll('form').forEach(form => {
        form.querySelectorAll('input, select, textarea').forEach(field => {
            if (!field.id) {
                field.id = `field_${Math.random().toString(36).substr(2, 9)}`;
            }
            
            let label = document.querySelector(`label[for="${field.id}"]`);
            if (!label) {
                const fieldContainer = field.closest('.form-group') || field.parentElement;
                const labelText = fieldContainer?.querySelector('label')?.textContent;
                if (labelText) {
                    field.setAttribute('aria-label', labelText);
                }
            }
        });
    });
    
    // Ensure images have alt text
    document.querySelectorAll('img').forEach(img => {
        if (!img.alt) {
            if (img.src.includes('placeholder')) {
                img.alt = 'Placeholder image';
            } else if (img.closest('.inventory-image')) {
                img.alt = 'Inventory item image';
            } else {
                img.alt = 'Image';
            }
        }
    });
    
    // Add landmarks
    const main = document.querySelector('main');
    if (!main) {
        const mainContent = document.getElementById('main-content');
        if (mainContent && !mainContent.hasAttribute('role')) {
            mainContent.setAttribute('role', 'main');
        }
    }
    
    // Color contrast check (development only)
    if (window.location.hostname === 'localhost') {
        document.querySelectorAll('*').forEach(el => {
            const style = window.getComputedStyle(el);
            const bg = style.backgroundColor;
            const fg = style.color;
            
            if (bg !== 'rgba(0, 0, 0, 0)' && fg !== 'rgba(0, 0, 0, 0)') {
                // This is a simplified check - real contrast checking is complex
                // Consider using axe-core or similar for production
            }
        });
    }
}

// Run accessibility enhancements when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceAccessibility);
} else {
    enhanceAccessibility();
}

// Re-run when Gradio updates the DOM
const observer = new MutationObserver((mutations) => {
    // Debounce to avoid running too frequently
    clearTimeout(window.accessibilityTimeout);
    window.accessibilityTimeout = setTimeout(enhanceAccessibility, 100);
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

// Handle dynamic content updates
document.addEventListener('gradio:change', enhanceAccessibility);
document.addEventListener('gradio:submit', enhanceAccessibility);

// Keyboard navigation improvements
document.addEventListener('keydown', (e) => {
    // Escape key closes modals
    if (e.key === 'Escape') {
        const modal = document.querySelector('.image-modal-overlay.show');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        }
    }
    
    // Tab trap for modals
    if (e.key === 'Tab') {
        const modal = document.querySelector('.image-modal-overlay.show');
        if (modal) {
            const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (focusable.length) {
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        }
    }
});

// Ensure table radio buttons work with keyboard and update properly
const tableObserver = new MutationObserver(() => {
    document.querySelectorAll('.recommendation-table input[type="radio"]').forEach(radio => {
        // Make sure radio buttons are keyboard accessible
        if (!radio.hasAttribute('tabindex')) {
            radio.setAttribute('tabindex', '0');
        }
        
        // Add keyboard support
        if (!radio.dataset.keyboardEnabled) {
            radio.dataset.keyboardEnabled = 'true';
            radio.addEventListener('keydown', (e) => {
                if (e.key === ' ' || e.key === 'Enter') {
                    e.preventDefault();
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        }
    });
});
tableObserver.observe(document.body, { childList: true, subtree: true });