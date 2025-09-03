# UI Development Workflow

## Visual Development Process

Our UI development follows a systematic design review process adapted from best practices, without requiring pull requests.

### Design Verification Checklist

After any UI changes, perform these checks:
1. **Identify Changed Components** - List all modified UI elements
2. **Navigate to Affected Pages** - Test each changed interface
3. **Verify Design Compliance** - Check against `/docs/design-principles.md`
4. **Validate Feature Implementation** - Ensure functionality works as expected
5. **Check Acceptance Criteria** - Verify all requirements are met
6. **Capture Screenshots** - Document UI states (empty, loading, success, error)
7. **Check Browser Console** - Ensure no errors or warnings

### Design Review Triggers

Run design reviews in these situations:
- After modifying any file in `factory_automation/factory_ui/`
- Before committing significant UI changes
- When adding new UI components or features
- After fixing UI-related bugs
- Before session documentation updates

### Automated UI Testing Commands

```bash
# Run all UI checks
make ui-check

# Capture UI screenshots
make ui-screenshot

# Check accessibility compliance (WCAG AA)
pytest factory_automation/factory_tests/test_ui_accessibility.py -v

# Run visual regression tests
python -m factory_automation.factory_ui.design_review

# Run design review agent
python -m factory_automation.factory_ui.visual_regression

# Quick UI validation
python run_factory_automation.py --check-ui
```

### UI Component Standards

All UI components must follow these standards:
- **Cards**: Use gradient backgrounds for key information (Customer, AI Recommendations)
- **Tables**: Responsive with proper headers, sortable columns
- **Status Indicators**: Color-coded confidence levels (Green >80%, Yellow 60-80%, Red <60%)
- **Loading States**: Show skeletons or spinners for async operations
- **Error States**: Clear error messages with recovery actions
- **Empty States**: Helpful guidance when no data available

### Accessibility Requirements

- **WCAG AA Compliance**: Minimum contrast ratios maintained
- **Keyboard Navigation**: All interactive elements keyboard accessible
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Touch Targets**: Minimum 44x44px for factory floor usage
- **Focus Indicators**: Visible focus states on all interactive elements

### Performance Targets

- **Page Load**: < 2 seconds for dashboard tabs
- **Search Response**: < 500ms for inventory queries
- **UI Interactions**: < 100ms response time
- **Memory Usage**: < 200MB for image-heavy views

### Visual Testing Strategy

1. **Baseline Screenshots**: Capture reference images of all UI states
2. **Regression Testing**: Compare current UI against baselines
3. **Responsive Testing**: Verify layouts at all breakpoints (mobile, tablet, desktop)
4. **Cross-browser Testing**: Check Chrome, Firefox, Safari, Edge
5. **Accessibility Testing**: Automated WCAG compliance checks

### Pre-commit UI Validation

When UI files are modified, these checks run automatically:
```bash
# Detected UI changes in factory_ui/
# Running design review...
✓ Visual hierarchy check
✓ Color contrast validation
✓ Responsive design verification
✓ Accessibility compliance
✓ Performance metrics
```

### Session-Based Design Reviews

At the end of each development session:
1. Document UI changes in session notes
2. Capture screenshots of new/modified interfaces
3. Update visual regression baselines if needed
4. Note any design decisions or trade-offs
5. Plan UI improvements for next session

### Common UI Issues to Check

- [ ] Placeholder data not replaced with real data
- [ ] Gradient cards rendering properly
- [ ] Tables responsive on mobile devices
- [ ] Loading states for async operations
- [ ] Error messages user-friendly
- [ ] Images loading and displaying correctly
- [ ] Form validation working properly
- [ ] Navigation between tabs smooth

### Design Resources

- **Design Principles**: `/docs/design-principles.md`
- **Component Guide**: `/docs/ui-component-guide.md`
- **Visual Tests**: `/factory_automation/factory_ui/visual_tests.py`
- **Accessibility Tests**: `/factory_automation/factory_tests/test_ui_accessibility.py`