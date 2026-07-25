// Smart Wardrobe - Frontend JavaScript
// Dual panel UI: Visualization (60%) + Touch Panel (40%)

const API_BASE = '/api/v1';
const STORAGE_KEY = 'smartwardrobe_state';

// State management
const state = {
    currentOutfit: null,
    selectedOccasion: 'casual',
    selectedSeason: 'all_season',
    selectedFormality: null,
    garments: [],
    stats: { totalGarments: 0, totalOutfits: 0, avgScore: 0, favorites: 0 },
    isLoading: false
};

// DOM Elements
const elements = {};

// Initialize DOM references
function initElements() {
    // Visualization Panel
    elements.outfitDisplay = document.querySelector('.outfit-display');
    elements.refreshBtn = document.getElementById('refreshBtn');
    elements.occasionFilter = document.getElementById('occasionFilter');
    elements.seasonFilter = document.getElementById('seasonFilter');
    elements.formalityFilter = document.getElementById('formalityFilter');
    elements.wardrobeBtn = document.getElementById('wardrobeBtn');
    elements.packingBtn = document.getElementById('packingBtn');
    elements.settingsBtn = document.getElementById('settingsBtn');
    
    // Touch Panel
    elements.occasionGrid = document.querySelector('.occasion-grid');
    elements.seasonGrid = document.querySelector('.season-grid');
    elements.generateBtn = document.getElementById('generateBtn');
    elements.rateBtn = document.getElementById('rateBtn');
    elements.packingActionBtn = document.getElementById('packingActionBtn');
    elements.wardrobeActionBtn = document.getElementById('wardrobeActionBtn');
    elements.settingsActionBtn = document.getElementById('settingsActionBtn');
    
    // Stats
    elements.totalGarments = document.getElementById('totalGarments');
    elements.totalOutfits = document.getElementById('totalOutfits');
    elements.avgScore = document.getElementById('avgScore');
    elements.favorites = document.getElementById('favorites');
    
    // Modals
    elements.packingModal = document.getElementById('packingModal');
    elements.packingResultModal = document.getElementById('packingResultModal');
    elements.wardrobeModal = document.getElementById('wardrobeModal');
    elements.addGarmentModal = document.getElementById('addGarmentModal');
    elements.closePackingModal = document.getElementById('closePackingModal');
    elements.closePackingResultModal = document.getElementById('closePackingResultModal');
    elements.closeWardrobeModal = document.getElementById('closeWardrobeModal');
    elements.closeAddGarmentModal = document.getElementById('closeAddGarmentModal');
    elements.cancelPacking = document.getElementById('cancelPacking');
    elements.cancelAddGarment = document.getElementById('cancelAddGarment');
    elements.packingForm = document.getElementById('packingForm');
    elements.addGarmentForm = document.getElementById('addGarmentForm');
    elements.packingResultBody = document.getElementById('packingResultBody');
    elements.wardrobeGrid = document.getElementById('wardrobeGrid');
    elements.wardrobeSearch = document.getElementById('wardrobeSearch');
    elements.wardrobeTypeFilter = document.getElementById('wardrobeTypeFilter');
    elements.wardrobeSeasonFilter = document.getElementById('wardrobeSeasonFilter');
    elements.addGarmentBtn = document.getElementById('addGarmentBtn');
    elements.imageUpload = document.getElementById('imageUpload');
    elements.garmentImage = document.getElementById('garmentImage');
    elements.previewImage = document.getElementById('previewImage');
    
    // Toast
    elements.toastContainer = document.getElementById('toastContainer');
    
    // Touch panel toggle (mobile)
    elements.touchPanel = document.querySelector('.touch-panel');
}

// API Helper
async function api(path, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    const response = await fetch(`${API_BASE}${path}`, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return response.json();
}

// Toast Notifications
function showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <svg class="toast-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${getToastIcon(type)}
        </svg>
        <span class="toast-message">${escapeHtml(message)}</span>
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
    
    elements.toastContainer.appendChild(toast);
    
    if (duration > 0) {
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'toastIn 0.3s ease reverse';
                setTimeout(() => toast.remove(), 300);
            }
        }, duration);
    }
    
    return toast;
}

function getToastIcon(type) {
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Modal Helpers
function openModal(modal) {
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    // Focus first focusable element
    const focusable = modal.querySelector('button, input, select, textarea, [href]');
    if (focusable) focusable.focus();
}

function closeModal(modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Outfit Display
async function loadOutfit() {
    if (state.isLoading) return;
    state.isLoading = true;
    
    // Show loading state
    showOutfitLoading();
    
    try {
        const params = new URLSearchParams();
        params.append('occasion', state.selectedOccasion);
        params.append('season', state.selectedSeason);
        if (state.selectedFormality) params.append('formality', state.selectedFormality);
        params.append('top_n', '1');
        
        const response = await api(`/recommend?${params.toString()}`);
        
        if (response.outfits && response.outfits.length > 0) {
            state.currentOutfit = response.outfits[0];
            renderOutfit(state.currentOutfit);
        } else {
            showOutfitEmpty();
        }
    } catch (error) {
        console.error('Error loading outfit:', error);
        showOutfitError(error.message);
        showToast(`Error al cargar outfit: ${error.message}`, 'error');
    } finally {
        state.isLoading = false;
    }
}

function showOutfitLoading() {
    elements.outfitDisplay.innerHTML = `
        <div class="outfit-loading">
            <div class="spinner"></div>
            <p>Generando outfit para ${formatOccasion(state.selectedOccasion)}...</p>
        </div>
    `;
}

function showOutfitEmpty() {
    elements.outfitDisplay.innerHTML = `
        <div class="outfit-empty">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
            </svg>
            <h3>No hay outfits disponibles</h3>
            <p>Añade prendas a tu armario para generar recomendaciones</p>
            <button class="btn btn-primary" onclick="openModal(elements.addGarmentModal)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                Añadir primera prenda
            </button>
        </div>
    `;
}

function showOutfitError(message) {
    elements.outfitDisplay.innerHTML = `
        <div class="outfit-empty">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <h3>Error al cargar</h3>
            <p>${escapeHtml(message)}</p>
            <button class="btn btn-primary" onclick="loadOutfit()">Reintentar</button>
        </div>
    `;
}

function renderOutfit(outfit) {
    const score = outfit.score || 0;
    const scoreClass = score >= 80 ? 'high' : score >= 60 ? 'medium' : 'low';
    
    let html = `
        <div class="outfit-result">
            <div class="outfit-header">
                <h2 class="outfit-name">${escapeHtml(outfit.name || 'Outfit Recomendado')}</h2>
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
            const imageUrl = garment.image_path 
                ? `/static/${garment.image_path.replace(/^.*[\\/]/, '')}`
                : null;
            
            html += `
                <article class="garment-card" data-garment-id="${garment.id}">
                    ${imageUrl 
                        ? `<img class="garment-image" src="${imageUrl}" alt="${escapeHtml(garment.name)}" loading="lazy">`
                        : `<div class="garment-image" style="background-color: ${colorHex};"></div>`
                    }
                    <div class="garment-info">
                        <h3 class="garment-name">${escapeHtml(garment.name)}</h3>
                        <div class="garment-meta">
                            <span class="garment-tag type">${formatType(garment.type)}</span>
                            <span class="garment-tag color" style="--tag-color: ${colorHex}">${escapeHtml(garment.color_name)}</span>
                            <span class="garment-tag">${formatPattern(garment.pattern)}</span>
                            <span class="garment-tag">${formatFormality(garment.formality)}</span>
                        </div>
                    </div>
                </article>
            `;
        });
    }
    
    html += `
            </div>
    `;
    
    // Description and tips if available
    if (outfit.score_breakdown) {
        html += `
            <div class="outfit-description">
                <p>Score breakdown: Color ${outfit.score_breakdown.color_harmony?.toFixed(0) || 0}% | 
                Formalidad ${outfit.score_breakdown.formality_match?.toFixed(0) || 0}% | 
                Patrones ${outfit.score_breakdown.pattern_balance?.toFixed(0) || 0}% | 
                Temporada ${outfit.score_breakdown.seasonal?.toFixed(0) || 0}%</p>
            </div>
        `;
    }
    
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
    
    elements.outfitDisplay.innerHTML = html;
    
    // Add event listeners for feedback buttons
    document.querySelectorAll('.feedback-btn').forEach(btn => {
        btn.addEventListener('click', handleFeedback);
    });
}

async function handleFeedback(event) {
    const btn = event.currentTarget;
    const outfitId = parseInt(btn.dataset.outfitId);
    const rating = parseInt(btn.dataset.rating);
    
    // Toggle active state
    const isLike = rating > 0;
    const otherBtn = btn.parentElement.querySelector(isLike ? '.dislike-btn' : '.like-btn');
    
    if (btn.classList.contains('active')) {
        // Remove feedback
        btn.classList.remove('active');
        // TODO: Call API to remove feedback
    } else {
        btn.classList.add('active');
        otherBtn.classList.remove('active');
        
        try {
            await api('/feedback/outfit', {
                method: 'POST',
                body: JSON.stringify({
                    outfit_id: outfitId,
                    rating: rating,
                    feedback_type: 'outfit'
                })
            });
            showToast(isLike ? '¡Gracias por tu like!' : 'Gracias por tu feedback', 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
            btn.classList.remove('active');
        }
    }
}

// Occasion & Season Selection
function initOccasionButtons() {
    const occasions = [
        { id: 'casual', label: 'Casual', icon: 'casual' },
        { id: 'work', label: 'Trabajo', icon: 'work' },
        { id: 'date', label: 'Cita', icon: 'date' },
        { id: 'party', label: 'Fiesta', icon: 'party' },
        { id: 'wedding', label: 'Boda', icon: 'wedding' },
        { id: 'travel', label: 'Viaje', icon: 'travel' }
    ];
    
    const seasons = [
        { id: 'all_season', label: 'Todas', icon: 'all' },
        { id: 'spring', label: 'Primavera', icon: 'spring' },
        { id: 'summer', label: 'Verano', icon: 'summer' },
        { id: 'autumn', label: 'Otoño', icon: 'autumn' },
        { id: 'winter', label: 'Invierno', icon: 'winter' }
    ];
    
    elements.occasionGrid.innerHTML = occasions.map(occ => `
        <button class="occasion-btn ${occ.id === state.selectedOccasion ? 'active' : ''}" 
                data-occasion="${occ.id}" aria-pressed="${occ.id === state.selectedOccasion}">
            <svg class="occasion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                ${getOccasionIcon(occ.icon)}
            </svg>
            <span>${occ.label}</span>
        </button>
    `).join('');
    
    elements.seasonGrid.innerHTML = seasons.map(season => `
        <button class="season-btn ${season.id === state.selectedSeason ? 'active' : ''}" 
                data-season="${season.id}" aria-pressed="${season.id === state.selectedSeason}">
            <svg class="season-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                ${getSeasonIcon(season.icon)}
            </svg>
            <span>${season.label}</span>
        </button>
    `).join('');
    
    // Add event listeners
    document.querySelectorAll('.occasion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.occasion-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-pressed', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-pressed', 'true');
            state.selectedOccasion = btn.dataset.occasion;
            loadOutfit();
        });
    });
    
    document.querySelectorAll('.season-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.season-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-pressed', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-pressed', 'true');
            state.selectedSeason = btn.dataset.season;
            loadOutfit();
        });
    });
    
    // Formality filter
    elements.formalityFilter.addEventListener('change', (e) => {
        state.selectedFormality = e.target.value ? parseInt(e.target.value) : null;
        loadOutfit();
    });
}

function getOccasionIcon(type) {
    switch (type) {
        case 'casual': return '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>';
        case 'work': return '<rect x="2" y="3" width="20" height="14" rx="2"></rect><path d="M8 21h8"></path><path d="M12 17v4"></path>';
        case 'date': return '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>';
        case 'party': return '<path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path>';
        case 'wedding': return '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2z"></path><path d="M12 6v6l4 2"></path>';
        case 'travel': return '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><path d="M12 4v16"></path>';
        default: return '';
    }
}

function getSeasonIcon(type) {
    switch (type) {
        case 'all': return '<circle cx="12" cy="12" r="10"></circle><path d="M12 2v20M2 12h20"></path>';
        case 'spring': return '<path d="M12 2v10M12 22v-10M4.93 4.93l7.07 7.07M12 12l7.07-7.07M20 12h-10M4 12h10"></path>';
        case 'summer': return '<circle cx="12" cy="12" r="5"></circle><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path>';
        case 'autumn': return '<path d="M17 18a5 5 0 0 0-10 0"></path><path d="M12 2v8"></path><path d="M5 18a7 7 0 0 1 14 0"></path>';
        case 'winter': return '<path d="M20 17.58A5 5 0 0 0 18 8h-12a5 5 0 0 0 0 10"></path><path d="M10 19v3M14 19v3"></path>';
        default: return '';
    }
}

// Stats Loading
async function loadStats() {
    try {
        const [garments, outfits] = await Promise.all([
            api('/garments?limit=1'),
            api('/outfits?limit=1')
        ]);
        
        state.stats.totalGarments = garments.length; // This would need count endpoint
        state.stats.totalOutfits = outfits.length;
        
        // Get more accurate counts
        const garmentCount = await api('/garments?limit=1000').catch(() => []);
        const outfitCount = await api('/outfits?limit=1000').catch(() => []);
        
        state.stats.totalGarments = Array.isArray(garmentCount) ? garmentCount.length : 0;
        state.stats.totalOutfits = Array.isArray(outfitCount) ? outfitCount.length : 0;
        
        // Calculate average score
        if (Array.isArray(outfitCount) && outfitCount.length > 0) {
            const scores = outfitCount.map(o => o.score || 0).filter(s => s > 0);
            state.stats.avgScore = scores.length > 0 
                ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) 
                : 0;
        }
        
        updateStatsDisplay();
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function updateStatsDisplay() {
    elements.totalGarments.textContent = state.stats.totalGarments;
    elements.totalOutfits.textContent = state.stats.totalOutfits;
    elements.avgScore.textContent = state.stats.avgScore;
    elements.favorites.textContent = state.stats.favorites;
}

// Packing Modal
elements.packingBtn?.addEventListener('click', () => {
    openModal(elements.packingModal);
});

elements.closePackingModal?.addEventListener('click', () => closeModal(elements.packingModal));
elements.cancelPacking?.addEventListener('click', () => closeModal(elements.packingModal));

elements.packingForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    closeModal(elements.packingModal);
    
    const formData = new FormData(elements.packingForm);
    const request = {
        days: parseInt(formData.get('packingDays') || '3'),
        occasion: formData.get('packingOccasion') || 'travel',
        season: formData.get('packingSeason') || 'all_season',
        max_items: parseInt(formData.get('packingMaxItems') || '15')
    };
    
    try {
        const result = await api('/packing', {
            method: 'POST',
            body: JSON.stringify(request)
        });
        
        renderPackingResult(result);
        openModal(elements.packingResultModal);
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
});

function renderPackingResult(result) {
    const stats = result.total_garments || 0;
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
                        <span class="packing-outfit-title">Día ${index + 1}: ${escapeHtml(outfit.name || 'Outfit')}</span>
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
            const imageUrl = garment.image_path 
                ? `/static/${garment.image_path.replace(/^.*[\\/]/, '')}`
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
    
    elements.packingResultBody.innerHTML = html;
}

// Wardrobe Modal
elements.wardrobeBtn?.addEventListener('click', async () => {
    openModal(elements.wardrobeModal);
    await loadWardrobe();
});

elements.closeWardrobeModal?.addEventListener('click', () => closeModal(elements.wardrobeModal));
elements.addGarmentBtn?.addEventListener('click', () => {
    closeModal(elements.wardrobeModal);
    openModal(elements.addGarmentModal);
});

async function loadWardrobe() {
    try {
        const garments = await api('/garments?limit=100');
        renderWardrobe(garments);
    } catch (error) {
        showToast(`Error al cargar armario: ${error.message}`, 'error');
    }
}

function renderWardrobe(garments) {
    if (!garments || garments.length === 0) {
        elements.wardrobeGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                </svg>
                <h3 style="margin-bottom: 8px; color: var(--text-secondary);">Armario vacío</h3>
                <p>Añade tu primera prenda para empezar</p>
            </div>
        `;
        return;
    }
    
    elements.wardrobeGrid.innerHTML = garments.map(garment => {
        const colorHex = garment.color_hex || '#666666';
        const imageUrl = garment.image_path 
            ? `/static/${garment.image_path.replace(/^.*[\\/]/, '')}`
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
                        <span class="wardrobe-item-tag type">${formatType(garment.type)}</span>
                        <span class="wardrobe-item-tag color" style="--tag-color: ${colorHex}">${escapeHtml(garment.color_name)}</span>
                        <span class="wardrobe-item-tag">${formatPattern(garment.pattern)}</span>
                        <span class="wardrobe-item-tag">${formatFormality(garment.formality)}</span>
                    </div>
                </div>
            </article>
        `;
    }).join('');
}

// Add Garment Modal
elements.closeAddGarmentModal?.addEventListener('click', () => closeModal(elements.addGarmentModal));
elements.cancelAddGarment?.addEventListener('click', () => closeModal(elements.addGarmentModal));

// Image upload preview
elements.garmentImage?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            elements.previewImage.src = e.target.result;
            elements.imageUpload.querySelector('.upload-placeholder').classList.add('hidden');
            elements.imageUpload.querySelector('.image-preview').classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }
});

elements.imageUpload?.querySelector('.remove-image')?.addEventListener('click', () => {
    elements.garmentImage.value = '';
    elements.previewImage.src = '';
    elements.imageUpload.querySelector('.upload-placeholder').classList.remove('hidden');
    elements.imageUpload.querySelector('.image-preview').classList.add('hidden');
});

elements.addGarmentForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(elements.addGarmentForm);
    
    // Validate image
    if (!elements.garmentImage.files[0]) {
        showToast('Por favor selecciona una imagen', 'warning');
        return;
    }
    
    const submitBtn = elements.addGarmentForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Guardando...';
    
    try {
        const response = await api('/garments', {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type for FormData
        });
        
        showToast('Prenda guardada correctamente', 'success');
        closeModal(elements.addGarmentModal);
        elements.addGarmentForm.reset();
        elements.imageUpload.querySelector('.upload-placeholder').classList.remove('hidden');
        elements.imageUpload.querySelector('.image-preview').classList.add('hidden');
        elements.garmentImage.value = '';
        
        // Reload wardrobe if open
        if (!elements.wardrobeModal.classList.contains('hidden')) {
            await loadWardrobe();
        }
        
        // Reload stats
        await loadStats();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                <polyline points="17 21 17 13 7 13 7 21"></polyline>
                <polyline points="7 3 7 8 15 8"></polyline>
            </svg>
            Guardar Prenda
        `;
    }
});

// Touch Panel Actions
elements.generateBtn?.addEventListener('click', loadOutfit);
elements.rateBtn?.addEventListener('click', () => {
    // Show feedback options or navigate to feedback
    showToast('Valora el outfit actual con los botones 👍/👎', 'info');
});

elements.packingActionBtn?.addEventListener('click', () => openModal(elements.packingModal));
elements.wardrobeActionBtn?.addEventListener('click', () => {
    closeModal(elements.touchPanel);
    openModal(elements.wardrobeModal);
    loadWardrobe();
});
elements.settingsActionBtn?.addEventListener('click', () => showToast('Configuración próximamente', 'info'));

// Filter Event Listeners
elements.refreshBtn?.addEventListener('click', loadOutfit);
elements.occasionFilter?.addEventListener('change', (e) => {
    state.selectedOccasion = e.target.value;
    syncOccasionButtons();
    loadOutfit();
});
elements.seasonFilter?.addEventListener('change', (e) => {
    state.selectedSeason = e.target.value;
    syncSeasonButtons();
    loadOutfit();
});

function syncOccasionButtons() {
    document.querySelectorAll('.occasion-btn').forEach(btn => {
        const active = btn.dataset.occasion === state.selectedOccasion;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-pressed', active);
    });
}

function syncSeasonButtons() {
    document.querySelectorAll('.season-btn').forEach(btn => {
        const active = btn.dataset.season === state.selectedSeason;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-pressed', active);
    });
}

// Touch panel toggle on mobile
let touchPanelExpanded = false;
function toggleTouchPanel() {
    touchPanelExpanded = !touchPanelExpanded;
    elements.touchPanel.classList.toggle('expanded', touchPanelExpanded);
}

// Close modals on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', () => {
        const modal = overlay.closest('.modal');
        if (modal) closeModal(modal);
    });
});

// Close modals with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal:not(.hidden)').forEach(closeModal);
    }
});

// Formatting Helpers
function formatOccasion(occasion) {
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

function formatType(type) {
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

function formatPattern(pattern) {
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

function formatFormality(formality) {
    const map = {
        1: 'Casual',
        2: 'Smart Casual',
        3: 'Business Casual',
        4: 'Formal',
        5: 'Gala'
    };
    return map[formality] || `Nivel ${formality}`;
}

// Initialize App
async function initApp() {
    initElements();
    
    // Initialize UI
    initOccasionButtons();
    
    // Load initial data
    await Promise.all([
        loadStats(),
        loadOutfit()
    ]);
    
    // Handle mobile touch panel
    if (window.innerWidth < 768) {
        // Add drag handle for touch panel
        const handle = document.createElement('div');
        handle.className = 'touch-panel-handle';
        handle.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="12" x2="16" y2="12"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>';
        handle.style.cssText = `
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            width: 40px;
            height: 24px;
            background: var(--bg-tertiary);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: grab;
            border: 1px solid var(--border-primary);
        `;
        elements.touchPanel.insertBefore(handle, elements.touchPanel.firstChild);
        
        let startY = 0;
        let panelStartY = 0;
        
        handle.addEventListener('pointerdown', (e) => {
            startY = e.clientY;
            panelStartY = touchPanelExpanded ? 0 : window.innerHeight * 0.4;
            handle.setPointerCapture(e.pointerId);
        });
        
        handle.addEventListener('pointermove', (e) => {
            if (handle.hasPointerCapture(e.pointerId)) {
                const delta = startY - e.clientY;
                const newY = Math.max(0, Math.min(window.innerHeight * 0.8, panelStartY - delta));
                elements.touchPanel.style.transform = `translateY(${newY}px)`;
            }
        });
        
        handle.addEventListener('pointerup', (e) => {
            handle.releasePointerCapture(e.pointerId);
            const currentY = parseFloat(elements.touchPanel.style.transform?.replace('translateY(', '').replace('px)', '') || '0');
            touchPanelExpanded = currentY < window.innerHeight * 0.2;
            elements.touchPanel.classList.toggle('expanded', touchPanelExpanded);
            elements.touchPanel.style.transform = '';
        });
    }
    
    console.log('Smart Wardrobe initialized');
}

// Start app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// Export for debugging
window.SmartWardrobe = {
    state,
    api,
    loadOutfit,
    showToast,
    openModal,
    closeModal
};