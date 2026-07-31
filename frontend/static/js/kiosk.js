// Smart Wardrobe - Kiosk UI
// Adaptive interface for /kiosk route - handles both dual-screen and single-screen modes

import { api } from './api.js';

/**
 * Kiosk UI Controller
 * Handles both dual-screen (visualization + touch panel) and single-screen modes
 */
class KioskUI {
    constructor() {
        this.state = {
            currentOutfit: null,
            selectedOccasion: 'casual',
            selectedSeason: 'all_season',
            selectedFormality: null,
            isLoading: false,
            layoutMode: 'auto', // 'auto', 'dual', 'single'
            screenWidth: window.innerWidth,
            screenHeight: window.innerHeight
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
        
        // Load initial outfit
        await this.loadOutfit();
        
        // Load stats periodically
        this.loadStats();
        setInterval(() => this.loadStats(), 60000);
    }
    
    cacheElements() {
        // Main containers
        this.elements.visualizationPanel = document.querySelector('.visualization-panel');
        this.elements.touchPanel = document.querySelector('.touch-panel');
        this.elements.appContainer = document.querySelector('.app-container');
        
        // Visualization elements
        this.elements.outfitDisplay = document.querySelector('.outfit-display');
        this.elements.refreshBtn = document.getElementById('refreshBtn');
        
        // Touch panel elements
        this.elements.occasionGrid = document.querySelector('.occasion-grid');
        this.elements.seasonGrid = document.querySelector('.season-grid');
        this.elements.generateBtn = document.getElementById('generateBtn');
        this.elements.packingBtn = document.getElementById('packingBtn');
        
        // Stats
        this.elements.totalGarments = document.getElementById('totalGarments');
        this.elements.totalOutfits = document.getElementById('totalOutfits');
        this.elements.avgScore = document.getElementById('avgScore');
        this.elements.favorites = document.getElementById('favorites');
        
        // Modals (referenced from index.html)
        this.elements.packingModal = document.getElementById('packingModal');
        this.elements.packingResultModal = document.getElementById('packingResultModal');
        this.elements.wardrobeModal = document.getElementById('wardrobeModal');
        this.elements.addGarmentModal = document.getElementById('addGarmentModal');
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
        
        // Packing button
        if (this.elements.packingBtn) {
            this.elements.packingBtn.addEventListener('click', () => this.openPackingModal());
        }
        
        // Occasion grid - event delegation
        if (this.elements.occasionGrid) {
            this.elements.occasionGrid.addEventListener('click', (e) => {
                const btn = e.target.closest('.occasion-btn');
                if (btn) this.selectOccasion(btn.dataset.occasion);
            });
        }
        
        // Season grid - event delegation
        if (this.elements.seasonGrid) {
            this.elements.seasonGrid.addEventListener('click', (e) => {
                const btn = e.target.closest('.season-btn');
                if (btn) this.selectSeason(btn.dataset.season);
            });
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
        const packingForm = document.getElementById('packingForm');
        if (packingForm) {
            packingForm.addEventListener('submit', (e) => this.handlePackingSubmit(e));
        }
        
        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal:not(.hidden)').forEach(modal => this.closeModal(modal));
            }
        });
        
        // Touch gestures for navigation
        this.bindTouchGestures();
    }
    
    bindTouchGestures() {
        let touchStartX = 0;
        let touchStartY = 0;
        
        const visualizationPanel = this.elements.visualizationPanel;
        if (!visualizationPanel) return;
        
        visualizationPanel.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        }, { passive: true });
        
        visualizationPanel.addEventListener('touchend', (e) => {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            
            // Horizontal swipe detection (min 50px, more horizontal than vertical)
            if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY)) {
                if (deltaX > 0) {
                    // Swipe right - previous outfit (could implement history)
                    this.loadOutfit();
                } else {
                    // Swipe left - next outfit
                    this.loadOutfit();
                }
                this.triggerHaptic('light');
            }
        }, { passive: true });
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
                <div class="spinner"></div>
                <p>Generando outfit para ${this.formatOccasion(this.state.selectedOccasion)}...</p>
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
                <h3>No hay prendas suficientes</h3>
                <p>Agrega al menos 2 prendas a tu armario para generar outfits</p>
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
                <h3>Error al cargar</h3>
                <p>${this.escapeHtml(message)}</p>
                <button class="btn btn-primary" onclick="kioskUI.loadOutfit()">Reintentar</button>
            </div>
        `;
    }
    
    renderOutfit(outfit) {
        const score = outfit.score || 0;
        
        let html = `
            <div class="outfit-result">
                <div class="outfit-header">
                    <h2 class="outfit-name">${this.escapeHtml(outfit.name || 'Outfit Recomendado')}</h2>
                    <div class="outfit-score">
                        <span class="score-value">${score.toFixed(0)}</span>
                        <span class="score-label">/100</span>
                    </div>
                </div>
                <div class="outfit-garments">
        `;
        
        if (outfit.garments && outfit.garments.length > 0) {
            outfit.garments.forEach(garment => {
                            const colorHex = garment.color_hex || '#666666';
                            // Use raw_image_path for high-quality display - serve via /images/raw/
                            const imageUrl = garment.raw_image_path
                                ? `/images/raw/${garment.raw_image_path.replace(/^.*[\\/]/, '')}`
                                : garment.processed_image_path
                                    ? `/images/processed/garments/${garment.processed_image_path.replace(/^.*[\\/]/, '')}`
                                    : null;
                
                html += `
                    <article class="garment-card" data-garment-id="${garment.id}">
                        ${imageUrl 
                            ? `<img class="garment-image" src="${imageUrl}" alt="${this.escapeHtml(garment.name)}" loading="lazy">`
                            : `<div class="garment-image" style="background-color: ${colorHex};"></div>`
                        }
                        <div class="garment-info">
                            <h3 class="garment-name">${this.escapeHtml(garment.name)}</h3>
                            <div class="garment-meta">
                                <span class="garment-tag type">${this.formatType(garment.type)}</span>
                                <span class="garment-tag color" style="--tag-color: ${colorHex}">${this.escapeHtml(garment.color_name)}</span>
                                <span class="garment-tag">${this.formatPattern(garment.pattern)}</span>
                                <span class="garment-tag">${this.formatFormality(garment.formality)}</span>
                            </div>
                        </div>
                    </article>
                `;
            });
        }
        
        html += `
                </div>
        `;
        
        // Description and tips
        if (outfit.score_breakdown) {
            html += `
                <div class="outfit-description">
                    <p>Color ${outfit.score_breakdown.color_harmony?.toFixed(0) || 0}% | 
                    Formalidad ${outfit.score_breakdown.formality_match?.toFixed(0) || 0}% | 
                    Patrones ${outfit.score_breakdown.pattern_balance?.toFixed(0) || 0}% | 
                    Temporada ${outfit.score_breakdown.seasonal?.toFixed(0) || 0}%</p>
                </div>
            `;
        }
        
        // AI Tips if available
        if (outfit.ai_tips && outfit.ai_tips.length > 0) {
            html += `
                <div class="outfit-tips">
                    <h3>Consejos de estilo:</h3>
                    <ul id="tipsList">
            `;
            outfit.ai_tips.forEach(tip => {
                html += `<li class="tip-item">${this.escapeHtml(tip)}</li>`;
            });
            html += `
                    </ul>
                </div>
            `;
        }
        
        // Feedback buttons
        html += `
                <div class="outfit-feedback">
                    <button class="feedback-btn like-btn" data-outfit-id="${outfit.id}" data-rating="1" aria-label="Me gusta">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                        </svg>
                        <span class="feedback-count">0</span>
                    </button>
                    <button class="feedback-btn dislike-btn" data-outfit-id="${outfit.id}" data-rating="-1" aria-label="No me gusta">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                        </svg>
                        <span class="feedback-count">0</span>
                    </button>
                </div>
            </div>
        `;
        
        const display = this.elements.outfitDisplay;
        if (display) {
            display.innerHTML = html;
            this.bindFeedbackButtons();
        }
    }
    
    bindFeedbackButtons() {
        document.querySelectorAll('.feedback-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFeedback(e));
        });
    }
    
    async handleFeedback(event) {
        const btn = event.currentTarget;
        const outfitId = parseInt(btn.dataset.outfitId);
        const rating = parseInt(btn.dataset.rating);
        
        // Toggle active state
        const isLike = rating > 0;
        const otherBtn = btn.parentElement.querySelector(isLike ? '.dislike-btn' : '.like-btn');
        
        if (btn.classList.contains('active')) {
            btn.classList.remove('active');
        } else {
            btn.classList.add('active');
            otherBtn?.classList.remove('active');
            
            try {
                await api.rateOutfit({
                    outfit_id: outfitId,
                    rating: rating,
                    feedback_type: 'outfit'
                });
                this.showToast(isLike ? '¡Gracias por tu like!' : 'Gracias por tu feedback', 'success');
                this.triggerHaptic('success');
            } catch (error) {
                this.showToast(`Error: ${error.message}`, 'error');
                btn.classList.remove('active');
            }
        }
    }
    
    // ========== OCCASION/SEASON SELECTION ==========
    
    selectOccasion(occasion) {
        this.state.selectedOccasion = occasion;
        this.updateOccasionButtons();
        this.loadOutfit();
    }
    
    selectSeason(season) {
        this.state.selectedSeason = season;
        this.updateSeasonButtons();
        this.loadOutfit();
    }
    
    updateOccasionButtons() {
        document.querySelectorAll('.occasion-btn').forEach(btn => {
            const active = btn.dataset.occasion === this.state.selectedOccasion;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active);
        });
    }
    
    updateSeasonButtons() {
        document.querySelectorAll('.season-btn').forEach(btn => {
            const active = btn.dataset.season === this.state.selectedSeason;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active);
        });
    }
    
    // ========== STATS ==========
    
    async loadStats() {
        try {
            const [garments, outfits] = await Promise.all([
                api.getGarments({ limit: 1000 }).catch(() => []),
                api.getOutfits({ limit: 1000 }).catch(() => [])
            ]);
            
            this.state.stats = {
                totalGarments: Array.isArray(garments) ? garments.length : 0,
                totalOutfits: Array.isArray(outfits) ? outfits.length : 0,
                avgScore: 0,
                favorites: 0
            };
            
            if (Array.isArray(outfits) && outfits.length > 0) {
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
            this.showToast(`Error: ${error.message}`, 'error');
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
                <h3>Resumen del Plan</h3>
                <div class="packing-stats">
                    <div class="packing-stat">
                        <div class="packing-stat-value">${stats}</div>
                        <div class="packing-stat-label">Prendas totales</div>
                    </div>
                    <div class="packing-stat">
                        <div class="packing-stat-value">${days}</div>
                        <div class="packing-stat-label">Días cubiertos</div>
                    </div>
                    <div class="packing-stat">
                        <div class="packing-stat-value">${ratio.toFixed(2)}</div>
                        <div class="packing-stat-label">Ratio mix-and-match</div>
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
                            <span class="packing-outfit-title">Día ${index + 1}: ${this.escapeHtml(outfit.name || 'Outfit')}</span>
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
                                ${this.escapeHtml(g.name)} (${this.formatType(g.type)})
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
            html += '<p style="color: var(--text-muted); text-align: center; padding: 20px;">No se pudieron generar outfits</p>';
        }
        
        html += '</div>';
        
        // Packing list
        if (result.packing_list && result.packing_list.length > 0) {
            html += `
                <div class="packing-list-section">
                    <h3>Lista de Maleta</h3>
            `;
            
            result.packing_list.forEach(item => {
                const garment = item.garment;
                const versatility = Math.round((item.versatility_score || 0) * 100);
                const colorHex = garment.color_hex || '#666666';
                const imageUrl = garment.raw_image_path 
                    ? `/static/${garment.raw_image_path.replace(/^.*[\\/]/, '')}`
                    : garment.processed_image_path
                        ? `/static/${garment.processed_image_path.replace(/^.*[\\/]/, '')}`
                        : null;
                
                html += `
                    <div class="packing-item-row">
                        ${imageUrl 
                            ? `<img class="packing-item-image" src="${imageUrl}" alt="${this.escapeHtml(garment.name)}" loading="lazy">`
                            : `<div class="packing-item-image" style="background-color: ${colorHex};"></div>`
                        }
                        <div class="packing-item-details">
                            <div class="packing-item-name">${this.escapeHtml(garment.name)}</div>
                            <div class="packing-item-meta">${this.formatType(garment.type)} • ${this.escapeHtml(garment.color_name)} • ${this.formatPattern(garment.pattern)}</div>
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
            work: 'Trabajo',
            business: 'Negocios',
            date: 'Cita',
            party: 'Fiesta',
            wedding: 'Boda',
            formal: 'Formal',
            travel: 'Viaje'
        };
        return map[occasion] || occasion;
    }
    
    formatType(type) {
        const map = {
            top: 'Top',
            bottom: 'Pantalón',
            dress: 'Vestido',
            outerwear: 'Abrigo',
            shoes: 'Zapatos',
            accessory: 'Accesorio'
        };
        return map[type] || type;
    }
    
    formatPattern(pattern) {
        const map = {
            solid: 'Liso',
            striped: 'Rayado',
            checked: 'Cuadros',
            floral: 'Floral',
            polka_dot: 'Lunares',
            geometric: 'Geométrico',
            abstract: 'Abstracto',
            animal_print: 'Animal print',
            paisley: 'Paisley',
            houndstooth: 'Pata de gallo'
        };
        return map[pattern] || pattern;
    }
    
    formatFormality(formality) {
        const map = {
            1: 'Casual',
            2: 'Smart Casual',
            3: 'Business Casual',
            4: 'Formal',
            5: 'Gala'
        };
        return map[formality] || `Nivel ${formality}`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showToast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toastContainer') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <svg class="toast-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                ${this.getToastIcon(type)}
            </svg>
            <span class="toast-message">${this.escapeHtml(message)}</span>
            <button class="toast-close" aria-label="Cerrar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;
        
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.style.animation = 'toastIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        });
        
        container.appendChild(toast);
        
        if (duration > 0) {
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.style.animation = 'toastIn 0.3s ease reverse';
                    setTimeout(() => toast.remove(), 300);
                }
            }, duration);
        }
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        container.setAttribute('aria-live', 'polite');
        document.body.appendChild(container);
        return container;
    }
    
    getToastIcon(type) {
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
    
    triggerHaptic(type = 'light') {
        if (navigator.vibrate) {
            const patterns = {
                light: [10],
                medium: [20],
                heavy: [30],
                success: [10, 50, 10],
                error: [30, 30, 30]
            };
            navigator.vibrate(patterns[type] || patterns.light);
        }
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