# Factory Flow Automation Project Memory

## Project Overview
Building an automated system for a garment price tag manufacturing factory to:
- Poll Gmail for order emails
- Extract order details using LLMs
- Match tag requests with inventory using multimodal RAG
- Manage approvals with human-in-the-loop
- Track payments (UTR/cheques)
- Provide real-time dashboard

## Current Status (Last Updated: 2025-07-27)

### GitHub Repository
- **URL**: https://github.com/samar-singh/factory-automation
- **Status**: Initial commit pushed successfully
- **Branch**: main

### Completed ✅
1. **Project Planning**
   - Created comprehensive implementation plan (`factory_automation_plan.md`)
   - Designed multi-agent architecture using OpenAI Agents SDK
   - Planned RAG integration with free ChromaDB
   - **NEW**: Updated plan to use OpenAI function tools pattern

2. **Project Setup**
   - Set up project structure with uv package manager
   - Created `pyproject.toml` with all dependencies
   - Installed OpenAI Agents SDK and other requirements
   - Created configuration management system
   - **NEW**: Created API setup guide with verification script

3. **Basic Implementation**
   - Base agent class using OpenAI Agents SDK
   - **NEW**: Added `as_tool()` method to base agent for function tools pattern
   - Orchestrator agent for workflow coordination
   - **NEW**: Created AI-powered orchestrator v2 with context awareness
   - Placeholder agents for email, order, and inventory
   - ChromaDB client for vector operations
   - Gradio dashboard with full UI layout

4. **Advanced Features** ✨
   - **NEW**: Implemented multimodal search with Qwen2.5VL + CLIP
   - **NEW**: LiteLLM integration for Together.ai access
   - **NEW**: Combined embeddings approach for enhanced search

### In Progress 🚧
- API key acquisition (OpenAI, Together.ai)
- Database setup (ChromaDB + PostgreSQL)
- Testing new orchestrator implementation
- Creating sample inventory data

### Pending 📋
- Gmail API integration (credentials ready)
- Excel inventory ingestion
- Payment processing (OCR)
- Testing with real data
- Migration from v1 to v2 orchestrator

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

## Important Files
- `/factory_automation_plan.md` - Complete implementation plan (updated with function tools)
- `/API_SETUP_GUIDE.md` - **NEW**: Detailed API configuration guide
- `/factory_automation/` - Main project directory
- `/factory_automation/pyproject.toml` - Dependencies
- `/factory_automation/main.py` - Entry point
- `/factory_automation/agents/` - Agent implementations
- `/factory_automation/agents/orchestrator_v2.py` - **NEW**: AI-powered orchestrator
- `/factory_automation/agents/base.py` - Updated with as_tool() method
- `/factory_automation/rag/multimodal_search.py` - **NEW**: Qwen2.5VL + CLIP search
- `/factory_automation/ui/gradio_app.py` - Dashboard

## Next Steps
1. Obtain API keys:
   - OpenAI API key from platform.openai.com
   - Together.ai API key for Qwen2.5VL access
2. Follow API_SETUP_GUIDE.md for Gmail configuration
3. Set up local ChromaDB and PostgreSQL
4. Test the new AI-powered orchestrator
5. Create sample inventory data with images
6. Migrate from orchestrator v1 to v2

## Notes
- Customer provided example email showing full order lifecycle
- Need Together AI API key for Qwen2.5VL72B vision model
- System designed for ~50 emails/day volume
- Budget updated: ~$120-190/month (includes Qwen2.5VL costs)
- Created ROADMAP_PROGRESS_REPORT.md for tracking
- Project is approximately 35% complete (major architecture improvements)
- Function tools pattern enables intelligent context-aware processing
- Dual multimodal approach provides best of both worlds

## Commands & Tools
- Using `uv` for Python package management
- Git repository initialized and pushed to GitHub
- Using Opus model for complex development work