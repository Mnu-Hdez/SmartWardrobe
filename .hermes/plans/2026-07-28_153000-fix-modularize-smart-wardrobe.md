# Smart Wardrobe - Fix & Modularization Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Fix all code issues that can cause runtime failures and refactor the codebase into a more modular, testable, and maintainable architecture.

**Architecture:** Clean Architecture with clear separation of concerns:
- Domain layer (models, schemas, enums)
- Application layer (services, use cases)
- Infrastructure layer (repositories, vision pipeline, AI providers)
- Interface layer (API routes, frontend)

**Tech Stack:** FastAPI, SQLModel/SQLite, PyTorch/SAM/CLIP, Docker, vanilla JS SPA

---

## Current Issues Identified

### Critical Bugs
1. **SAMSegmenter.segment()** returns RGBA image but ingestion pipeline saves as JPEG → "cannot write mode RGBA as JPEG" crash
2. **OutfitComposer.recommend()** calls `get_available_provider()` without `await` in API route
3. **StyleRule.parameters** stored as JSON string but validator doesn't handle empty dict → crash
4. **GarmentCreate** requires `dominant_color_hex` but API uses `color_hex` field name
5. **CLIPClassifier.classify()** returns formality as string but DB expects IntEnum
6. **OutfitComposer.get_outfit_with_details()** manually constructs dict instead of using schema
7. **Frontend kiosk.js** assumes `/static/` prefix for images but paths are absolute

### Architectural Issues
1. **Circular imports**: `backend/repositories/__init__.py` imports from `backend.models.garment` which imports from `backend.models.schemas`
2. **God classes**: `OutfitComposer` (398 lines), `StyleEngine` (407 lines), `IngestionPipeline` (266 lines) do too much
3. **Tight coupling**: Services directly instantiate vision models; hard to test/mock
4. **No dependency injection**: Settings accessed globally via `get_settings()`
5. **Mixed concerns**: Vision pipeline, DB operations, and business logic intertwined
6. **No interfaces**: Concrete classes used everywhere; can't swap implementations

---

## Step-by-Step Plan

### Phase 1: Fix Critical Bugs (Immediate)

#### Task 1: Fix SAMSegmenter RGBA→JPEG Save Error
**Files:** `backend/vision/ingestion_pipeline.py`
**Steps:**
1. Write test reproducing the error
2. Change masked image save to PNG format
3. Update path generation to use `.png` extension

#### Task 2: Fix OutfitComposer.recommend() Missing Await
**Files:** `backend/api/routers/wardrobe.py:299`
**Steps:**
1. Add `await` before `AIProviderFactory.get_available_provider()`
2. Add test for `/enhance` endpoint

#### Task 3: Fix StyleRule Parameters JSON Parsing
**Files:** `backend/models/schemas.py:193-199`
**Steps:**
1. Handle `None`/empty string in validator
2. Return empty dict instead of crashing

#### Task 4: Fix Field Name Mismatch (color_hex vs dominant_color_hex)
**Files:** `backend/api/routers/wardrobe.py:66,123`, `backend/models/schemas.py:59`
**Steps:**
1. Align API form field with schema field name
2. Update both create and update endpoints

#### Task 5: Fix CLIPClassifier Formality Return Type
**Files:** `backend/vision/classifier.py`
**Steps:**
1. Map string formality to `FormalityLevel` IntEnum
2. Add validation

#### Task 6: Fix Frontend Image Path Resolution
**Files:** `frontend/static/js/kiosk.js:328-332`
**Steps:**
1. Use absolute paths from API response
2. Don't prepend `/static/`

---

### Phase 2: Break Circular Dependencies

#### Task 7: Separate Domain Models from SQLModel Tables
**Files:** 
- Create: `backend/domain/models.py` (pure Pydantic models)
- Modify: `backend/models/garment.py` (SQLModel tables only)
- Modify: `backend/models/schemas.py` (API schemas only)

**Steps:**
1. Create `GarmentType`, `Season`, `FormalityLevel`, `PatternType` enums in domain
2. Move `GarmentBase`, `GarmentCreate`, `GarmentRead` to domain
3. Keep `Garment` (SQLModel) in `models/garment.py`
4. Update all imports

#### Task 8: Fix Repository Import Cycle
**Files:** `backend/repositories/__init__.py`, `backend/repositories/garment_repository.py`
**Steps:**
1. Remove import of `Garment` from `backend.models.garment` in repositories
2. Use domain models or string annotations
3. Add `TYPE_CHECKING` imports where needed

---

### Phase 3: Introduce Dependency Injection & Interfaces

#### Task 9: Create Vision Pipeline Interfaces
**Files:**
- Create: `backend/vision/interfaces.py` (protocols)
- Modify: `backend/vision/segmenter.py`, `backend/vision/classifier.py`, `backend/vision/color_extractor.py`
- Create: `backend/vision/pipeline.py` (orchestrator)

**Steps:**
1. Define `SegmenterProtocol`, `ClassifierProtocol`, `ColorExtractorProtocol`
2. Implement protocols in concrete classes
3. Create `VisionPipeline` class that orchestrates all three
4. Add factory function for easy testing

#### Task 10: Create AI Provider Interface
**Files:**
- Create: `backend/ai_providers/protocols.py`
- Modify: `backend/ai_providers/local.py`, `backend/ai_providers/nim.py`, `backend/ai_providers/factory.py`

**Steps:**
1. Define `AIProviderProtocol` with `enhance_recommendation`, `generate_outfit_description`, `health_check`
2. Implement in both providers
3. Update factory to use protocol

#### Task 11: Create Settings Dependency
**Files:**
- Create: `backend/core/dependencies.py`
- Modify: All files using `get_settings()`

**Steps:**
1. Create `get_settings_dependency()` for FastAPI
2. Replace global `get_settings()` calls with dependency injection
3. Add `override_settings` for testing

---

### Phase 4: Decompose God Classes

#### Task 12: Split OutfitComposer into Focused Services
**Files:**
- Create: `backend/services/outfit_generator.py` (combination logic)
- Create: `backend/services/outfit_scorer.py` (scoring wrapper)
- Create: `backend/services/outfit_persister.py` (DB save logic)
- Modify: `backend/services/outfit_composer.py` (facade)
- Modify: `backend/services/__init__.py`

**Steps:**
1. Extract template definitions to `outfit_templates.py`
2. Extract combination generation to `OutfitGenerator`
3. Extract scoring to `OutfitScorer` (uses StyleEngine)
4. Extract persistence to `OutfitPersister`
5. `OutfitComposer` becomes thin facade

#### Task 13: Split StyleEngine into Rule-Based Scorers
**Files:**
- Create: `backend/services/scoring/rules.py` (base rule class)
- Create: `backend/services/scoring/color_harmony.py`
- Create: `backend/services/scoring/formality_match.py`
- Create: `backend/services/scoring/pattern_balance.py`
- Create: `backend/services/scoring/seasonal.py`
- Create: `backend/services/scoring/occasion.py`
- Create: `backend/services/scoring/user_bias.py`
- Create: `backend/services/scoring/engine.py` (composes rules)
- Modify: `backend/services/style_engine.py` (thin adapter)

**Steps:**
1. Create abstract `StyleRule` base class with `score(garments, context)`
2. Implement each rule as separate class
3. `StyleEngine` becomes registry + aggregator
4. Easy to add/remove/modify rules

#### Task 14: Split IngestionPipeline into Stages
**Files:**
- Create: `backend/vision/stages/segmentation_stage.py`
- Create: `backend/vision/stages/classification_stage.py`
- Create: `backend/vision/stages/color_extraction_stage.py`
- Create: `backend/vision/stages/storage_stage.py`
- Create: `backend/vision/stages/persistence_stage.py`
- Create: `backend/vision/pipeline.py` (orchestrator)
- Modify: `backend/vision/ingestion_pipeline.py` (thin wrapper)

**Steps:**
1. Each stage is a class with `process(input) -> output`
2. Pipeline chains stages with clear data flow
3. Each stage testable in isolation
4. Easy to reorder/replace stages

---

### Phase 5: Add Comprehensive Tests

#### Task 15: Unit Tests for Vision Pipeline Stages
**Files:**
- Create: `tests/unit/vision/test_segmentation_stage.py`
- Create: `tests/unit/vision/test_classification_stage.py`
- Create: `tests/unit/vision/test_color_extraction_stage.py`
- Create: `tests/unit/vision/test_storage_stage.py`

#### Task 16: Unit Tests for Scoring Rules
**Files:**
- Create: `tests/unit/services/scoring/test_color_harmony.py`
- Create: `tests/unit/services/scoring/test_formality_match.py`
- Create: `tests/unit/services/scoring/test_pattern_balance.py`
- Create: `tests/unit/services/scoring/test_seasonal.py`
- Create: `tests/unit/services/scoring/test_occasion.py`
- Create: `tests/unit/services/scoring/test_user_bias.py`
- Create: `tests/unit/services/scoring/test_engine.py`

#### Task 17: Integration Tests for API Endpoints
**Files:**
- Create: `tests/integration/api/test_garments.py`
- Create: `tests/integration/api/test_outfits.py`
- Create: `tests/integration/api/test_recommendations.py`
- Create: `tests/integration/api/test_feedback.py`

---

### Phase 6: Configuration & Docker Improvements

#### Task 18: Centralize Configuration
**Files:**
- Modify: `backend/core/config.py` (add validation)
- Create: `backend/core/constants.py` (magic numbers)
- Modify: `docker-compose.yml` (health checks, resource limits)

**Steps:**
1. Add pydantic validators for all config fields
2. Move hardcoded values to constants
3. Add proper health check endpoints
4. Set CPU/memory limits in docker-compose

#### Task 19: Add Database Migrations
**Files:**
- Create: `alembic/env.py`, `alembic/script.py.mako`
- Create: `alembic/versions/001_initial.py`
- Modify: `Dockerfile` (run migrations on startup)

---

## Files to Create/Modify Summary

### New Files (Core Architecture)
```
backend/domain/
├── __init__.py
├── models.py              # Pure domain models (enums, base classes)
└── exceptions.py          # Domain exceptions

backend/vision/
├── interfaces.py          # Protocols for segmenter, classifier, color_extractor
├── pipeline.py            # VisionPipeline orchestrator
└── stages/
    ├── __init__.py
    ├── segmentation_stage.py
    ├── classification_stage.py
    ├── color_extraction_stage.py
    ├── storage_stage.py
    └── persistence_stage.py

backend/ai_providers/
├── protocols.py           # AIProviderProtocol
└── factory.py             # Updated to use protocol

backend/services/
├── outfit_generator.py    # Template + combination logic
├── outfit_scorer.py       # Scoring wrapper
├── outfit_persister.py    # DB persistence
├── outfit_composer.py     # Facade (simplified)
└── scoring/
    ├── __init__.py
    ├── rules.py           # Base StyleRule abstract class
    ├── color_harmony.py
    ├── formality_match.py
    ├── pattern_balance.py
    ├── seasonal.py
    ├── occasion.py
    ├── user_bias.py
    └── engine.py          # Composes and runs rules

backend/core/
├── dependencies.py        # FastAPI dependency injection
└── constants.py           # Magic numbers, templates
```

### Modified Files (Critical Fixes)
```
backend/vision/ingestion_pipeline.py      # Fix RGBA save, use pipeline
backend/api/routers/wardrobe.py           # Fix await, field names, use services
backend/models/schemas.py                 # Fix StyleRule validator
backend/vision/classifier.py              # Fix formality return type
backend/vision/segmenter.py               # Return RGB for JPEG compatibility
backend/core/config.py                    # Add validators
backend/repositories/__init__.py          # Break circular import
backend/models/garment.py                 # Use domain enums
backend/models/schemas.py                 # Use domain models
```

### Test Files
```
tests/unit/vision/
├── test_segmentation_stage.py
├── test_classification_stage.py
├── test_color_extraction_stage.py
└── test_storage_stage.py

tests/unit/services/scoring/
├── test_color_harmony.py
├── test_formality_match.py
├── test_pattern_balance.py
├── test_seasonal.py
├── test_occasion.py
├── test_user_bias.py
└── test_engine.py

tests/integration/api/
├── test_garments.py
├── test_outfits.py
├── test_recommendations.py
└── test_feedback.py
```

---

## Verification Steps

### After Each Task
```bash
# Run relevant tests
pytest tests/unit/... -v

# Check linting
ruff check backend/
mypy backend/

# Quick API test
curl http://localhost:8000/health
```

### Full Integration Test
```bash
# Build and run dev container
docker compose --profile dev up --build

# Test all endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/garments
curl http://localhost:8000/api/v1/outfits
curl http://localhost:8000/api/v1/rules
curl -X POST http://localhost:8000/api/v1/recommend -H "Content-Type: application/json" -d '{"occasion":"casual"}'

# Test frontend loads
curl http://localhost:8000/ | grep "Smart Wardrobe"
```

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|------------|
| Breaking changes during refactor | Comprehensive tests before each change; feature flags for new pipeline |
| Vision model download time in CI | Mock models in unit tests; use small test checkpoints |
| Circular import resolution | Use `TYPE_CHECKING` + string annotations; separate domain layer |
| Performance overhead of abstractions | Profile critical paths; keep hot paths simple |
| Frontend/backend contract changes | Version API (`/api/v1/`); maintain backward compatibility |

---

## Acceptance Criteria

- [ ] All critical bugs fixed (no 500 errors on core flows)
- [ ] No circular imports (`python -m py_compile` passes)
- [ ] All unit tests pass (`pytest tests/unit -v`)
- [ ] All integration tests pass (`pytest tests/integration -v`)
- [ ] Linting clean (`ruff check backend/`, `mypy backend/`)
- [ ] Docker build succeeds (`docker compose --profile dev up --build`)
- [ ] API responds correctly to all endpoints
- [ ] Frontend loads and navigates between `/kiosk` and `/settings`
- [ ] Code is modular: each class < 100 lines, single responsibility
- [ ] Dependencies can be mocked for testing