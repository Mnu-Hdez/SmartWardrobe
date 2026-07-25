# Smart Wardrobe Outfit System

An AI-powered outfit recommendation system that helps you manage your wardrobe, generate stylish outfits, and pack efficiently for trips. Built with FastAPI, computer vision (SAM + CLIP), and a responsive dual-panel web interface.

## ✨ Features

- **📸 Smart Garment Ingestion** - Photo your clothes, auto-segment with SAM, classify with CLIP
- **🎨 AI Style Engine** - Color harmony, formality matching, pattern balance, seasonal appropriateness
- **👗 Outfit Composer** - Top-N diverse recommendations with 0-100 scoring
- **👍 Feedback Learning** - Like/dislike outfits to personalize future recommendations
- **🧳 Packing Optimizer** - N-day trip planning with maximum mix-and-match
- **🔌 Pluggable AI** - Local rules or NVIDIA NIM LLM enhancement
- **📱 Dual-Panel UI** - Visualization screen (60%) + Touch control panel (40%)
- **🥧 Raspberry Pi Ready** - systemd + nginx + Chromium kiosk mode

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue/Vanilla JS)                │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │  Visualization Panel │  │      Touch Control Panel       │  │
│  │      (60% width)     │  │         (40% width)            │  │
│  │  - Outfit display    │  │  - Occasion presets            │  │
│  │  - Garment cards     │  │  - Season selector             │  │
│  │  - Score breakdown   │  │  - Generate/Rate/Pack actions  │  │
│  │  - AI tips           │  │  - Wardrobe browser            │  │
│  └──────────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │ REST API + WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐ │
│  │   Routers    │ │  Services    │ │  AI Providers │ │ Vision │ │
│  │ - Wardrobe   │ │ - StyleEngine│ │ - LocalRules │ │ - SAM  │ │
│  │ - Recommend  │ │ - OutfitComp │ │ - NVIDIA NIM │ │ - CLIP │ │
│  │ - Feedback   │ │ - PackingSvc │ │              │ │ - Color│ │
│  │ - Packing    │ │ - FeedbackSvc│ │              │ │        │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  Repositories│ │    Models    │ │  Database    │             │
│  │ - Garment    │ │ - SQLModel   │ │  SQLite +    │             │
│  │ - Outfit     │ │ - Pydantic   │ │  Alembic     │             │
│  │ - Rules      │ │              │ │              │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Requirements

- Python 3.11+
- 4GB+ RAM (8GB+ recommended for AI models)
- CUDA-compatible GPU (optional, for faster inference)
- Raspberry Pi 4/5 (for edge deployment)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/your-repo/smart-wardrobe.git
cd smart-wardrobe

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Or use Make
make install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Key settings:
- `AI_PROVIDER=local` (or `nim` for NVIDIA NIM)
- `NIM_API_KEY=your_key` (if using NIM)
- `DEVICE=cuda` (or `cpu`, `mps`)

### 3. Initialize Database

```bash
make db-init
```

### 4. Download AI Models

```bash
make download-models
```

This downloads:
- SAM (Segment Anything Model) - ~2.5GB
- CLIP (Contrastive Language-Image Pre-training) - ~500MB

### 5. Run Development Server

```bash
make dev
# or
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000

## 🐳 Docker Deployment

### Development
```bash
docker-compose --profile dev up --build
```

### Production
```bash
docker-compose --profile prod up -d --build
```

Services:
- **app**: FastAPI backend (port 8000)
- **nginx**: Reverse proxy (port 80)

## 📦 Raspberry Pi Deployment

### Automated Setup
```bash
# On Raspberry Pi
curl -sSL https://raw.githubusercontent.com/your-repo/smart-wardrobe/main/deploy/scripts/setup_pi.sh | bash
```

### Manual Steps
1. Run `make setup-pi` from your development machine
2. Or copy files and run `./deploy/scripts/setup_pi.sh` on the Pi
3. Edit `/home/pi/smart-wardrobe/.env` with your config
4. `sudo systemctl start smart-wardrobe`
5. Reboot for kiosk mode: `sudo reboot`

### Systemd Service
```bash
# Check status
sudo systemctl status smart-wardrobe

# View logs
sudo journalctl -u smart-wardrobe -f

# Restart
sudo systemctl restart smart-wardrobe
```

### Kiosk Mode
Chromium starts automatically in fullscreen on boot pointing to `http://localhost:8000`

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `true` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DATABASE_URL` | `sqlite:///data/db/smart_wardrobe.db` | Database connection |
| `AI_PROVIDER` | `local` | `local` or `nim` |
| `NIM_API_KEY` | - | NVIDIA NIM API key |
| `NIM_API_URL` | `https://integrate.api.nvidia.com/v1` | NIM endpoint |
| `NIM_MODEL` | `nvidia/llama-3.1-nemotron-3-ultra` | LLM model |
| `DEVICE` | `cuda` | `cuda`, `cpu`, `mps` |
| `SAM_MODEL_TYPE` | `vit_h` | `vit_h`, `vit_l`, `vit_b` |
| `CLIP_MODEL` | `ViT-B-32` | CLIP model variant |

### Style Rules (Database)

Default rules created on init:
- Color harmony (complementary, analogous, monochromatic)
- Formality matching
- Pattern balance
- Seasonal appropriateness

Customize via API:
```bash
POST /api/v1/rules
{
  "name": "my_rule",
  "description": "Custom rule",
  "rule_type": "color_harmony",
  "weight": 2.0,
  "parameters": {"method": "triadic"}
}
```

## 📖 API Reference

### Garments
```
POST   /api/v1/garments              # Create garment (with image upload)
GET    /api/v1/garments              # List garments
GET    /api/v1/garments/{id}         # Get garment
PATCH  /api/v1/garments/{id}         # Update garment
DELETE /api/v1/garments/{id}         # Delete garment
```

### Outfits
```
POST   /api/v1/outfits               # Create outfit
GET    /api/v1/outfits               # List outfits
GET    /api/v1/outfits/{id}          # Get outfit with garments
PATCH  /api/v1/outfits/{id}          # Update outfit
DELETE /api/v1/outfits/{id}          # Delete outfit
```

### Recommendations
```
POST   /api/v1/recommend             # Get outfit recommendations
POST   /api/v1/enhance               # Enhance with AI
```

### Feedback
```
POST   /api/v1/feedback/outfit       # Rate outfit
POST   /api/v1/feedback/garment      # Rate garment
GET    /api/v1/feedback/outfit/{id}  # Get outfit feedback
GET    /api/v1/feedback/garment/{id} # Get garment feedback
```

### Packing
```
POST   /api/v1/packing               # Generate packing plan
```

### Style Rules
```
POST   /api/v1/rules                 # Create rule
GET    /api/v1/rules                 # List rules
GET    /api/v1/rules/{id}            # Get rule
PATCH  /api/v1/rules/{id}            # Update rule
DELETE /api/v1/rules/{id}            # Delete rule
```

### Health
```
GET    /health                       # Health check
GET    /api/v1/health                # API health check
```

## 🎯 Usage Examples

### Add a Garment (with AI analysis)
```bash
curl -X POST http://localhost:8000/api/v1/garments \
  -F "name=Blue Oxford Shirt" \
  -F "type=top" \
  -F "color_name=blue" \
  -F "color_hex=#0000FF" \
  -F "brand=Uniqlo" \
  -F "size=M" \
  -F "material=cotton" \
  -F "image=@shirt.jpg"
```

### Get Recommendations
```bash
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "occasion": "work",
    "season": "autumn",
    "formality": 3,
    "top_n": 5
  }'
```

### Rate an Outfit
```bash
curl -X POST http://localhost:8000/api/v1/feedback/outfit \
  -H "Content-Type: application/json" \
  -d '{
    "outfit_id": 1,
    "rating": 1,
    "feedback_type": "like",
    "context": "Monday meeting"
  }'
```

### Create Packing Plan
```bash
curl -X POST http://localhost:8000/api/v1/packing \
  -H "Content-Type: application/json" \
  -d '{
    "days": 5,
    "occasion": "business",
    "season": "autumn",
    "max_items": 12
  }'
```

## 🧪 Testing

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# Contract tests (AI provider interface)
make test-contract

# With coverage
pytest tests/ --cov=backend --cov-report=html
```

## 🔍 Code Quality

```bash
# Linting
make lint

# Format
make format

# Type check
make typecheck

# Pre-commit
pre-commit run --all-files
```

## 📁 Project Structure

```
smart-wardrobe/
├── backend/
│   ├── api/                 # FastAPI routers
│   │   ├── main.py         # App factory
│   │   └── routers/        # API endpoints
│   ├── ai_providers/       # Pluggable AI
│   │   ├── local.py        # Local rules
│   │   ├── nim.py          # NVIDIA NIM
│   │   └── factory.py      # Provider factory
│   ├── core/               # Config
│   ├── database/           # DB connection
│   ├── models/             # SQLModel + Pydantic
│   ├── repositories/       # Data access
│   ├── services/           # Business logic
│   │   ├── style_engine.py
│   │   ├── outfit_composer.py
│   │   ├── feedback_service.py
│   │   └── packing_service.py
│   └── vision/             # AI Pipeline
│       ├── segmenter.py    # SAM
│       ├── classifier.py   # CLIP
│       ├── color_extractor.py
│       └── ingestion_pipeline.py
├── frontend/
│   ├── index.html          # Main SPA
│   ├── static/
│   │   ├── css/style.css   # Styles
│   │   └── js/             # Touch panel JS
│   └── templates/
├── deploy/
│   ├── nginx/              # Nginx config
│   ├── systemd/            # Systemd service
│   └── scripts/            # Pi setup scripts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── data/                   # Runtime data (gitignored)
├── .env.example
├── pyproject.toml
├── Makefile
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a PR

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Segment Anything Model (SAM)](https://github.com/facebookresearch/segment-anything) by Meta AI
- [CLIP](https://github.com/openai/CLIP) by OpenAI
- [OpenCLIP](https://github.com/mlfoundations/open_clip) by ML Foundations
- [FastAPI](https://fastapi.tiangolo.com/) for the amazing framework
- [NVIDIA NIM](https://www.nvidia.com/en-us/ai-data-science/nim/) for LLM inference

## 📞 Support

- Issues: [GitHub Issues](https://github.com/your-repo/smart-wardrobe/issues)
- Discussions: [GitHub Discussions](https://github.com/your-repo/smart-wardrobe/discussions)

---

Built with ❤️ for organized wardrobes everywhere.