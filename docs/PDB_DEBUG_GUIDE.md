# PDB Debugging Guide for AI Integration

## Running the Debug Session

```bash
source .venv/bin/activate
python debug_ai_with_pdb.py
```

## Key PDB Commands

- **n** (next): Execute current line
- **s** (step): Step into functions
- **c** (continue): Continue execution
- **l** (list): Show current code
- **p <variable>**: Print variable value
- **pp <variable>**: Pretty-print variable
- **w** (where): Show call stack
- **u** (up): Move up in call stack
- **d** (down): Move down in call stack
- **b <line>**: Set breakpoint
- **cl**: Clear all breakpoints
- **q** (quit): Quit debugger

## Breakpoint Locations

The debug version has 5 strategic breakpoints:

1. **Before GPT-4 Analysis**: Check order text is correct
2. **Before Order Line Extraction**: Inspect AI understanding
3. **Before Inventory Search**: Check extracted order lines
4. **Before Creating Recommendation**: Review search results
5. **Exception Handler**: Debug any errors

## Example Debug Session

```python
(Pdb) n  # Go to next line
(Pdb) p order_text  # Print the order text
(Pdb) s  # Step into the GPT-4 analysis function
(Pdb) p ai_understanding  # After GPT-4 call, check response
(Pdb) c  # Continue to next breakpoint
(Pdb) p order_lines  # Check extracted lines
(Pdb) p len(order_lines)  # How many lines extracted?
(Pdb) pp order_lines[0]  # Pretty print first line
(Pdb) c  # Continue through inventory search
```

## Common Issues to Check

1. **Empty order_lines**: GPT-4 extraction format issue
2. **No search results**: Query formatting problem
3. **Low confidence**: Embedding mismatch
4. **API errors**: Check OpenAI key and quota

## Tips

- Use `pp` for complex data structures
- Set conditional breakpoints: `b 75, confidence_score < 0.5`
- Use `!` prefix to execute Python: `!import json`
- Save debug session: `alias save_debug 'p locals()' > debug_vars.txt`