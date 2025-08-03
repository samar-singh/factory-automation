# Agentic Orchestrator Flow Example

## Traditional Workflow (V2) vs Agentic (V3)

### Scenario: Email arrives asking for "500 black tags similar to last order"

## V2 Workflow Approach (Current)
```python
# Fixed sequence - developer defines the flow
async def process_email(email):
    # Step 1: AI generates text about what to do
    analysis = "This appears to be an order for black tags..."
    
    # Step 2: Extract order (hardcoded logic)
    items = extract_with_regex(email.body)  # Returns ["500 black tags"]
    
    # Step 3: Search inventory (direct call)
    results = chromadb.search("black tags")
    
    # Step 4: Decision (if-else logic)
    if results[0].score > 0.8:
        decision = "approve"
    else:
        decision = "review"
    
    # Step 5: Return text description
    return "I would approve this order for 500 black tags"
```

## V3 Agentic Approach (New)
```python
# AI decides the flow autonomously
async def process_email(email):
    # Give email to AI with tools
    result = await agent.run("Process this email", tools=[...])
    
    # AI autonomously:
    # 1. Calls analyze_email() → {"type": "order", "urgent": true}
    # 2. Calls get_customer_context() → {"previous_orders": [...]}
    # 3. Notices "similar to last order" 
    # 4. Calls search_inventory("black tags style from last order")
    # 5. Gets high confidence match
    # 6. Calls make_decision() → {"decision": "auto_approve"}
    # 7. Calls generate_document() → {"quotation": "..."}
    
    return result  # Contains actual actions taken
```

## Real Example Flow

### Email Input:
```
From: allen.solly@example.com
Subject: Urgent order required
Body: "Hi, we need 500 black tags similar to our last order. 
       Also include 200 blue tags if available. Need by next week."
```

### V3 Agentic Processing:

**AI's Autonomous Decisions:**

1. **AI thinks**: "This is an email, let me analyze it"
   - **Calls**: `analyze_email(subject, body, from)`
   - **Gets**: `{"type": "order", "urgent": true, "mentions_previous": true}`

2. **AI thinks**: "They mentioned 'last order', I should check history"
   - **Calls**: `get_customer_context("allen.solly@example.com")`
   - **Gets**: `{"last_order": {"items": ["Black Tag SKU-123"], "quantity": 1000}}`

3. **AI thinks**: "Now I know what they ordered before, let me search"
   - **Calls**: `search_inventory("black tags SKU-123", min_quantity=500)`
   - **Gets**: `[{"name": "Black Tag SKU-123", "stock": 2000, "score": 0.95}]`

4. **AI thinks**: "They also want blue tags, let me search"
   - **Calls**: `search_inventory("blue tags", brand="ALLEN_SOLLY")`
   - **Gets**: `[{"name": "Blue Tag SKU-456", "stock": 500, "score": 0.88}]`

5. **AI thinks**: "High confidence matches, I can auto-approve"
   - **Calls**: `make_decision([black_results, blue_results], customer_history)`
   - **Gets**: `{"decision": "auto_approve", "confidence": 0.91}`

6. **AI thinks**: "Let me generate a quotation"
   - **Calls**: `generate_document("quotation", order_details, selected_items)`
   - **Gets**: `{"document_id": "QUO-20240115-001", "total": 1500.00}`

### Final Result:
```json
{
  "success": true,
  "autonomous_actions": 6,
  "tool_calls": [
    {"tool": "analyze_email", "result": "order detected"},
    {"tool": "get_customer_context", "result": "history retrieved"},
    {"tool": "search_inventory", "result": "black tags found"},
    {"tool": "search_inventory", "result": "blue tags found"},
    {"tool": "make_decision", "result": "auto-approved"},
    {"tool": "generate_document", "result": "quotation created"}
  ],
  "documents_generated": ["QUO-20240115-001"],
  "final_summary": "Processed urgent order from Allen Solly. Found exact matches for both black tags (same as previous order) and blue tags. Auto-approved with 91% confidence. Generated quotation for $1,500."
}
```

## Key Advantages of V3 Agentic:

1. **Adaptive**: AI noticed "similar to last order" and checked history
2. **Intelligent**: Searched for both black AND blue tags without explicit programming
3. **Contextual**: Used customer history to improve search accuracy
4. **Autonomous**: Made decisions without hardcoded if-else logic
5. **Complete**: Generated actual documents, not just descriptions

## When AI Handles Edge Cases:

### Edge Case 1: Ambiguous Request
**Email**: "Send me the usual tags"
- **V2**: Would fail - no regex match for quantity/color
- **V3**: AI checks history, finds pattern, asks for clarification if needed

### Edge Case 2: Complex Multi-Part Order
**Email**: "500 black like before, 200 blue, and do you have gold thread options?"
- **V2**: Might only catch first item
- **V3**: AI processes all three requests, searches for gold thread variants

### Edge Case 3: Payment Reference
**Email**: "Previous order was great, sending payment today. Need 500 more."
- **V2**: Might misclassify as payment email
- **V3**: AI understands it's both feedback AND new order

## The Power of Autonomous Tools

Instead of you writing code for every scenario, the AI:
- Decides which tools to use
- Determines the order of operations
- Handles unexpected cases
- Combines multiple tools for complex tasks
- Learns from context

This is true agentic behavior - the AI is an autonomous actor, not just a text generator!