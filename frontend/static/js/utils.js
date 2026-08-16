// Smart Wardrobe - Shared Utilities
// Single source of truth for common functions

// ========== FORMATTERS ==========

export function formatType(type) {
    const map = { top: 'Top', bottom: 'Bottom', dress: 'Dress', outerwear: 'Outerwear', shoes: 'Shoes', accessory: 'Accessory' };
    return map[type] || type;
}

export function formatPattern(pattern) {
    const map = { solid: 'Solid', striped: 'Striped', checked: 'Checked', floral: 'Floral', polka_dot: 'Polka Dot', geometric: 'Geometric', abstract: 'Abstract', animal_print: 'Animal Print', paisley: 'Paisley', houndstooth: 'Houndstooth' };
    return map[pattern] || pattern;
}

export function formatFormality(formality) {
    const map = { 1: 'Casual', 2: 'Smart Casual', 3: 'Business Casual', 4: 'Formal', 5: 'Gala' };
    return map[formality] || `Level ${formality}`;
}

// ========== HTML ESCAPING ==========

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== TOAST ICONS ==========

export function getToastIcon(type) {
    switch (type) {
        case 'success':
            return '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>';
        case 'error':
            return '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>';
        case 'warning':
            return '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>';
        default:
            return '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>';
    }
}

// ========== TOAST SYSTEM ==========

let toastContainer = null;

export function getToastContainer() {
    if (!toastContainer) {
        toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container';
            toastContainer.setAttribute('aria-live', 'polite');
            toastContainer.setAttribute('aria-atomic', 'true');
            document.body.appendChild(toastContainer);
        }
    }
    return toastContainer;
}

export function showToast(message, type = 'info', duration = 4000) {
    const container = getToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    toast.innerHTML = `
        <svg class="toast-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${getToastIcon(type)}</svg>
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close" aria-label="Close"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.style.animation = 'toastIn 0.2s var(--ease-out) reverse';
        setTimeout(() => toast.remove(), 200);
    });

    container.appendChild(toast);
    toast.offsetHeight; // Trigger reflow

    if (duration > 0) {
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'toastIn 0.2s var(--ease-out) reverse';
                setTimeout(() => toast.remove(), 200);
            }
        }, duration);
    }
}

// ========== MODAL HELPERS ==========

export function openModal(modal) {
    if (!modal) return;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    const focusable = modal.querySelector('button, input, select, textarea, [href]');
    if (focusable) focusable.focus();
}

export function closeModal(modal) {
    if (!modal) return;
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// ========== UTILITIES ==========

export function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => { clearTimeout(timeout); func(...args); };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

export function triggerHaptic(type = 'light') {
    if (navigator.vibrate) {
        const patterns = { light: [10], medium: [20], heavy: [30], success: [10, 50, 10], error: [30, 30, 30] };
        navigator.vibrate(patterns[type] || patterns.light);
    }
}

// ========== ANIMATION HELPERS ==========

/**
 * Staggered animation for grid items
 * @param {NodeList|Array} elements - Elements to animate
 * @param {number} baseDelay - Base delay in ms
 * @param {number} staggerDelay - Stagger delay in ms
 */
export function staggerAnimation(elements, baseDelay = 0, staggerDelay = 50) {
    if (prefersReducedMotion()) return;

    elements.forEach((el, i) => {
        el.style.animationDelay = `${baseDelay + i * staggerDelay}ms`;
        el.style.animationFillMode = 'both';
    });
}

/**
 * Observe elements for scroll reveal
 * @param {string} selector - CSS selector for elements
 * @param {Object} options - IntersectionObserver options
 */
export function observeReveal(selector = '.reveal-on-scroll', options = {}) {
    if (prefersReducedMotion()) {
        document.querySelectorAll(selector).forEach(el => el.classList.add('revealed'));
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px', ...options });

    document.querySelectorAll(selector).forEach(el => observer.observe(el));
}

// ========== SPRING (apple-design gesture physics) ==========
// Lightweight velocity-aware spring integrator - no external animation
// library needed (see /mnt/skills/user/apple-design). Used to settle
// anything the user just dragged (garment swipe reject/exit, dial snap) so
// the release inherits real momentum instead of easing on a fixed curve.

/**
 * Animates a single numeric value from `from` toward `to`, inheriting
 * `velocity` from the gesture that released it, via a damped-spring
 * integrator (critically damped by default - no overshoot). Calls
 * `onUpdate(value)` every frame and `onComplete()` once settled.
 * Respects prefers-reduced-motion by jumping straight to the target.
 * @param {Object} opts
 * @param {number} opts.from
 * @param {number} opts.to
 * @param {number} [opts.velocity=0] - initial velocity in value-units/sec (e.g. px/s)
 * @param {number} [opts.damping=1] - 1 = critically damped; <1 = overshoot/bounce (e.g. 0.8)
 * @param {number} [opts.response=0.3] - seconds to reach target; lower = snappier
 * @param {(value:number)=>void} opts.onUpdate
 * @param {()=>void} [opts.onComplete]
 * @returns {() => number} cancel function - stops the spring and returns the
 *   live value at that instant, so an interrupting gesture can grab the
 *   *presentation* value instead of jumping to the old target (apple-design §3).
 */
export function animateSpring({ from, to, velocity = 0, damping = 1, response = 0.3, onUpdate, onComplete }) {
    let value = from;

    if (prefersReducedMotion()) {
        onUpdate(to);
        if (onComplete) onComplete();
        return () => to;
    }

    const angularFreq = (2 * Math.PI) / response;
    const stiffness = angularFreq * angularFreq;
    const dampingCoef = 2 * damping * angularFreq;

    let v = velocity;
    let cancelled = false;
    let rafId = null;
    let lastTime = performance.now();

    function step(now) {
        if (cancelled) return;
        const dt = Math.min((now - lastTime) / 1000, 1 / 30); // clamp huge frame gaps (e.g. tab switch)
        lastTime = now;

        // Semi-implicit Euler integration of a damped spring: a = -k·x - c·v
        const displacement = value - to;
        const accel = -stiffness * displacement - dampingCoef * v;
        v += accel * dt;
        value += v * dt;

        onUpdate(value);

        if (Math.abs(value - to) < 0.5 && Math.abs(v) < 5) {
            value = to;
            onUpdate(to);
            if (onComplete) onComplete();
            return;
        }
        rafId = requestAnimationFrame(step);
    }

    rafId = requestAnimationFrame(step);

    return () => {
        cancelled = true;
        if (rafId) cancelAnimationFrame(rafId);
        return value;
    };
}

// ========== FORM HELPERS ==========

/**
 * Serialize form data to object
 * @param {HTMLFormElement} form
 * @returns {Object}
 */
export function formDataToObject(form) {
    const data = {};
    new FormData(form).forEach((value, key) => {
        if (data[key]) {
            // Handle multiple values (arrays)
            if (!Array.isArray(data[key])) data[key] = [data[key]];
            data[key].push(value);
        } else {
            data[key] = value;
        }
    });
    return data;
}

/**
 * Validate form fields and show inline errors
 * @param {HTMLFormElement} form
 * @returns {boolean} - true if valid
 */
export function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        const errorEl = document.getElementById(`${field.id}Error`);
        if (!field.value.trim()) {
            field.setAttribute('aria-invalid', 'true');
            if (errorEl) {
                errorEl.textContent = 'This field is required';
                errorEl.hidden = false;
            }
            isValid = false;
        } else {
            field.removeAttribute('aria-invalid');
            if (errorEl) errorEl.hidden = true;
        }
    });

    return isValid;
}

/**
 * Clear form validation state
 * @param {HTMLFormElement} form
 */
export function clearFormValidation(form) {
    form.querySelectorAll('[aria-invalid]').forEach(field => {
        field.removeAttribute('aria-invalid');
    });
    form.querySelectorAll('.field-error').forEach(el => el.hidden = true);
}

// ========== IMAGE HELPERS ==========

/**
 * Resolves the URL to display a garment's photo - prefers the raw upload
 * (higher quality) and falls back to the processed/masked version. Shared
 * by every card renderer (settings grid, kiosk outfit/packing/wardrobe
 * views) so there's a single place that knows the /images/raw|processed
 * routing and the path-basename stripping.
 * @param {Object} garment - needs raw_image_path and/or processed_image_path
 * @returns {string|null}
 */
export function garmentImageUrl(garment) {
    if (garment.raw_image_path) {
        return `/images/raw/${garment.raw_image_path.replace(/^.*[\\\/]/, '')}`;
    }
    if (garment.processed_image_path) {
        return `/images/processed/garments/${garment.processed_image_path.replace(/^.*[\\\/]/, '')}`;
    }
    return null;
}

/**
 * Create object URL for file preview
 * @param {File} file
 * @returns {Promise<string>}
 */
export function createImagePreview(file) {
    return new Promise((resolve, reject) => {
        if (!file.type.startsWith('image/')) {
            reject(new Error('Not an image file'));
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
    });
}

/**
 * Validate image file
 * @param {File} file
 * @param {Object} options - { maxSize: number, allowedTypes: string[] }
 * @returns {Object} - { valid: boolean, error?: string }
 */
export function validateImageFile(file, options = {}) {
    const { maxSize = 10 * 1024 * 1024, allowedTypes = ['image/jpeg', 'image/png', 'image/webp'] } = options;

    if (!allowedTypes.includes(file.type)) {
        return { valid: false, error: 'Invalid file type. Please use JPEG, PNG, or WebP.' };
    }

    if (file.size > maxSize) {
        return { valid: false, error: `File too large. Maximum size is ${Math.round(maxSize / 1024 / 1024)}MB.` };
    }

    return { valid: true };
}