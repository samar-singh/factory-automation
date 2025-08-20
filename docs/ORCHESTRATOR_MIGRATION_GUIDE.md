# Orchestrator Migration Guide: V3 to V4

## Overview
This guide provides a comprehensive migration path from the autonomous execution-based Orchestrator V3 to the proposal-based Orchestrator V4. The new architecture ensures all system actions require human approval before execution.

## Architecture Comparison

### V3: Autonomous Execution
```python
# V3 executes actions directly
orchestrator = OrchestratorV3()
result = await orchestrator.process_order_email(email_data)
# Actions are already executed at this point
```

### V4: Proposal Generation
```python
# V4 generates proposals for human review
orchestrator = ProposalOrchestratorV4()
proposal = await orchestrator.process_email(email_data)
# Nothing is executed until explicit approval
orchestrator.approve_proposal(proposal.workflow_id)
# Then execute via WorkflowExecutor (separate service)
```

## Migration Strategy

### Phase 1: Parallel Operation (Current State)
Both V3 and V4 can operate simultaneously during transition:

```python
# run_factory_automation.py
if settings.use_proposal_system:
    from factory_automation.factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4
    orchestrator = ProposalOrchestratorV4(chromadb_client)
else:
    from factory_automation.factory_agents.orchestrator_v3_agentic import OrchestratorV3
    orchestrator = OrchestratorV3(chromadb_client)
```

### Phase 2: Integration with UI
Modify the human review dashboard to support both systems:

```python
# human_review_dashboard.py
def display_review_item(item):
    if isinstance(item, ProposedWorkflow):
        display_workflow_proposal(item)
    else:
        display_legacy_review(item)
```

### Phase 3: Gradual Migration
1. Start with low-risk workflows (inquiries, catalog requests)
2. Move to medium-risk (quotations, clarifications)
3. Finally migrate high-risk workflows (orders, payments)

### Phase 4: V3 Deprecation
After all workflows migrated and validated:
```python
# Mark V3 as deprecated
import warnings
warnings.warn(
    "OrchestratorV3 is deprecated. Use ProposalOrchestratorV4 instead.",
    DeprecationWarning,
    stacklevel=2
)
```

## Tool Migration Mapping

| V3 Tool | V4 Equivalent | Migration Notes |
|---------|---------------|-----------------|
| `process_order_email` | `analyze_email_and_propose` | Returns proposal instead of executing |
| `search_inventory` | `search_inventory_for_proposal` | Read-only, no reservations |
| `update_inventory` | Included in proposal | Database ops planned, not executed |
| `send_email` | Email draft in proposal | Content generated, not sent |
| `create_human_review` | Built into workflow | Automatic based on confidence |
| `update_customer` | `enrich_proposal_with_context` | Adds context without DB updates |
| `process_attachments` | `analyze_attachments_for_proposal` | Analysis only, no processing |

## Code Changes Required

### 1. Update Main Application Entry Point

```python
# run_factory_automation.py
async def main():
    # Initialize ChromaDB
    chromadb_client = ChromaDBClient()
    
    # Use V4 by default
    orchestrator = ProposalOrchestratorV4(
        chromadb_client=chromadb_client,
        use_mock_gmail=settings.use_mock_gmail
    )
    
    # Add workflow executor
    executor = WorkflowExecutor(
        chromadb_client=chromadb_client,
        db_operations=db_operations
    )
    
    # Start monitoring
    await orchestrator.start_monitoring()
```

### 2. Update Human Review Dashboard

```python
# human_review_dashboard.py
import gradio as gr
from factory_automation.factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4
from factory_automation.factory_agents.workflow_executor import WorkflowExecutor

def create_proposal_interface():
    """Create interface for reviewing proposals"""
    
    def display_proposals():
        orchestrator = get_orchestrator()
        proposals = orchestrator.get_all_proposals()
        
        # Format for display
        data = []
        for p in proposals:
            data.append({
                "ID": p.workflow_id,
                "Type": p.workflow_type.value,
                "Confidence": f"{p.confidence:.2%}",
                "Status": p.approval_status.value,
                "Actions": len(p.proposed_actions)
            })
        return pd.DataFrame(data)
    
    def approve_proposal(workflow_id, approver_email):
        orchestrator = get_orchestrator()
        success = orchestrator.approve_proposal(workflow_id, approver_email)
        
        if success:
            # Execute the approved workflow
            executor = get_executor()
            asyncio.run(executor.execute_workflow(
                orchestrator.get_proposal_by_id(workflow_id)
            ))
            return "Workflow approved and executed"
        return "Approval failed"
    
    # Create Gradio interface
    with gr.Tab("Workflow Proposals"):
        proposals_table = gr.DataFrame(label="Pending Proposals")
        
        with gr.Row():
            workflow_id = gr.Textbox(label="Workflow ID")
            approver = gr.Textbox(label="Your Email")
            approve_btn = gr.Button("Approve")
            
        approve_btn.click(
            approve_proposal,
            inputs=[workflow_id, approver],
            outputs=[gr.Textbox(label="Result")]
        )
```

### 3. Create Workflow Executor Service

```python
# workflow_executor.py
class WorkflowExecutor:
    """Executes approved workflow proposals"""
    
    def __init__(self, chromadb_client, db_operations):
        self.chromadb = chromadb_client
        self.db_ops = db_operations
        self.execution_log = []
    
    async def execute_workflow(self, proposal: ProposedWorkflow):
        """Execute all actions in an approved workflow"""
        
        if proposal.approval_status != ApprovalStatus.APPROVED:
            raise ValueError(f"Cannot execute unapproved workflow {proposal.workflow_id}")
        
        logger.info(f"Executing workflow {proposal.workflow_id}")
        
        for action in proposal.proposed_actions:
            try:
                result = await self.execute_action(action, proposal)
                self.execution_log.append({
                    "workflow_id": proposal.workflow_id,
                    "step": action.step,
                    "action": action.action.value,
                    "status": "success",
                    "result": result,
                    "timestamp": datetime.now()
                })
            except Exception as e:
                logger.error(f"Action failed: {e}")
                await self.handle_failure(action, proposal, e)
                raise
        
        return self.execution_log
    
    async def execute_action(self, action: ProposedAction, workflow: ProposedWorkflow):
        """Execute a single action"""
        
        if action.action == ActionType.VALIDATE_INVENTORY:
            return await self.validate_inventory(action.data)
            
        elif action.action == ActionType.CALCULATE_PRICING:
            return await self.calculate_pricing(action.data)
            
        elif action.action == ActionType.COMPOSE_EMAIL:
            return await self.send_email(action.content, workflow.email_content)
            
        elif action.action == ActionType.UPDATE_DATABASE:
            return await self.update_database(action.database_operations)
            
        # Add more action handlers...
```

## Testing the Migration

### 1. Unit Tests for V4
```python
# test_v4_migration.py
async def test_v4_generates_proposals_not_executions():
    orchestrator = ProposalOrchestratorV4(mock_chromadb)
    
    # Process email
    proposal = await orchestrator.process_email(test_email)
    
    # Verify it's a proposal, not executed
    assert isinstance(proposal, ProposedWorkflow)
    assert proposal.approval_status == ApprovalStatus.PENDING
    
    # Verify no side effects (no DB updates, no emails sent)
    assert mock_db.call_count == 0
    assert mock_email.call_count == 0
```

### 2. Integration Tests
```python
async def test_v3_to_v4_compatibility():
    # Test that both can process same email
    v3_result = await orchestrator_v3.process_order_email(email)
    v4_proposal = await orchestrator_v4.process_email(email)
    
    # V3 executes, V4 proposes
    assert v3_result.order_created == True
    assert v4_proposal.approval_status == ApprovalStatus.PENDING
```

### 3. Regression Tests
```python
async def test_v4_maintains_extraction_quality():
    # Ensure V4 extracts same quality data as V3
    v3_order = await v3.extract_order(email)
    v4_proposal = await v4.analyze_email_and_propose(email)
    
    # Compare extracted data
    assert len(v4_proposal.analysis.extracted_requirements["items_requested"]) == len(v3_order.items)
```

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Switch back to V3 via configuration
```python
# config.yaml
orchestrator_version: "v3"  # Change from "v4"
```

2. **Partial Rollback**: Use V3 for critical workflows only
```python
if workflow_type in ["payment_processing", "order_fulfillment"]:
    use_v3_orchestrator()
else:
    use_v4_orchestrator()
```

3. **Data Recovery**: All V4 proposals are logged
```python
# Recover from proposal logs if needed
proposals = load_proposal_logs()
for p in proposals:
    if p.was_approved and not p.was_executed:
        executor.execute_workflow(p)
```

## Monitoring During Migration

### Key Metrics to Track
1. **Proposal Generation Time**: Should be <500ms
2. **Approval Rate**: Track human approval patterns
3. **Execution Success Rate**: After approval
4. **Error Rate Comparison**: V3 vs V4
5. **User Satisfaction**: Feedback on proposal quality

### Logging Configuration
```python
# Enhanced logging for migration
logging.config.dictConfig({
    'version': 1,
    'handlers': {
        'v4_migration': {
            'class': 'logging.FileHandler',
            'filename': 'v4_migration.log',
            'formatter': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(orchestrator_version)s] - %(message)s'
            }
        }
    },
    'loggers': {
        'factory_automation.orchestrator': {
            'handlers': ['v4_migration'],
            'level': 'DEBUG'
        }
    }
})
```

## Common Issues and Solutions

### Issue 1: Tools Not Found
**Problem**: V4 tools have different names than V3  
**Solution**: Update tool references in agent instructions

### Issue 2: Approval Workflow Confusion
**Problem**: Users unsure when to approve  
**Solution**: Add confidence indicators and risk assessment display

### Issue 3: Performance Degradation
**Problem**: V4 slower due to comprehensive analysis  
**Solution**: Cache common patterns, optimize proposal generation

### Issue 4: Missing Execution Capabilities
**Problem**: V4 doesn't execute, needs separate executor  
**Solution**: Implement WorkflowExecutor service

## Success Criteria

Migration is complete when:
- [ ] All workflows use V4 proposal system
- [ ] Human review dashboard fully integrated
- [ ] WorkflowExecutor handles all approved workflows
- [ ] V3 marked as deprecated
- [ ] No V3 dependencies in production code
- [ ] All tests passing with V4
- [ ] Documentation updated
- [ ] Team trained on new workflow

## Timeline

- **Week 1**: Parallel operation, low-risk workflows
- **Week 2**: UI integration, medium-risk workflows
- **Week 3**: High-risk workflows, executor service
- **Week 4**: V3 deprecation, final validation
- **Week 5**: Complete migration, remove V3

---
*Migration Guide Version 1.0*  
*Created: January 19, 2025*  
*Author: Claude (Session 20)*