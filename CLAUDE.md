# Factory Flow Automation Project Memory

## Project Overview

Building an automated system for a garment price tag manufacturing factory to:

- Poll Gmail for order emails
- Extract order details using LLMs
- Match tag requests with inventory using multimodal RAG
- Manage approvals with human-in-the-loop
- Track payments (UTR/cheques)
- Provide real-time dashboard

## Current Status (Last Updated: 2025-08-02)

### GitHub Repository

- **URL**: <https://github.com/samar-singh/factory-automation>
- **Status**: Active development, regular commits
- **Branch**: main
- **Progress**: ~80% Complete

### Completed Features ✅

1. **Project Foundation**
   - Multi-agent architecture using OpenAI Agents SDK
   - AI-powered orchestrator v2 with context awareness
   - Function tools pattern for intelligent routing
   - Comprehensive configuration management (config.yaml + .env)
   - Python best practices: pre-commit, CI/CD, Makefile

2. **Database Infrastructure**
   - **ChromaDB**: Vector database with multi-collection support
   - **PostgreSQL**: Business logic and order tracking (7 tables)
   - **SQLAlchemy**: ORM models for all entities
   - **Dual approach**: ChromaDB for RAG, PostgreSQL for transactions

3. **RAG-Based Inventory System**
   - **Stella-400M embeddings**: Primary (1024 dimensions, 54-79% accuracy)
   - **All-MiniLM-L6-v2**: Fallback (384 dimensions, 43-58% accuracy)
   - **478 items ingested** from 12 Excel files
   - **Natural language search** with confidence scoring
   - **Multi-model support** via EmbeddingsManager

4. **Gmail Integration**
   - Service account authentication ready
   - Email body parsing for order extraction
   - Attachment processing (Excel, PDF, Images)
   - Combined email + attachment data extraction

5. **Multimodal Search**
   - **Qwen2.5VL-72B**: Visual understanding via Together.ai
   - **CLIP ViT-B/32**: Image embeddings
   - **Dual approach**: Detailed analysis + similarity search

6. **User Interface**
   - **Live Gradio Dashboard** with three tabs:
     - Inventory Search
     - Order Processing
     - System Status
   - **Confidence-based routing**:
     - >80%: Auto-approve
     - 60-80%: Manual review
     - <60%: Find alternatives

7. **Testing & Quality**
   - Comprehensive test suite
   - End-to-end workflow validation
   - Interactive testing tools
   - Code formatting with black/ruff/isort

### In Progress 🚧

- Gmail domain-wide delegation setup
- Payment OCR implementation
- Production deployment configuration

### Pending 📋

- Document generation (quotations, confirmations)
- Payment tracker agent (UTR/cheque processing)
- Approval manager agent
- Gmail polling loop
- Customer code mapping (ST-057 → internal codes)

## Technical Stack (Current)

- **Framework**: OpenAI Agents SDK with function tools pattern
- **Orchestration**: AI-powered orchestrator using GPT-4
- **Vector Database**: ChromaDB with multi-collection support
- **Embeddings**:
  - **Primary**: Stella-400M (1024 dims, higher accuracy)
  - **Fallback**: all-MiniLM-L6-v2 (384 dims, faster)
  - **Images**: CLIP ViT-B/32
  - **Visual QA**: Qwen2.5VL-72B via Together.ai
- **UI**: Gradio interactive dashboard
- **Database**: PostgreSQL + SQLAlchemy
- **OCR**: Tesseract (planned)
- **APIs**: OpenAI GPT-4, Together.ai, Gmail
- **Package Management**: uv
- **Code Quality**: pre-commit, black, ruff, mypy

## Key Architecture Decisions

1. **Multi-Agent System**: Specialized agents for each task
2. **Function Tools Pattern**: Dynamic context-aware processing
3. **Dual Embeddings**: Trade-off between accuracy and speed
4. **ChromaDB Collections**: Separate collections for different embedding models
5. **Human-in-the-Loop**: Confidence-based routing for approvals
6. **Configuration Split**: config.yaml (settings) + .env (secrets)
7. **Modular Design**: factory_ prefix for all modules

## Performance Metrics

- **Search Accuracy**: 54-79% (Stella) vs 43-58% (MiniLM)
- **Query Time**: 2.4s (Stella) vs 0.1s (MiniLM)
- **Inventory Size**: 478 items across 12 brands
- **Ingestion Success**: 10/12 Excel files processed
- **Confidence Thresholds**:
  - Auto-approve: >80%
  - Manual review: 60-80%
  - Alternative needed: <60%

## Important Files & Directories

### Configuration
- `/config.yaml` - Application settings
- `/.env.example` - Secret keys template
- `/API_SETUP_GUIDE.md` - API configuration guide
- `/CONFIGURATION_GUIDE.md` - Settings documentation

### Core Implementation
- `/factory_automation/` - Main application directory
- `/factory_automation/factory_agents/` - Agent implementations
- `/factory_automation/factory_rag/` - RAG and search components
- `/factory_automation/factory_ui/gradio_app_live.py` - Live dashboard
- `/factory_automation/factory_database/` - Database models and connections

### Documentation
- `/factory_automation_plan.md` - Implementation roadmap
- `/ROADMAP_PROGRESS_REPORT.md` - Progress tracking
- `/MIGRATION_GUIDE.md` - Deployment guide
- `/RAG_SCALABILITY_PLAN.md` - Future scaling plans

### Data & Storage
- `/inventory/` - Excel inventory files
- `/chroma_data/` - ChromaDB persistent storage
- `/sample_images/` - Auto-generated tag images

### Testing
- `/test_system.py` - Comprehensive system test
- `/factory_automation/factory_tests/` - Test suite

## Recent Updates (2025-08-02)

- ✅ Migrated to Stella-400M embeddings (20-35% accuracy improvement)
- ✅ Fixed search_inventory data structure (returns list, not dict)
- ✅ Enabled multi-collection support in ChromaDB
- ✅ Updated Gradio app to use Stella collection
- ✅ Comprehensive testing of email → search → decision flow
- ✅ Documentation updates reflecting current state

## Known Issues & Limitations

1. **Email Parsing**: Regex patterns need improvement for item extraction
2. **Type Errors**: 122 mypy errors need resolution
3. **Excel Formats**: Some files have datetime/duplicate issues
4. **Gmail Auth**: Requires IT admin for domain delegation
5. **Attachment Parsing**: Not yet implemented for orders

## Budget & Resources

- **Monthly Cost**: ~$120-190 (includes all API calls)
- **Daily Volume**: Designed for ~50 orders/day
- **Query Cost**: ~$0.10-0.15 per order with Qwen2.5VL
- **Storage**: <1GB for embeddings and images

## Commands & Tools

```bash
# Virtual Environment
source .venv/bin/activate

# Development
make format    # Format code
make check     # Run linters
make test      # Run tests

# Run Application
python -m factory_automation.factory_ui.gradio_app_live

# Database
psql -U postgres -d factory_automation

# Git
git status
git commit -m "feat: description"
```

## Next Immediate Tasks

1. Fix mypy type errors for better code quality
2. Implement Gmail polling loop
3. Add attachment parsing for Excel/PDF orders
4. Create customer code mapping system
5. Deploy to production environment

## Contact & Support

- GitHub Issues: https://github.com/samar-singh/factory-automation/issues
- Project Lead: Samar Singh
- AI Assistant: Claude (Anthropic)