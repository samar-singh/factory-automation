# Factory Flow Automation Project Memory

## 🔒 ACTIVE IMPLEMENTATION PLAN - STRICT ADHERENCE REQUIRED

**CRITICAL**: An implementation plan is currently LOCKED and active. ALL work must follow this plan.

### Current Plan: Two-Tier Action System for V3 Orchestrator
- **Lock File**: `/docs/IMPLEMENTATION_PLAN_LOCK.md` 
- **Status**: ACTIVE - Phase 6 COMPLETED → Ready for Phase 9 (Production Preparation)
- **Plan ID**: PLAN-2025-01-TWOTIER
- **Deviation Policy**: NO DEVIATIONS without explicit user approval using `OVERRIDE PLAN` command
- **Standard Test Case**: `/factory_automation/factory_tests/standard_test_case.py`
- **Integration Test**: `uv run python test_phase_integration.py`
- **Test Runner**: `./run_tests.sh` (interactive test menu)
- **Key Achievement**: Full approval flow working with functional approve/reject buttons

### ⚠️ Interpretation Rules for ALL Future Prompts:
1. **ALWAYS** read `/docs/IMPLEMENTATION_PLAN_LOCK.md` before any work
2. **INTERPRET** all requests in context of the active plan
3. **REFUSE** requests that deviate from plan unless user explicitly says "OVERRIDE PLAN"
4. **WARN** if a request might conflict with the plan
5. **TRACK** progress in the lock file after each phase completion
6. **TEST** after each phase with `python run_factory_automation.py`

### Magic Commands (User Controls):
- `PLAN STATUS` - Report current phase and progress
- `PLAN CHECKPOINT` - Validate recent work against plan
- `OVERRIDE PLAN: [task]` - Request deviation (requires approval)
- `LOCK PLAN` - Prevent any changes
- `UNLOCK PLAN` - Resume implementation

### Examples of Plan Adherence:
- User: "Add a new email feature" 
  → AI: "⚠️ This deviates from the current plan. Use 'OVERRIDE PLAN' to proceed."
- User: "Update the orchestrator"
  → AI: "Updating orchestrator per Phase 3 of active plan..."
- User: "OVERRIDE PLAN: Add feature X"
  → AI: "Plan override acknowledged. Proceeding..."

### Phase Checkpoints:
Before starting ANY work:
1. Check `/docs/IMPLEMENTATION_PLAN_LOCK.md` for current phase
2. Verify request aligns with current phase goals
3. If not aligned, request clarification or override
4. After completing work, update phase checkboxes in lock file

---

## Project Overview

Building an automated system for a garment price tag manufacturing factory to:

- Poll Gmail for order emails
- Extract order details using LLMs
- Match tag requests with inventory using multimodal RAG
- Manage approvals with human-in-the-loop
- Track payments (UTR/cheques)
- Provide real-time dashboard

## Current Status (Last Updated: 2025-08-29 - Session 23 Complete)

### GitHub Repository

- **URL**: <https://github.com/samar-singh/factory-automation>
- **Status**: Active development, regular commits
- **Branch**: feature/orchestrator-action-proposal-system
- **Progress**: ~80% Complete (Phase 6 fixed, approval flow functional)

### Completed Features ✅

1. **Project Foundation**
   - Multi-agent architecture using OpenAI Agents SDK
   - **Orchestrator V3**: Two implementations:
     - `orchestrator_v3_agentic.py`: Current integrated version using OpenAI Agents SDK
     - `orchestrator_v3_approval.py`: New version with true pre-execution approval flow
   - **Orchestrator V4**: Proposal-based system (no autonomous execution)
   - **Two-Tier Action System**: Actions classified as reversible (auto-execute) vs irreversible (require approval)
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
   - **1,184 items ingested** from 12 Excel files (20 sheets total)
   - **Multi-sheet support**: Handles Sheet1 and Sheet2 with merged cells
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

### Recent Updates (2025-08-29 - Session 23 Complete) 🆕

**Session 23 - Approval Flow Fixed & Customer Email Identification Resolved:**

**✅ PHASE 6 COMPLETED:**
- **Fixed Human Review Dashboard**: Now properly shows pending approval items (was showing 0 items)
- **Fixed Approval Flow**: Approve/Reject buttons now fully functional and wired to backend
- **Fixed recommendation_queue**: Properly populated from ActionAudit for irreversible actions
- **Added Approval Endpoints**: Created /approve_action and /reject_action in run_factory_automation.py
- **Connected UI to Orchestrator**: Buttons now trigger orchestrator's approve_action method

**✅ CUSTOMER IDENTIFICATION FIXED:**
- **Fixed Email Thread Understanding**: AI now correctly identifies customers in forwarded/quoted emails
- **Enhanced Context Awareness**: System distinguishes between suppliers and customers
- **Updated AI Prompts**: Added explicit instructions for email thread analysis
- **Validation Added**: Known supplier emails validated and corrected
- **Test Case Success**: Correctly identifies Rajlaxmi Home Products as customer (not Interface Direct)

**🟢 SYSTEM NOW FUNCTIONAL:**
- Two-Tier Action System: WORKING (reversible auto-execute, irreversible require approval)
- Human Review Dashboard: OPERATIONAL (displays pending items correctly)
- Approval Workflow: FUNCTIONAL (approve/reject actions execute properly)
- Customer Extraction: ACCURATE (correctly identifies from email threads)

### Previous Updates (2025-01-29 - Session 22)

**Session 22 - Critical Issues Fixed and Validation System Created:**

**✅ COMPLETED:**
- **Fixed Tool Registration**: All 14 tools properly registered including `classify_email_intent`
- **Fixed Tool Schemas**: Preserved params_json_schema through wrapper for correct API calls  
- **Fixed Attachment Tools**: Made content parameter optional for direct file path reading
- **Fixed Validation Rules**: Corrected parameter mismatches (changed `process_complete_order` from `email_data` to `email_subject, email_body, sender_email`)
- **Created Validation System**: Complete pre-execution validation framework with ValidationAgent
- **Created Debugging Protocol**: Added mandatory debugging checklist at `/docs/CLAUDE_DEBUGGING_PROTOCOL.md`
- **Fixed Async/Sync**: All 14 tools now use `async def` for consistency
- **Added Negative Guidance**: Tools include "what not to do" instructions for AI
- **Integration Testing**: Successfully processed Allen Solly email with 5 attachments via Playwright MCP

**🔴 REMAINING CRITICAL ISSUES:**
1. ~~**Human Review Dashboard BROKEN**~~ ✅ FIXED in Session 23
2. ~~**Approval Flow NOT WIRED**~~ ✅ FIXED in Session 23
3. **Tool-Calling Loop Limited**: AI stuck with 2 API calls, cannot recover from mistakes (fix documented)
4. **ValidationAgent NOT INTEGRATED**: Created but not connected to orchestrator

**⚠️ KNOWN LIMITATIONS:**
- **OpenAI SDK Issue CONFIRMED**: Tools execute immediately when LLM requests them, preventing true pre-execution approval
- **Data Issues**: Only 569/1184 items in ChromaDB (48% missing)
- **Customer Email Field**: Stores company name instead of email address

**Two-Tier Action System Status (Phase 6 Fixed, Phase 9 Ready):**
- ✅ **Phase 1-5**: Database, classification, tracking, execution, and UI implemented
- ✅ **Phase 6**: FIXED and COMPLETE - Approval flow now fully functional
- ✅ **Phase 7**: V4 cleanup completed, files moved to /deprecated/
- ✅ **Phase 8**: Integration testing completed, some issues remain
- 🚀 **Phase 9**: Ready to start - Production preparation

### Previous Session History

**See `/docs/SESSION_ARCHIVE.md` for detailed session history (Sessions 1-21)**

**Key Historical Achievements:**
- ✅ **Sessions 20-21**: V4 Proposal System + Shared Tools Architecture
- ✅ **Sessions 17-19**: Multi-sheet Excel ingestion + WCAG AA compliance
- ✅ **Sessions 15-16**: UI consolidation + gradient card enhancements
- ✅ **Sessions 11-12**: Database queue system + modern interface design
- ✅ **Sessions 8-10**: Image deduplication + human review system planning
- ✅ **Sessions 6-7**: Attachment refactoring + order extraction fixes
- ✅ **Sessions 3-5**: Enhanced RAG + cross-encoder reranking + AI-powered extraction
- ✅ **Sessions 1-2**: Agentic orchestrator foundation + GPT-4 integration

### Next Priority Tasks 📋

1. **✅ COMPLETED: Human Review Dashboard Fixed** (Session 23)
   - ✅ Fixed recommendation_queue population
   - ✅ Integrated ActionAudit with recommendation_queue
   - ✅ Pending actions now appear correctly
   - ✅ Approve/Reject buttons fully functional

2. **✅ COMPLETED: Approval Flow Wired** (Session 23)
   - ✅ Connected buttons to backend endpoints
   - ✅ Created approval handler in orchestrator
   - ✅ Implemented execution of approved actions
   - ⏳ Email modification capability (deferred enhancement)
   - ✅ Emails require explicit approval before sending

3. **🔴 CRITICAL: Integration Fixes** (Required for Production)
   - Integrate ValidationAgent into orchestrator_v3_agentic.py (1-2 hours)
   - Implement tool-calling loop fix (enable >2 iterations for error recovery)
   - Test complete workflow with validation enabled
   - Verify AI can correct mistakes and follow proper order

4. **🟡 HIGH: Fix Data Issues**
   - Re-ingest inventory data into ChromaDB (currently only 569 items vs 1,184 expected)
   - Fix customer email field in database (currently stores company name instead of email)
   - Implement data migration script for existing records
   - Resolve embedding dimension mismatch (1024 vs 384)

4. **🟡 HIGH: Complete Human Review System** (As per HUMAN_INTERFACE_IMPLEMENTATION_PLAN.md)
   - Finalize batch processing system
   - Implement document generation with ReportLab for PI/quotations
   - Create Excel change log system (Option C: inventory_change_log_2025.xlsx)
   - Implement comprehensive audit trail
   - Build queue-based review system

5. **🟢 MEDIUM: Complete Phase 9 - Production Preparation**
   - Update config.yaml with production thresholds
   - Add comprehensive monitoring and logging
   - Create user documentation for two-tier system
   - Update all memory bank files
   - Create production deployment guide

6. **🟢 MEDIUM: Excel Update Functionality** (From previous sessions)
   - Implement Option A: Create NEW Excel files instead of modifying originals
   - Build version management system (Allen_Solly_Items_v2_20250113.xlsx)
   - Create inventory reconciliation system
   - Track changes without modifying source files

5. **🟢 MEDIUM: Document Generation System**
   - Implement Proforma Invoice (PI) generation
   - Create quotation templates
   - Build order confirmation documents
   - Add PDF export functionality with ReportLab
   - Integrate with order processing workflow

6. **🟢 MEDIUM: Payment Tracking with OCR**
   - Implement UTR (bank transfer) extraction
   - Add cheque processing with Tesseract
   - Build payment reconciliation system
   - Create payment status tracking
   - Add payment confirmation notifications

7. **🟢 MEDIUM: Production Deployment**
   - Set up Gmail service account
   - Configure attachment storage directory
   - Deploy to staging environment
   - Test with live emails
   - Docker containerization
   - Set up monitoring and logging

8. **🔵 LOW: Google Gemini Embeddings Migration**
   - Test Gemini embeddings (3072 dimensions)
   - A/B test against Stella-400M
   - Re-embed all inventory data
   - Update search configurations
   - Measure accuracy improvements

9. **🔵 LOW: Contextual Chunking**
   - Add context prefixes to inventory items
   - Group items by brand/category
   - Implement hierarchical chunking
   - Expected: 15-25% accuracy improvement

10. **🔵 LOW: Visual Analysis Integration**
   - Wire Qwen2.5VL to order processing
   - Enable image analysis from emails
   - Add visual similarity matching
   - Create image-based search UI

11. **⏸️ BLOCKED: Gmail Live Connection** (Waiting on IT)
   - Domain-wide delegation needed
   - Service account setup
   - Automatic polling configuration

## Technical Stack (Current)

- **Framework**: OpenAI Agents SDK with function tools pattern
- **Orchestration**: Orchestrator V3 - Two-tier action system with human approval
- **Trace Monitoring**: OpenAI trace integration for debugging
- **Vector Database**: ChromaDB with multi-collection support
- **Embeddings**:
  - **Primary**: Stella-400M (1024 dims, higher accuracy) ✅ WORKING
  - **Fallback**: all-MiniLM-L6-v2 (384 dims, faster)
  - **Images**: CLIP ViT-B/32
  - **Visual QA**: Qwen2.5VL-72B via Together.ai
- **UI**: Gradio interactive dashboard with Proposal Review tab
- **Database**: PostgreSQL + SQLAlchemy
- **OCR**: Tesseract (planned)
- **APIs**: OpenAI GPT-4, Together.ai, Gmail
- **Package Management**: uv
- **Code Quality**: pre-commit, black, ruff, mypy

## Key Architecture Decisions

1. **Two-Tier Action System**: Reversible auto-execute, irreversible require approval
2. **Multi-Agent System**: Specialized agents with shared tools architecture
3. **Validation Layer**: Pre-execution validation enforces workflow order (pending integration)
4. **OpenAI SDK Workaround**: Two orchestrator implementations (agentic vs approval)
5. **Human-in-the-Loop**: ALL irreversible actions require approval
6. **Database Strategy**: PostgreSQL (transactions) + ChromaDB (search)
7. **Excel Management**: Create new files + change logs (never modify originals)
8. **Action Classification**: 23 irreversible vs 36 reversible actions
9. **Dual Embeddings**: Stella-400M (accuracy) vs MiniLM (speed)
10. **Clean Architecture**: Deprecated code in `/deprecated/`, docs in `/docs/`

## Performance Metrics

- **Search**: 54-79% accuracy (Stella), ~400ms response time ✅
- **Inventory**: 569/1,184 items in ChromaDB (needs re-ingestion)
- **UI**: 2.5s page load (target <2s), WCAG AA compliant ✅
- **Tests**: V3/V4 orchestrators functional, all tabs working ✅

## Important Files & Directories

### Project Structure 📁
- **Documentation**: All docs now in `/docs/` folder (except README.md and CLAUDE.md)
- **Testing**: All tests in `/factory_automation/factory_tests/`
- **Deprecated**: Unused code and backups in `/deprecated/` folder
  - Old orchestrator versions
  - Unused agents and tools
  - ChromaDB backups
  - Legacy ingestion scripts
  - Previous test files

### Configuration
- `/config.yaml` - Application settings
- `/.env.example` - Secret keys template
- `/docs/API_SETUP_GUIDE.md` - API configuration guide
- `/docs/CONFIGURATION_GUIDE.md` - Settings documentation

### Core Implementation
- `/factory_automation/` - Main application directory
- `/factory_automation/factory_agents/` - Agent implementations
  - `orchestrator_v3_agentic.py` - V3 orchestrator with OpenAI SDK (integrated, tracks actions)
  - `orchestrator_v3_approval.py` - V3 with true pre-execution approval (direct API, not integrated)
  - `orchestrator_v4_proposal.py` - V4 proposal-based orchestrator (moved to /deprecated/)
  - `proposal_engine.py` - Workflow proposal generation
  - `action_classifier.py` - Classifies actions as reversible/irreversible
  - `validation_agent.py` - **NEW**: Pre-execution validation system for tool calls
  - `validation_rules.py` - **NEW**: Tool dependency and ordering rules
  - `tools/` - **Shared tools architecture**
    - `tool_factory.py` - Centralized tool creation and configuration
    - `inventory_tools.py` - Inventory search and management tools
    - `order_tools.py` - Order processing tools
    - `email_tools.py` - Email classification and response tools
    - `customer_tools.py` - Customer management tools
    - `payment_tools.py` - Payment tracking tools
    - `document_tools.py` - Document generation tools
    - `attachment_tools.py` - Attachment processing tools
    - `supplier_tools.py` - Supplier management tools
- `/factory_automation/factory_rag/` - RAG and search components
  - `chromadb_client.py` - ChromaDB client management
  - `enhanced_search.py` - Enhanced RAG search with reranking
  - `embeddings_config.py` - Embeddings configuration
- `/factory_automation/factory_ui/` - User interface components
  - `gradio_app_live.py` - Live dashboard
  - `proposal_review_dashboard.py` - Proposal review interface
  - `assets/` - **External UI assets**
    - `styles/dashboard.css` - Dashboard styling (640+ lines)
    - `scripts/accessibility.js` - Accessibility enhancements (180+ lines)
    - `loader.py` - Dynamic asset loading for Gradio
- `/factory_automation/factory_database/` - Database models and connections
- `/factory_automation/factory_models/` - Pydantic models
  - `order.py` - Order models
  - `workflow_models.py` - Workflow and proposal models

### Documentation (in /docs/)
- `/docs/factory_automation_plan.md` - Implementation roadmap
- `/docs/ROADMAP_PROGRESS_REPORT.md` - Progress tracking
- `/docs/MIGRATION_GUIDE.md` - Deployment guide
- `/docs/RAG_SCALABILITY_PLAN.md` - Future scaling plans
- `/docs/SESSION_18_DATABASE_CLEANUP.md` - Latest session updates
- `/docs/HOW_TO_RUN.md` - Execution instructions
- `/docs/HUMAN_INTERACTION_GUIDE.md` - Human-in-loop documentation
- `/docs/INVENTORY_SYNC_STRATEGY.md` - Excel/DB reconciliation
- `/docs/HUMAN_INTERFACE_IMPLEMENTATION_PLAN.md` - Complete human review system design
- `/docs/ORCHESTRATOR_ACTION_PROPOSAL_SYSTEM.md` - Architecture for workflow-centric proposal system
- `/docs/ORCHESTRATOR_TOOL_LOOP_FIX.md` - **NEW**: Critical fix for tool-calling limitation
- `/docs/VALIDATION_INTEGRATION_EXAMPLE.md` - **NEW**: Guide for integrating validation system
- `/docs/SESSION_22_VALIDATION_AND_FIXES.md` - **NEW**: Latest session documentation
- `/docs/design-principles.md` - UI design standards
- `/docs/ui-component-guide.md` - UI component specifications

### Data & Storage
- `/inventory/` - Excel inventory files
- `/chroma_data/` - ChromaDB persistent storage
- `/sample_images/` - Auto-generated tag images

### Testing
- `/factory_automation/factory_tests/` - ALL test files go here
- Key test files:
  - `test_complete_workflow.py` - End-to-end workflow test
  - `test_human_interaction.py` - Human review system test
  - `test_integration.py` - Integration testing
  - `test_ai_extraction.py` - AI extraction testing
  - `test_cleanup.py` - Tool consolidation verification
  - `test_ui_accessibility.py` - WCAG AA compliance testing
  - `test_proposal_orchestrator.py` - **NEW: V4 proposal system testing**

## Foundation Achievements (Sessions 1-3)

- ✅ **Agentic Orchestrator**: OpenAI Agents SDK with tool call tracking
- ✅ **AI-Powered Order Extraction**: GPT-4 replaces regex parsing
- ✅ **Enhanced RAG**: Cross-encoder reranking, 60% fewer false positives
- ✅ **Multimodal Search**: Qwen2.5VL image analysis + CLIP embeddings
- ✅ **Complete Pipeline**: End-to-end order processing workflow
- ✅ **Tool Consolidation**: Streamlined to essential tools

## Known Issues & Limitations

1. ~~**🔴 CRITICAL Human Review Dashboard BROKEN**~~ ✅ **FIXED in Session 23**: 
   - Dashboard now shows pending items correctly
   - recommendation_queue properly populated from ActionAudit
   - Integration between two-tier system and human review working
   - **Status**: RESOLVED - Full functionality restored

2. ~~**🔴 CRITICAL Approval Flow NOT FUNCTIONAL**~~ ✅ **FIXED in Session 23**: 
   - Approve/Reject buttons now wired to backend endpoints
   - Approval endpoints added to orchestrator
   - Email modification capability deferred (future enhancement)
   - **Phase 6 Status**: NOW COMPLETE and FUNCTIONAL
   - **Status**: RESOLVED - Approval flow working end-to-end

3. **🔴 CRITICAL Tool Loop Limited to 2 Iterations**: 
   - Orchestrator makes only 2 API calls (first with tools, second without)
   - AI cannot recover from tool calling mistakes
   - Prevents complex multi-step workflows
   - **Solution Documented**: See `/docs/ORCHESTRATOR_TOOL_LOOP_FIX.md`
   - **Status**: Fix ready to implement, not yet integrated

4. **🔴 CRITICAL ValidationAgent NOT INTEGRATED**: 
   - ValidationAgent created with complete rule system
   - Not connected to orchestrator_v3_agentic.py
   - AI frequently calls tools in wrong order
   - **Solution Ready**: Complete validation system in `validation_agent.py`
   - **Status**: Integration guide available in `/docs/VALIDATION_INTEGRATION_EXAMPLE.md`

5. **🔴 CRITICAL SDK Limitation CONFIRMED**: 
   - OpenAI Agents SDK executes tools immediately when LLM requests them
   - Cannot prevent execution for true pre-execution approval
   - Workaround: Created `orchestrator_v3_approval.py` using direct API
   - Current integrated version (`v3_agentic.py`) tracks but can't prevent

6. **🟡 HIGH Data Issues**: 
   - ChromaDB has only 569/1184 items (48% missing data)
   - Embedding dimension mismatch causing warnings (1024 vs 384)
   - Customer email field stores company name instead of email address

6. **🟡 HIGH Priority Issues**:
   - Page load performance at 2.5s (target <2s)
   - Excel update functionality not implemented
   - Document generation system (PI/quotations) not built
4. **🟢 MEDIUM Priority Issues**:
   - Type Errors: 122 mypy errors need resolution (non-critical)
   - Lint Errors: 2 E722 errors (bare except) in image_storage.py
   - Excel Formats: Some files have datetime/duplicate issues
   - Visual Analysis: Qwen2.5VL ready but not wired for production
5. **⏸️ BLOCKED Issues**:
   - Gmail Auth: Requires IT admin for domain delegation
   - Live email testing: Blocked on Gmail setup

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

## CRITICAL DEVELOPMENT RULES ⚠️

### 1. Integration Testing Rule
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

### 2. Test File Location Rule
**ALL test files MUST be created in `/factory_automation/factory_tests/`:**

```bash
# CORRECT - Create tests here:
factory_automation/factory_tests/test_new_feature.py

# WRONG - Never create tests in root:
test_something.py  # ❌ Don't do this

# When creating a new test:
1. Navigate to factory_automation/factory_tests/
2. Create test file with descriptive name
3. Import from factory_automation modules using absolute imports
4. Follow existing test patterns for consistency
```

### 3. Documentation Organization Rule
**All documentation goes in `/docs/` folder except README.md and CLAUDE.md:**

```bash
# These stay in root:
- README.md         # Project overview
- CLAUDE.md         # This memory file

# Everything else goes in docs/:
- docs/guides/      # How-to guides
- docs/api/         # API documentation
- docs/reports/     # Progress reports
```

## AI & RAG Enhancements

**AI Integration Complete:**
- ✅ GPT-4 orchestrator + natural language processing
- ✅ Cross-encoder reranking (60% fewer false positives)
- ✅ Hybrid search (BM25 + semantic)
- ✅ Stella-400M embeddings (higher accuracy)
- ⏳ Qwen2.5VL ready for visual analysis

**Next Priority:**
1. ValidationAgent integration
2. Tool-calling loop fix
3. Document generation
4. Production deployment

## UI Development

**See `/docs/UI_DEVELOPMENT_WORKFLOW.md` for complete workflow, `/docs/design-principles.md` for standards**

**Core Design Principles:**
- **Factory-First**: 44x44px touch targets, high contrast for factory conditions
- **Status Colors**: Green (>80% confidence), Yellow (60-80%), Red (<60%)
- **Gradient Cards**: Purple (Customer), Pink (AI Recommendations), Teal (Inventory)
- **Accessibility**: WCAG AA compliance, keyboard navigation, screen reader support
- **Performance**: <2s page load, <500ms search, <100ms interactions

**Key Standards:**
- **Cards**: 8px radius, 20px padding, gradient backgrounds for key info
- **Tables**: Sortable headers, hover states, responsive design
- **Forms**: 40px input height, inline validation, clear error messages
- **Testing**: `make ui-check` for validation, `pytest test_ui_accessibility.py` for compliance

## Standard Test Case for Integration Testing

### Test Email Scenario (Used for all Phase Testing)
- **From**: trimsblr@yahoo.co.in (Interface Direct - Tag Supplier)
- **To**: storerhppl@gmail.com (Rajlaxmi Home Products)
- **Subject**: Pro-Forma Invoice #1542 for Allen Solly tags
- **Contains**: 32 tag codes across 4 fit types (Bootcut, Classic straight, Skinny, Slim)
- **Attachment**: Allen Solly PO Excel file

### Test Commands
```bash
# Run standard integration test after each phase
uv run python test_phase_integration.py

# Test with UI (using uv and dotenv)
python3 -m dotenv run -- python3 run_factory_automation.py
# Then paste the formatted email from standard_test_case.py
```

### Expected Actions Classification
**Reversible (Auto-execute in Phase 4):**
- analyze_email, search_inventory, extract_excel_data, calculate_price

**Irreversible (Queue for approval in Phase 4):**
- send_email_response, create_proforma_invoice, reserve_inventory_final

## 🚨 DEBUGGING PROTOCOL (MANDATORY)

**ALWAYS follow `/docs/CLAUDE_DEBUGGING_PROTOCOL.md` when:**
- Running ANY test
- Debugging issues  
- Claiming something "works"
- After fixing bugs

**Key Steps:**
1. Check `app_*.log` files FIRST (not just console)
2. Search for "Validation failed" and "ERROR"
3. Verify ALL expected tools executed
4. Check BashOutput for background processes

**If you see Claude claim "test successful", ask:**
- "What app log did you check?"
- "Show me the validation errors from the log"

## Contact & Support

- GitHub Issues: https://github.com/samar-singh/factory-automation/issues
- Project Lead: Samar Singh
- AI Assistant: Claude (Anthropic)