// Smart Wardrobe - i18n minimal (ponytail: fetch + textContent, sin librerías)
const STORAGE_KEY = 'wardrobe_lang';
let dict = {};

export function getLanguage() {
    return localStorage.getItem(STORAGE_KEY) || (navigator.language.startsWith('es') ? 'es' : 'en');
}

export function t(key) {
    return dict[key] || key;
}

export function applyTranslations(root = document) {
    root.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    root.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
        el.setAttribute('aria-label', t(el.dataset.i18nAriaLabel));
    });
    root.querySelectorAll('[data-i18n-lang-label]').forEach(el => {
        el.textContent = getLanguage() === 'es' ? 'EN' : 'ES';
    });
}

export async function setLanguage(lang) {
    const res = await fetch(`/static/i18n/${lang}.json`);
    dict = await res.json();
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
    applyTranslations();
    document.dispatchEvent(new CustomEvent('i18n:changed'));
}

export async function initI18n() {
    await setLanguage(getLanguage());
}

export function toggleLanguage() {
    return setLanguage(getLanguage() === 'es' ? 'en' : 'es');
}
