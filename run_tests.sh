#!/bin/bash
# Test runner script for Factory Automation using uv
# This script provides easy access to all test commands

echo "🏭 Factory Automation Test Suite"
echo "================================"
echo ""
echo "Available test commands:"
echo ""
echo "1. Run main application:"
echo "   python3 -m dotenv run -- python3 run_factory_automation.py"
echo ""
echo "2. Run standard integration test:"
echo "   uv run python test_phase_integration.py"
echo ""
echo "3. Test action tracking:"
echo "   uv run python test_audit_tracking.py"
echo ""
echo "4. Test Phase 3 implementation:"
echo "   uv run python test_phase3_tracking.py"
echo ""
echo "5. Run all tests:"
echo "   uv run pytest factory_automation/factory_tests/ -v"
echo ""
echo "Select option (1-5) or press Enter to exit: "
read option

case $option in
    1)
        echo "Starting main application..."
        python3 -m dotenv run -- python3 run_factory_automation.py
        ;;
    2)
        echo "Running integration test with standard test case..."
        uv run python test_phase_integration.py
        ;;
    3)
        echo "Testing action audit tracking..."
        uv run python test_audit_tracking.py
        ;;
    4)
        echo "Testing Phase 3 implementation..."
        uv run python test_phase3_tracking.py
        ;;
    5)
        echo "Running all tests..."
        uv run pytest factory_automation/factory_tests/ -v
        ;;
    *)
        echo "Exiting..."
        ;;
esac