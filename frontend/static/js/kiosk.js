// Smart Wardrobe - Kiosk UI
// Adaptive interface for /kiosk route - handles both dual-screen and single-screen modes

import { api } from './api.js';
import { t } from './i18n.js';
import {
    formatType, formatPattern, formatFormality, escapeHtml,
    showToast, openModal, closeModal, prefersReducedMotion, triggerHaptic,
    staggerAnimation, observeReveal
} from './utils.js';

/**
 * Kiosk UI Controller
 * Handles both dual-screen (visualization + touch panel) and single-screen modes
 */
class KioskUI {
    constructor() {
        this.occasions = ['casual', 'work', 'party', 'date', 'formal', 'wedding'];
        this.seasons = ['all_season', 'spring', 'summer', 'autumn', 'winter'];

        this.state = {
            currentOutfit: null,
            selectedOccasion: 'casual',
            selectedSeason: 'all_season',
            selectedFormality: null,
            isLoading: false,
            layoutMode: 'auto', // 'auto', 'dual', 'single'
            screenWidth: window.innerWidth,
            screenHeight: window.innerHeight,
            stats: {}
        };

        this.elements = {};
        this.resizeObserver = null;

        this.init();
    }

    async init() {
        this.cacheElements();
        this.bindEvents();
        this.detectLayoutMode();
        this.setupResizeObserver();

        // Load initial outfit - today's auto-generated look, falling back
        // to a fresh recommendation if it can't be fetched
        await this.loadDailyOutfit();

        // Load stats periodically
        this.loadStats();
        setInterval(() => this.loadStats(), 60000);

        // Setup scroll reveal
        observeReveal('.reveal-on-scroll');
    }

    cacheElements() {
        // Main containers
        this.elements.visualizationPanel = document.querySelector('.visualization-panel');
        this.elements.touchPanel = document.querySelector('.touch-panel');
        this.elements.appContainer = document.querySelector('.app-container');

        // Visualization elements
        this.elements.outfitDisplay = document.querySelector('.outfit-display');
        this.elements.refreshBtn = document.getElementById('refreshBtn');

        // Occasion dial (left) + season dial (right) — both are the same
        // compact vertical-swipe component (see bindDialGestures)
        this.elements.occasionDial = document.getElementById('occasionDial');
        this.elements.occasionDialTrack = document.getElementById('occasionDialTrack');
        this.elements.seasonDial = document.getElementById('seasonDial');
        this.elements.seasonDialTrack = document.getElementById('seasonDialTrack');

        // Touch panel elements
        this.elements.generateBtn = document.getElementById('generateBtn');
        this.elements.favoriteBtn = document.getElementById('favoriteBtn');
        this.elements.outfitDescription = document.getElementById('outfitDescription');
        this.elements.outfitRating = document.getElementById('outfitRating');
        this.elements.packingBtn = document.getElementById('packingBtn');
        this.elements.wardrobeBtn = document.getElementById('wardrobeBtn');

        // Stats
        this.elements.totalGarments = document.getElementById('totalGarments');
        this.elements.totalOutfits = document.getElementById('totalOutfits');
        this.elements.avgScore = document.getElementById('avgScore');
        this.elements.favorites = document.getElementById('favorites');

        // Modals
        this.elements.packingModal = document.getElementById('packingModal');
        this.elements.packingResultModal = document.getElementById('packingResultModal');
        this.elements.wardrobeModal = document.getElementById('wardrobeModal');
        this.elements.packingForm = document.getElementById('packingForm');
        this.elements.packingResultBody = document.getElementById('packingResultBody');
        this.elements.wardrobeGrid = document.getElementById('wardrobeGrid');
    }

    bindEvents() {
        // Refresh button
        if (this.elements.refreshBtn) {
            this.elements.refreshBtn.addEventListener('click', () => this.loadOutfit());
        }

        // Generate button (touch panel)
        if (this.elements.generateBtn) {
            this.elements.generateBtn.addEventListener('click', () => this.loadOutfit());
        }

        // Favorite (heart) button
        if (this.elements.favoriteBtn) {
            this.elements.favoriteBtn.addEventListener('click', () => this.toggleFavorite());
        }

        // Packing button
        if (this.elements.packingBtn) {
            this.elements.packingBtn.addEventListener('click', () => this.openPackingModal());
        }

        // Wardrobe button
        if (this.elements.wardrobeBtn) {
            this.elements.wardrobeBtn.addEventListener('click', () => this.openWardrobeModal());
        }

        // Modal close buttons
        document.querySelectorAll('.modal-close, [data-modal-close]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this.closeModal(modal);
            });
        });

        // Modal overlays
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this.closeModal(modal);
            });
        });

        // Packing form
        if (this.elements.packingForm) {
            this.elements.packingForm.addEventListener('submit', (e) => this.handlePackingSubmit(e));
        }

        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal:not(.hidden)').forEach(modal => this.closeModal(modal));
            }
        });

        // Occasion dial (left) + season dial (right)
        this.renderDial('occasion');
        this.renderDial('season');
        this.bindDialGestures('occasion');
        this.bindDialGestures('season');

        // Re-render dynamic labels when language changes
        document.addEventListener('i18n:changed', () => {
            this.renderDial('occasion');
            this.renderDial('season');
        });
    }

    detectLayoutMode() {
        const width = window.innerWidth;
        const height = window.innerHeight;

        this.state.screenWidth = width;
        this.state.screenHeight = height;

        // Auto-detect layout based on screen size and aspect ratio
        // Dual screen mode: wide screens (landscape tablets, dual monitors)
        // Single screen mode: narrow screens (phones, portrait tablets)

        let mode = 'single';

        if (width >= 1024 && width > height) {
            // Wide landscape - dual panel
            mode = 'dual';
        } else if (width >= 768 && height >= 600) {
            // Tablet landscape - dual panel
            mode = 'dual';
        }

        this.setLayoutMode(mode);
    }

    setLayoutMode(mode) {
        if (mode === this.state.layoutMode) return;

        this.state.layoutMode = mode;
        const container = this.elements.appContainer;

        if (!container) return;

        // Remove all layout classes
        container.classList.remove('layout-dual', 'layout-single');

        // Add new layout class
        container.classList.add(`layout-${mode}`);

        // Update CSS custom properties for dynamic layout
        document.documentElement.style.setProperty('--layout-mode', mode);

        // Trigger reflow for smooth transition
        container.offsetHeight;

        console.log(`Layout mode changed to: ${mode}`);
    }

    setupResizeObserver() {
        // Debounced resize handler
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.detectLayoutMode();
            }, 150);
        });
    }

    // ========== OUTFIT LOADING ==========

    async loadDailyOutfit() {
        if (this.state.isLoading) return;

        this.state.isLoading = true;
        this.showLoading();

        try {
            const outfit = await api.getDailyOutfit();
            this.state.currentOutfit = outfit;
            this.state.selectedOccasion = outfit.occasion;
            this.state.selectedSeason = outfit.season;
            this.renderOutfit(outfit);
            this.updateDialPosition('occasion', false);
            this.updateDialPosition('season', false);
        } catch (error) {
            console.error('Error loading daily outfit, falling back to a fresh recommendation:', error);
            this.state.isLoading = false;
            await this.loadOutfit();
            return;
        } finally {
            this.state.isLoading = false;
        }
    }

    async loadOutfit() {
        if (this.state.isLoading) return;

        this.state.isLoading = true;
        this.showLoading();

        try {
            const params = {
                occasion: this.state.selectedOccasion,
                season: this.state.selectedSeason,
                top_n: 1
            };

            if (this.state.selectedFormality) {
                params.formality = this.state.selectedFormality;
            }

            const response = await api.recommendOutfits(params);

            if (response.outfits && response.outfits.length > 0) {
                this.state.currentOutfit = response.outfits[0];
                this.renderOutfit(this.state.currentOutfit);
            } else {
                this.showEmptyState();
            }
        } catch (error) {
            console.error('Error loading outfit:', error);
            this.showError(error.message);
        } finally {
            this.state.isLoading = false;
        }
    }

    showLoading() {
        const display = this.elements.outfitDisplay;
        if (!display) return;

        display.innerHTML = `
            <div class="outfit-loading">
                <div class="skeleton">
                    <div class="skeleton-image"></div>
                    <div class="skeleton-info">
                        <div class="skeleton-title"></div>
                        <div class="skeleton-tags">
                            <div class="skeleton-tag"></div>
                            <div class="skeleton-tag"></div>
                            <div class="skeleton-tag"></div>
                        </div>
                    </div>
                </div>
                <div class="skeleton" style="margin-top: 16px;">
                    <div class="skeleton-image"></div>
                    <div class="skeleton-info">
                        <div class="skeleton-title" style="width: 50%;"></div>
                        <div class="skeleton-tags"><div class="skeleton-tag"></div></div>
                    </div>
                </div>
            `;
    }

    showEmptyState() {
        const display = this.elements.outfitDisplay;
        if (!display) return;

        display.innerHTML = `
            <div class="outfit-empty">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <h3>Not enough garments</h3>
                <p>Add at least 2 garments to your wardrobe to generate outfits</p>
                <button class="btn btn-primary" onclick="kioskUI.loadOutfit()">Retry</button>
            </div>
        `;
    }

    showError(message) {
        const display = this.elements.outfitDisplay;
        if (!display) return;

        display.innerHTML = `
            <div class="outfit-empty">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
                <h3>Error loading</h3>
                <p>${escapeHtml(message)}</p>
                <button class="btn btn-primary" onclick="kioskUI.loadOutfit()">Retry</button>
            </div>
        `;
    }

    renderOutfit(outfit) {
        const score = outfit.score || 0;

        let html = `
            <div class="outfit-result">
                <div class="outfit-header">
                    <h2 class="outfit-name">${escapeHtml(outfit.name || 'Recommended Outfit')}</h2>
                    <div class="outfit-score">
                        <span class="score-value">${score.toFixed(0)}</span>
                        <span class="score-label">/100</span>
                    </div>
                </div>
                <div class="outfit-garments">
        `;

        // OutfitResponse doesn't have a flat `garments` array - each garment
        // is nested at item.garment inside outfit.items (same shape the
        // swipe-swap handler below already relies on for garment_id).
        if (outfit.items && outfit.items.length > 0) {
            outfit.items.forEach(item => {
                const garment = item.garment;
                if (!garment) return;
                const colorHex = garment.color_hex || '#666666';
                // Use raw_image_path for high-quality display - serve via /images/raw/
                const imageUrl = garment.raw_image_path
                    ? `/images/raw/${garment.raw_image_path.replace(/^.*[\\\/]/, '')}`
                    : garment.processed_image_path
                        ? `/images/processed/garments/${garment.processed_image_path.replace(/^.*[\\\/]/, '')}`
                        : null;

                html += `
                    <article class="garment-card" data-garment-id="${garment.id}" data-garment-type="${garment.type}">
                        ${imageUrl
                            ? `<img class="garment-image" src="${imageUrl}" alt="${escapeHtml(garment.name)}" loading="lazy">`
                            : `<div class="garment-image" style="background-color: ${colorHex};"></div>`
                        }
                        <div class="garment-info">
                            <h3 class="garment-name">${escapeHtml(garment.name)}</h3>
                            <div class="garment-meta">
                                <span class="tag tag-type">${formatType(garment.type)}</span>
                                <span class="tag tag-color" style="--tag-color: ${colorHex}">${escapeHtml(garment.color_name)}</span>
                                <span class="tag">${formatPattern(garment.pattern)}</span>
                                <span class="tag">${formatFormality(garment.formality)}</span>
                            </div>
                        </div>
                    </article>
                `;
            });
        }

        html += `
                </div>
        `;

        // AI Tips if available (style hints stay inside the visual card)
        if (outfit.ai_tips && outfit.ai_tips.length > 0) {
            html += `
                <div class="outfit-tips">
                    <h3>Style Tips:</h3>
                    <ul class="tips-list">
            `;
            outfit.ai_tips.forEach(tip => {
                html += `<li class="tip-item">${escapeHtml(tip)}</li>`;
            });
            html += `
                    </ul>
                </div>
            `;
        }

        html += `
            </div>
        `;

        const display = this.elements.outfitDisplay;
        if (display) {
            display.innerHTML = html;
            this.bindGarmentSwipeGestures();
        }

        // Description + favorite state + rating live outside the outfit card
        // (persistent DOM, see kiosk.html) so they survive garment swaps.
        this.renderOutfitDescription(outfit);
        this.resetFavoriteButton();
        this.renderStarRating(outfit);
    }

    // ========== DESCRIPTION ==========

    renderOutfitDescription(outfit) {
        const el = this.elements.outfitDescription;
        if (!el) return;

        if (!outfit.score_breakdown) {
            el.textContent = '';
            return;
        }

        const b = outfit.score_breakdown;
        el.innerHTML = `<p>Color ${b.color_harmony?.toFixed(0) || 0}% · ` +
            `Formality ${b.formality_match?.toFixed(0) || 0}% · ` +
            `Patterns ${b.pattern_balance?.toFixed(0) || 0}% · ` +
            `Season ${b.seasonal?.toFixed(0) || 0}%</p>`;
    }

    // ========== FAVORITE (heart) ==========

    resetFavoriteButton() {
        const btn = this.elements.favoriteBtn;
        if (!btn) return;
        btn.classList.remove('liked', 'pop-animate');
        btn.setAttribute('aria-pressed', 'false');
    }

    async toggleFavorite() {
        const btn = this.elements.favoriteBtn;
        const outfit = this.state.currentOutfit;
        if (!btn || !outfit) return;

        const wasLiked = btn.classList.contains('liked');
        const nowLiked = !wasLiked;

        btn.classList.toggle('liked', nowLiked);
        btn.setAttribute('aria-pressed', String(nowLiked));
        if (nowLiked) {
            btn.classList.remove('pop-animate');
            // Force reflow so the animation re-triggers on repeated taps
            void btn.offsetWidth;
            btn.classList.add('pop-animate');
            triggerHaptic('success');
        } else {
            btn.classList.remove('pop-animate');
            triggerHaptic('light');
        }

        try {
            await api.rateOutfit({
                outfit_id: outfit.id,
                rating: nowLiked ? 1 : -1,
                feedback_type: 'outfit'
            });
            if (nowLiked) showToast('Added to favorites', 'success');
        } catch (error) {
            // Roll back on failure
            btn.classList.toggle('liked', wasLiked);
            btn.setAttribute('aria-pressed', String(wasLiked));
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    // ========== STAR RATING ==========
    // UI-only for now: renders 1-5 stars and tracks the selection locally.
    // TODO(personalization): once the backend exposes a per-outfit star
    // score, wire submitStarRating() below to POST it (e.g. a new
    // `stars` field on /feedback/outfit) so ratings feed future
    // recommendation tuning instead of just sitting in the UI.

    renderStarRating(outfit) {
        const container = this.elements.outfitRating;
        if (!container) return;

        container.innerHTML = '';
        for (let i = 1; i <= 5; i++) {
            const star = document.createElement('button');
            star.type = 'button';
            star.className = 'rating-star';
            star.dataset.value = String(i);
            star.setAttribute('role', 'radio');
            star.setAttribute('aria-checked', 'false');
            star.setAttribute('aria-label', `${i} star${i > 1 ? 's' : ''}`);
            star.innerHTML = `
                <svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2l2.9 6.9 7.1.6-5.4 4.6 1.7 7-6.3-4-6.3 4 1.7-7-5.4-4.6 7.1-.6z"></path>
                </svg>
            `;
            star.addEventListener('click', () => this.submitStarRating(outfit, i));
            container.appendChild(star);
        }
    }

    /**
     * TODO(personalization): currently just paints the stars and keeps the
     * value in memory; wire this to the backend once a rating endpoint for
     * outfits exists so it can inform future recommendations.
     */
    submitStarRating(outfit, value) {
        this.state.currentRating = value;
        const stars = this.elements.outfitRating?.querySelectorAll('.rating-star') || [];
        stars.forEach(star => {
            const filled = parseInt(star.dataset.value, 10) <= value;
            star.classList.toggle('filled', filled);
            star.setAttribute('aria-checked', String(filled));
        });
        triggerHaptic('light');
    }

    // ========== PER-GARMENT SWAP (swipe gesture) ==========

    bindGarmentSwipeGestures() {
        const cards = this.elements.outfitDisplay?.querySelectorAll('.garment-card');
        if (!cards) return;

        cards.forEach(card => {
            let startX = 0;
            let dragging = false;

            const onStart = (clientX) => {
                if (this.state.isSwapping) return;
                dragging = true;
                startX = clientX;
                card.classList.add('dragging');
            };
            const onMove = (clientX) => {
                if (!dragging) return;
                const delta = clientX - startX;
                card.style.transform = `translateX(${delta}px) rotate(${delta * 0.03}deg)`;
                card.style.opacity = String(1 - Math.min(Math.abs(delta) / 240, 0.5));
            };
            const onEnd = (clientX) => {
                if (!dragging) return;
                dragging = false;
                card.classList.remove('dragging');
                const delta = clientX - startX;
                const threshold = 60;

                if (Math.abs(delta) > threshold) {
                    triggerHaptic('light');
                    this.handleGarmentSwipe(card, delta < 0 ? 'next' : 'prev');
                } else {
                    card.style.transform = '';
                    card.style.opacity = '';
                }
            };

            card.addEventListener('touchstart', (e) => onStart(e.touches[0].clientX), { passive: true });
            card.addEventListener('touchmove', (e) => onMove(e.touches[0].clientX), { passive: true });
            card.addEventListener('touchend', (e) => onEnd(e.changedTouches[0].clientX), { passive: true });

            card.addEventListener('pointerdown', (e) => {
                if (e.pointerType === 'touch') return;
                card.setPointerCapture(e.pointerId);
                onStart(e.clientX);
            });
            card.addEventListener('pointermove', (e) => {
                if (e.pointerType === 'touch') return;
                onMove(e.clientX);
            });
            card.addEventListener('pointerup', (e) => {
                if (e.pointerType === 'touch') return;
                onEnd(e.clientX);
            });
        });
    }

    async handleGarmentSwipe(card, direction) {
        const outfit = this.state.currentOutfit;
        if (!outfit || !outfit.items || this.state.isSwapping) return;

        this.state.isSwapping = true;
        card.classList.add('swapping');

        try {
            const request = {
                occasion: this.state.selectedOccasion,
                season: this.state.selectedSeason,
                garment_ids: outfit.items.map(item => item.garment_id),
                swap_type: card.dataset.garmentType,
                direction
            };
            if (this.state.selectedFormality) {
                request.formality = this.state.selectedFormality;
            }

            const updated = await api.swapGarment(request);
            this.state.currentOutfit = updated;
            this.renderOutfit(updated);
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
            card.style.transform = '';
            card.style.opacity = '';
            card.classList.remove('swapping');
        } finally {
            this.state.isSwapping = false;
        }
    }

    // ========== OCCASION DIAL / SEASON DIAL ==========

    selectOccasion(occasion, options = {}) {
        this.state.selectedOccasion = occasion;
        this.updateDialPosition('occasion', options.animate !== false);
        this.loadOutfit();
    }

    selectSeason(season, options = {}) {
        this.state.selectedSeason = season;
        this.updateDialPosition('season', options.animate !== false);
        this.loadOutfit();
    }

    occasionIcon(value) {
        const icons = {
            casual: '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>',
            work: '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8"></path><path d="M12 17v4"></path>',
            party: '<path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path>',
            date: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>',
            formal: '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2z"></path><path d="M12 6v6l4 2"></path>',
            wedding: '<circle cx="12" cy="12" r="9"></circle><path d="M9 12l2 2 4-4"></path>'
        };
        return icons[value] || '';
    }

    seasonIcon(value) {
        const icons = {
            all_season: '<circle cx="12" cy="12" r="10"></circle><path d="M12 2v20M2 12h20"></path>',
            spring: '<path d="M12 2v10M12 22v-10M4.93 4.93l7.07 7.07M12 12l7.07-7.07M20 12h-10M4 12h10"></path>',
            summer: '<circle cx="12" cy="12" r="5"></circle><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path>',
            autumn: '<path d="M17 18a5 5 0 0 0-10 0"></path><path d="M12 2v8"></path><path d="M5 18a7 7 0 0 1 14 0"></path>',
            winter: '<path d="M20 17.58A5 5 0 0 0 18 8h-12a5 5 0 0 0 0 10"></path><path d="M10 19v3M14 19v3"></path>'
        };
        return icons[value] || '';
    }

    /**
     * Both the occasion dial (left) and the season dial (right) are the
     * same compact vertical-swipe component, just bound to different
     * value lists and state keys. `kind` is 'occasion' or 'season'.
     */
    dialSpec(kind) {
        return kind === 'occasion'
            ? {
                values: this.occasions,
                selected: this.state.selectedOccasion,
                dial: this.elements.occasionDial,
                track: this.elements.occasionDialTrack,
                icon: (v) => this.occasionIcon(v),
                label: (v) => t('occasion.' + v),
                select: (v, opts) => this.selectOccasion(v, opts)
            }
            : {
                values: this.seasons,
                selected: this.state.selectedSeason,
                dial: this.elements.seasonDial,
                track: this.elements.seasonDialTrack,
                icon: (v) => this.seasonIcon(v),
                label: (v) => t('season.' + v),
                select: (v, opts) => this.selectSeason(v, opts)
            };
    }

    renderDial(kind) {
        const spec = this.dialSpec(kind);
        if (!spec.track) return;

        spec.track.innerHTML = spec.values.map(value => `
            <div class="side-dial-item ${value === spec.selected ? 'active' : ''}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${spec.icon(value)}</svg>
                <span>${spec.label(value)}</span>
            </div>
        `).join('');

        this.updateDialPosition(kind, false);
    }

    updateDialPosition(kind, animate = true) {
        const spec = this.dialSpec(kind);
        const { track, dial, values, selected } = spec;
        if (!track || !dial) return;

        const index = values.indexOf(selected);
        const height = dial.clientHeight || 1;

        track.querySelectorAll('.side-dial-item').forEach(item => {
            item.style.height = `${height}px`;
        });

        track.classList.toggle('dragging', !animate);
        track.style.transform = `translateY(${-index * height}px)`;

        track.querySelectorAll('.side-dial-item').forEach((item, i) => {
            item.classList.toggle('active', i === index);
        });
    }

    bindDialGestures(kind) {
        const spec = this.dialSpec(kind);
        const { dial: container, track } = spec;
        if (!container || !track) return;

        let startY = 0;
        let dragging = false;
        let height = 0;
        let index = 0;

        const currentValues = () => this.dialSpec(kind).values;
        const currentSelected = () => this.dialSpec(kind).selected;

        const onStart = (clientY) => {
            dragging = true;
            startY = clientY;
            height = container.clientHeight || 1;
            index = currentValues().indexOf(currentSelected());
            track.classList.add('dragging');
        };
        const onMove = (clientY) => {
            if (!dragging) return;
            const delta = clientY - startY;
            track.style.transform = `translateY(${-index * height + delta}px)`;
        };
        const onEnd = (clientY) => {
            if (!dragging) return;
            dragging = false;
            track.classList.remove('dragging');
            const delta = clientY - startY;
            const threshold = height * 0.18;
            const values = currentValues();

            if (delta <= -threshold && index < values.length - 1) {
                triggerHaptic('light');
                this.dialSpec(kind).select(values[index + 1]);
            } else if (delta >= threshold && index > 0) {
                triggerHaptic('light');
                this.dialSpec(kind).select(values[index - 1]);
            } else {
                this.updateDialPosition(kind, true);
            }
        };

        container.addEventListener('touchstart', (e) => onStart(e.touches[0].clientY), { passive: true });
        container.addEventListener('touchmove', (e) => onMove(e.touches[0].clientY), { passive: true });
        container.addEventListener('touchend', (e) => onEnd(e.changedTouches[0].clientY), { passive: true });

        container.addEventListener('pointerdown', (e) => {
            if (e.pointerType === 'touch') return;
            container.setPointerCapture(e.pointerId);
            onStart(e.clientY);
        });
        container.addEventListener('pointermove', (e) => {
            if (e.pointerType === 'touch') return;
            onMove(e.clientY);
        });
        container.addEventListener('pointerup', (e) => {
            if (e.pointerType === 'touch') return;
            onEnd(e.clientY);
        });

        window.addEventListener('resize', () => this.updateDialPosition(kind, false));
    }

    // ========== STATS ==========

    async loadStats() {
        try {
            // Both list endpoints are paginated ({ garments/outfits, total, ... }),
            // not bare arrays - read .total for the counts instead of .length,
            // and only pull the full outfits page when we need the scores.
            const [garmentsResp, outfitsResp] = await Promise.all([
                api.getGarments({ page_size: 1 }).catch(() => ({ total: 0 })),
                api.getOutfits({ page_size: 100 }).catch(() => ({ total: 0, outfits: [] }))
            ]);
            const outfits = Array.isArray(outfitsResp.outfits) ? outfitsResp.outfits : [];

            this.state.stats = {
                totalGarments: garmentsResp.total || 0,
                totalOutfits: outfitsResp.total || 0,
                avgScore: 0,
                favorites: 0
            };

            if (outfits.length > 0) {
                const scores = outfits.map(o => o.score || 0).filter(s => s > 0);
                this.state.stats.avgScore = scores.length > 0
                    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
                    : 0;
            }

            this.updateStatsDisplay();
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    updateStatsDisplay() {
        if (this.elements.totalGarments) this.elements.totalGarments.textContent = this.state.stats.totalGarments;
        if (this.elements.totalOutfits) this.elements.totalOutfits.textContent = this.state.stats.totalOutfits;
        if (this.elements.avgScore) this.elements.avgScore.textContent = this.state.stats.avgScore;
        if (this.elements.favorites) this.elements.favorites.textContent = this.state.stats.favorites;
    }

    // ========== PACKING MODAL ==========

    openPackingModal() {
        this.openModal(this.elements.packingModal);
    }

    async handlePackingSubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const request = {
            days: parseInt(formData.get('packingDays') || '3'),
            occasion: formData.get('packingOccasion') || 'travel',
            season: formData.get('packingSeason') || 'all_season',
            max_items: parseInt(formData.get('packingMaxItems') || '15')
        };

        this.closeModal(this.elements.packingModal);

        try {
            const result = await api.createPackingPlan(request);
            this.renderPackingResult(result);
            this.openModal(this.elements.packingResultModal);
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    renderPackingResult(result) {
        const body = this.elements.packingResultBody;
        if (!body) return;

        const stats = result.total_items || 0;
        const days = result.days_covered || 0;
        const ratio = result.mix_and_match_ratio || 0;

        let html = `
            <div class="packing-summary">
                <h3>Plan Summary</h3>
                <div class="packing-stats">
                    <div class="packing-stat">
                        <div class="packing-stat-value">${stats}</div>
                        <div class="packing-stat-label">Total Items</div>
                    </div>
                    <div class="packing-stat">
                        <div class="packing-stat-value">${days}</div>
                        <div class="packing-stat-label">Days Covered</div>
                    </div>
                    <div class="packing-stat">
                        <div class="packing-stat-value">${ratio.toFixed(2)}</div>
                        <div class="packing-stat-label">Mix & Match Ratio</div>
                    </div>
                </div>
            </div>
            <div class="packing-outfits">
        `;

        if (result.outfits && result.outfits.length > 0) {
            result.outfits.forEach((outfit, index) => {
                html += `
                    <div class="packing-outfit">
                        <div class="packing-outfit-header">
                            <span class="packing-outfit-title">Day ${index + 1}: ${escapeHtml(outfit.name || 'Outfit')}</span>
                            <span class="packing-outfit-score">${(outfit.score || 0).toFixed(0)}/100</span>
                        </div>
                        <div class="packing-outfit-items">
                `;

                if (outfit.garments) {
                    outfit.garments.forEach(g => {
                        const colorHex = g.color_hex || '#666666';
                        html += `
                            <span class="packing-outfit-item">
                                <span class="packing-outfit-item-color" style="background-color: ${colorHex}"></span>
                                ${escapeHtml(g.name)} (${formatType(g.type)})
                            </span>
                        `;
                    });
                }

                html += `
                        </div>
                    </div>
                `;
            });
        } else {
            html += '<p style="color: var(--text-muted); text-align: center; padding: 20px;">Could not generate outfits</p>';
        }

        html += '</div>';

        // Packing list
        if (result.packing_list && result.packing_list.length > 0) {
            html += `
                <div class="packing-list-section">
                    <h3>Packing List</h3>
            `;

            result.packing_list.forEach(item => {
                const garment = item.garment;
                const versatility = Math.round((item.versatility_score || 0) * 100);
                const colorHex = garment.color_hex || '#666666';
                const imageUrl = garment.raw_image_path
                    ? `/images/raw/${garment.raw_image_path.replace(/^.*[\\\/]/, '')}`
                    : garment.processed_image_path
                        ? `/images/processed/garments/${garment.processed_image_path.replace(/^.*[\\\/]/, '')}`
                        : null;

                html += `
                    <div class="packing-item-row">
                        ${imageUrl
                            ? `<img class="packing-item-image" src="${imageUrl}" alt="${escapeHtml(garment.name)}" loading="lazy">`
                            : `<div class="packing-item-image" style="background-color: ${colorHex};"></div>`
                        }
                        <div class="packing-item-details">
                            <div class="packing-item-name">${escapeHtml(garment.name)}</div>
                            <div class="packing-item-meta">${formatType(garment.type)} • ${escapeHtml(garment.color_name)} • ${formatPattern(garment.pattern)}</div>
                        </div>
                        <div class="packing-item-versatility">
                            <div class="packing-versatility-bar">
                                <div class="packing-versatility-fill" style="width: ${versatility}%"></div>
                            </div>
                            <div class="packing-versatility-value">${versatility}%</div>
                        </div>
                    </div>
                `;
            });

            html += '</div>';
        }

        body.innerHTML = html;
    }

    // ========== WARDROBE MODAL ==========

    async openWardrobeModal() {
        this.openModal(this.elements.wardrobeModal);
        await this.loadWardrobeModal();
    }

    async loadWardrobeModal() {
        const grid = this.elements.wardrobeGrid;
        if (!grid) return;

        grid.innerHTML = `
            <div class="grid-loading" style="grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; color: var(--text-muted);">
                <div class="spinner" style="width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 16px;"></div>
                <p>Loading wardrobe...</p>
            </div>
        `;

        try {
            // getGarments() returns { garments, total, ... }, not a bare array -
            // getAllGarments() unwraps it and walks every page.
            const garments = await api.getAllGarments();
            if (garments.length > 0) {
                grid.innerHTML = garments.map(garment => this.createWardrobeCard(garment)).join('');
            } else {
                grid.innerHTML = `
                    <div class="empty-state" style="grid-column: 1 / -1;">
                        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                            <circle cx="12" cy="7" r="4"></circle>
                        </svg>
                        <h3>No garments yet</h3>
                        <p>Add garments from Settings to see them here.</p>
                    </div>
                `;
            }
        } catch (error) {
            grid.innerHTML = `
                <div class="grid-error" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                    </svg>
                    <h3 style="margin-bottom: 8px; color: var(--text-secondary);">Error loading</h3>
                    <p>${escapeHtml(error.message)}</p>
                </div>
            `;
        }
    }

    createWardrobeCard(garment) {
        const colorHex = garment.color_hex || '#666666';
        const imageUrl = garment.raw_image_path
            ? `/images/raw/${garment.raw_image_path.replace(/^.*[\\\/]/, '')}`
            : garment.processed_image_path
                ? `/images/processed/garments/${garment.processed_image_path.replace(/^.*[\\\/]/, '')}`
                : null;

        return `
            <article class="wardrobe-item" data-garment-id="${garment.id}">
                ${imageUrl
                    ? `<img class="wardrobe-item-image" src="${imageUrl}" alt="${escapeHtml(garment.name)}" loading="lazy">`
                    : `<div class="wardrobe-item-image" style="background-color: ${colorHex};"></div>`
                }
                <div class="wardrobe-item-info">
                    <h4 class="wardrobe-item-name">${escapeHtml(garment.name)}</h4>
                    <div class="wardrobe-item-meta">
                        <span class="tag tag-type">${formatType(garment.type)}</span>
                        <span class="tag tag-color" style="--tag-color: ${colorHex}">${escapeHtml(garment.color_name)}</span>
                        <span class="tag">${formatPattern(garment.pattern)}</span>
                        <span class="tag">${formatFormality(garment.formality)}</span>
                    </div>
                </div>
            </article>
        `;
    }

    // ========== MODAL HELPERS ==========

    openModal(modal) {
        if (!modal) return;
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        const focusable = modal.querySelector('button, input, select, textarea, [href]');
        if (focusable) focusable.focus();
    }

    closeModal(modal) {
        if (!modal) return;
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    // ========== UTILITIES ==========

    formatOccasion(occasion) {
        const map = {
            casual: 'Casual',
            work: 'Work',
            business: 'Business',
            date: 'Date',
            party: 'Party',
            wedding: 'Wedding',
            formal: 'Formal',
            travel: 'Travel'
        };
        return map[occasion] || occasion;
    }
}

// Initialize when DOM is ready
export function initKioskUI() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.kioskUI = new KioskUI();
        });
    } else {
        window.kioskUI = new KioskUI();
    }
}