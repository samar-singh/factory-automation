# Factory Flow Automation Project Memory

## Project Overview

Building an automated system for a garment price tag manufacturing factory to:

- Poll Gmail for order emails
- Extract order details using LLMs
- Match tag requests with inventory using multimodal RAG
- Manage approvals with human-in-the-loop
- Track payments (UTR/cheques)
- Provide real-time dashboard

## Current Status (Last Updated: 2025-08-03)

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

## Recent Updates (2025-08-03 - Session 2)

### Major Enhancements

1. **AI-Powered Order Extraction**: Replaced basic regex with GPT-4 for intelligent order parsing
   - Handles complex formats like fit mappings (Bootcut → TBALWBL0009N)
   - Extracts customer info, quantities, specifications automatically
   - Falls back to pattern matching if AI fails

2. **Image Processing with Qwen2.5VL**: 
   - Analyzes tag images using Together.ai API
   - Stores base64 encoded images in ChromaDB
   - Creates searchable visual inventory

3. **Complete Order Processing Workflow**:
   - New `process_complete_order` tool handles entire pipeline
   - Confidence-based routing: >80% auto, 60-80% human review, <60% clarification
   - Integrated ChromaDB search and inventory updates

4. **Inventory Reconciliation System**:
   - Excel files as source of truth (employee-maintained)
   - PostgreSQL for real-time transactions
   - ChromaDB as rebuildable search cache
   - Automatic sync with configurable thresholds

5. **Tool Consolidation**:
   - Removed redundant tools (analyze_email, extract_order_items, make_decision)
   - Streamlined to 8 essential tools
   - Clearer AI decision making with less confusion

6. **UI Improvements**:
   - Automatic email extraction from pasted content
   - No manual customer email input needed
   - Enhanced placeholder text with examples

## Recent Updates (2025-08-03 - Session 1)

- ✅ Implemented agentic orchestrator with OpenAI Agents SDK
- ✅ Fixed schema validation issues (Dict[str, Any] → str returns)
- ✅ Added tool call tracking with TrackedOrchestratorV3
- ✅ Designed human-orchestrator interaction system
- ✅ Gmail polling loop implemented with mock testing
- ✅ Comprehensive test suite for agentic features
- ✅ Code formatting and linting cleanup

## Known Issues & Limitations

1. **Type Errors**: 122 mypy errors need resolution
2. **Gmail Auth**: Requires IT admin for domain delegation
3. **Attachment Parsing**: Not yet implemented for orders
4. **Excel Formats**: Some files have datetime/duplicate issues
5. **Visual Analysis**: Qwen2.5VL ready but not wired for production
6. **Human Interaction**: System designed but not fully implemented

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

# Run Application (ALWAYS TEST WITH THIS AFTER CHANGES)
python3 -m dotenv run -- python3 run_factory_automation.py

# Alternative UIs
python -m factory_automation.factory_ui.gradio_app_live  # Basic UI
python launch_ai_app.py  # AI-Enhanced UI

# Database
psql -U postgres -d factory_automation

# Git
git status
git commit -m "feat: description"
```

## CRITICAL DEVELOPMENT RULE ⚠️

**ALWAYS test any code changes with `run_factory_automation.py` to ensure integration works:**

```bash
# After ANY modification to the codebase:
1. Save your changes
2. Run: source .venv/bin/activate
3. Run: python3 -m dotenv run -- python3 run_factory_automation.py
4. Verify no import errors or initialization failures
5. Check that the web interface loads at http://localhost:7860

# If errors occur:
- Check imports match actual file/class names
- Verify all dependencies are installed with uv
- Ensure ChromaDB and PostgreSQL are accessible
- Kill existing processes on port 7860 if needed: lsof -i :7860 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

This ensures the integrated system always works as a whole, not just individual components.

## AI Integration Update (2025-08-03)

**AI Components NOW CONNECTED! 🎉**
- ✅ GPT-4 orchestrator integrated via AI bridge
- ✅ New AI-enhanced Gradio dashboard (gradio_app_ai.py)
- ✅ Natural language order processing active
- ✅ Intelligent search with query enhancement
- ⏳ Qwen2.5VL ready but not yet wired for visual analysis
- 🚀 System upgraded from "dumb mode" to "AI-powered mode"

## Next Immediate Tasks (Priority Order)

1. ✅ ~~Connect AI Brain: Wire orchestrator to Gradio UI~~ DONE!
2. ✅ ~~Enable LLM Processing: Use GPT-4 for email/order parsing~~ DONE!
3. ✅ ~~Implement Agentic Orchestrator: OpenAI Agents SDK with tools~~ DONE!
4. **Human Interaction**: Implement human-orchestrator interface
5. **Wire Qwen2.5VL**: Enable visual tag analysis
6. **Fix Type Errors**: Resolve 122 mypy issues
7. **Complete Agents**: Document creator, payment tracker
8. **Production Deploy**: Docker + proper error handling

## Contact & Support

- GitHub Issues: https://github.com/samar-singh/factory-automation/issues
- Project Lead: Samar Singh
- AI Assistant: Claude (Anthropic)