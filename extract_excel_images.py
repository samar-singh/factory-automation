#!/usr/bin/env python3
"""Extract embedded images from Excel files and map them to rows"""

import os
import zipfile
from pathlib import Path
import pandas as pd
import openpyxl
import base64

def extract_images_from_excel(excel_file, output_dir="extracted_images"):
    """Extract all embedded images from an Excel file"""
    
    print(f"Extracting images from: {excel_file}")
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    brand = Path(excel_file).stem.split(" STOCK")[0]
    brand_dir = Path(output_dir) / brand
    brand_dir.mkdir(exist_ok=True)
    
    extracted_images = []
    
    # Extract images from Excel ZIP structure
    try:
        with zipfile.ZipFile(excel_file, 'r') as zip_ref:
            # Find all media files
            media_files = [f for f in zip_ref.namelist() if 'xl/media/' in f]
            
            print(f"Found {len(media_files)} embedded images")
            
            for media_file in media_files:
                # Extract image
                image_data = zip_ref.read(media_file)
                
                # Get image filename
                image_name = os.path.basename(media_file)
                output_path = brand_dir / image_name
                
                # Save image
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                
                # Convert to base64 for storage
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                extracted_images.append({
                    'filename': image_name,
                    'path': str(output_path),
                    'base64': base64_data[:100] + '...',  # Store sample
                    'size': len(image_data)
                })
                
                print(f"  - Extracted: {image_name} ({len(image_data)/1024:.1f} KB)")
    
    except Exception as e:
        print(f"Error extracting images: {e}")
    
    return extracted_images

def map_images_to_rows(excel_file):
    """Try to map images to their corresponding Excel rows"""
    
    print(f"\nMapping images to rows in: {excel_file}")
    
    # Load workbook with openpyxl to access images
    wb = openpyxl.load_workbook(excel_file)
    ws = wb.active
    
    # Get image positions (which cells they're anchored to)
    image_positions = []
    
    if hasattr(ws, '_images') and ws._images:
        for idx, img in enumerate(ws._images):
            # Images have anchor information
            if hasattr(img, 'anchor'):
                anchor = img.anchor
                # Get the cell reference
                if hasattr(anchor, '_from'):
                    from_cell = anchor._from
                    row = from_cell.row + 1  # Convert to 1-based
                    col = from_cell.col + 1
                    
                    # Convert column number to letter
                    col_letter = openpyxl.utils.get_column_letter(col)
                    cell_ref = f"{col_letter}{row}"
                    
                    image_positions.append({
                        'image_index': idx,
                        'row': row,
                        'column': col,
                        'cell': cell_ref
                    })
                    
                    print(f"  - Image {idx} anchored at cell {cell_ref} (row {row})")
    
    # Now load with pandas to get the data
    df = pd.read_excel(excel_file, header=1)
    
    # Map image positions to DataFrame rows
    print("\nMapping to DataFrame (header at row 1, so data starts at row 2):")
    for pos in image_positions[:10]:  # Show first 10
        df_row = pos['row'] - 2  # Adjust for header position
        if 0 <= df_row < len(df):
            row_data = df.iloc[df_row]
            tagname = row_data.get('TAGNAME', 'N/A')
            tag_code = row_data.get('TAG CODE', 'N/A')
            qty = row_data.get('QTY', 'N/A')
            
            print(f"  Row {df_row}: Image at row {pos['row']} -> TAGNAME='{tagname}', CODE='{tag_code}', QTY={qty}")
    
    return image_positions

def main():
    """Main function to extract and map images"""
    
    excel_files = [
        'inventory/PETER ENGLAND STOCK 2026.xlsx',
        'inventory/MYNTRA STOCK 2026.xlsx',
        'inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx'
    ]
    
    for excel_file in excel_files:
        if os.path.exists(excel_file):
            print("\n" + "="*60)
            print(f"Processing: {excel_file}")
            print("="*60)
            
            # Extract images
            extracted = extract_images_from_excel(excel_file)
            
            # Map to rows
            positions = map_images_to_rows(excel_file)
            
            print("\nSummary:")
            print(f"  - Extracted {len(extracted)} images")
            print(f"  - Mapped {len(positions)} image positions")

if __name__ == "__main__":
    main()