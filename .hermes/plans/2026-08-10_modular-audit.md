# Smart Wardrobe — Modular Architecture Audit

## Two parallel systems exist

### Runtime system (what the app actually uses)
These files are imported by `backend/api/routers/wardrobe.py` and `backend/api/main.py`:

| Layer | File | Responsibility |
|-------|------|---------------|
| Models | `backend/models/garment.py` | SQLModel tables: Garment, Outfit, OutfitItem, StyleRule, UserFeedback |
| Schemas | `backend/models/schemas.py` | Pydantic request/response models |
| Repositories | `backend/repositories/garment_repo.py` | All repos in one file: Garment, Outfit, OutfitItem, StyleRule |
| Services | `backend/services/outfit_service.py` | All business logic: recommend, pack, score, feedback |
| Vision | `backend/vision/segmenter.py`, `classifier.py`, `color_extractor.py` | SAM, CLIP, ColorThief |
| Vision pipeline | `backend/vision/ingestion_pipeline.py` | Orchestrates vision stages |
| Config | `backend/core/config.py` | Pydantic Settings |
| Database | `backend/database/connection.py` | Engine, session, init |
| AI | `backend/ai_providers/factory.py`, `local.py`, `nim.py` | Provider abstraction |

### Legacy system (only used by tests, NOT by runtime)
These files are NOT imported by any runtime code. Only `tests/` and `__init__.py` files reference them.

| File | Status | Used by |
|------|--------|---------|
| `backend/domain/` (entire dir) | **Dead code** | Only imports itself |
| `backend/repositories/garment_repository.py` | **Legacy** | `repositories/__init__.py`, tests |
| `backend/repositories/outfit_repository.py` | **Legacy** | `repositories/__init__.py`, tests |
| `backend/repositories/style_rule_repository.py` | **Semi-active** | `database/connection.py:51` (seed data) |
| `backend/repositories/user_feedback_repository.py` | **Legacy** | `repositories/__init__.py`, tests |
| `backend/services/outfit_composer.py` | **Legacy** | `services/__init__.py`, tests |
| `backend/services/packing_service.py` | **Legacy** | `services/__init__.py`, tests |
| `backend/services/style_engine.py` | **Legacy** | `services/__init__.py`, tests, outfit_composer, packing_service |
| `backend/services/feedback_service.py` | **Legacy** | `services/__init__.py`, tests |
| `backend/vision/pipeline.py` | **Dead code** | Nobody |
| `backend/vision/stages/` | **Dead code** | Only pipeline.py (which is dead) |
| `frontend/static/js/main.js` | **Dead code** | Nobody imports it |
| `frontend/static/js/touch_panel.js` | **Dead code** | Nobody imports it |

## Extensibility assessment

### How to add a new feature WITHOUT touching existing code:

1. **New API endpoint**: Add a new router in `wardrobe.py` (or create a new router file and include it in `main.py`). No existing endpoint needs modification.

2. **New garment field**: Add to `GarmentBase` schema → auto-propagates to Create/Update/Response. Add column to `Garment` SQLModel. Run migration. No existing endpoint changes.

3. **New vision stage**: Create a new module in `backend/vision/` (e.g., `pattern_detector.py`). Import it in `ingestion_pipeline.py`. The existing segmenter/classifier/color_extractor don't need changes.

4. **New AI provider**: Create a new file in `backend/ai_providers/` implementing the same interface. Register in `factory.py`. Existing providers untouched.

5. **New frontend view**: Create `templates/newview.html` + `static/js/newview.js`. Add route to `index.html` router. Existing views untouched.

### What CANNOT be extended without touching existing code:

- **Adding a new field to outfits**: Requires changes to `OutfitBase` schema AND `Outfit` model (both in different files, but same concept)
- **Adding filtering logic**: `garment_repo.get_all()` has hardcoded filter types. A new filter type requires adding an `if` block to this function.
- **Adding a new scoring criterion**: `_calculate_score()` in `outfit_service.py` has hardcoded scoring components.

## Recommendation (ponytail: not now, YAGNI)

The dual system is debt but not blocking. The legacy files should be deleted when:
1. Tests are migrated to use the runtime system
2. `__init__.py` files stop re-exporting legacy classes
3. `database/connection.py:51` stops using legacy `StyleRuleRepository`

Until then, leaving them avoids a risky refactor with no runtime benefit.
