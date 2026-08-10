// Smart Wardrobe - Settings UI
// Admin panel for /settings route - CRUD operations, bulk actions, configuration

import { api } from './api.js';
import {
    formatType, formatPattern, formatFormality, escapeHtml,
    showToast, openModal, closeModal, prefersReducedMotion, debounce
} from './utils.js';

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
            isLoading: false,
            currentTags: [],
            suggestedTags: []
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
        this.elements.garmentsGrid = document.getElementById('garmentsGrid');
        this.elements.emptyState = document.getElementById('emptyState');
        this.elements.openAddGarmentModal = document.getElementById('openAddGarmentModal');
        this.elements.emptyAddGarmentBtn = document.getElementById('emptyAddGarmentBtn');

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
        this.elements.uploadZone = document.getElementById('uploadZone');
        this.elements.imagePreview = document.getElementById('imagePreview');
        this.elements.previewImage = document.getElementById('previewImage');
        this.elements.removeImage = document.getElementById('removeImage');

        // Style & Tags fields
        this.elements.garmentColorName = document.getElementById('garmentColorName');
        this.elements.garmentColorHex = document.getElementById('garmentColorHex');
        this.elements.garmentPattern = document.getElementById('garmentPattern');
        this.elements.garmentFormality = document.getElementById('garmentFormality');
        this.elements.garmentTagInput = document.getElementById('garmentTagInput');
        this.elements.currentTagsList = document.getElementById('currentTagsList');
        this.elements.suggestTagsBtn = document.getElementById('suggestTagsBtn');
        this.elements.suggestedTagsList = document.getElementById('suggestedTagsList');
        this.elements.suggestedTagsChips = document.getElementById('suggestedTagsChips');
        this.elements.garmentTagsHidden = document.getElementById('garmentTagsHidden');

        // System status
        this.elements.aiProviderStatus = document.getElementById('aiProviderStatus');
        this.elements.dbStatus = document.getElementById('dbStatus');
        this.elements.nimApiKeyInput = document.getElementById('nimApiKeyInput');
        this.elements.saveConfigBtn = document.getElementById('saveConfigBtn');
    }

    bindEvents() {
        // Add garment buttons
        if (this.elements.openAddGarmentModal) {
            this.elements.openAddGarmentModal.addEventListener('click', () => this.openAddGarmentModal());
        }
        if (this.elements.emptyAddGarmentBtn) {
            this.elements.emptyAddGarmentBtn.addEventListener('click', () => this.openAddGarmentModal());
        }

        // Image upload - drag & drop
        const upload = this.elements.imageUpload;
        const uploadZone = this.elements.uploadZone;
        const fileInput = this.elements.garmentImage;
        if (upload && uploadZone && fileInput) {
            // Click to open
            uploadZone.addEventListener('click', (e) => {
                if (!e.target.closest('.preview-remove') && !e.target.closest('.image-preview')) {
                    fileInput.click();
                }
            });

            // File input change
            fileInput.addEventListener('change', (e) => this.handleImageSelect(e));

            // Drag & drop
            ['dragenter', 'dragover'].forEach(evt => {
                uploadZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    uploadZone.classList.add('drag-active');
                });
            });
            ['dragleave', 'drop'].forEach(evt => {
                uploadZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    uploadZone.classList.remove('drag-active');
                });
            });
            uploadZone.addEventListener('drop', (e) => {
                const file = e.dataTransfer.files[0];
                if (file && file.type.startsWith('image/')) {
                    fileInput.files = e.dataTransfer.files;
                    this.handleImageSelect({ target: fileInput });
                }
            });
        }

        // Remove image
        if (this.elements.removeImage) {
            this.elements.removeImage.addEventListener('click', () => this.clearImagePreview());
        }

        // Tags
        if (this.elements.garmentTagInput) {
            this.elements.garmentTagInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const value = this.elements.garmentTagInput.value.trim();
                    if (value) {
                        this.addTag(value);
                        this.elements.garmentTagInput.value = '';
                    }
                }
            });
        }
        if (this.elements.suggestTagsBtn) {
            this.elements.suggestTagsBtn.addEventListener('click', () => this.suggestTagsWithAI());
        }

        // Bulk actions
        if (this.elements.selectAllCheckbox) {
            this.elements.selectAllCheckbox.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
        }
        if (this.elements.bulkDeleteBtn) {
            this.elements.bulkDeleteBtn.addEventListener('click', () => this.confirmBulkDelete());
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

        // Scroll reveal for sections (IntersectionObserver)
        if ('IntersectionObserver' in window && !prefersReducedMotion()) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('revealed');
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

            document.querySelectorAll('.reveal-on-scroll').forEach(el => {
                observer.observe(el);
            });
        }
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
        const grid = this.elements.garmentsGrid;
        const emptyState = this.elements.emptyState;
        if (!grid) return;

        const start = (this.state.currentPage - 1) * this.state.pageSize;
        const end = start + this.state.pageSize;
        const pageItems = this.state.filteredGarments.slice(start, end);

        if (pageItems.length === 0) {
            grid.innerHTML = '';
            if (emptyState) emptyState.hidden = false;
            return;
        }

        if (emptyState) emptyState.hidden = true;

        grid.innerHTML = pageItems.map(garment => this.createGarmentCard(garment)).join('');

        // Bind events for new cards
        this.bindGarmentCardEvents();
    }

    createGarmentCard(garment) {
        const colorHex = garment.color_hex || '#666666';
        const isSelected = this.state.selectedGarmentIds.has(garment.id);
        const imageUrl = garment.raw_image_path
            ? `/images/raw/${garment.raw_image_path.replace(/^.*[\\\/]/, '')}`
            : garment.processed_image_path
                ? `/images/processed/garments/${garment.processed_image_path.replace(/^.*[\\\/]/, '')}`
                : null;

        return `
            <article class="wardrobe-item ${isSelected ? 'selected' : ''}" data-garment-id="${garment.id}">
                <div class="wardrobe-item-checkbox">
                    <input type="checkbox" class="item-checkbox" data-garment-id="${garment.id}" ${isSelected ? 'checked' : ''} aria-label="Select ${this.escapeHtml(garment.name)}">
                </div>
                ${imageUrl
                    ? `<img class="wardrobe-item-image" src="${imageUrl}" alt="${this.escapeHtml(garment.name)}" loading="lazy">`
                    : `<div class="wardrobe-item-image" style="background-color: ${colorHex};"></div>`
                }
                <div class="wardrobe-item-info">
                    <h4 class="wardrobe-item-name">${this.escapeHtml(garment.name)}</h4>
                    <div class="wardrobe-item-meta">
                        <span class="tag tag-type">${formatType(garment.type)}</span>
                        <span class="tag tag-color" style="--tag-color: ${colorHex}">${this.escapeHtml(garment.color_name)}</span>
                        <span class="tag">${formatPattern(garment.pattern)}</span>
                        <span class="tag">${formatFormality(garment.formality)}</span>
                    </div>
                </div>
                <div class="wardrobe-item-actions">
                    <button class="item-action-btn edit-btn" data-garment-id="${garment.id}" aria-label="Edit garment">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                    <button class="item-action-btn delete-btn" data-garment-id="${garment.id}" aria-label="Delete garment">
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
            this.elements.bulkDeleteBtn.textContent = `Delete ${count} garments`;
        }
    }

    async confirmBulkDelete() {
        const count = this.state.selectedGarmentIds.size;
        if (count === 0) return;

        if (!confirm(`Delete ${count} selected garments? This action cannot be undone.`)) {
            return;
        }

        try {
            const ids = Array.from(this.state.selectedGarmentIds);
            await api.bulkDeleteGarments(ids);
            showToast(`${count} garments deleted`, 'success');
            this.state.selectedGarmentIds.clear();
            await this.loadGarments();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    async confirmDeleteGarment(id) {
        if (!confirm('Delete this garment? This action cannot be undone.')) return;

        try {
            await api.deleteGarment(id);
            showToast('Garment deleted', 'success');
            await this.loadGarments();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
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
        if (submitBtn) {
            submitBtn.querySelector('.btn-text').textContent = 'Update Garment';
        }
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
        if (form.garmentColorName) form.garmentColorName.value = garment.color_name || '';
        if (form.garmentColorHex) form.garmentColorHex.value = garment.color_hex || '#4a4a4a';
        if (form.garmentPattern) form.garmentPattern.value = garment.pattern || 'solid';
        if (form.garmentFormality) form.garmentFormality.value = garment.formality || 1;

        this.state.currentTags = Array.isArray(garment.tags) ? [...garment.tags] : [];
        this.state.suggestedTags = [];
        this.renderTags();

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
            showToast('Please select an image', 'warning');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        const btnText = submitBtn?.querySelector('.btn-text');
        const btnLoading = submitBtn?.querySelector('.btn-loading');
        const originalText = btnText?.textContent;

        if (submitBtn) {
            submitBtn.disabled = true;
            if (btnText) btnText.hidden = true;
            if (btnLoading) btnLoading.hidden = false;
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
                    material: formData.get('garmentMaterial') || undefined,
                    color_name: formData.get('garmentColorName') || undefined,
                    color_hex: formData.get('garmentColorHex') || undefined,
                    pattern: formData.get('garmentPattern') || undefined,
                    formality: formData.get('garmentFormality') ? parseInt(formData.get('garmentFormality'), 10) : undefined,
                    tags: this.state.currentTags
                };

                await api.updateGarment(parseInt(editId), garmentData);
                showToast('Garment updated', 'success');
            } else {
                formData.set('tags', JSON.stringify(this.state.currentTags));
                await api.createGarment(formData);
                showToast('Garment saved successfully', 'success');
            }

            this.closeModal(this.elements.addGarmentModal);
            form.reset();
            this.clearImagePreview();
            delete form.dataset.editId;
            if (btnText) btnText.textContent = 'Save Garment';

            await this.loadGarments();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                if (btnText) btnText.hidden = false;
                if (btnLoading) btnLoading.hidden = true;
            }
        }
    }

    openAddGarmentModal() {
        const form = this.elements.addGarmentForm;
        if (form) {
            form.reset();
            delete form.dataset.editId;
            const btnText = form.querySelector('.btn-text');
            if (btnText) btnText.textContent = 'Save Garment';
        }
        this.state.currentTags = [];
        this.state.suggestedTags = [];
        this.renderTags();
        this.clearImagePreview();
        this.openModal(this.elements.addGarmentModal);
    }

    handleImageSelect(event) {
        const file = event.target.files?.[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            showToast('Please select a valid image', 'warning');
            event.target.value = '';
            return;
        }

        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            showToast('Image too large (max 10MB)', 'warning');
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
        const uploadZone = this.elements.uploadZone;
        const imagePreview = this.elements.imagePreview;
        const previewImage = this.elements.previewImage;

        if (uploadZone) uploadZone.classList.add('hidden');
        if (imagePreview) imagePreview.hidden = false;
        if (previewImage) previewImage.src = dataUrl;
    }

    clearImagePreview() {
        const uploadZone = this.elements.uploadZone;
        const imagePreview = this.elements.imagePreview;
        const fileInput = this.elements.garmentImage;

        if (uploadZone) uploadZone.classList.remove('hidden');
        if (imagePreview) imagePreview.hidden = true;
        if (fileInput) fileInput.value = '';
        if (uploadZone) uploadZone.classList.remove('drag-active');
    }

    // ========== TAGS ==========

    addTag(tag) {
        tag = tag.trim().toLowerCase();
        if (!tag || this.state.currentTags.includes(tag)) return;
        this.state.currentTags.push(tag);
        this.state.suggestedTags = this.state.suggestedTags.filter(t => t !== tag);
        this.renderTags();
    }

    removeTag(tag) {
        this.state.currentTags = this.state.currentTags.filter(t => t !== tag);
        this.renderTags();
    }

    dismissSuggestedTag(tag) {
        this.state.suggestedTags = this.state.suggestedTags.filter(t => t !== tag);
        this.renderTags();
    }

    renderTags() {
        const list = this.elements.currentTagsList;
        if (list) {
            list.innerHTML = this.state.currentTags.map(tag => `
                <span class="tag-chip">
                    ${escapeHtml(tag)}
                    <button type="button" class="tag-chip-remove" data-tag="${escapeHtml(tag)}" aria-label="Remove tag ${escapeHtml(tag)}">&times;</button>
                </span>
            `).join('');
            list.querySelectorAll('.tag-chip-remove').forEach(btn => {
                btn.addEventListener('click', () => this.removeTag(btn.dataset.tag));
            });
        }

        const suggList = this.elements.suggestedTagsList;
        const suggChips = this.elements.suggestedTagsChips;
        if (suggList && suggChips) {
            if (this.state.suggestedTags.length === 0) {
                suggList.hidden = true;
            } else {
                suggList.hidden = false;
                suggChips.innerHTML = this.state.suggestedTags.map(tag => `
                    <span class="tag-chip tag-chip-suggested">
                        <button type="button" class="tag-chip-accept" data-tag="${escapeHtml(tag)}">+ ${escapeHtml(tag)}</button>
                        <button type="button" class="tag-chip-dismiss" data-tag="${escapeHtml(tag)}" aria-label="Dismiss ${escapeHtml(tag)}">&times;</button>
                    </span>
                `).join('');
                suggChips.querySelectorAll('.tag-chip-accept').forEach(btn => {
                    btn.addEventListener('click', () => this.addTag(btn.dataset.tag));
                });
                suggChips.querySelectorAll('.tag-chip-dismiss').forEach(btn => {
                    btn.addEventListener('click', () => this.dismissSuggestedTag(btn.dataset.tag));
                });
            }
        }

        if (this.elements.garmentTagsHidden) {
            this.elements.garmentTagsHidden.value = JSON.stringify(this.state.currentTags);
        }
    }

    // ========== SYSTEM CONFIGURATION ==========

    async suggestTagsWithAI() {
        const form = this.elements.addGarmentForm;
        const name = form.garmentName?.value?.trim();
        const type = form.garmentType?.value;

        if (!name || !type) {
            showToast('Add a name and type first', 'warning');
            return;
        }

        const btn = this.elements.suggestTagsBtn;
        if (btn) btn.disabled = true;

        try {
            const result = await api.suggestTags({
                name,
                type,
                color_name: form.garmentColorName?.value || null,
                material: form.garmentMaterial?.value || null,
                pattern: form.garmentPattern?.value || null,
                brand: form.garmentBrand?.value || null,
                season: form.garmentSeason?.value || null,
                existing_tags: this.state.currentTags
            });
            const newOnes = (result.suggested_tags || []).filter(t => !this.state.currentTags.includes(t));
            this.state.suggestedTags = [...new Set([...this.state.suggestedTags, ...newOnes])];
            this.renderTags();
            if (newOnes.length === 0) {
                showToast('No new tag suggestions', 'info');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    async loadSystemStatus() {
        try {
            const health = await api.healthCheck();

            if (this.elements.aiProviderStatus) {
                this.elements.aiProviderStatus.textContent = health.ai_provider === 'nim' ? 'NVIDIA NIM (Advanced)' : 'Local Rules (Standard)';
                this.elements.aiProviderStatus.className = 'status-value ' + (health.ai_provider === 'nim' ? 'status-success' : 'status-warning');
            }

            if (this.elements.dbStatus) {
                this.elements.dbStatus.textContent = health.database === 'connected' ? 'Connected' : 'Disconnected';
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
            showToast('Configuration saved. Restart backend to apply changes.', 'info');
        } else {
            showToast('Please enter a valid API Key', 'warning');
        }
    }

    // ========== UI HELPERS ==========

    showGridLoading() {
        const grid = this.elements.garmentsGrid;
        const emptyState = this.elements.emptyState;
        if (grid) {
            grid.innerHTML = `
                <div class="grid-loading" style="grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; color: var(--text-muted);">
                    <div class="spinner" style="width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 16px;"></div>
                    <p>Loading garments...</p>
                </div>
            `;
            if (emptyState) emptyState.hidden = true;
        }
    }

    showGridError(message) {
        const grid = this.elements.garmentsGrid;
        const emptyState = this.elements.emptyState;
        if (grid) {
            grid.innerHTML = `
                <div class="grid-error" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                    </svg>
                    <h3 style="margin-bottom: 8px; color: var(--text-secondary);">Error loading</h3>
                    <p>${this.escapeHtml(message)}</p>
                    <button class="btn btn-primary" onclick="settingsUI.loadGarments()" style="margin-top: 16px;">Retry</button>
                </div>
            `;
            if (emptyState) emptyState.hidden = true;
        }
    }

    // Use shared utilities from utils.js
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
                const btnText = form.querySelector('.btn-text');
                if (btnText) btnText.textContent = 'Save Garment';
            }
            this.clearImagePreview();
        }
    }
}

export function initSettingsUI() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.settingsUI = new SettingsUI();
        });
    } else {
        window.settingsUI = new SettingsUI();
    }
}