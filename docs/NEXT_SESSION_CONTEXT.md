# Next Session Context
**Last Updated:** January 27, 2025 (August 27)
**Last Session:** Session 22 - Tool Registration Fixes and Validation Testing
**Next Session:** Fix UI Display and Wire Approval Flow

## Current State Summary

### What Was Just Completed ✅ (Session 22 - Validation Testing)
1. **Fixed Tool Registration** - All 14 tools now properly registered including `classify_email_intent`
2. **Fixed Tool Schemas** - Preserved params_json_schema through wrapper for correct API calls
3. **Fixed Attachment Tools** - Made content parameter optional for direct file path reading
4. **Updated Validation Rules** - Fixed parameter mismatches in validation_rules.py
5. **Playwright MCP Testing** - Successfully processed Allen Solly email with 5 attachments
6. **Validation Enforcement** - Tool calling order enforced, preventing workflow violations
7. **Identified UI Issue** - Processing Result showing raw JSON instead of formatted HTML
8. **Created Test Files** - Moved 17 test files to proper factory_tests directory
9. **Session Documentation** - Created SESSION_22_VALIDATION_AND_FIXES.md
10. **Memory Bank Updated** - CLAUDE.md updated with latest fixes and status

### System Architecture Status
- **Two-Tier Action System**: ✅ PHASES 1-8 COMPLETE
- **Action Classification**: ✅ WORKING - All actions properly classified
- **Tool Registration**: ✅ FIXED - All 14 tools registered with correct schemas
- **Validation System**: ✅ CREATED - ValidationAgent enforces tool order
- **Integration Testing**: ✅ WORKING - Playwright MCP successfully tested
- **Attachment Processing**: ✅ FIXED - Can read directly from file paths
- **UI Two-Tier Display**: ⚠️ BROKEN - Showing raw JSON instead of formatted HTML
- **Approval Flow**: ❌ NOT WIRED - Buttons exist but not connected to backend
- **Tool-Calling Loop**: ❌ LIMITED - Only 2 API calls, can't recover from errors
- **ValidationAgent Integration**: ❌ PENDING - Created but not integrated into orchestrator

## Immediate Next Steps 🎯

### Priority 1: Fix UI Display (1-2 hours)
**Current Status**: IDENTIFIED
**Objective**: Fix Processing Result to show formatted HTML with colored bullets
**File to Fix**: `run_factory_automation.py`
**Issue**: Currently showing raw JSON instead of formatted two-tier display

### Priority 2: Wire Approval Flow (3-4 hours)
**Current Status**: PHASE 6 INCOMPLETE
**Objective**: Connect UI buttons to backend for actual approval/rejection

#### Tasks:
1. **Create Approval Endpoints**
   ```python
   # In orchestrator_v3_agentic.py or new approval_handler.py
   def approve_action(workflow_id: str, action_id: str):
       # Mark action as approved in ActionAudit
       # Execute the action
       # Update UI status
   
   def reject_action(workflow_id: str, action_id: str):
       # Mark as rejected
       # Remove from pending queue
       # Update UI
   
   def modify_action(workflow_id: str, action_id: str, new_params: dict):
       # Update action parameters
       # Re-queue for approval
   ```

2. **Wire UI Buttons**
   - Connect Approve button to approval endpoint
   - Connect Reject button to rejection endpoint
   - Add modal for Modify with parameter editing

3. **Implement Email Modification**
   - Allow editing email draft before sending
   - Preview modified email
   - Track modifications in audit log

4. **Add Status Updates**
   - Real-time updates when actions approved/rejected
   - Loading states during execution
   - Success/error notifications

### Integration Decision Needed

**CRITICAL DECISION**: Which orchestrator to integrate?

**Option A: Keep orchestrator_v3_agentic.py (Current)**
- Pros: Already integrated throughout system
- Cons: Can't prevent tool execution due to SDK limitation
- Workaround: Track and display what SHOULD require approval

**Option B: Switch to orchestrator_v3_approval.py**
- Pros: True pre-execution approval using direct OpenAI API
- Cons: Requires refactoring integration points
- Benefit: Actually prevents execution until approved

**Option C: Hybrid Approach**
- Use v3_agentic for reversible actions (auto-execute)
- Switch to v3_approval for irreversible actions
- Most complex but gives best of both worlds

CREATE TABLE workflow_executions (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(50),
    action_step INT,
    action_type VARCHAR(50),
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSONB,
    error_message TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflow_proposals(workflow_id)
);

CREATE TABLE workflow_audit_log (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100),
    user_id VARCHAR(100),
    details JSONB
);
```

### 3. Data Issues Fix (Priority: MEDIUM)
```python
# Re-ingest inventory data
# Current: 569 items
# Expected: 1,184 items
# Fix: Run complete re-ingestion from all Excel sheets

# Fix customer email field
# Current: Stores company name
# Fix: Data migration script to update existing records
```

## Code Snippets for Next Session

### 1. Approval Handler Implementation
```python
# approval_handler.py
from factory_automation.factory_database.models import ActionAudit
from factory_automation.factory_agents.action_classifier import ActionType
import json
from datetime import datetime

class ApprovalHandler:
    """Handles approval/rejection of pending actions"""
    
    def __init__(self, chromadb_client, db_session):
        self.chromadb_client = chromadb_client
        self.db_session = db_session
        self.execution_log = []
        
    async def execute_workflow(self, proposal: ProposedWorkflow) -> Dict[str, Any]:
        """Execute all actions in approved workflow"""
        if proposal.approval_status != ApprovalStatus.APPROVED:
            raise ValueError(f"Cannot execute unapproved workflow {proposal.workflow_id}")
        
        # Record execution start
        await self.record_execution_start(proposal)
        
        execution_results = []
        for action in proposal.proposed_actions:
            try:
                # Execute based on action type
                result = await self.execute_action(action)
                execution_results.append({
                    "step": action.step,
                    "action": action.action.value,
                    "status": "success",
                    "result": result
                })
                
                # Update progress in database
                await self.update_execution_progress(
                    proposal.workflow_id, 
                    action.step, 
                    "success"
                )
                
            except Exception as e:
                # Record failure
                execution_results.append({
                    "step": action.step,
                    "action": action.action.value,
                    "status": "failed",
                    "error": str(e)
                })
                
                # Attempt rollback
                await self.rollback_actions(execution_results)
                
                # Update database with failure
                await self.update_execution_progress(
                    proposal.workflow_id, 
                    action.step, 
                    "failed",
                    error=str(e)
                )
                
                raise
        
        # Record execution completion
        await self.record_execution_complete(proposal, execution_results)
        
        return {
            "workflow_id": proposal.workflow_id,
            "status": "completed",
            "results": execution_results
        }
    
    async def execute_action(self, action):
        """Execute a single action based on its type"""
        action_map = {
            "SEARCH_INVENTORY": self.execute_inventory_search,
            "UPDATE_INVENTORY": self.execute_inventory_update,
            "CREATE_ORDER": self.execute_order_creation,
            "SEND_EMAIL": self.execute_email_send,
            "UPDATE_CUSTOMER": self.execute_customer_update,
            "GENERATE_DOCUMENT": self.execute_document_generation,
        }
        
        handler = action_map.get(action.action.value)
        if not handler:
            raise NotImplementedError(f"No handler for action {action.action.value}")
        
        return await handler(action)
```

### 2. Connect Executor to Dashboard
```python
# In proposal_review_dashboard.py
async def handle_approval(workflow_id: str, approver: str):
    """Handle workflow approval and trigger execution"""
    
    # Get the proposal
    proposal = orchestrator_v4.get_proposal_by_id(workflow_id)
    
    if not proposal:
        return {"error": "Proposal not found"}
    
    # Mark as approved
    orchestrator_v4.approve_proposal(workflow_id, approver)
    
    # Execute the workflow
    executor = WorkflowExecutor(chromadb_client, db_session)
    
    try:
        result = await executor.execute_workflow(proposal)
        return {
            "status": "success",
            "message": "Workflow executed successfully",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Execution failed: {str(e)}"
        }
```

## Key Files Created/Modified in Phase 5

### Created Files (Two-Tier System)
- ✅ `factory_automation/factory_agents/action_classifier.py` - Classifies actions as reversible/irreversible
- ✅ `factory_automation/factory_agents/orchestrator_v3_approval.py` - New orchestrator with true approval flow
- ✅ `factory_automation/factory_database/models.py` - Added ActionAudit table
- ✅ `factory_automation/factory_agents/tools/inventory_tools.py` - Inventory operations
- ✅ `factory_automation/factory_agents/tools/order_tools.py` - Order processing
- ✅ `factory_automation/factory_agents/tools/email_tools.py` - Email operations
- ✅ `factory_automation/factory_agents/tools/customer_tools.py` - Customer management
- ✅ `factory_automation/factory_agents/tools/payment_tools.py` - Payment tracking
- ✅ `factory_automation/factory_agents/tools/document_tools.py` - Document generation
- ✅ `factory_automation/factory_agents/tools/attachment_tools.py` - Attachment handling
- ✅ `factory_automation/factory_agents/tools/supplier_tools.py` - Supplier management

### Created Files (UI Assets)
- ✅ `factory_automation/factory_ui/assets/styles/dashboard.css` - 640+ lines of CSS
- ✅ `factory_automation/factory_ui/assets/scripts/accessibility.js` - 180+ lines of JS
- ✅ `factory_automation/factory_ui/assets/loader.py` - Dynamic asset loading

### Modified Files
- ✅ `factory_automation/factory_agents/orchestrator_v3_agentic.py` - Tracks actions in ActionAudit
- ✅ `factory_automation/factory_ui/human_review_dashboard.py` - Two-tier display with green/orange bullets
- ✅ `factory_automation/factory_agents/tools/tool_factory.py` - Added action classification
- ✅ `docs/IMPLEMENTATION_PLAN_LOCK.md` - Updated to Phase 5 complete

### Moved to Deprecated
- 📦 Old orchestrator backups
- 📦 Unused agents (design_review_agent.py, gmail_production_agent.py)
- 📦 Legacy ingestion scripts
- 📦 ChromaDB test backups
- 📦 Old test files

## Session 21 Test Results

### Comprehensive Testing Performed
1. **UX Design Expert Review**: Score 7/10
   - Clean layout and organized content
   - Good use of colors for status indicators
   - Suggested improvements: more visual hierarchy, better spacing

2. **Design Reviewer Assessment**: Score B+ (87/100)
   - Strong functional design
   - Good accessibility features
   - Could improve visual polish

3. **Code Review Expert Analysis**: 
   - Moderate quality overall
   - Sound architecture with ToolFactory pattern
   - Needs better error handling in some areas
   - Type hints could be improved

4. **Playwright UI Testing**: 
   - All tabs verified functional
   - Gradient cards display correctly
   - Forms and buttons responsive
   - No JavaScript errors in console

5. **End-to-End Workflow Testing**:
   - V3 Orchestrator: Successfully created order ORD-20250821202002
   - V4 Orchestrator: Successfully generated proposal WF-20250821-d1993154
   - Both workflows completed without errors

## Testing Strategy for Phase 6

### Approval Flow Tests Needed
```python
# test_approval_flow.py
async def test_approval_execution():
    """Test successful workflow execution"""
    proposal = create_test_proposal()
    proposal.approval_status = ApprovalStatus.APPROVED
    
    executor = WorkflowExecutor(mock_chromadb, mock_db)
    result = await executor.execute_workflow(proposal)
    
    assert result["status"] == "completed"
    assert len(result["results"]) == len(proposal.proposed_actions)

async def test_execution_rollback():
    """Test rollback on failure"""
    proposal = create_test_proposal_with_failing_action()
    executor = WorkflowExecutor(mock_chromadb, mock_db)
    
    with pytest.raises(Exception):
        await executor.execute_workflow(proposal)
    
    # Verify rollback occurred
    assert executor.rollback_called

async def test_execution_tracking():
    """Test database tracking of execution"""
    proposal = create_test_proposal()
    executor = WorkflowExecutor(chromadb, real_db)
    
    await executor.execute_workflow(proposal)
    
    # Check database for execution records
    records = db.query(WorkflowExecution).filter_by(
        workflow_id=proposal.workflow_id
    ).all()
    
    assert len(records) == len(proposal.proposed_actions)
```

## Environment Setup Reminders

```bash
# Activate environment
source .venv/bin/activate

# Test current V4 integration
python3 run_factory_automation.py
# Navigate to "Proposal Review" tab
# Test "Generate Proposal (V4)" button

# Run proposal tests
pytest factory_automation/factory_tests/test_proposal_orchestrator.py -v

# Check ChromaDB status
python -c "from factory_automation.factory_rag.enhanced_search import EnhancedTagSearch; 
search = EnhancedTagSearch(); 
print(f'Items in DB: {len(search.get_all_items())}')"
```

## Architecture Decisions Made

1. **Shared Tools Architecture**: Single tool codebase with mode-based behavior
2. **ToolFactory Pattern**: Centralized tool creation and dependency injection
3. **Mode-Based Configuration**: "execute" mode for V3, "propose" mode for V4
4. **External UI Assets**: CSS/JS in separate files for maintainability
5. **Dynamic Asset Loading**: Runtime injection of styles and scripts in Gradio
6. **Clean Repository Structure**: Deprecated code isolated in `/deprecated/`
7. **Proposal-First**: All V4 actions go through proposal generation first
8. **No Autonomous Execution**: V4 never executes without human approval
9. **Trace Monitoring**: All V4 operations include OpenAI trace for debugging
10. **Risk Assessment**: Every proposal includes comprehensive risk analysis

## Questions Resolved in Session 21

1. **Tool Sharing Strategy**: Implemented ToolFactory pattern with mode-based configuration
2. **CSS/JS Management**: Extracted to external files with dynamic loading
3. **Repository Organization**: Created `/deprecated/` folder for unused code
4. **Import Dependencies**: Removed base.py dependency, MockGmailAgent now standalone
5. **Testing Strategy**: Both orchestrators tested successfully with real workflows

## Outstanding Questions for Phase 6

1. **Integration Decision**: Keep v3_agentic, switch to v3_approval, or hybrid?
2. **Execution Prevention**: How to truly prevent execution with OpenAI SDK?
3. **Email Modification UI**: Modal dialog or inline editing?
4. **Approval Persistence**: Store approvals in database or memory?
5. **Batch Approvals**: Allow approving multiple actions at once?
6. **Notification System**: How to notify user when actions complete?
7. **Error Recovery**: What if approved action fails during execution?
8. **Audit Trail**: How detailed should approval audit logs be?

## Success Criteria for Phase 6

- [ ] Approve button executes pending actions
- [ ] Reject button removes actions from queue
- [ ] Modify button allows parameter editing
- [ ] Email drafts can be edited before sending
- [ ] Status updates show in UI
- [ ] Loading states during execution
- [ ] End-to-end test: action queued → approved → executed
- [ ] No emails sent without explicit approval

## 🚨 CRITICAL SDK LIMITATION DISCOVERED 🚨

**OpenAI Agents SDK Cannot Prevent Tool Execution:**

During Phase 5 testing with Playwright MCP, we discovered that the OpenAI Agents SDK's `Runner` class executes tools immediately when the LLM requests them. This is a fundamental limitation that prevents true pre-execution approval.

**Evidence:**
- When the LLM decides to call a tool, the SDK's Runner executes it immediately
- There is no callback or hook to intercept and approve/reject before execution
- The `tool_choice` parameter only affects which tools are available, not when they execute

**Current State:**
1. **orchestrator_v3_agentic.py** (INTEGRATED):
   - Uses OpenAI Agents SDK
   - Tracks actions in ActionAudit database
   - Shows two-tier display in UI
   - BUT: Cannot actually prevent execution
   - Actions execute immediately, then we show what "should have" required approval

2. **orchestrator_v3_approval.py** (CREATED BUT NOT INTEGRATED):
   - Uses direct OpenAI API (not SDK)
   - Can truly intercept tool calls before execution
   - Implements proper approval flow
   - BUT: Not integrated into the system yet

**UI Behavior:**
The UI correctly shows:
- ✅ Green section: "Auto-Executed Actions" (reversible)
- 🟠 Orange section: "Pending Approval" (irreversible)
- Buttons: Approve/Reject/Modify (not wired)

However, with the current integrated orchestrator (v3_agentic), ALL actions have already executed by the time the UI displays them.

## Notes for Next Developer

**Phase 5 Complete - Two-Tier Display Working!**

Key achievements:
1. **Action Classification**: 23 irreversible actions require approval, 36 reversible auto-execute
2. **UI Shows Two Tiers**: Green bullets for executed, orange for pending
3. **Workflow Tracking**: Every email creates a workflow ID (WF-YYYYMMDD-HHMMSS-hash)
4. **ActionAudit Database**: Complete tracking of all actions
5. **Two Orchestrator Implementations**: One integrated (SDK), one with true approval (direct API)

What needs to be done (Phase 6):
1. **Wire the UI buttons**: Approve/Reject/Modify currently not connected
2. **Create approval endpoints**: Handle the button clicks
3. **Decide on integration**: Which orchestrator to use going forward?

Key insights:
- The ToolFactory pattern makes adding new tools trivial
- Mode-based configuration ensures consistent behavior
- External assets make UI maintenance much easier
- The embedding dimension mismatch needs investigation (1024 vs 384)

**Test Commands That Work:**
```bash
# Run main app with two-tier display
python3 -m dotenv run -- python3 run_factory_automation.py

# Test standard case with Allen Solly order
uv run python test_phase_integration.py

# See two-tier display:
# 1. Paste email in Order Processing tab
# 2. Click "Process Order"
# 3. See green section (Auto-Executed Actions)
# 4. See orange section (Pending Approval)
# 5. Note: Buttons not yet wired in Phase 6
```

---
*Prepared by: Claude (Phase 5 Complete)*  
*For: Phase 6 - Approval Flow Implementation*  
*Key Discovery: OpenAI SDK executes immediately, true approval needs direct API*