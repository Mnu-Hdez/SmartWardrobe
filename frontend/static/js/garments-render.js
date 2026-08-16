// Smart Wardrobe - Shared garment card rendering
// The image + name + meta-tag-row markup is identical across every place a
// garment gets shown as a card (settings wardrobe grid, kiosk wardrobe
// modal, kiosk outfit display) - only the outer wrapper (checkbox, actions,
// heading level, class names) differs per caller. Extracted so the near-
// identical copies can't drift out of sync (SRP - see the architecture
// review, section 3).

import { formatType, formatPattern, formatFormality, escapeHtml, garmentImageUrl } from './utils.js';

/**
 * Renders a garment's image + name + meta tag row (type/color/pattern/
 * formality) - the part that's byte-identical across cards. Callers wrap
 * this in their own <article> with whatever extra chrome (checkbox,
 * actions) their card needs.
 * @param {Object} garment
 * @param {Object} [opts]
 * @param {'h3'|'h4'} [opts.headingTag='h4']
 * @param {string} [opts.imageClass='wardrobe-item-image']
 * @param {string} [opts.infoClass='wardrobe-item-info']
 * @param {string} [opts.nameClass='wardrobe-item-name']
 * @param {string} [opts.metaClass='wardrobe-item-meta']
 */
export function garmentCardBodyHTML(garment, opts = {}) {
    const {
        headingTag = 'h4',
        imageClass = 'wardrobe-item-image',
        infoClass = 'wardrobe-item-info',
        nameClass = 'wardrobe-item-name',
        metaClass = 'wardrobe-item-meta',
    } = opts;
    const colorHex = garment.color_hex || '#666666';
    const imageUrl = garmentImageUrl(garment);

    return `
        ${imageUrl
            ? `<img class="${imageClass}" src="${imageUrl}" alt="${escapeHtml(garment.name)}" loading="lazy">`
            : `<div class="${imageClass}" style="background-color: ${colorHex};"></div>`
        }
        <div class="${infoClass}">
            <${headingTag} class="${nameClass}">${escapeHtml(garment.name)}</${headingTag}>
            <div class="${metaClass}">
                <span class="tag tag-type">${formatType(garment.type)}</span>
                <span class="tag tag-color" style="--tag-color: ${colorHex}">${escapeHtml(garment.color_name)}</span>
                <span class="tag">${formatPattern(garment.pattern)}</span>
                <span class="tag">${formatFormality(garment.formality)}</span>
            </div>
        </div>
    `;
}
