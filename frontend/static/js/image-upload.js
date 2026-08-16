// Smart Wardrobe - Image Upload component
// Self-contained drag & drop / click-to-browse image picker with preview.
// Owns its own preview state; the caller is notified via onSelect(file)
// when a valid image is chosen so it can react (e.g. trigger AI auto-fill).

import { showToast } from './utils.js';

const MAX_SIZE_BYTES = 10 * 1024 * 1024;

/**
 * @param {Object} elements
 * @param {HTMLElement} elements.zone - drop zone / click target
 * @param {HTMLInputElement} elements.fileInput - the underlying <input type="file">
 * @param {HTMLElement} elements.preview - preview container, toggled via .hidden
 * @param {HTMLImageElement} elements.previewImage - <img> that gets the data URL
 * @param {HTMLElement} elements.removeBtn - clears the preview
 * @param {HTMLElement} [elements.autoFillBtn] - shown once an image is picked, hidden on clear
 * @param {(file: File) => void} [onSelect] - called with the picked File after validation
 */
export function createImageUpload({ zone, fileInput, preview, previewImage, removeBtn, autoFillBtn }, onSelect) {
    function handleFile(file) {
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            showToast('Please select a valid image', 'warning');
            if (fileInput) fileInput.value = '';
            return;
        }
        if (file.size > MAX_SIZE_BYTES) {
            showToast('Image too large (max 10MB)', 'warning');
            if (fileInput) fileInput.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => showPreview(e.target.result);
        reader.readAsDataURL(file);

        if (autoFillBtn) autoFillBtn.hidden = false;
        if (onSelect) onSelect(file);
    }

    function showPreview(dataUrl) {
        if (zone) zone.classList.add('hidden');
        if (preview) preview.hidden = false;
        if (previewImage) previewImage.src = dataUrl;
    }

    function clear() {
        if (zone) zone.classList.remove('hidden');
        if (preview) preview.hidden = true;
        if (fileInput) fileInput.value = '';
        if (zone) zone.classList.remove('drag-active');
        if (autoFillBtn) autoFillBtn.hidden = true;
    }

    if (zone && fileInput) {
        zone.addEventListener('click', (e) => {
            if (!e.target.closest('.preview-remove') && !e.target.closest('.image-preview')) {
                fileInput.click();
            }
        });

        fileInput.addEventListener('change', (e) => handleFile(e.target.files?.[0]));

        ['dragenter', 'dragover'].forEach(evt => {
            zone.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.add('drag-active');
            });
        });
        ['dragleave', 'drop'].forEach(evt => {
            zone.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.remove('drag-active');
            });
        });
        zone.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                fileInput.files = e.dataTransfer.files;
                handleFile(file);
            }
        });
    }

    if (removeBtn) {
        removeBtn.addEventListener('click', () => clear());
    }

    return { clear };
}
