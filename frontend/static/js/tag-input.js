// Smart Wardrobe - Tag Input component
// Self-contained tag-chip widget: current tags (removable) + AI-suggested
// tags (accept/dismiss). Owns its own state so callers don't need to keep
// currentTags/suggestedTags in their own state object - they read tags via
// getTags() and feed new ones in via setTags()/addSuggestions().

import { escapeHtml } from './utils.js';

/**
 * @param {Object} elements
 * @param {HTMLInputElement} elements.input - text input, Enter adds a tag
 * @param {HTMLElement} elements.currentList - container for current tag chips
 * @param {HTMLElement} elements.suggestedList - wrapper shown/hidden based on suggestions
 * @param {HTMLElement} elements.suggestedChips - container for suggested tag chips
 * @param {HTMLInputElement} elements.hiddenField - hidden form field synced with current tags (JSON)
 */
export function createTagInput({ input, currentList, suggestedList, suggestedChips, hiddenField }) {
    let currentTags = [];
    let suggestedTags = [];

    function render() {
        if (currentList) {
            currentList.innerHTML = currentTags.map(tag => `
                <span class="tag-chip">
                    ${escapeHtml(tag)}
                    <button type="button" class="tag-chip-remove" data-tag="${escapeHtml(tag)}" aria-label="Remove tag ${escapeHtml(tag)}">&times;</button>
                </span>
            `).join('');
            currentList.querySelectorAll('.tag-chip-remove').forEach(btn => {
                btn.addEventListener('click', () => remove(btn.dataset.tag));
            });
        }

        if (suggestedList && suggestedChips) {
            if (suggestedTags.length === 0) {
                suggestedList.hidden = true;
            } else {
                suggestedList.hidden = false;
                suggestedChips.innerHTML = suggestedTags.map(tag => `
                    <span class="tag-chip tag-chip-suggested">
                        <button type="button" class="tag-chip-accept" data-tag="${escapeHtml(tag)}">+ ${escapeHtml(tag)}</button>
                        <button type="button" class="tag-chip-dismiss" data-tag="${escapeHtml(tag)}" aria-label="Dismiss ${escapeHtml(tag)}">&times;</button>
                    </span>
                `).join('');
                suggestedChips.querySelectorAll('.tag-chip-accept').forEach(btn => {
                    btn.addEventListener('click', () => add(btn.dataset.tag));
                });
                suggestedChips.querySelectorAll('.tag-chip-dismiss').forEach(btn => {
                    btn.addEventListener('click', () => dismissSuggestion(btn.dataset.tag));
                });
            }
        }

        if (hiddenField) {
            hiddenField.value = JSON.stringify(currentTags);
        }
    }

    function add(tag) {
        tag = tag.trim().toLowerCase();
        if (!tag || currentTags.includes(tag)) return;
        currentTags.push(tag);
        suggestedTags = suggestedTags.filter(t => t !== tag);
        render();
    }

    function remove(tag) {
        currentTags = currentTags.filter(t => t !== tag);
        render();
    }

    function dismissSuggestion(tag) {
        suggestedTags = suggestedTags.filter(t => t !== tag);
        render();
    }

    /** Merges newly-suggested tags in (deduped against current + existing suggestions). Returns how many were actually new. */
    function addSuggestions(tags) {
        const newOnes = (tags || []).filter(t => !currentTags.includes(t));
        suggestedTags = [...new Set([...suggestedTags, ...newOnes])];
        render();
        return newOnes.length;
    }

    /** Replaces the current tag list wholesale (e.g. populating the edit form) and clears any pending suggestions. */
    function setTags(tags) {
        currentTags = Array.isArray(tags) ? [...tags] : [];
        suggestedTags = [];
        render();
    }

    function reset() {
        setTags([]);
    }

    function getTags() {
        return currentTags;
    }

    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const value = input.value.trim();
                if (value) {
                    add(value);
                    input.value = '';
                }
            }
        });
    }

    return { render, add, remove, dismissSuggestion, addSuggestions, setTags, reset, getTags };
}
