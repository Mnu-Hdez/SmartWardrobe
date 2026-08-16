// Smart Wardrobe - Settings UI
// Admin panel for /settings route - CRUD operations, bulk actions, configuration

import { api } from './api.js';
import { getLanguage } from './i18n.js';
import { getColorPalette, getHexForColorName } from './colors.js';
import {
    escapeHtml,
    showToast, openModal, closeModal, prefersReducedMotion, debounce
} from './utils.js';
import { garmentCardBodyHTML } from './garments-render.js';
import { createTagInput } from './tag-input.js';
import { createImageUpload } from './image-upload.js';

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
            // Tracks whether each provider already has a key saved server-side
            // (independent of whatever's currently typed in the password
            // inputs) - lets switching providers work without retyping a key
            // that was already configured in a previous save.
            aiConfigured: { nim: false, gemini: false }
        };

        this.elements = {};

        this.init();
    }

    async init() {
        this.cacheElements();
        this.tagInput = createTagInput({
            input: this.elements.garmentTagInput,
            currentList: this.elements.currentTagsList,
            suggestedList: this.elements.suggestedTagsList,
            suggestedChips: this.elements.suggestedTagsChips,
            hiddenField: this.elements.garmentTagsHidden
        });
        this.imageUpload = createImageUpload({
            zone: this.elements.uploadZone,
            fileInput: this.elements.garmentImage,
            preview: this.elements.imagePreview,
            previewImage: this.elements.previewImage,
            removeBtn: this.elements.removeImage,
            autoFillBtn: this.elements.autoFillBtn
        });
        this.bindEvents();
        this.populateColorSuggestions();
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
        this.elements.garmentImage = document.getElementById('garmentImage');
        this.elements.uploadZone = document.getElementById('uploadZone');
        this.elements.imagePreview = document.getElementById('imagePreview');
        this.elements.previewImage = document.getElementById('previewImage');
        this.elements.removeImage = document.getElementById('removeImage');
        this.elements.autoFillBtn = document.getElementById('autoFillBtn');
        this.elements.autoFillBtnText = document.getElementById('autoFillBtnText');

        // Style & Tags fields
        this.elements.garmentColorName = document.getElementById('garmentColorName');
        this.elements.garmentColorHex = document.getElementById('garmentColorHex');
        this.elements.colorSuggestions = document.getElementById('colorSuggestions');
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
        this.elements.aiProviderSelect = document.getElementById('aiProviderSelect');
        this.elements.nimApiKeyInput = document.getElementById('nimApiKeyInput');
        this.elements.geminiApiKeyInput = document.getElementById('geminiApiKeyInput');
        this.elements.saveConfigBtn = document.getElementById('saveConfigBtn');

        // Export / Import
        this.elements.exportGarmentsBtn = document.getElementById('exportGarmentsBtn');
        this.elements.importGarmentsBtn = document.getElementById('importGarmentsBtn');
        this.elements.importGarmentsInput = document.getElementById('importGarmentsInput');
    }

    bindEvents() {
        // Add garment buttons
        if (this.elements.openAddGarmentModal) {
            this.elements.openAddGarmentModal.addEventListener('click', () => this.openAddGarmentModal());
        }
        if (this.elements.emptyAddGarmentBtn) {
            this.elements.emptyAddGarmentBtn.addEventListener('click', () => this.openAddGarmentModal());
        }

        // Image upload, drag & drop, and remove are bound inside createImageUpload()

        // Auto-fill with AI
        if (this.elements.autoFillBtn) {
            this.elements.autoFillBtn.addEventListener('click', () => this.autoFillFromImage());
        }

        // Tag "Enter to add" is bound inside createTagInput()
        if (this.elements.suggestTagsBtn) {
            this.elements.suggestTagsBtn.addEventListener('click', () => this.suggestTagsWithAI());
        }

        // Color name -> auto-derive the hidden color_hex swatch, and
        // refresh the tone suggestions if the app language changes
        if (this.elements.garmentColorName) {
            this.elements.garmentColorName.addEventListener('input', () => this.updateColorHexFromName());
        }
        document.addEventListener('i18n:changed', () => this.populateColorSuggestions());

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

        // Export / Import
        if (this.elements.exportGarmentsBtn) {
            this.elements.exportGarmentsBtn.addEventListener('click', () => this.exportGarments());
        }
        if (this.elements.importGarmentsBtn && this.elements.importGarmentsInput) {
            this.elements.importGarmentsBtn.addEventListener('click', () => this.elements.importGarmentsInput.click());
            this.elements.importGarmentsInput.addEventListener('change', (e) => this.handleImportFile(e));
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
            // getGarments() returns the paginated shape { garments, total, ... },
            // not a bare array - getAllGarments() unwraps it and walks every
            // page so nothing (including a garment just created) is missed.
            this.state.garments = await api.getAllGarments();
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
        const isSelected = this.state.selectedGarmentIds.has(garment.id);

        return `
            <article class="wardrobe-item ${isSelected ? 'selected' : ''}" data-garment-id="${garment.id}">
                <div class="wardrobe-item-checkbox">
                    <input type="checkbox" class="item-checkbox" data-garment-id="${garment.id}" ${isSelected ? 'checked' : ''} aria-label="Select ${escapeHtml(garment.name)}">
                </div>
                ${garmentCardBodyHTML(garment)}
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

        this.tagInput.setTags(garment.tags);

        // Clear image preview
        this.imageUpload.clear();
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
                    tags: this.tagInput.getTags()
                };

                await api.updateGarment(parseInt(editId), garmentData);
                showToast('Garment updated', 'success');
            } else {
                // The form's `name` attributes are prefixed (garmentName, garmentType...)
                // for readability/namespacing, but the backend's multipart Form(...)
                // params expect the unprefixed keys. Rebuild the payload explicitly
                // rather than relying on FormData(form) 1:1.
                const uploadData = new FormData();
                uploadData.set('name', formData.get('garmentName') || '');
                uploadData.set('type', formData.get('garmentType') || '');
                uploadData.set('season', formData.get('garmentSeason') || '');
                uploadData.set('color_name', formData.get('garmentColorName') || '');
                uploadData.set('color_hex', formData.get('garmentColorHex') || '');
                uploadData.set('pattern', formData.get('garmentPattern') || '');
                uploadData.set('formality', formData.get('garmentFormality') || '1');
                const brand = formData.get('garmentBrand');
                if (brand) uploadData.set('brand', brand);
                const size = formData.get('garmentSize');
                if (size) uploadData.set('size', size);
                const material = formData.get('garmentMaterial');
                if (material) uploadData.set('material', material);
                uploadData.set('tags', JSON.stringify(this.tagInput.getTags()));
                uploadData.set('garmentImage', formData.get('garmentImage'));

                await api.createGarment(uploadData);
                showToast('Garment saved successfully', 'success');
            }

            this.closeModal(this.elements.addGarmentModal);
            form.reset();
            this.imageUpload.clear();
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
        this.tagInput.reset();
        this.imageUpload.clear();
        this.openModal(this.elements.addGarmentModal);
    }

    // ========== COLOR ==========

    /**
     * Fills the <datalist> backing the Color field with tone suggestions
     * for the current app language (e.g. typing "blanco" surfaces "Blanco
     * roto", "Blanco cáscara de huevo"...). Re-run when the language toggles.
     */
    populateColorSuggestions() {
        const datalist = this.elements.colorSuggestions;
        if (!datalist) return;
        const palette = getColorPalette(getLanguage());
        datalist.innerHTML = palette.map(c => `<option value="${escapeHtml(c.name)}"></option>`).join('');
    }

    /**
     * There's no more RGB/color picker in the UI, but the backend still
     * requires a valid color_hex. Derive it automatically from whatever
     * the user types in the Color field (falls back to a neutral gray for
     * names outside the known palette).
     */
    updateColorHexFromName() {
        const nameInput = this.elements.garmentColorName;
        const hexInput = this.elements.garmentColorHex;
        if (!nameInput || !hexInput) return;
        hexInput.value = getHexForColorName(nameInput.value, getLanguage());
    }

    // ========== SYSTEM CONFIGURATION ==========

    async autoFillFromImage() {
        const fileInput = this.elements.garmentImage;
        const file = fileInput?.files?.[0];
        if (!file) {
            showToast('Select an image first', 'warning');
            return;
        }

        const btn = this.elements.autoFillBtn;
        const btnText = this.elements.autoFillBtnText;
        const originalText = btnText?.textContent;
        if (btn) btn.disabled = true;
        if (btnText) btnText.textContent = 'Analyzing...';

        try {
            const result = await api.analyzeImage(file);
            const form = this.elements.addGarmentForm;
            let filledCount = 0;

            // Only fill fields that are still empty/default, so we never
            // clobber something the user already typed on purpose.
            if (result.name && form.garmentName && !form.garmentName.value.trim()) {
                form.garmentName.value = result.name;
                filledCount++;
            }
            if (result.type && form.garmentType && !form.garmentType.value) {
                form.garmentType.value = result.type;
                filledCount++;
            }
            if (result.color_name && form.garmentColorName && !form.garmentColorName.value.trim()) {
                form.garmentColorName.value = result.color_name;
                filledCount++;
            }
            if (result.color_hex && form.garmentColorHex) {
                form.garmentColorHex.value = result.color_hex;
                filledCount++;
            }
            if (result.material && form.garmentMaterial && !form.garmentMaterial.value.trim()) {
                form.garmentMaterial.value = result.material;
                filledCount++;
            }
            if (result.pattern && form.garmentPattern) {
                form.garmentPattern.value = result.pattern;
                filledCount++;
            }
            if (result.formality && form.garmentFormality) {
                form.garmentFormality.value = String(result.formality);
                filledCount++;
            }
            if (result.tags && result.tags.length) {
                this.tagInput.addSuggestions(result.tags);
            }

            if (filledCount === 0 && (!result.tags || result.tags.length === 0)) {
                showToast(
                    result.provider === 'local'
                        ? 'Only color detected — connect NIM or Gemini for full auto-fill'
                        : 'Could not confidently read this photo',
                    'info'
                );
            } else {
                showToast(`Auto-filled from photo (${result.provider})`, 'success');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            if (btn) btn.disabled = false;
            if (btnText) btnText.textContent = originalText;
        }
    }

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
                existing_tags: this.tagInput.getTags()
            });
            const addedCount = this.tagInput.addSuggestions(result.suggested_tags || []);
            if (addedCount === 0) {
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
            const providerLabels = {
                nim: 'NVIDIA NIM',
                gemini: 'Google Gemini',
                local: 'Local Rules'
            };

            if (this.elements.aiProviderStatus) {
                this.elements.aiProviderStatus.textContent = providerLabels[health.ai_provider] || health.ai_provider;
                this.elements.aiProviderStatus.className = 'status-value ' + (health.ai_provider === 'local' ? 'status-warning' : 'status-success');
            }

            if (this.elements.dbStatus) {
                this.elements.dbStatus.textContent = health.database === 'connected' ? 'Connected' : 'Disconnected';
                this.elements.dbStatus.className = 'status-value ' + (health.database === 'connected' ? 'status-success' : 'status-error');
            }

            if (this.elements.aiProviderSelect) {
                this.elements.aiProviderSelect.value = health.ai_provider;
            }

            const config = await api.getAIConfig();
            // Remember which providers already have a key saved server-side,
            // independent of the (currently empty) password inputs - this is
            // what lets saveSystemConfig() allow switching providers without
            // forcing the user to retype a key that was already configured.
            this.state.aiConfigured.nim = !!config.nim_configured;
            this.state.aiConfigured.gemini = !!config.gemini_configured;
            if (this.elements.nimApiKeyInput && config.nim_configured) {
                this.elements.nimApiKeyInput.placeholder = '•••••••• (configured)';
            }
            if (this.elements.geminiApiKeyInput && config.gemini_configured) {
                this.elements.geminiApiKeyInput.placeholder = '•••••••• (configured)';
            }
        } catch (error) {
            console.error('Error loading system status:', error);
        }
    }

    async saveSystemConfig() {
        const provider = this.elements.aiProviderSelect?.value || 'local';
        const nimKey = this.elements.nimApiKeyInput?.value?.trim();
        const geminiKey = this.elements.geminiApiKeyInput?.value?.trim();

        // Only block the switch if this provider has NEITHER a freshly
        // typed key NOR one already saved server-side - switching to a
        // provider that was configured in a previous save must work without
        // retyping its key every time.
        if (provider === 'nim' && !nimKey && !this.state.aiConfigured.nim) {
            showToast('Enter a NIM API key, or pick another provider', 'warning');
            return;
        }
        if (provider === 'gemini' && !geminiKey && !this.state.aiConfigured.gemini) {
            showToast('Enter a Google AI Studio API key, or pick another provider', 'warning');
            return;
        }

        const btn = this.elements.saveConfigBtn;
        if (btn) btn.disabled = true;

        try {
            await api.updateAIConfig({
                provider,
                nim_api_key: nimKey || undefined,
                gemini_api_key: geminiKey || undefined
            });
            showToast('AI provider saved and applied — will survive restarts too', 'success');
            if (this.elements.nimApiKeyInput) this.elements.nimApiKeyInput.value = '';
            if (this.elements.geminiApiKeyInput) this.elements.geminiApiKeyInput.value = '';
            await this.loadSystemStatus();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // ========== EXPORT / IMPORT ==========

    /**
     * Downloads the whole wardrobe (metadata + photos, bundled as a .zip by
     * the backend) via api.exportGarments(), which triggers the browser's
     * native save dialog directly - nothing to render here.
     */
    async exportGarments() {
        const btn = this.elements.exportGarmentsBtn;
        if (btn) btn.disabled = true;
        try {
            await api.exportGarments();
            showToast('Wardrobe exported', 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    /**
     * Uploads a .zip previously produced by exportGarments(). The backend
     * unpacks wardrobe.json + images/ and creates a brand-new garment (with
     * its own copied photo) per entry - always additive, never overwrites
     * or dedupes against what's already in the wardrobe.
     */
    async handleImportFile(event) {
        const file = event.target.files?.[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.zip')) {
            showToast('Select a .zip export file', 'warning');
            event.target.value = '';
            return;
        }

        const btn = this.elements.importGarmentsBtn;
        if (btn) btn.disabled = true;

        try {
            const result = await api.importGarments(file);
            const skippedNote = result.skipped ? ` (${result.skipped} skipped)` : '';
            showToast(`Imported ${result.imported} garments${skippedNote}`, 'success');
            await this.loadGarments();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            if (btn) btn.disabled = false;
            event.target.value = '';
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
                    <p>${escapeHtml(message)}</p>
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
            this.imageUpload.clear();
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