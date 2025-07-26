# Factory Flow Automation Project Memory

## Project Overview
Building an automated system for a garment price tag manufacturing factory to:
- Poll Gmail for order emails
- Extract order details using LLMs
- Match tag requests with inventory using multimodal RAG
- Manage approvals with human-in-the-loop
- Track payments (UTR/cheques)
- Provide real-time dashboard

## Current Status (Last Updated: 2025-07-26)

### GitHub Repository
- **URL**: https://github.com/samar-singh/factory-automation
- **Status**: Initial commit pushed successfully
- **Branch**: main

### Completed ✅
1. **Project Planning**
   - Created comprehensive implementation plan (`factory_automation_plan.md`)
   - Designed multi-agent architecture using OpenAI Agents SDK
   - Planned RAG integration with free ChromaDB

2. **Project Setup**
   - Set up project structure with uv package manager
   - Created `pyproject.toml` with all dependencies
   - Installed OpenAI Agents SDK and other requirements
   - Created configuration management system

3. **Basic Implementation**
   - Base agent class using OpenAI Agents SDK
   - Orchestrator agent for workflow coordination
   - Placeholder agents for email, order, and inventory
   - ChromaDB client for vector operations
   - Gradio dashboard with full UI layout

### In Progress 🚧
- Gmail API configuration and credentials setup
- Database initialization (ChromaDB + PostgreSQL)
- Email processing implementation
- RAG embedding pipeline

### Pending 📋
- Gmail API integration
- Multimodal embeddings (CLIP + text)
- Excel inventory ingestion
- Payment processing (OCR)
- Testing with real data

## Technical Stack
- **Framework**: OpenAI Agents SDK (replaced Swarm)
- **Vector DB**: ChromaDB (free, open-source)
- **Embeddings**: CLIP ViT-B/32 + all-MiniLM-L6-v2
- **UI**: Gradio
- **Database**: PostgreSQL
- **OCR**: Tesseract
- **Deployment**: Docker

## Key Design Decisions
1. Using OpenAI Agents SDK instead of deprecated Swarm
2. ChromaDB for free RAG solution
3. Multimodal search combining text and image embeddings
4. Human-in-the-loop for critical approvals
5. Gradio for easy-to-use dashboard

## Important Files
- `/factory_automation_plan.md` - Complete implementation plan
- `/factory_automation/` - Main project directory
- `/factory_automation/pyproject.toml` - Dependencies
- `/factory_automation/main.py` - Entry point
- `/factory_automation/agents/` - Agent implementations
- `/factory_automation/ui/gradio_app.py` - Dashboard

## Next Steps
1. Get Gmail API credentials from Google Cloud Console
2. Set up local ChromaDB and PostgreSQL
3. Create sample inventory data for testing
4. Implement email polling functionality
5. Build embedding pipeline for multimodal search

## Notes
- Customer provided example email showing full order lifecycle
- Need Together AI API key for Qwen2.5VL72B vision model
- System designed for ~50 emails/day volume
- Budget: ~$100-150/month for API costs
- Created ROADMAP_PROGRESS_REPORT.md for tracking
- Project is approximately 25% complete

## Commands & Tools
- Using `uv` for Python package management
- Git repository initialized and pushed to GitHub
- Using Opus model for complex development work