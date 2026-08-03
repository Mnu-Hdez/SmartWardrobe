// Smart Wardrobe - Settings UI
// Admin panel for /settings route - CRUD operations, bulk actions, configuration

import { api } from './api.js';

/**
 * Settings UI Controller
 * Handles wardrobe management, garment CRUD, and system configuration
 */
class SettingsUI {
    constructor() {
        this.state = {
            garments: [],
            filteredGarments: [],
            selectedGarmentIds: new Set(),
            currentPage: 1,
            pageSize: 24,
            filters: {
                search: '',
                type: '',
                season: ''
            },
            isLoading: false
        };
        
        this.elements = {};
        
        this.init();
    }
    
    async init() {
        this.cacheElements();
        this.bindEvents();
        await this.loadGarments();
        this.loadSystemStatus();
    }
    
    cacheElements() {
        // Grid and controls
        this.elements.wardrobeGrid = document.getElementById('wardrobeGrid');
        this.elements.wardrobeSearch = document.getElementById('wardrobeSearch');
        this.elements.wardrobeTypeFilter = document.getElementById('wardrobeTypeFilter');
        this.elements.wardrobeSeasonFilter = document.getElementById('wardrobeSeasonFilter');
        this.elements.addGarmentBtn = document.getElementById('addGarmentBtn');
        
        // Selection
        this.elements.selectAllCheckbox = document.getElementById('selectAllCheckbox');
        this.elements.bulkActions = document.getElementById('bulkActions');
        this.elements.bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
        this.elements.selectedCount = document.getElementById('selectedCount');
        
        // Modals
        this.elements.addGarmentModal = document.getElementById('addGarmentModal');
        this.elements.addGarmentForm = document.getElementById('addGarmentForm');
        this.elements.imageUpload = document.getElementById('imageUpload');
        this.elements.garmentImage = document.getElementById('garmentImage');
        this.elements.previewImage = document.getElementById('previewImage');
        
        // System status
        this.elements.aiProviderStatus = document.getElementById('aiProviderStatus');
        this.elements.dbStatus = document.getElementById('dbStatus');
        this.elements.nimApiKeyInput = document.getElementById('nimApiKeyInput');
        this.elements.saveConfigBtn = document.getElementById('saveConfigBtn');
    }
    
    bindEvents() {
        // Search and filters
        if (this.elements.wardrobeSearch) {
            this.elements.wardrobeSearch.addEventListener('input', this.debounce(() => {
                this.state.filters.search = this.elements.wardrobeSearch.value;
                this.applyFilters();
            }, 300));
        }

        if (this.elements.wardrobeTypeFilter) {
            this.elements.wardrobeTypeFilter.addEventListener('change', (e) => {
                this.state.filters.type = e.target.value;
                this.applyFilters();
            });
        }

        if (this.elements.wardrobeSeasonFilter) {
            this.elements.wardrobeSeasonFilter.addEventListener('change', (e) => {
                this.state.filters.season = e.target.value;
                this.applyFilters();
            });
        }
        
        // Add garment button
        if (this.elements.addGarmentBtn) {
            this.elements.addGarmentBtn.addEventListener('click', () => this.openAddGarmentModal());
        }
        
        // Select all checkbox
        if (this.elements.selectAllCheckbox) {
            this.elements.selectAllCheckbox.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
        }
        
        // Bulk delete
        if (this.elements.bulkDeleteBtn) {
            this.elements.bulkDeleteBtn.addEventListener('click', () => this.confirmBulkDelete());
        }
        
        // Image upload
        if (this.elements.garmentImage) {
            this.elements.garmentImage.addEventListener('change', (e) => this.handleImageSelect(e));
        }

        if (this.elements.imageUpload && this.elements.garmentImage) {
            this.elements.imageUpload.addEventListener('click', (e) => {
                // Don't trigger if clicking the remove button or preview
                if (!e.target.closest('.remove-image') && !e.target.closest('.image-preview')) {
                    this.elements.garmentImage.click();
                }
            });
        }
        
        // Remove image
        const removeImageBtn = this.elements.imageUpload?.querySelector('.remove-image');
        if (removeImageBtn) {
            removeImageBtn.addEventListener('click', () => this.clearImagePreview());
        }
        
        // Add garment form
        if (this.elements.addGarmentForm) {
            this.elements.addGarmentForm.addEventListener('submit', (e) => this.handleAddGarmentSubmit(e));
        }
        
        // Cancel buttons
        document.querySelectorAll('[data-modal-cancel]').forEach(btn => {
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
        
        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this.closeModal(modal);
            });
        });
        
        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal:not(.hidden)').forEach(modal => this.closeModal(modal));
            }
        });
        
        // System config
        if (this.elements.saveConfigBtn) {
            this.elements.saveConfigBtn.addEventListener('click', () => this.saveSystemConfig());
        }
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // ========== GARMENT MANAGEMENT ==========
    
    async loadGarments() {
        this.state.isLoading = true;
        this.showGridLoading();
        
        try {
            const garments = await api.getGarments({ limit: 1000 });
            this.state.garments = Array.isArray(garments) ? garments : [];
            this.applyFilters();
        } catch (error) {
            console.error('Error loading garments:', error);
            this.showGridError(error.message);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    applyFilters() {
        const { search, type, season } = this.state.filters;
        
        this.state.filteredGarments = this.state.garments.filter(g => {
            const matchesSearch = !search || 
                g.name.toLowerCase().includes(search.toLowerCase()) ||
                g.color_name.toLowerCase().includes(search.toLowerCase()) ||
                (g.brand && g.brand.toLowerCase().includes(search.toLowerCase()));
            
            const matchesType = !type || g.type === type;
            const matchesSeason = !season || g.season === season || g.season === 'all_season';
            
            return matchesSearch && matchesType && matchesSeason;
        });
        
        this.state.currentPage = 1;
        this.renderGarmentGrid();
        this.updateSelectionState();
    }
    
    renderGarmentGrid() {
        const grid = this.elements.wardrobeGrid;
        if (!grid) return;
        
        const start = (this.state.currentPage - 1) * this.state.pageSize;
        const end = start + this.state.pageSize;
        const pageItems = this.state.filteredGarments.slice(start, end);
        
        if (pageItems.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                    </svg>
                    <h3 style="margin-bottom: 8px; color: var(--text-secondary);">No hay prendas</h3>
                    <p>Añade tu primera prenda para empezar</p>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = pageItems.map(garment => this.createGarmentCard(garment)).join('');
        
        // Bind events for new cards
        this.bindGarmentCardEvents();
    }
    
    createGarmentCard(garment) {
        const colorHex = garment.color_hex || '#666666';
        const isSelected = this.state.selectedGarmentIds.has(garment.id);
        const imageUrl = garment.raw_image_path 
            ? `/static/${garment.raw_image_path.replace(/^.*[\\/]/, '')}`
            : garment.processed_image_path
                ? `/static/${garment.processed_image_path.replace(/^.*[\\/]/, '')}`
                : null;
        
        return `
            <article class="wardrobe-item ${isSelected ? 'selected' : ''}" data-garment-id="${garment.id}">
                <div class="wardrobe-item-checkbox">
                    <input type="checkbox" class="item-checkbox" data-garment-id="${garment.id}" ${isSelected ? 'checked' : ''} aria-label="Seleccionar ${this.escapeHtml(garment.name)}">
                </div>
                ${imageUrl 
                    ? `<img class="wardrobe-item-image" src="${imageUrl}" alt="${this.escapeHtml(garment.name)}" loading="lazy">`
                    : `<div class="wardrobe-item-image" style="background-color: ${colorHex};"></div>`
                }
                <div class="wardrobe-item-info">
                    <h4 class="wardrobe-item-name">${this.escapeHtml(garment.name)}</h4>
                    <div class="wardrobe-item-meta">
                        <span class="wardrobe-item-tag type">${this.formatType(garment.type)}</span>
                        <span class="wardrobe-item-tag color" style="--tag-color: ${colorHex}">${this.escapeHtml(garment.color_name)}</span>
                        <span class="wardrobe-item-tag">${this.formatPattern(garment.pattern)}</span>
                        <span class="wardrobe-item-tag">${this.formatFormality(garment.formality)}</span>
                    </div>
                </div>
                <div class="wardrobe-item-actions">
                    <button class="item-action-btn edit-btn" data-garment-id="${garment.id}" aria-label="Editar prenda">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                    <button class="item-action-btn delete-btn" data-garment-id="${garment.id}" aria-label="Eliminar prenda">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </div>
            </article>
        `;
    }
    
    bindGarmentCardEvents() {
        // Checkboxes
        document.querySelectorAll('.item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const id = parseInt(e.target.dataset.garmentId);
                this.toggleGarmentSelection(id, e.target.checked);
            });
        });
        
        // Edit buttons
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.dataset.garmentId);
                this.editGarment(id);
            });
        });
        
        // Delete buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.dataset.garmentId);
                this.confirmDeleteGarment(id);
            });
        });
        
        // Card click (for selection on mobile)
        document.querySelectorAll('.wardrobe-item').forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't trigger if clicking on action buttons or checkbox
                if (e.target.closest('.item-action-btn') || e.target.closest('.item-checkbox') || e.target.closest('.wardrobe-item-checkbox')) {
                    return;
                }
                
                const checkbox = card.querySelector('.item-checkbox');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }
    
    toggleGarmentSelection(id, selected) {
        if (selected) {
            this.state.selectedGarmentIds.add(id);
        } else {
            this.state.selectedGarmentIds.delete(id);
        }
        this.updateSelectionState();
    }
    
    toggleSelectAll(selectAll) {
        if (selectAll) {
            this.state.filteredGarments.forEach(g => this.state.selectedGarmentIds.add(g.id));
        } else {
            this.state.selectedGarmentIds.clear();
        }
        this.renderGarmentGrid();
        this.updateSelectionState();
    }
    
    updateSelectionState() {
        const count = this.state.selectedGarmentIds.size;
        const allItems = this.state.filteredGarments.length;
        
        if (this.elements.selectAllCheckbox) {
            this.elements.selectAllCheckbox.checked = count > 0 && count === allItems;
            this.elements.selectAllCheckbox.indeterminate = count > 0 && count < allItems;
        }
        
        if (this.elements.bulkActions) {
            this.elements.bulkActions.classList.toggle('hidden', count === 0);
        }
        
        if (this.elements.selectedCount) {
            this.elements.selectedCount.textContent = count;
        }
        
        if (this.elements.bulkDeleteBtn) {
            this.elements.bulkDeleteBtn.textContent = `Eliminar ${count} prendas`;
        }
    }
    
    async confirmBulkDelete() {
        const count = this.state.selectedGarmentIds.size;
        if (count === 0) return;
        
        if (!confirm(`¿Eliminar ${count} prendas seleccionadas? Esta acción no se puede deshacer.`)) {
            return;
        }
        
        try {
            const ids = Array.from(this.state.selectedGarmentIds);
            await api.bulkDeleteGarments(ids);
            this.showToast(`${count} prendas eliminadas`, 'success');
            this.state.selectedGarmentIds.clear();
            await this.loadGarments();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    }
    
    async confirmDeleteGarment(id) {
        if (!confirm('¿Eliminar esta prenda? Esta acción no se puede deshacer.')) return;
        
        try {
            await api.deleteGarment(id);
            this.showToast('Prenda eliminada', 'success');
            await this.loadGarments();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        }
    }
    
    editGarment(id) {
        const garment = this.state.garments.find(g => g.id === id);
        if (!garment) return;
        
        // Populate form with garment data
        this.populateEditForm(garment);
        this.openModal(this.elements.addGarmentModal);
        
        // Change form to edit mode
        this.elements.addGarmentForm.dataset.editId = id;
        const submitBtn = this.elements.addGarmentForm.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.textContent = 'Actualizar Prenda';
    }
    
    populateEditForm(garment) {
        const form = this.elements.addGarmentForm;
        if (!form) return;
        
        if (form.garmentName) form.garmentName.value = garment.name || '';
        if (form.garmentBrand) form.garmentBrand.value = garment.brand || '';
        if (form.garmentType) form.garmentType.value = garment.type || '';
        if (form.garmentSeason) form.garmentSeason.value = garment.season || 'all_season';
        if (form.garmentSize) form.garmentSize.value = garment.size || '';
        if (form.garmentMaterial) form.garmentMaterial.value = garment.material || '';
        
        // Clear image preview
        this.clearImagePreview();
    }
    
    async handleAddGarmentSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const editId = form.dataset.editId;
        const isEditing = !!editId;
        
        const formData = new FormData(form);
        
        // Validate image for new garments
        if (!isEditing && !formData.get('garmentImage')?.size) {
            this.showToast('Por favor selecciona una imagen', 'warning');
            return;
        }
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn?.textContent;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = isEditing ? 'Actualizando...' : 'Guardando...';
        }
        
        try {
            if (isEditing) {
                // For editing, we only update metadata (not image)
                const garmentData = {
                    name: formData.get('garmentName'),
                    brand: formData.get('garmentBrand') || undefined,
                    type: formData.get('garmentType'),
                    season: formData.get('garmentSeason'),
                    size: formData.get('garmentSize') || undefined,
                    material: formData.get('garmentMaterial') || undefined
                };
                
                await api.updateGarment(parseInt(editId), garmentData);
                this.showToast('Prenda actualizada', 'success');
            } else {
                await api.createGarment(formData);
                this.showToast('Prenda guardada correctamente', 'success');
            }
            
            this.closeModal(this.elements.addGarmentModal);
            form.reset();
            this.clearImagePreview();
            delete form.dataset.editId;
            if (submitBtn) submitBtn.textContent = originalText;
            
            await this.loadGarments();
        } catch (error) {
            this.showToast(`Error: ${error.message}`, 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    }
    
    openAddGarmentModal() {
        const form = this.elements.addGarmentForm;
        if (form) {
            form.reset();
            delete form.dataset.editId;
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.textContent = 'Guardar Prenda';
        }
        this.clearImagePreview();
        this.openModal(this.elements.addGarmentModal);
    }
    
    handleImageSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.showToast('Por favor selecciona una imagen válida', 'warning');
            event.target.value = '';
            return;
        }
        
        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            this.showToast('La imagen es demasiado grande (máx. 10MB)', 'warning');
            event.target.value = '';
            return;
        }
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            this.showImagePreview(e.target.result);
        };
        reader.readAsDataURL(file);
    }
    
    showImagePreview(dataUrl) {
        const upload = this.elements.imageUpload;
        const placeholder = upload?.querySelector('.upload-placeholder');
        const preview = upload?.querySelector('.image-preview');
        const img = preview?.querySelector('#previewImage');
        
        if (placeholder) placeholder.classList.add('hidden');
        if (preview) preview.classList.remove('hidden');
        if (img) img.src = dataUrl;
    }
    
       clearImagePreview() {
        const upload = this.elements.imageUpload;
        if (!upload) return;
        const placeholder = upload.querySelector('.upload-placeholder');
        const preview = upload.querySelector('.image-preview');
        const input = upload.querySelector('#garmentImage');

        if (placeholder) placeholder.classList.remove('hidden');
        if (preview) preview.classList.add('hidden');
        if (input) input.value = '';
    }
    
    // ========== SYSTEM CONFIGURATION ==========
    
    async loadSystemStatus() {
        try {
            const health = await api.healthCheck();
            
            if (this.elements.aiProviderStatus) {
                this.elements.aiProviderStatus.textContent = health.ai_provider === 'nim' ? 'NVIDIA NIM (Avanzado)' : 'Reglas Locales (Estándar)';
                this.elements.aiProviderStatus.className = 'status-value ' + (health.ai_provider === 'nim' ? 'status-success' : 'status-warning');
            }
            
            if (this.elements.dbStatus) {
                this.elements.dbStatus.textContent = health.database === 'connected' ? 'Conectada' : 'Desconectada';
                this.elements.dbStatus.className = 'status-value ' + (health.database === 'connected' ? 'status-success' : 'status-error');
            }
        } catch (error) {
            console.error('Error loading system status:', error);
        }
    }
    
    async saveSystemConfig() {
        const apiKey = this.elements.nimApiKeyInput?.value?.trim();
        
        if (apiKey) {
            // In a real implementation, this would update the backend config
            // For now, we'll show a message
            this.showToast('Configuración guardada. Reinicia el backend para aplicar cambios.', 'info');
        } else {
            this.showToast('Ingresa una API Key válida', 'warning');
        }
    }
    
    // ========== UI HELPERS ==========
    
    showGridLoading() {
        const grid = this.elements.wardrobeGrid;
        if (grid) {
            grid.innerHTML = `
                <div class="grid-loading" style="grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; color: var(--text-muted);">
                    <div class="spinner" style="width: 40px; height: 40px; border: 3px solid var(--border-primary); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 16px;"></div>
                    <p>Cargando prendas...</p>
                </div>
            `;
        }
    }
    
    showGridError(message) {
        const grid = this.elements.wardrobeGrid;
        if (grid) {
            grid.innerHTML = `
                <div class="grid-error" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                    </svg>
                    <h3 style="margin-bottom: 8px; color: var(--text-secondary);">Error al cargar</h3>
                    <p>${this.escapeHtml(message)}</p>
                    <button class="btn btn-primary" onclick="settingsUI.loadGarments()" style="margin-top: 16px;">Reintentar</button>
                </div>
            `;
        }
    }
    
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
        
        // Reset form if it's the add/edit garment modal
        if (modal === this.elements.addGarmentModal) {
            const form = this.elements.addGarmentForm;
            if (form) {
                form.reset();
                delete form.dataset.editId;
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) submitBtn.textContent = 'Guardar Prenda';
            }
            this.clearImagePreview();
        }
    }
    
    // ========== UTILITIES ==========
    
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
}

// Initialize when DOM is ready — exported for SPA router
export function initSettingsUI() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.settingsUI = new SettingsUI();
        });
    } else {
        window.settingsUI = new SettingsUI();
    }
}