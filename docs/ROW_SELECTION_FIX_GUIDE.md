# Row Selection Fix Guide

## Date: 2025-08-05

## Problem Fixed
The row selection was failing because:
1. `evt.index` could be either an integer or a list
2. The error check `len(evt.index)` failed when index was an integer
3. No proper error handling for edge cases

## Solution Applied

### Enhanced Row Selection Handler
```python
def on_row_select(data, evt: gr.SelectData):
    """Handle row selection in the queue"""
    try:
        if evt.index is not None:
            # Handle both single index and list of indices
            if isinstance(evt.index, list):
                row_idx = evt.index[0] if len(evt.index) > 0 else None
            else:
                row_idx = evt.index
            
            # Check if we have valid data and index
            if data and row_idx is not None and row_idx < len(data):
                selected_row = data[row_idx]
                review_id = selected_row[0]  # ID is first column
                logger.info(f"Selected review: {review_id} at index {row_idx}")
                return f"Selected: {review_id}", review_id
    except Exception as e:
        logger.error(f"Error in row selection: {e}")
        logger.error(f"evt.index type: {type(evt.index)}, value: {evt.index}")
        logger.error(f"data length: {len(data) if data else 0}")
    
    return "No review selected", None
```

## Key Improvements

1. **Type Checking**: Properly handles both integer and list indices
2. **Error Logging**: Captures detailed error information
3. **Null Safety**: Checks for None values before accessing
4. **Bounds Checking**: Ensures index is within data bounds

## Testing Instructions

### 1. Create a Test Review
Process an order to create a review in the queue:
```
From: test@customer.com
Subject: Test Order

Need 500 pieces of unknown tags XYZ123
```

### 2. Test Row Selection
1. Go to http://127.0.0.1:7860
2. Navigate to "Human Review" tab
3. Click "Refresh Queue"
4. Click on any row in the table
5. Check the "Selected Review" field - it should show the review ID
6. Click "Open Selected Review"

### 3. Monitor Logs
Check `factory_improved.log` for:
- "Selected review: REV-XXXX at index X"
- "Refreshed queue with X reviews"
- Any error messages

## Debugging Tips

If selection still fails:
1. Check browser console (F12) for JavaScript errors
2. Look for error patterns in the log:
   ```bash
   grep -i "error in row selection" factory_improved.log
   ```
3. Verify data format in logs:
   ```bash
   grep "Refreshed queue" factory_improved.log
   ```

## What Happens Now

When you click a row:
1. The `on_row_select` function is called
2. It safely extracts the row index (handles int or list)
3. Gets the review ID from the first column
4. Updates the "Selected Review" text field
5. Stores the ID in Gradio state for opening

The system should now handle row selection without errors!