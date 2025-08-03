#!/bin/bash
# Demo script showing pdb debugging interaction

echo "=============================================="
echo "PDB DEBUGGING DEMO"
echo "=============================================="
echo ""
echo "This will run the test and hit a breakpoint in make_decision()"
echo "When pdb prompt appears, you can:"
echo "  - Type 'p search_results' to see the search results"
echo "  - Type 'p urgency' to see the urgency flag"
echo "  - Type 'n' to go to next line"
echo "  - Type 'c' to continue execution"
echo ""
echo "Press Enter to start..."
read

# Run the test
source .venv/bin/activate
python test_agentic_with_pdb.py