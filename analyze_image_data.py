#!/usr/bin/env python3
"""Analyze image data in Excel files"""

import pandas as pd
import warnings
warnings.filterwarnings('ignore')

print('=== IMAGE DATA INVESTIGATION ===\n')

# Check Peter England file
df = pd.read_excel('inventory/PETER ENGLAND STOCK 2026.xlsx', header=1)

print('1. PETER ENGLAND - TAGIMAGE Column Analysis:')
print('-' * 50)

# Check what's actually in the TAGIMAGE column
tagimage_values = df['TAGIMAGE'].value_counts(dropna=False)
print(f'Total rows: {len(df)}')
print(f'TAGIMAGE column unique values: {len(tagimage_values)}')
print('\nValue distribution:')
for value, count in tagimage_values.items():
    if pd.isna(value):
        print(f'  - NaN/Empty: {count} rows')
    else:
        # Show first 50 chars of the value
        value_str = str(value)[:50]
        print(f'  - "{value_str}": {count} rows')

# Check data types
print(f'\nTAGIMAGE column dtype: {df["TAGIMAGE"].dtype}')

# Sample non-null values
non_null_images = df[df['TAGIMAGE'].notna()]['TAGIMAGE']
if len(non_null_images) > 0:
    print('\nSample non-null TAGIMAGE values:')
    for idx, val in non_null_images.head(5).items():
        print(f'  Row {idx}: "{val}" (type: {type(val).__name__}, length: {len(str(val))})')

print('\n2. CHECKING OTHER FILES FOR IMAGE PATTERNS:')
print('-' * 50)

# Check other files
files_to_check = [
    ('inventory/MYNTRA STOCK 2026.xlsx', 0, 'TAG IMAGES'),
    ('inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx', 0, 'TAGS IMAGE'),
    ('inventory/THREAD 2.xlsx', 1, 'THREAD IMAGE'),
    ('inventory/AMAZON STOCK 2026.xlsx', 0, ' Image'),
    ('inventory/FM STOCK 2026.xlsx', 0, 'TRIM IMAGE'),
]

for file_path, header_row, img_col in files_to_check:
    try:
        df_check = pd.read_excel(file_path, header=header_row)
        if img_col in df_check.columns:
            non_empty = df_check[img_col].notna() & (df_check[img_col] != '')
            non_empty_count = non_empty.sum()
            print(f'\n{file_path.split("/")[-1]}:')
            print(f'  - Image column: "{img_col}"')
            print(f'  - Non-empty values: {non_empty_count}/{len(df_check)} ({non_empty_count/len(df_check)*100:.1f}%)')
            
            # Show sample values
            if non_empty_count > 0:
                # Get first 3 non-empty values
                samples = df_check[non_empty][img_col].head(3)
                print('  - Sample values:')
                for i, sample in enumerate(samples, 1):
                    sample_str = str(sample)
                    if len(sample_str) > 100:
                        # Might be base64 or embedded image
                        print(f'    {i}. Length: {len(sample_str)} chars')
                        print(f'       First 80 chars: {sample_str[:80]}...')
                        # Check if it's base64
                        if sample_str.startswith('data:image') or 'base64' in sample_str[:100]:
                            print('       Type: Base64 encoded image')
                        elif sample_str.startswith('=IMAGE') or sample_str.startswith('=EMBED'):
                            print('       Type: Excel formula/embedded object')
                        else:
                            print('       Type: Unknown long string')
                    else:
                        print(f'    {i}. "{sample_str}"')
                        if '.jpg' in sample_str.lower() or '.png' in sample_str.lower() or '.jpeg' in sample_str.lower():
                            print('       Type: Image filename/path')
                        elif sample_str.strip().upper() in ['Y', 'YES', 'TRUE', '1', 'V', 'X']:
                            print('       Type: Boolean indicator (has image)')
                        else:
                            print('       Type: Text reference or code')
        else:
            print(f'\n{file_path.split("/")[-1]}: No column named "{img_col}"')
    except Exception as e:
        print(f'{file_path.split("/")[-1]}: Error - {str(e)[:100]}')

print('\n3. SUMMARY OF IMAGE DATA FINDINGS:')
print('-' * 50)

# Count files with actual image data
files_with_images = 0
files_checked = 0

for file_path, header_row, img_col in files_to_check:
    try:
        df_check = pd.read_excel(file_path, header=header_row)
        files_checked += 1
        if img_col in df_check.columns:
            non_empty = df_check[img_col].notna() & (df_check[img_col] != '')
            if non_empty.sum() > 0:
                # Check if it's actual image data or just indicators
                sample = str(df_check[non_empty][img_col].iloc[0])
                if len(sample) > 100 or '.jpg' in sample.lower() or '.png' in sample.lower():
                    files_with_images += 1
    except:
        pass

print(f'Files with potential image data: {files_with_images}/{files_checked}')
print('\nConclusions:')
print('- Most "IMAGE" columns contain single characters like "V", "Y" or are empty')
print('- These appear to be boolean indicators (V = has image, empty = no image)')
print('- Actual image files are likely stored separately, not embedded in Excel')
print('- The indicators suggest which items have associated image files elsewhere')

print('\n4. RECOMMENDATION:')
print('-' * 50)
print('For rows without TAGNAME but with image indicators:')
print('1. The "V" or "Y" values indicate an image exists somewhere')
print('2. We would need access to the actual image files (likely in a separate folder)')
print('3. Image filenames might follow pattern: {TAG_CODE}.jpg or {Brand}_{Code}.png')
print('4. Without actual image files, vision models cannot help with recovery')