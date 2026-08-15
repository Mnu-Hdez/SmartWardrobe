// Smart Wardrobe - Color palette
// Base color families with named tone variants (ES/EN), used to:
//   1. Power the <datalist> suggestions on the "Color" field (type "blanco",
//      get "Blanco roto", "Blanco cáscara de huevo"...).
//   2. Auto-derive a color_hex swatch from the typed name, since the
//      backend still needs a valid hex for the wardrobe/kiosk color dots
//      even though there's no more RGB picker in the UI.

const PALETTE = [
    {
        hex: '#FFFFFF',
        tones: [
            { es: 'Blanco', en: 'White' },
            { es: 'Blanco roto', en: 'Off-white', hex: '#F5F0E6' },
            { es: 'Blanco hueso', en: 'Bone white', hex: '#F9F6EE' },
            { es: 'Blanco cáscara de huevo', en: 'Eggshell white', hex: '#F0EAD6' },
            { es: 'Blanco nieve', en: 'Snow white', hex: '#FFFAFA' },
            { es: 'Blanco marfil', en: 'Ivory', hex: '#FFFFF0' },
            { es: 'Blanco perla', en: 'Pearl white', hex: '#F1F0EA' },
        ],
    },
    {
        hex: '#000000',
        tones: [
            { es: 'Negro', en: 'Black' },
            { es: 'Negro azabache', en: 'Jet black', hex: '#0A0A0A' },
            { es: 'Negro carbón', en: 'Charcoal black', hex: '#1C1C1C' },
            { es: 'Negro grafito', en: 'Graphite black', hex: '#2B2B2B' },
            { es: 'Negro tinta', en: 'Ink black', hex: '#111111' },
        ],
    },
    {
        hex: '#808080',
        tones: [
            { es: 'Gris', en: 'Gray' },
            { es: 'Gris claro', en: 'Light gray', hex: '#D3D3D3' },
            { es: 'Gris oscuro', en: 'Dark gray', hex: '#4A4A4A' },
            { es: 'Gris perla', en: 'Pearl gray', hex: '#C9C9C9' },
            { es: 'Gris antracita', en: 'Anthracite gray', hex: '#383838' },
            { es: 'Gris topo', en: 'Taupe gray', hex: '#8B8589' },
            { es: 'Gris piedra', en: 'Stone gray', hex: '#A8A29E' },
        ],
    },
    {
        hex: '#2563EB',
        tones: [
            { es: 'Azul', en: 'Blue' },
            { es: 'Azul marino', en: 'Navy blue', hex: '#1B2A4A' },
            { es: 'Azul cielo', en: 'Sky blue', hex: '#87CEEB' },
            { es: 'Azul turquesa', en: 'Turquoise blue', hex: '#40E0D0' },
            { es: 'Azul cobalto', en: 'Cobalt blue', hex: '#0047AB' },
            { es: 'Azul petróleo', en: 'Petrol blue', hex: '#1F4E5F' },
            { es: 'Azul eléctrico', en: 'Electric blue', hex: '#4169E1' },
            { es: 'Azul denim', en: 'Denim blue', hex: '#3B5D82' },
        ],
    },
    {
        hex: '#D32F2F',
        tones: [
            { es: 'Rojo', en: 'Red' },
            { es: 'Rojo vino', en: 'Wine red', hex: '#722F37' },
            { es: 'Rojo granate', en: 'Garnet red', hex: '#6E0D25' },
            { es: 'Rojo coral', en: 'Coral red', hex: '#FF6F61' },
            { es: 'Rojo cereza', en: 'Cherry red', hex: '#C40233' },
            { es: 'Rojo ladrillo', en: 'Brick red', hex: '#B22222' },
            { es: 'Rojo carmín', en: 'Carmine red', hex: '#960018' },
        ],
    },
    {
        hex: '#2E7D32',
        tones: [
            { es: 'Verde', en: 'Green' },
            { es: 'Verde oliva', en: 'Olive green', hex: '#708238' },
            { es: 'Verde botella', en: 'Bottle green', hex: '#006A4E' },
            { es: 'Verde menta', en: 'Mint green', hex: '#98FF98' },
            { es: 'Verde militar', en: 'Military green', hex: '#4B5320' },
            { es: 'Verde esmeralda', en: 'Emerald green', hex: '#50C878' },
            { es: 'Verde musgo', en: 'Moss green', hex: '#8A9A5B' },
            { es: 'Verde bosque', en: 'Forest green', hex: '#228B22' },
        ],
    },
    {
        hex: '#FFD700',
        tones: [
            { es: 'Amarillo', en: 'Yellow' },
            { es: 'Amarillo mostaza', en: 'Mustard yellow', hex: '#E1AD01' },
            { es: 'Amarillo pastel', en: 'Pastel yellow', hex: '#FFF6A5' },
            { es: 'Amarillo limón', en: 'Lemon yellow', hex: '#FFF44F' },
            { es: 'Amarillo canario', en: 'Canary yellow', hex: '#FFEF00' },
        ],
    },
    {
        hex: '#FF8C00',
        tones: [
            { es: 'Naranja', en: 'Orange' },
            { es: 'Naranja quemado', en: 'Burnt orange', hex: '#CC5500' },
            { es: 'Naranja pastel', en: 'Pastel orange', hex: '#FFCC99' },
            { es: 'Naranja teja', en: 'Terracotta orange', hex: '#C86B4A' },
            { es: 'Naranja calabaza', en: 'Pumpkin orange', hex: '#FF7518' },
        ],
    },
    {
        hex: '#FFC0CB',
        tones: [
            { es: 'Rosa', en: 'Pink' },
            { es: 'Rosa palo', en: 'Dusty pink', hex: '#D8A7B1' },
            { es: 'Rosa fucsia', en: 'Fuchsia pink', hex: '#FF00FF' },
            { es: 'Rosa empolvado', en: 'Powder pink', hex: '#F1DADA' },
            { es: 'Rosa chicle', en: 'Bubblegum pink', hex: '#FFC1E0' },
            { es: 'Rosa salmón', en: 'Salmon pink', hex: '#FF91A4' },
        ],
    },
    {
        hex: '#800080',
        tones: [
            { es: 'Morado', en: 'Purple' },
            { es: 'Morado lavanda', en: 'Lavender purple', hex: '#B497BD' },
            { es: 'Morado berenjena', en: 'Aubergine purple', hex: '#3D0C3D' },
            { es: 'Morado malva', en: 'Mauve purple', hex: '#915F6D' },
            { es: 'Morado ciruela', en: 'Plum purple', hex: '#8E4585' },
        ],
    },
    {
        hex: '#795548',
        tones: [
            { es: 'Marrón', en: 'Brown' },
            { es: 'Marrón chocolate', en: 'Chocolate brown', hex: '#4B2E1E' },
            { es: 'Marrón camel', en: 'Camel brown', hex: '#C19A6B' },
            { es: 'Marrón tierra', en: 'Earth brown', hex: '#6B4423' },
            { es: 'Marrón caramelo', en: 'Caramel brown', hex: '#A9702F' },
            { es: 'Marrón café', en: 'Coffee brown', hex: '#6F4E37' },
        ],
    },
    {
        hex: '#F5F5DC',
        tones: [
            { es: 'Beige', en: 'Beige' },
            { es: 'Beige arena', en: 'Sand beige', hex: '#E8D9B5' },
            { es: 'Beige topo', en: 'Mushroom beige', hex: '#C2B280' },
        ],
    },
    {
        hex: '#D4AF37',
        tones: [
            { es: 'Dorado', en: 'Gold' },
            { es: 'Dorado champán', en: 'Champagne gold', hex: '#F7E7CE' },
        ],
    },
    {
        hex: '#C0C0C0',
        tones: [{ es: 'Plateado', en: 'Silver' }],
    },
];

const DEFAULT_HEX = '#4a4a4a';

function normalize(str) {
    return String(str)
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
}

/**
 * Flat list of {name, hex} for the given language ('es' | 'en'), used to
 * populate the color <datalist>. Prefix-ordered within each family so
 * typing the base color name (e.g. "Blanco") surfaces all its tones.
 */
export function getColorPalette(lang = 'es') {
    const list = [];
    for (const family of PALETTE) {
        for (const tone of family.tones) {
            list.push({
                name: lang === 'en' ? tone.en : tone.es,
                hex: tone.hex || family.hex,
            });
        }
    }
    return list;
}

/**
 * Best-effort hex lookup for a freely-typed color name. Tries an exact
 * match in the given language, then the other language (in case the app
 * language was switched after typing), then a substring match. Falls back
 * to a neutral gray so the required color_hex field is always valid.
 */
export function getHexForColorName(name, lang = 'es') {
    if (!name || !name.trim()) return DEFAULT_HEX;
    const target = normalize(name);

    const primary = getColorPalette(lang);
    let match = primary.find((c) => normalize(c.name) === target);
    if (match) return match.hex;

    const other = getColorPalette(lang === 'en' ? 'es' : 'en');
    match = other.find((c) => normalize(c.name) === target);
    if (match) return match.hex;

    match =
        primary.find((c) => normalize(c.name).includes(target)) ||
        other.find((c) => normalize(c.name).includes(target));
    if (match) return match.hex;

    return DEFAULT_HEX;
}

export { DEFAULT_HEX };
