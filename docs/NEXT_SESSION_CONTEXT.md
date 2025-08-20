# Next Session Context
**Last Updated:** January 19, 2025  
**Last Session:** Session 20 - Proposal-Based Orchestrator Implementation

## Current State Summary

### What Was Just Completed ✅
1. **Orchestrator V4 Proposal System** - Fully implemented and tested
2. **Workflow Models** - Comprehensive data models for proposals
3. **Proposal Engine** - Sophisticated analysis and generation engine
4. **Testing Suite** - Complete test coverage for proposal system
5. **Documentation** - Updated CLAUDE.md and created session docs

### System Architecture Status
- **Orchestrator V3**: Still operational (autonomous execution)
- **Orchestrator V4**: Ready for integration (proposal generation)
- **Human Review Dashboard**: Needs connection to V4
- **Workflow Executor**: Not yet built (next priority)

## Immediate Next Steps 🎯

### 1. Integration Phase (Priority: CRITICAL)
```python
# Connect V4 to Human Review Dashboard
# Files to modify:
- factory_automation/factory_ui/human_review_dashboard.py
- factory_automation/factory_database/operations.py

# Tasks:
1. Add proposal display in dashboard
2. Create approval/rejection interface
3. Wire up to V4 orchestrator
4. Test end-to-end flow
```

### 2. Workflow Executor Service (Priority: HIGH)
```python
# Build executor for approved workflows
# New files needed:
- factory_automation/factory_agents/workflow_executor.py
- factory_automation/factory_tests/test_workflow_executor.py

# Core functionality:
- Execute approved ProposedWorkflows
- Handle each ProposedAction sequentially
- Implement rollback on failure
- Update status in real-time
```

### 3. Database Migration (Priority: MEDIUM)
```sql
-- Add workflow tracking tables
CREATE TABLE workflow_proposals (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(50) UNIQUE,
    workflow_type VARCHAR(50),
    confidence FLOAT,
    status VARCHAR(20),
    created_at TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR(100),
    proposal_data JSONB
);

CREATE TABLE workflow_executions (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(50),
    action_step INT,
    action_type VARCHAR(50),
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSONB
);
```

## Code Snippets for Next Session

### 1. Human Review Integration
```python
# In human_review_dashboard.py
async def display_workflow_proposal(workflow_id: str):
    """Display proposal in human review interface"""
    orchestrator = get_orchestrator_v4()
    proposal = orchestrator.get_proposal_by_id(workflow_id)
    
    if proposal:
        # Display workflow details
        st.header(f"Workflow: {proposal.workflow_id}")
        st.metric("Confidence", f"{proposal.confidence:.2%}")
        st.metric("Type", proposal.workflow_type.value)
        
        # Show proposed actions
        for action in proposal.proposed_actions:
            with st.expander(f"Step {action.step}: {action.action.value}"):
                st.write(action.details)
                st.write(f"Risk: {action.risk.value}")
                
        # Approval buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve", key=f"approve_{workflow_id}"):
                execute_workflow(proposal)
        with col2:
            if st.button("Reject", key=f"reject_{workflow_id}"):
                reject_workflow(proposal)
```

### 2. Workflow Executor Start
```python
# workflow_executor.py skeleton
class WorkflowExecutor:
    """Executes approved workflow proposals"""
    
    async def execute_workflow(self, proposal: ProposedWorkflow):
        """Execute all actions in approved workflow"""
        if proposal.approval_status != ApprovalStatus.APPROVED:
            raise ValueError("Cannot execute unapproved workflow")
        
        execution_log = []
        for action in proposal.proposed_actions:
            try:
                result = await self.execute_action(action)
                execution_log.append({
                    "step": action.step,
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                # Rollback previous actions
                await self.rollback(execution_log)
                raise
        
        return execution_log
```

## Key Files to Review

### Must Read First
1. `orchestrator_v4_proposal.py` - Understand the new architecture
2. `workflow_models.py` - Review data models
3. `proposal_engine.py` - See how proposals are generated
4. `test_proposal_orchestrator.py` - Understand test patterns

### Reference During Development
1. `human_review_dashboard.py` - Current UI implementation
2. `orchestrator_v3_agentic.py` - How execution currently works
3. `order_processor_agent.py` - Order extraction logic

## Testing Strategy for Next Session

### Integration Tests Needed
```python
# Test V4 → Dashboard → Executor flow
async def test_full_proposal_to_execution():
    # 1. Generate proposal
    proposal = await orchestrator_v4.process_email(test_email)
    
    # 2. Display in dashboard
    dashboard_response = await display_proposal(proposal)
    
    # 3. Approve proposal
    orchestrator_v4.approve_proposal(proposal.workflow_id)
    
    # 4. Execute workflow
    executor = WorkflowExecutor()
    result = await executor.execute_workflow(proposal)
    
    # 5. Verify execution
    assert all(r["status"] == "success" for r in result)
```

## Known Issues to Address

### 1. Customer Email Field
- Database stores company name instead of email
- Need data migration script
- Update order creation logic

### 2. ChromaDB Data
- Only 569/1184 items ingested
- Need re-ingestion script
- Verify all Excel sheets processed

### 3. V3 Deprecation Path
- Identify all V3 usage points
- Create migration checklist
- Plan phased rollout

## Environment Setup Reminders

```bash
# Activate environment
source .venv/bin/activate

# Test current system
python3 run_factory_automation.py

# Run new tests
pytest factory_automation/factory_tests/test_proposal_orchestrator.py -v

# Check for issues
make check
make format
```

## Questions for Next Session

1. **UI Framework**: Should we keep Gradio or migrate to Streamlit for better proposal display?
2. **Execution Strategy**: Sequential or parallel action execution?
3. **Rollback Mechanism**: How to handle partial execution failures?
4. **Notification System**: How to notify users of proposal status changes?
5. **Audit Trail**: What level of execution logging is needed?

## Success Criteria for Next Session

- [ ] V4 orchestrator connected to human review dashboard
- [ ] Proposals displayable and approvable in UI
- [ ] Basic workflow executor implemented
- [ ] At least one end-to-end test passing
- [ ] Documentation updated with integration guide

## Model Flow Clarification

### How ExtractedOrder is Used
```python
# In V3 (orchestrator_v3_agentic.py):
result = await self.order_processor.process_order_email(...)
# result is OrderProcessingResult containing ExtractedOrder
order = result.order  # This is ExtractedOrder
customer_email = order.customer.email
items = order.items

# In V4 (proposal_engine.py):
# ExtractedOrder is passed to proposal engine
proposal = self.proposal_engine.generate_workflow_proposal(
    email_data=email_data,
    order_data=extracted_order,  # ExtractedOrder instance
    inventory_matches=matches,
    customer_data=customer_data
)
```

### Complete Data Flow
1. **Email arrives** → Raw email data
2. **OrderProcessorAgent** → Creates ExtractedOrder from email
3. **ProposalEngine** → Uses ExtractedOrder to generate ProposedWorkflow
4. **Human Review** → Reviews ProposedWorkflow
5. **WorkflowExecutor** → Executes approved ProposedWorkflow
6. **Database** → Updates with execution results

## Notes for Next Developer

The proposal system is fully functional but not yet integrated with the UI. The architecture cleanly separates proposal generation from execution, which is a major improvement over V3. Focus on building the bridge between proposals and the existing human review dashboard. The workflow executor should be kept simple initially - execute actions sequentially and fail fast on errors. Rollback logic can be added later.

The key insight from this session: ExtractedOrder is a business domain model (what the customer wants), while ProposedWorkflow is an orchestration model (how we plan to fulfill it). This separation allows for flexible workflow generation based on business rules, customer tier, inventory availability, and risk assessment.

---
*Prepared by: Claude (Session 20)*  
*For: Next development session*