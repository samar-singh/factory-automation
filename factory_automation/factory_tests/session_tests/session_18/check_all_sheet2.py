#!/usr/bin/env python3
"""Check all Excel files for Sheet2 data"""

import pandas as pd
from pathlib import Path

def check_all_excel_files():
    """Check all Excel files for Sheet2 and analyze data"""
    
    inventory_dir = Path('/Users/samarsingh/Factory_flow_Automation/inventory')
    excel_files = [f for f in inventory_dir.glob('*.xlsx') if not f.name.startswith('~$')]
    
    print(f"Found {len(excel_files)} Excel files\n")
    print("="*70)
    
    files_with_sheet2 = []
    
    for file_path in excel_files:
        print(f"\n📁 {file_path.name}")
        print("-"*50)
        
        try:
            # Check available sheets
            xl_file = pd.ExcelFile(file_path)
            sheets = xl_file.sheet_names
            print(f"Sheets: {sheets}")
            
            if 'Sheet2' in sheets:
                files_with_sheet2.append(file_path.name)
                # Read Sheet2
                df = pd.read_excel(file_path, sheet_name='Sheet2', header=0)
                
                # Check for merged cells by looking for NaN values in key columns
                if 'TRIM NAME' in df.columns:
                    nan_count = df['TRIM NAME'].isna().sum()
                    total_rows = len(df)
                    print(f"  ✅ Has Sheet2 with {total_rows} rows")
                    print(f"  📊 TRIM NAME column: {nan_count} NaN values (likely merged cells)")
                    
                    # Sample first few non-null items
                    non_null = df[df['TRIM NAME'].notna()]['TRIM NAME'].head(3).tolist()
                    if non_null:
                        print(f"  📝 Sample items: {', '.join(str(x) for x in non_null[:3])}")
                else:
                    print("  ✅ Has Sheet2 but no TRIM NAME column")
                    print(f"  📊 Columns: {list(df.columns)[:5]}...")
            else:
                print("  ❌ No Sheet2 found")
                
        except Exception as e:
            print(f"  ⚠️ Error reading file: {e}")
    
    print("\n" + "="*70)
    print("\n📊 Summary:")
    print(f"Total Excel files: {len(excel_files)}")
    print(f"Files with Sheet2: {len(files_with_sheet2)}")
    
    if files_with_sheet2:
        print("\n📋 Files that need Sheet2 ingestion:")
        for idx, file_name in enumerate(files_with_sheet2, 1):
            print(f"  {idx}. {file_name}")
    
    return files_with_sheet2

if __name__ == "__main__":
    files_with_sheet2 = check_all_excel_files()