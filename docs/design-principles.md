# Factory Automation UI Design Principles

## Overview
This document defines the design principles and standards for the Factory Flow Automation system UI. These principles ensure consistency, usability, and accessibility across all interfaces.

## Core Design Philosophy

### 1. Factory-First Design
- **Large Touch Targets**: Minimum 44x44px for factory floor tablet usage
- **High Contrast**: Ensure readability in varying lighting conditions
- **Clear Visual Hierarchy**: Critical information immediately visible
- **Minimal Cognitive Load**: Simple, intuitive interfaces for quick decisions

### 2. Data Clarity
- **Progressive Disclosure**: Show essential info first, details on demand
- **Status Visualization**: Clear color coding for system states
- **Real-time Feedback**: Immediate visual response to user actions
- **Error Prevention**: Guide users to correct inputs before errors occur

### 3. Efficiency & Speed
- **Single-Click Actions**: Minimize steps for common tasks
- **Batch Operations**: Process multiple items efficiently
- **Keyboard Shortcuts**: Support power users with shortcuts
- **Auto-Save**: Preserve work automatically

## Visual Design System

### Color Palette

#### Status Colors
```css
/* Confidence Levels */
--high-confidence: #10b981;    /* Green - Auto-approve (>80%) */
--medium-confidence: #f59e0b;  /* Yellow - Manual review (60-80%) */
--low-confidence: #ef4444;     /* Red - Needs attention (<60%) */

/* System States */
--success: #22c55e;
--warning: #eab308;
--error: #dc2626;
--info: #3b82f6;

/* UI Elements */
--primary: #6366f1;           /* Indigo - Primary actions */
--secondary: #8b5cf6;         /* Purple - Secondary actions */
--neutral: #6b7280;           /* Gray - Neutral elements */
```

#### Gradient Cards
```css
/* Customer Information Card */
--customer-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* AI Recommendation Card */
--ai-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);

/* Inventory Match Card */
--inventory-gradient: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
```

### Typography

#### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 
             'Helvetica Neue', 'Arial', sans-serif;
```

#### Size Scale
- **Headings**: 24px (H1), 20px (H2), 18px (H3), 16px (H4)
- **Body**: 14px (default), 12px (small)
- **Labels**: 12px (uppercase, letter-spacing: 0.05em)
- **Data Tables**: 13px (optimal for scanning)

### Spacing System
- **Base Unit**: 4px
- **Spacing Scale**: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px
- **Component Padding**: 16px (default), 12px (compact), 20px (spacious)
- **Grid Gap**: 16px (cards), 8px (form elements)

## Component Standards

### Cards
- **Border Radius**: 8px
- **Shadow**: 0 1px 3px rgba(0,0,0,0.1)
- **Padding**: 20px
- **Margin Between**: 16px
- **Hover State**: Slight elevation increase

### Tables
- **Header Background**: #f9fafb
- **Row Hover**: #f3f4f6
- **Border**: 1px solid #e5e7eb
- **Cell Padding**: 12px 16px
- **Striped Rows**: Optional for long lists

### Buttons
- **Primary**: Solid background, white text
- **Secondary**: Outlined, colored text
- **Danger**: Red background for destructive actions
- **Disabled**: 50% opacity
- **Min Height**: 40px (mobile), 36px (desktop)

### Forms
- **Input Height**: 40px
- **Label Position**: Above input
- **Error Messages**: Below input, red text
- **Required Indicator**: Red asterisk (*)
- **Help Text**: Gray, below input

## Responsive Design

### Breakpoints
```css
/* Mobile First Approach */
--mobile: 0-639px;      /* Single column */
--tablet: 640-1023px;   /* Two columns */
--desktop: 1024-1279px; /* Three columns */
--wide: 1280px+;        /* Full layout */
```

### Layout Adaptations
- **Mobile**: Stack all cards vertically
- **Tablet**: 2-column grid for cards
- **Desktop**: 3-column layout with sidebar
- **Wide**: Maximum content width 1400px

## Accessibility Standards

### WCAG 2.1 Level AA Compliance
- **Color Contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
- **Focus Indicators**: Visible outline on all interactive elements
- **Keyboard Navigation**: All features accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels and semantic HTML

### Interactive Elements
- **Touch Target Size**: Minimum 44x44px
- **Click Target Padding**: 8px around text links
- **Hover States**: Clear visual feedback
- **Loading States**: Animated indicators with text alternatives

## Loading & Empty States

### Loading States
```html
<!-- Skeleton Loader Pattern -->
<div class="skeleton-loader">
  <div class="skeleton-header"></div>
  <div class="skeleton-text"></div>
  <div class="skeleton-text"></div>
</div>
```

### Empty States
- **Icon**: Relevant illustration or icon
- **Heading**: Clear description of empty state
- **Body Text**: Helpful guidance on next steps
- **Action Button**: Primary action to resolve empty state

## Error Handling

### Error Message Patterns
- **Field Errors**: Inline below field, red text
- **Form Errors**: Summary at top of form
- **System Errors**: Toast notification or modal
- **Network Errors**: Retry button with explanation

### Error Prevention
- **Input Validation**: Real-time as user types
- **Confirmation Dialogs**: For destructive actions
- **Undo Options**: Where possible
- **Auto-Save**: Prevent data loss

## Performance Guidelines

### Target Metrics
- **First Contentful Paint**: < 1.5s
- **Time to Interactive**: < 3.5s
- **Layout Shift**: < 0.1
- **Input Latency**: < 100ms

### Optimization Strategies
- **Lazy Loading**: Images and non-critical content
- **Virtualization**: For long lists (>100 items)
- **Debouncing**: Search inputs (300ms)
- **Caching**: Previous search results

## Dashboard-Specific Guidelines

### Human Review Dashboard
- **Queue Table**: Sortable, filterable, paginated
- **Detail View**: Side panel or modal
- **Action Buttons**: Fixed position for consistency
- **Status Badges**: Color-coded with icons

### Inventory Search
- **Search Bar**: Prominent, with suggestions
- **Results Grid**: Card or table view toggle
- **Filters**: Collapsible sidebar
- **Sorting**: Multiple options clearly visible

### Order Processing
- **Step Indicator**: Show current stage
- **Progress Bar**: Visual completion percentage
- **Action Log**: Timestamped activity feed
- **Quick Actions**: Floating action button

## Testing Checklist

### Visual Testing
- [ ] All colors meet contrast requirements
- [ ] Responsive breakpoints work correctly
- [ ] Images load and display properly
- [ ] Animations are smooth (60fps)

### Interaction Testing
- [ ] All buttons and links are clickable
- [ ] Forms validate correctly
- [ ] Keyboard navigation works
- [ ] Touch gestures respond appropriately

### Accessibility Testing
- [ ] Screen reader announces correctly
- [ ] Focus order is logical
- [ ] Alt text present for images
- [ ] ARIA labels accurate

### Performance Testing
- [ ] Page loads within targets
- [ ] Interactions feel responsive
- [ ] No memory leaks
- [ ] Handles large datasets

## Implementation Notes

### CSS Architecture
- **Methodology**: BEM (Block Element Modifier)
- **Preprocessor**: CSS-in-JS for Gradio components
- **Variables**: CSS custom properties for theming

### Component Library
- **Base**: Gradio components
- **Extensions**: Custom CSS overrides
- **Icons**: Emoji for simplicity (no icon library needed)

### Browser Support
- **Chrome**: Latest 2 versions
- **Firefox**: Latest 2 versions
- **Safari**: Latest 2 versions
- **Edge**: Latest 2 versions
- **Mobile**: iOS Safari, Chrome Android

## Maintenance

### Review Frequency
- **Quarterly**: Review and update principles
- **Per Feature**: Apply checklist to new features
- **On Issues**: Update based on user feedback

### Documentation
- **Screenshots**: Maintain visual examples
- **Changelog**: Track design system changes
- **Component Docs**: Update as components evolve

---

*Last Updated: 2025-01-18*
*Version: 1.0*
*Maintained by: Factory Automation Team*