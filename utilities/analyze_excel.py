import pandas as pd

file_path = "/Users/samarsingh/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/4C7D8FC2-7A28-468A-8CE3-EF6B878FA056/ML ENTERPRISES_VOGUE COLLECTIONS 1032.xlsx"

df = pd.read_excel(file_path)

# Extract order items (rows 25-29 based on the output)
print("=== ORDER ITEMS ===")
for idx in range(25, 30):
    if idx < len(df):
        row = df.iloc[idx]
        # Print non-null values
        values = []
        for val in row.values:
            if pd.notna(val) and str(val) != "nan":
                values.append(str(val))
        if values:
            print(f'Item {idx-24}: {" | ".join(values)}')

# Look for tag codes in row 21
print("\n=== TAG CODES ===")
row_21 = df.iloc[21]
tag_codes = []
for val in row_21.values:
    if pd.notna(val) and "TAG" in str(val).upper():
        tag_codes.append(str(val))
print("Found tag codes:", tag_codes)

# Extract customer and invoice details
print("\n=== INVOICE DETAILS ===")
for idx in range(10):
    row = df.iloc[idx]
    row_values = []
    for val in row.values:
        if pd.notna(val):
            row_values.append(str(val))
    row_str = " ".join(row_values)
    if any(keyword in row_str for keyword in ["P.I. No.", "Date", "Customer"]):
        print(f"{row_str}")

# Save as JSON for attachment processing
import json

order_data = {"invoice_number": "1032-2025-26", "customer": "NAIR", "items": []}

# Extract items
for idx in range(25, 30):
    if idx < len(df):
        row = df.iloc[idx]
        if pd.notna(row[1]) and pd.notna(row[2]):  # Has description and qty
            item = {
                "description": str(row[1]),
                "quantity": int(row[2]) if pd.notna(row[2]) else 0,
                "rate": float(row[3]) if pd.notna(row[3]) else 0.0,
                "amount": float(row[5]) if pd.notna(row[5]) else 0.0,
            }
            order_data["items"].append(item)

print("\n=== EXTRACTED ORDER DATA ===")
print(json.dumps(order_data, indent=2))
