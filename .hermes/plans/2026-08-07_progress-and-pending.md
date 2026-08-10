# Smart Wardrobe — Estado de Progreso y Tareas Pendientes

**Fecha:** 2026-08-07
**Sesión:** Continuación del rediseño completo del Smart Wardrobe

---

## ✅ COMPLETADO

### Infraestructura
- [x] Contenedor Docker levantado en puerto 7000 (`docker compose --profile dev up -d --build`)
- [x] Health endpoint responde 200 OK (`{"status":"ok","database":"connected"}`)
- [x] Base de datos SQLite operativa con 2 garments de prueba (Test Shirt, Test Pants)
- [x] Migración de puerto 8000 → 7000 en todos los configs (Dockerfile, compose, nginx, scripts)

### Frontend — Fixes aplicados (vía 3 subagents paralelos)
- [x] **kiosk.js**: `outfit.garments` → `outfit.items[].garment` (líneas 368-370, 673-675)
  - Las imágenes de prendas ahora cargan correctamente en el kiosk
  - Test Shirt y Test Pants se muestran con tipo, color, patrón y formalidad
- [x] **kiosk.js stats**: `loadStats()` ahora maneja respuesta `{garments: [...]}` en vez de array directo (líneas 570-590)
  - Stats ahora muestran: 2 garments, 24 outfits, avg score 50
- [x] **api.js**: `/garments/bulk` → `/garments/bulk-delete` (línea 135)
- [x] **api.js**: `/packing` → `/recommend/packing` (línea 214)
- [x] **settings.js**: `Array.isArray(garments)` → `response.garments || []` (línea 191)

### Verificado funcional
- [x] `GET /health` → 200 OK
- [x] `GET /garments` → 200 OK, 2 garments
- [x] `GET /outfits` → 200 OK, 24 outfits
- [x] `POST /recommend/outfits` → 200 OK, outfit con score 50, items con garment data
- [x] `POST /feedback/outfit` → 200 OK, feedback registrado
- [x] `GET /rules` → 200 OK, 0 rules
- [x] Kiosk UI carga con imágenes de prendas, style tips, score breakdown, stats
- [x] Settings UI carga con formulario Add Garment, drag & drop image upload
- [x] `node --check` pasa para kiosk.js, api.js, settings.js

---

## 🔴 PENDIENTE — BUGS POR ARREGLAR

### Bug 1: `POST /recommend/packing` devuelve 500 Internal Server Error
**Síntoma:** `curl -X POST http://127.0.0.1:7000/recommend/packing -H "Content-Type: application/json" -d '{"days":3,"occasion":"travel","season":"all_season","max_items":15}'` → 500
**Causa probable:** El método `create_packing_plan` en `outfit_service.py:278` llama:
1. `self.garment_repo.get_all(limit=1000, filters={"season": request.season})` — El método `get_all` en `garment_repo.py:31` puede no soportar el parámetro `filters`
2. O el error está en `_save_outfit()` o en la serialización a `PackingPlanResponse`
**Investigar:**
- Leer `garment_repo.py` línea 31 (`get_all` con filters) — verificar si acepta `filters` dict
- Leer `PackingPlanResponse` y `PackingPlanItem` en `schemas.py:185-206` — verificar que los campos coincidan con lo que devuelve `create_packing_plan`
- Habilitar logging de errores en el contenedor para ver el traceback completo: `docker compose --profile dev logs --tail 30 app`
- Posible fix: agregar `try/except` con logging en el endpoint, o corregir la firma de `get_all`

### Bug 2: `api.js` — endpoints GET de feedback no existen en backend
**Estado:** Los subagents los comentaron, pero verificar que kiosk.js no los llame
- `getOutfitFeedback(outfitId)` → `/feedback/outfit/${outfitId}` — no existe en backend (solo POST)
- `getGarmentFeedback(garmentId)` → `/feedback/garment/${garmentId}` — no existe en backend (solo POST)
**Acción:** Verificar que estén comentados en api.js y que nada los llame

### Bug 3: Router SPA no soporta path-based routing
**Síntoma:** `http://127.0.0.1:7000/settings` carga kiosk en vez de settings
**Causa:** El router usa `window.location.hash` — necesita `http://127.0.0.1:7000/#/settings`
**Acción:** Documentar que el routing es hash-based, o añadir soporte path-based en `index.html`

---

## 🔴 PENDIENTE — AUDITORÍA MODULAR (Ponytail Audit)

### Objetivo
Verificar que los componentes son modulares y que añadir funcionalidades nuevas NO requiere tocar código existente.

### Archivos duplicados detectados (debt técnica)
- `backend/repositories/garment_repo.py` vs `garment_repository.py` — dos repositorios para garments
- `backend/services/outfit_service.py` vs `outfit_composer.py` — dos servicios para outfits
- `frontend/static/js/main.js` vs `kiosk.js` + `api.js` — main.js tiene su propia implementación de API client

### Auditoría por capas
- [ ] **Frontend**: Verificar que `api.js`, `kiosk.js`, `settings.js`, `utils.js` tienen responsabilidades claras y no se solapan con `main.js`
- [ ] **Backend routers**: Verificar que `wardrobe.py` no tiene imports circulares ni dependencias cruzadas
- [ ] **Backend services**: Unificar `outfit_service.py` y `outfit_composer.py` o documentar cuál es canónico
- [ ] **Backend repositories**: Unificar `garment_repo.py` y `garment_repository.py` o documentar cuál es canónico
- [ ] **Vision pipeline**: Verificar que `segmenter.py`, `classifier.py`, `color_extractor.py` son intercambiables
- [ ] **AI Providers**: Verificar que `local.py` y `nim.py` implementan la misma interfaz via `factory.py`

### Regla ponytail
- Cada fix debe ser root-cause, shortest diff
- No refactorizar sin necesidad
- Dejar `ponytail:` comment solo si se corta una esquina real

---

## 🔴 PENDIENTE — QA COMPLETO DE INTERFAZ (Computer-Use)

### Objetivo
Probar todos los botones e interacciones desde el punto de vista del usuario.

### Tests pendientes
- [ ] Click "Generate Outfit" → debe cargar un outfit nuevo con imágenes
- [ ] Cambiar occasion (Casual, Work, Party, Date, Formal, Wedding) → debe filtrar outfits
- [ ] Cambiar season (All Season, Spring, Summer, Autumn, Winter) → debe filtrar outfits
- [ ] Click "Packing Mode" → debe abrir modal de packing (REQUIERE fix del Bug 1)
- [ ] Click "My Wardrobe" → debe abrir modal con grid de garments
- [ ] Click "Like" / "Dislike" → debe registrar feedback (verificado API, falta UI)
- [ ] Settings: Click "Add Garment" → debe abrir modal con form
- [ ] Settings: Drag & drop image → debe previsualizar imagen
- [ ] Settings: Submit form → debe crear garment y aparecer en grid
- [ ] Settings: Edit garment → debe cargar datos en form
- [ ] Settings: Delete garment → debe eliminar del grid
- [ ] Settings: Bulk select + delete → debe eliminar múltiples
- [ ] Settings: System status (AI provider, DB status) → debe mostrar estado

### Nota sobre computer-use
La herramienta `computer_use` no está disponible en este entorno (no aparece en tools ni en deferred tools). Usar `open_preview` + `read_preview` del desktop app, o `browser_navigate` + `browser_snapshot` para probar la interfaz.

---

## 🔴 PENDIENTE — PUSH A GITHUB

### Objetivo
Subir todos los cambios al repo `https://github.com/Mnu-Hdez/SmartWardrobe`

### Pasos
1. `cd "/Users/manuhdezz/Proyectos Hermes/SmartWardrobe"`
2. `git status` — revisar todos los archivos modificados
3. `git add -A`
4. `git commit -m "fix: outfit.items mapping, stats response shape, endpoint mismatches + port 7000 migration"`
5. `git remote -v` — verificar que el remoto apunta a `https://github.com/Mnu-Hdez/SmartWardrobe`
6. `git push origin master` (o la rama activa)

### Nota
El repositorio puede no tener commits todavía. Si es así, puede necesitar `git push -u origin master`.

---

## 📋 ORDEN RECOMENDADO AL RETOMAR

1. **Fix Bug 1**: `/recommend/packing` 500 error — es el blocker para Packing Mode
2. **Fix Bug 2**: Verificar que feedback GET endpoints están comentados en api.js
3. **QA completo**: Probar todos los botones con `open_preview` + `read_preview`
4. **Auditoría modular**: Revisar archivos duplicados y fronteras de responsabilidad
5. **Push a GitHub**: Commit + push de todos los cambios

---

## 🔧 COMANDOS ÚTILES

```bash
# Levantar contenedor
cd "/Users/manuhdezz/Proyectos Hermes/SmartWardrobe"
docker compose --profile dev up -d --build

# Ver logs
docker compose --profile dev logs --tail 30 app

# Health check
curl -s http://127.0.0.1:7000/health

# Probar endpoints
curl -s http://127.0.0.1:7000/garments | python3 -m json.tool
curl -s -X POST http://127.0.0.1:7000/recommend/outfits -H "Content-Type: application/json" -d '{"occasion":"casual","season":"all_season","top_n":1}' | python3 -m json.tool

# Abrir en preview pane
# Usar tool: open_preview(url="http://127.0.0.1:7000/#/kiosk")
# Usar tool: open_preview(url="http://127.0.0.1:7000/#/settings")

# Reconstruir después de cambios en JS
docker compose --profile dev up -d --build
```
