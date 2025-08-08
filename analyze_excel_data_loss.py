#!/usr/bin/env python3
"""Analyze data loss in Excel ingestion"""

import pandas as pd
import warnings
warnings.filterwarnings('ignore')

print('=== DATA LOSS & RECOVERY ANALYSIS ===\n')

# Analyze Peter England file
df = pd.read_excel('inventory/PETER ENGLAND STOCK 2026.xlsx', header=1)

print('1. CURRENT INGESTION BEHAVIOR:')
print('-' * 50)

total_rows = len(df)
has_tagname = df['TAGNAME'].notna() & (df['TAGNAME'] != '')
rows_with_tagname = df[has_tagname].copy()
rows_without_tagname = df[~has_tagname].copy()

print(f'Total rows in Excel: {total_rows}')
print(f'Rows WITH tagname: {len(rows_with_tagname)} ({len(rows_with_tagname)/total_rows*100:.1f}%)')
print(f'Rows WITHOUT tagname: {len(rows_without_tagname)} ({len(rows_without_tagname)/total_rows*100:.1f}%)')

print('\n2. DATA IN SKIPPED ROWS:')
print('-' * 50)

# Analyze what's in the skipped rows
lost_data_count = 0
for idx, row in rows_without_tagname.iterrows():
    has_data = []
    if pd.notna(row.get('TAG CODE')) and str(row.get('TAG CODE')) != '' and str(row.get('TAG CODE')) != 'nan':
        has_data.append(f"CODE={row['TAG CODE']}")
    if pd.notna(row.get('QTY')) and row.get('QTY') != 0:
        has_data.append(f"QTY={row['QTY']}")
    if pd.notna(row.get('TAGIMAGE')) and str(row.get('TAGIMAGE')) != '' and str(row.get('TAGIMAGE')) != 'nan':
        has_data.append(f"IMAGE={row['TAGIMAGE']}")
    
    if has_data:
        lost_data_count += 1
        if lost_data_count <= 5:  # Show first 5
            print(f'Row {idx}: Lost data -> {" | ".join(has_data)}')

print(f'\nTotal rows with lost data: {lost_data_count}')

print('\n3. RECOVERY POTENTIAL:')
print('-' * 50)

# Count recoverable rows
has_image = rows_without_tagname['TAGIMAGE'].notna() & (rows_without_tagname['TAGIMAGE'] != '') & (rows_without_tagname['TAGIMAGE'] != 'nan')
recoverable_by_image = rows_without_tagname[has_image]

has_code = rows_without_tagname['TAG CODE'].notna() & (rows_without_tagname['TAG CODE'] != '') & (rows_without_tagname['TAG CODE'] != 'nan')
recoverable_by_code = rows_without_tagname[has_code]

has_qty = rows_without_tagname['QTY'].notna() & (rows_without_tagname['QTY'] > 0)
recoverable_by_qty = rows_without_tagname[has_qty]

print('Rows that could be recovered:')
print(f'  - Using image analysis (QwenVL/CLIP): {len(recoverable_by_image)} rows')
print(f'  - Have TAG CODE but no name: {len(recoverable_by_code)} rows')
print(f'  - Have quantity data: {len(recoverable_by_qty)} rows')

print('\n4. SIZE VARIATION ANALYSIS:')
print('-' * 50)

# Check for duplicate tagnames (indicating size variations)
tagname_counts = df['TAGNAME'].value_counts()
duplicates = tagname_counts[tagname_counts > 1]

if len(duplicates) > 0:
    print(f'Found {len(duplicates)} items with multiple rows (likely size variations):')
    for tag, count in duplicates.head(5).items():
        if pd.notna(tag):
            print(f'\n  "{tag}": {count} variations')
            # Show the variations
            variations = df[df['TAGNAME'] == tag][['TAG CODE', 'QTY']].head(3)
            for _, var in variations.iterrows():
                code = var['TAG CODE'] if pd.notna(var['TAG CODE']) else 'No code'
                qty = var['QTY'] if pd.notna(var['QTY']) else 0
                print(f'    - CODE: {code}, QTY: {qty}')

print('\n5. IMAGE COLUMN STATUS:')
print('-' * 50)
total_images = df['TAGIMAGE'].notna() & (df['TAGIMAGE'] != '') & (df['TAGIMAGE'] != 'nan')
print(f'Rows with actual image data: {total_images.sum()} / {len(df)} ({total_images.sum()/len(df)*100:.1f}%)')

# Check other Excel files
print('\n6. PATTERN ACROSS OTHER FILES:')
print('-' * 50)

files_to_check = [
    ('inventory/MYNTRA STOCK 2026.xlsx', 0, 'TAG NAME'),
    ('inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx', 0, 'TRIM NAME'),
]

for file_path, header_row, name_col in files_to_check:
    try:
        df_check = pd.read_excel(file_path, header=header_row)
        if name_col in df_check.columns:
            empty_names = df_check[df_check[name_col].isna() | (df_check[name_col] == '')].copy()
            print(f'{file_path.split("/")[-1]}: {len(empty_names)} empty {name_col} rows out of {len(df_check)}')
    except Exception as e:
        print(f'{file_path.split("/")[-1]}: Error - {str(e)[:50]}')

print('\n' + '=' * 50)
print('ANALYSIS COMPLETE')
print('=' * 50)