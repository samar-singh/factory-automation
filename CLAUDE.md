# Factory Flow Automation Project Memory

## Project Overview
Building an automated system for a garment price tag manufacturing factory to:
- Poll Gmail for order emails
- Extract order details using LLMs
- Match tag requests with inventory using multimodal RAG
- Manage approvals with human-in-the-loop
- Track payments (UTR/cheques)
- Provide real-time dashboard

## Current Status (Last Updated: 2025-07-29)

### GitHub Repository
- **URL**: https://github.com/samar-singh/factory-automation
- **Status**: Initial commit pushed successfully
- **Branch**: main

### Completed ✅
1. **Project Planning**
   - Created comprehensive implementation plan (`factory_automation_plan.md`)
   - Designed multi-agent architecture using OpenAI Agents SDK
   - Planned RAG integration with free ChromaDB
   - Updated plan to use OpenAI function tools pattern

2. **Project Setup**
   - Set up project structure with uv package manager
   - Created `pyproject.toml` with all dependencies
   - Installed OpenAI Agents SDK (imported as `agents`)
   - Created configuration management system
   - Created API setup guide with verification script
   - **NEW**: Fixed import issues - using `agents` module instead of `openai_agents`

3. **Basic Implementation**
   - Base agent class using OpenAI Agents SDK
   - Added `as_tool()` method to base agent for function tools pattern
   - Orchestrator agent for workflow coordination
   - Created AI-powered orchestrator v2 with context awareness
   - Placeholder agents for email, order, and inventory
   - ChromaDB client for vector operations
   - Gradio dashboard with full UI layout

4. **Advanced Features** ✨
   - Implemented multimodal search with Qwen2.5VL + CLIP
   - LiteLLM integration for Together.ai access
   - Combined embeddings approach for enhanced search
   - **NEW**: CLIP module installed and working

5. **Code Organization** 🏗️
   - Renamed all agent files to have `_agent.py` extension
   - Renamed all folders to have `factory_` prefix
   - Updated all imports throughout codebase
   - Cleaned up .env file to match .env.example structure

6. **Database & Storage** 💾
   - **NEW**: ChromaDB fully operational with persistent storage
   - **NEW**: Created 10 sample inventory items with auto-generated images
   - **NEW**: Text embeddings and search working (89% accuracy for "blue cotton tag")
   - **NEW**: PostgreSQL installed and configured
   - **NEW**: Database schema created with 7 tables
   - **NEW**: SQLAlchemy models implemented for all tables
   - **NEW**: Database connection tested successfully

7. **API Configuration** 🔑
   - **NEW**: OpenAI API key validated and working
   - **NEW**: Together.ai API key validated and working
   - **NEW**: Gmail credentials file in place
   - **NEW**: SECRET_KEY generated for security

### In Progress 🚧
- Launch Gradio dashboard
- Test end-to-end workflow

### Pending 📋
- Gmail API integration (credentials ready, need to implement polling)
- Excel inventory ingestion
- Payment processing (OCR)
- Testing with real data
- Migration from v1 to v2 orchestrator
- Implement missing agents (document_creator, payment_tracker, approval_manager)
- Implement database CRUD operations

## Technical Stack
- **Framework**: OpenAI Agents SDK with function tools pattern
- **Orchestration**: AI-powered orchestrator using GPT-4
- **Vector DB**: ChromaDB (free, open-source)
- **Embeddings**: 
  - CLIP ViT-B/32 for image embeddings
  - all-MiniLM-L6-v2 for text embeddings
  - Qwen2.5VL72B via Together.ai for visual analysis
- **UI**: Gradio
- **Database**: PostgreSQL
- **OCR**: Tesseract
- **Deployment**: Docker

## Key Design Decisions
1. Using OpenAI Agents SDK instead of deprecated Swarm
2. **NEW**: Adopted function tools pattern for better context handling
3. ChromaDB for free RAG solution
4. Multimodal search with dual approach:
   - Qwen2.5VL for detailed visual understanding
   - CLIP for efficient similarity search
5. Human-in-the-loop for critical approvals
6. Gradio for easy-to-use dashboard
7. **NEW**: AI-powered orchestrator for intelligent workflow routing
8. **NEW**: Separated configuration (config.yaml) from secrets (.env)

## Important Files
- `/factory_automation_plan.md` - Complete implementation plan (updated with function tools)
- `/API_SETUP_GUIDE.md` - Detailed API configuration guide
- `/CONFIGURATION_GUIDE.md` - How to use config.yaml + .env
- `/config.yaml` - All non-sensitive configuration
- `/.env.example` - Only API keys and secrets template
- `/factory_automation/` - Main project directory
- `/factory_automation/pyproject.toml` - Dependencies
- `/factory_automation/main.py` - Entry point
- `/factory_automation/factory_agents/` - Agent implementations
- `/factory_automation/factory_agents/orchestrator_v2_agent.py` - AI-powered orchestrator
- `/factory_automation/factory_agents/base.py` - Base agent with as_tool() method
- `/factory_automation/factory_rag/multimodal_search.py` - Qwen2.5VL + CLIP search
- `/factory_automation/factory_config/settings.py` - Configuration loader
- `/factory_automation/factory_ui/gradio_app.py` - Dashboard UI
- `/factory_automation/factory_database/models.py` - **NEW**: SQLAlchemy models
- `/factory_automation/factory_database/connection.py` - **NEW**: DB connection utility
- `/test_api_keys.py` - API key verification script
- `/test_system.py` - **NEW**: Comprehensive system test
- `/create_sample_inventory_simple.py` - **NEW**: Sample data generator
- `/setup_database.sql` - **NEW**: PostgreSQL schema
- `/sample_images/` - **NEW**: Auto-generated tag images
- `/chroma_data/` - **NEW**: ChromaDB persistent storage

## Next Steps
1. Launch Gradio dashboard to visualize the system
2. Test end-to-end workflow with sample data
3. Implement Gmail polling loop
4. Create Excel inventory ingestion
5. Add OCR for payment processing
6. Implement missing agents (document_creator, payment_tracker)
7. Migrate from orchestrator v1 to v2

## Notes
- Customer provided example email showing full order lifecycle
- All API keys working (OpenAI + Together.ai)
- System designed for ~50 emails/day volume
- Budget updated: ~$120-190/month (includes Qwen2.5VL costs)
- Created ROADMAP_PROGRESS_REPORT.md for tracking
- Project is approximately 50% complete (significant progress today)
- Function tools pattern enables intelligent context-aware processing
- Dual database approach: ChromaDB for RAG, PostgreSQL for business logic
- Configuration split - config.yaml for settings, .env for secrets
- Settings can be overridden via environment variables
- All agent files now use `_agent.py` naming convention
- All project folders now use `factory_` prefix to avoid conflicts
- Sample inventory created with 10 items and auto-generated images
- Database schema supports full order lifecycle tracking

## Commands & Tools
- Using `uv` for Python package management
- Git repository initialized and pushed to GitHub
- Using Opus model for complex development work