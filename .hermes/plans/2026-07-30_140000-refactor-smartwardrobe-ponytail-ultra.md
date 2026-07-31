# SmartWardrobe Refactoring Plan — Ponytail Ultra

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Eliminate god classes, reduce coupling, replace custom code with stdlib/stdlib-like patterns, and improve cohesion while maintaining all functionality.

**Architecture:** Clean separation: `domain` (models/enums), `vision` (pipeline + stages), `ai_providers` (protocol + implementations), `services` (thin facades), `repositories` (DB access), `api` (FastAPI routes). Dependency inversion via protocols, not concrete classes.

**Tech Stack:** FastAPI, SQLModel, PyTorch, SAM/CLIP, stdlib (`dataclasses`, `itertools`, `collections`, `functools`, `enum`).

---

## Phase 1: Domain & Foundation (Low Risk, High Impact)

### Task 1: Centralize Enums & Type Definitions

**Objective:** Move all enums to single source of truth, remove duplicates.

**Files:**
- Create: `backend/domain/enums.py`
- Modify: `backend/models/garment.py:13-45` (remove GarmentType, Season, FormalityLevel, PatternType)
- Modify: `backend/models/schemas.py:7-50` (import from domain)

**Step 1: Write failing test**
```python
def test_enums_imported_from_domain():
    from backend.domain.enums import GarmentType, Season, FormalityLevel, PatternType
    assert GarmentType.TOP == "top"
    assert FormalityLevel.CASUAL == 1
```

**Step 2: Run test to verify failure** → Expected: ImportError

**Step 3: Create domain/enums.py**
```python
# backend/domain/enums.py
from enum import IntEnum, StrEnum

class GarmentType(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORY = "accessory"

class Season(StrEnum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    ALL_SEASON = "all_season"

class FormalityLevel(IntEnum):
    CASUAL = 1
    SMART_CASUAL = 2
    BUSINESS_CASUAL = 3
    FORMAL = 4
    BLACK_TIE = 5

class PatternType(StrEnum):
    SOLID = "solid"
    STRIPED = "striped"
    CHECKERED = "checkered"
    FLORAL = "floral"
    POLKA_DOT = "polka_dot"
    GEOMETRIC = "geometric"
    ABSTRACT = "abstract"

class FeedbackType(StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"
    NEUTRAL = "neutral"

class AIProviderType(StrEnum):
    LOCAL = "local"
    NIM = "nim"
```

**Step 4: Update garment.py & schemas.py to import from domain**

**Step 5: Run test to verify pass** → Expected: PASS

---

### Task 2: Create Domain Models (Pure Dataclasses)

**Objective:** Extract pure domain models from SQLModel, remove DB coupling from domain logic.

**Files:**
- Create: `backend/domain/models.py`
- Modify: `backend/models/garment.py` (keep SQLModel, import domain models)

**Step 1: Write failing test**
```python
def test_domain_garment_is_pure():
    from backend.domain.models import Garment
    g = Garment(name="Test", type="top", dominant_color_hex="#FF0000", color_name="Red")
    assert g.name == "Test"
```

**Step 2: Create domain/models.py with @dataclass models (no SQLModel)**

**Step 3: Update SQLModel classes to use domain models as base**

---

### Task 3: Protocol-Based AI Provider Interface

**Objective:** Replace abstract base class with Protocol for structural subtyping.

**Files:**
- Modify: `backend/ai_providers/__init__.py` (use Protocol)
- Modify: `backend/ai_providers/local.py`, `nim.py` (remove ABC inheritance)

**Step 1: Write failing test**
```python
def test_protocol_accepts_duck_type():
    from backend.ai_providers import AIProviderProtocol
    class FakeProvider:
        async def enhance_recommendation(self, outfit, context="", user_preferences=None):
            return {"description": "test"}
        async def generate_outfit_description(self, garments, occasion, context=""):
            return "test"
        def get_provider_name(self): return "fake"
        async def health_check(self): return True
    assert isinstance(FakeProvider(), AIProviderProtocol)
```

**Step 2: Replace ABC with Protocol**

---

## Phase 2: Vision Pipeline Refactoring (Medium Risk)

### Task 4: Split Vision Pipeline into Stages

**Objective:** Replace `IngestionPipeline` (266 lines) with composable stage classes.

**Files:**
- Create: `backend/vision/stages/segmenter_stage.py`
- Create: `backend/vision/stages/classifier_stage.py`
- Create: `backend/vision/stages/color_stage.py`
- Create: `backend/vision/pipeline.py` (orchestrator)
- Modify: `backend/vision/ingestion_pipeline.py` (delete or keep as thin facade)

**Step 1: Write failing test for each stage**
```python
def test_segmenter_stage():
    from backend.vision.stages.segmenter_stage import SegmenterStage
    stage = SegmenterStage()
    assert hasattr(stage, 'process')
```

**Step 2: Extract each stage as single-responsibility class**

**Step 3: Pipeline orchestrator uses `functools.reduce` or simple loop**

```python
# backend/vision/pipeline.py
from dataclasses import dataclass
from typing import Protocol

class VisionStage(Protocol):
    def process(self, image: Image.Image, context: dict) -> dict: ...

@dataclass
class VisionPipeline:
    stages: list[VisionStage]
    
    def run(self, image: Image.Image) -> dict:
        ctx = {"image": image}
        for stage in self.stages:
            ctx.update(stage.process(ctx["image"], ctx))
        return ctx
```

---

### Task 5: Replace Custom Color Logic with stdlib

**Objective:** Remove custom HSV conversion, use `colorsys` stdlib.

**Files:**
- Modify: `backend/vision/classifier.py:355-382` (replace `_hex_to_hsv` with `colorsys.rgb_to_hsv`)
- Modify: `backend/vision/style_engine.py:355-382` (same)

**Step 1: Write failing test**
```python
def test_colorsys_replacement():
    import colorsys
    r, g, b = 1.0, 0.0, 0.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    assert abs(h - 0.0) < 0.01
```

**Step 2: Replace custom implementations**

---

## Phase 3: Service Layer Refactoring (High Risk - God Classes)

### Task 6: Decompose StyleEngine (407 lines → ~6 small classes)

**Objective:** Split into `ColorHarmonyScorer`, `FormalityScorer`, `PatternScorer`, `SeasonalScorer`, `OccasionScorer`, `UserBiasScorer` + `StyleEngine` facade.

**Files:**
- Create: `backend/services/scoring/color_harmony.py`
- Create: `backend/services/scoring/formality.py`
- Create: `backend/services/scoring/pattern.py`
- Create: `backend/services/scoring/seasonal.py`
- Create: `backend/services/scoring/occasion.py`
- Create: `backend/services/scoring/user_bias.py`
- Modify: `backend/services/style_engine.py` (thin facade using scorers)

**Step 1: Write failing test for each scorer**
```python
def test_color_harmony_scorer():
    from backend.services.scoring.color_harmony import ColorHarmonyScorer
    scorer = ColorHarmonyScorer()
    score, details = scorer.score([garment1, garment2])
    assert 0 <= score <= 100
```

**Step 2: Extract each `_score_*` method to its own class with Protocol**

```python
# backend/services/scoring/protocol.py
from typing import Protocol
from backend.models.garment import Garment
from backend.domain.models import StyleScore

class Scorer(Protocol):
    def score(self, garments: list[Garment], **kwargs) -> tuple[float, dict]: ...
```

**Step 3: StyleEngine becomes coordinator**

```python
# backend/services/style_engine.py
from backend.services.scoring import (
    ColorHarmonyScorer, FormalityScorer, PatternScorer,
    SeasonalScorer, OccasionScorer, UserBiasScorer
)

class StyleEngine:
    def __init__(self, session):
        self.scorers = [
            ColorHarmonyScorer(), FormalityScorer(), PatternScorer(),
            SeasonalScorer(), OccasionScorer(), UserBiasScorer()
        ]
        self.rule_repo = StyleRuleRepository(session)
    
    def score_outfit(self, outfit, occasion, season):
        garments = self._get_garments(outfit)
        rules = self.rule_repo.get_all(active_only=True)
        weights = {r.rule_type: r.weight for r in rules}
        
        total = 0
        details = {}
        for scorer in self.scorers:
            score, detail = scorer.score(garments, occasion=occasion, season=season)
            details[scorer.__class__.__name__] = detail
            total += score * weights.get(scorer.rule_type, 1.0)
        
        # normalize...
        return StyleScore(total=total, details=details)
```

---

### Task 7: Decompose OutfitComposer (398 lines)

**Objective:** Split into `OutfitGenerator`, `OutfitScorer`, `OutfitPersister`, `DiversityFilter` + thin `OutfitComposer` facade.

**Files:**
- Create: `backend/services/outfit_generator.py`
- Create: `backend/services/outfit_scorer.py`
- Create: `backend/services/outfit_persister.py`
- Create: `backend/services/diversity_filter.py`
- Modify: `backend/services/outfit_composer.py` (thin facade)

**Step 1: Write failing tests**

**Step 2: Extract `compose_outfits` logic to `OutfitGenerator`**

**Step 3: Extract scoring to `OutfitScorer` (uses StyleEngine)**

**Step 4: Extract persistence to `OutfitPersister`**

**Step 5: Extract diversity to `DiversityFilter`**

---

### Task 8: Decompose PackingService (315 lines)

**Objective:** Split into `OutfitSetGenerator`, `VersatilityCalculator`, `GreedyPacker`, `ItemSuggester`.

**Files:**
- Create: `backend/services/packing/outfit_set_generator.py`
- Create: `backend/services/packing/versatility.py`
- Create: `backend/services/packing/greedy_packer.py`
- Create: `backend/services/packing/item_suggester.py`
- Modify: `backend/services/packing_service.py` (thin facade)

---

### Task 9: Simplify FeedbackService (131 lines)

**Objective:** Remove duplicated `_update_garment_bias` logic, use single method.

**Files:**
- Modify: `backend/services/feedback_service.py`

**Step 1: Write failing test**
```python
def test_garment_bias_updated_once():
    service = FeedbackService(session)
    service.rate_outfit(outfit_id=1, rating=1)
    garment = garment_repo.get_by_id(garment_id)
    assert garment.style_bias > 0
```

**Step 2: DRY the bias update methods**

```python
def _update_bias(self, garment_id: int):
    bias = self.feedback_repo.get_garment_bias(garment_id)
    garment = self.garment_repo.get_by_id(garment_id)
    if garment:
        garment.style_bias = max(-1.0, min(1.0, bias))
        garment.updated_at = datetime.utcnow()
        self.session.add(garment)
        self.session.commit()
```

---

## Phase 4: Repository & Database (Low Risk)

### Task 10: Fix Repository SQLModel Issues

**Objective:** Fix mypy errors in repositories (`.contains()`, `.desc()`, `.in_()`).

**Files:**
- Modify: `backend/repositories/garment_repository.py`
- Modify: `backend/repositories/outfit_repository.py`
- Modify: `backend/repositories/user_feedback_repository.py`

**Fixes:**
- `str.contains()` → `col.contains()` or `col.like()`
- `datetime.desc()` → `desc(datetime)` or `col.desc()`
- `int.in_()` → `col.in_(list)`

---

### Task 11: Dependency Injection for Services

**Objective:** Replace `get_settings()` calls with injected dependencies.

**Files:**
- Create: `backend/core/dependencies.py` (FastAPI DI)
- Modify: All services to accept dependencies in `__init__`
- Modify: `backend/api/main.py` to wire DI

**Step 1: Create DI container**
```python
# backend/core/dependencies.py
from functools import lru_cache
from backend.core.config import Settings
from backend.database.connection import get_session

@lru_cache
def get_settings() -> Settings: ...

def get_garment_repo(session=Depends(get_session)):
    return GarmentRepository(session)

def get_style_engine(session=Depends(get_session)):
    return StyleEngine(session)

# etc.
```

---

## Phase 5: Cleanup & Validation

### Task 12: Remove Dead Code & Fix Imports

**Objective:** Remove unused imports, fix circular imports, ensure clean layer boundaries.

**Files:** All modified files above + `backend/models/__init__.py`

---

### Task 13: Run Full Test Suite & Lint

**Commands:**
```bash
cd "/Users/manuhdezz/Proyectos Hermes/SmartWardrobe"
make lint
make test
```

**Expected:** Ruff PASS, MyPy clean (or only 3rd-party stub issues), Tests PASS

---

## Phase 6: Frontend Router Fix (Already Done)

**Objective:** Ensure SPA fallback works, templates mount correctly.

**Files:**
- `backend/api/main.py` (templates mount + SPA fallback)
- `frontend/index.html` (fetch template before import)

**Status:** ✅ Done in current session

---

## Verification Checklist

- [ ] Ruff: 0 errors
- [ ] MyPy: Only 3rd-party stub issues (segment_anything, open_clip, colorthief, sklearn)
- [ ] Tests: All pass
- [ ] App runs: `docker compose --profile dev up -d`
- [ ] Endpoints: `/health`, `/api/v1/garments`, `/api/v1/outfits`, `/api/v1/recommend`, `/kiosk`, `/settings` all 200 OK
- [ ] No circular imports
- [ ] No god classes (>200 lines)
- [ ] All services < 150 lines
- [ ] Dependency inversion via Protocols
- [ ] No global `get_settings()` in services

---

## Execution Approach

**"Plan complete and saved. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?"**