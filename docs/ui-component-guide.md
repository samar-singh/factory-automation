# UI Component Guide - Factory Automation

## Overview
This guide documents all UI components used in the Factory Flow Automation system, their specifications, usage patterns, and implementation details.

## Component Library

### 1. Dashboard Cards

#### Customer Information Card
**Purpose**: Display customer details and order information

**Visual Design**:
- Background: Purple gradient (`linear-gradient(135deg, #667eea 0%, #764ba2 100%)`)
- Text Color: White (#ffffff)
- Border Radius: 8px
- Padding: 20px
- Shadow: `0 4px 6px rgba(0, 0, 0, 0.1)`

**Structure**:
```html
<div class="customer-info-card">
  <h3>👤 Customer Information</h3>
  <div class="info-row">
    <span class="label">Email:</span>
    <span class="value">{customer_email}</span>
  </div>
  <div class="info-row">
    <span class="label">Company:</span>
    <span class="value">{company_name}</span>
  </div>
  <div class="info-row">
    <span class="label">Order Date:</span>
    <span class="value">{order_date}</span>
  </div>
</div>
```

**Implementation Notes**:
- Use inline styles for gradient (Gradio CSS limitations)
- Ensure email addresses are clickable (`mailto:` links)
- Format dates consistently (YYYY-MM-DD HH:MM)

#### AI Recommendation Card
**Purpose**: Display AI analysis and recommendations

**Visual Design**:
- Background: Pink gradient (`linear-gradient(135deg, #f093fb 0%, #f5576c 100%)`)
- Text Color: White (#ffffff)
- Border Radius: 8px
- Padding: 20px
- Shadow: `0 4px 6px rgba(0, 0, 0, 0.1)`

**Structure**:
```html
<div class="ai-recommendation-card">
  <h3>🤖 AI Recommendation</h3>
  <div class="recommendation-text">
    {ai_analysis}
  </div>
  <div class="confidence-badge">
    Confidence: {confidence}%
  </div>
</div>
```

**Confidence Color Coding**:
- High (>80%): Green badge (#10b981)
- Medium (60-80%): Yellow badge (#f59e0b)
- Low (<60%): Red badge (#ef4444)

### 2. Data Tables

#### Inventory Matches Table
**Purpose**: Display search results from inventory

**Specifications**:
- Header Background: #f9fafb
- Row Hover: #f3f4f6
- Border: 1px solid #e5e7eb
- Cell Padding: 12px 16px
- Font Size: 13px

**Required Columns**:
```python
columns = [
    "Tag Code",      # Unique identifier
    "Item Name",     # Descriptive name
    "Brand",         # Brand/collection
    "Size",          # Size variant
    "Quantity",      # Stock level
    "Confidence",    # Match confidence %
    "Action"         # Select/View button
]
```

**Features**:
- Sortable columns (click header to sort)
- Selectable rows (checkbox or radio)
- Responsive horizontal scrolling
- Alternating row colors (optional)

#### Queue Management Table
**Purpose**: Display orders pending review

**Specifications**:
- Clickable rows for detail view
- Status badges in first column
- Priority indicators
- Timestamp formatting

**Status Badges**:
```css
.status-pending { background: #fbbf24; }
.status-approved { background: #34d399; }
.status-rejected { background: #f87171; }
.status-processing { background: #60a5fa; }
```

### 3. Form Elements

#### Search Input
**Purpose**: Primary search interface

**Specifications**:
- Height: 40px
- Font Size: 14px
- Padding: 0 16px
- Border: 1px solid #d1d5db
- Border Radius: 6px
- Focus Border: #6366f1

**Features**:
- Placeholder text with examples
- Clear button (X) when text present
- Auto-complete suggestions
- Debounced input (300ms)

#### Action Buttons

**Primary Button**:
```css
.btn-primary {
  background: #6366f1;
  color: white;
  padding: 10px 20px;
  border-radius: 6px;
  font-weight: 500;
  min-height: 40px;
}
.btn-primary:hover {
  background: #4f46e5;
}
```

**Secondary Button**:
```css
.btn-secondary {
  background: transparent;
  color: #6366f1;
  border: 1px solid #6366f1;
  padding: 10px 20px;
  border-radius: 6px;
}
```

**Danger Button**:
```css
.btn-danger {
  background: #ef4444;
  color: white;
  padding: 10px 20px;
  border-radius: 6px;
}
```

### 4. Status Indicators

#### Confidence Level Indicator
**Visual Representation**:
```python
def get_confidence_color(confidence):
    if confidence > 80:
        return "#10b981"  # Green
    elif confidence > 60:
        return "#f59e0b"  # Yellow
    else:
        return "#ef4444"  # Red
```

**Display Format**:
- Progress bar with color coding
- Percentage text overlay
- Tooltip with explanation

#### Stock Availability Badge
**States**:
- In Stock: Green dot + "Available"
- Low Stock: Yellow dot + "Limited"
- Out of Stock: Red dot + "Unavailable"

### 5. Loading States

#### Skeleton Loader
**Purpose**: Show content structure while loading

```css
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

#### Spinner
**Purpose**: Indicate active processing

```html
<div class="spinner">
  <div class="spinner-circle"></div>
  <span>Processing...</span>
</div>
```

### 6. Modal Dialogs

#### Confirmation Modal
**Purpose**: Confirm destructive actions

**Structure**:
```html
<div class="modal-overlay">
  <div class="modal-content">
    <h3>⚠️ Confirm Action</h3>
    <p>{confirmation_message}</p>
    <div class="modal-actions">
      <button class="btn-secondary">Cancel</button>
      <button class="btn-danger">Confirm</button>
    </div>
  </div>
</div>
```

#### Image Zoom Modal
**Purpose**: View images in detail

**Features**:
- Click to zoom
- Escape key to close
- Pinch to zoom on mobile
- Pan with mouse/touch

### 7. Navigation Components

#### Tab Navigation
**Purpose**: Switch between dashboard views

**Specifications**:
- Active Tab: Bottom border 2px solid #6366f1
- Inactive Tab: Text color #6b7280
- Hover: Background #f9fafb
- Transition: 200ms ease

**Implementation**:
```python
gr.Tab("Inventory Search", elem_classes=["tab-item"])
gr.Tab("Order Processing", elem_classes=["tab-item"])
gr.Tab("Human Review", elem_classes=["tab-item"])
```

### 8. Notification Components

#### Toast Notifications
**Purpose**: Show temporary status messages

**Types**:
- Success: Green background
- Warning: Yellow background
- Error: Red background
- Info: Blue background

**Position**: Top-right corner
**Duration**: 5 seconds (auto-dismiss)

### 9. Empty States

#### No Results
**Structure**:
```html
<div class="empty-state">
  <div class="empty-icon">🔍</div>
  <h3>No Results Found</h3>
  <p>Try adjusting your search criteria</p>
  <button class="btn-primary">Clear Filters</button>
</div>
```

#### No Data
**Structure**:
```html
<div class="empty-state">
  <div class="empty-icon">📊</div>
  <h3>No Data Available</h3>
  <p>Start by adding inventory items</p>
  <button class="btn-primary">Add Item</button>
</div>
```

## Responsive Behavior

### Mobile (< 640px)
- Single column layout
- Full-width cards and tables
- Collapsible navigation
- Touch-optimized controls (44px minimum)

### Tablet (640px - 1024px)
- Two-column grid for cards
- Condensed table view
- Side-by-side form elements

### Desktop (> 1024px)
- Three-column layout
- Full table view
- Inline form elements
- Hover states enabled

## Accessibility Requirements

### Keyboard Navigation
- All interactive elements focusable
- Tab order follows visual hierarchy
- Escape key closes modals
- Enter key submits forms

### Screen Reader Support
- Semantic HTML structure
- ARIA labels for icons
- Form field descriptions
- Status announcements

### Color Contrast
- Normal text: 4.5:1 minimum
- Large text: 3:1 minimum
- Interactive elements: Clear focus indicators

## Implementation Tips

### Gradio-Specific Considerations
1. Use inline styles for complex CSS (gradients, animations)
2. Leverage `elem_classes` for component styling
3. Use `gr.HTML()` for custom layouts
4. Handle state updates with `gr.State()`

### Performance Optimization
1. Lazy load images
2. Virtualize long lists (>100 items)
3. Debounce search inputs
4. Cache API responses

### Testing Checklist
- [ ] Components render correctly
- [ ] Interactions work as expected
- [ ] Responsive breakpoints function
- [ ] Accessibility standards met
- [ ] Performance targets achieved

## Component States

### Interactive States
Each interactive component should handle:
- Default
- Hover
- Focus
- Active
- Disabled
- Loading
- Error

### Data States
Each data component should handle:
- Empty
- Loading
- Loaded
- Error
- Refreshing

## Version History

- **v1.0** (2025-01-18): Initial component guide
- Components documented: 9 categories
- Accessibility standards: WCAG 2.1 AA
- Responsive breakpoints: 3 levels

---

*For design principles and philosophy, see `/docs/design-principles.md`*
*For implementation details, see component source files in `/factory_automation/factory_ui/`*