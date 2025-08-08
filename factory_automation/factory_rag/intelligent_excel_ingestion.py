"""Intelligent Excel ingestion with automatic header detection and mapping"""

import base64
import hashlib
import io
import logging
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient
from ..factory_database.image_storage import ImageStorageManager
from .embeddings_config import EmbeddingsManager

logger = logging.getLogger(__name__)


class IntelligentExcelIngestion:
    """Smart Excel ingestion that automatically detects and maps columns"""
    
    def __init__(
        self,
        chroma_client: Optional[ChromaDBClient] = None,
        embedding_model: Optional[str] = None,
        use_vision_model: Optional[bool] = None,
        use_clip_embeddings: Optional[bool] = None,
    ):
        """Initialize intelligent ingestion system
        
        Args:
            chroma_client: ChromaDB client instance
            embedding_model: Embedding model to use (defaults to config)
            use_vision_model: Enable vision model (defaults to config)
            use_clip_embeddings: Enable CLIP embeddings (defaults to config)
        """
        # Load from config if not specified
        rag_config = settings.get_rag_config()
        model_config = settings.get_model_config()
        
        self.chroma_client = chroma_client or ChromaDBClient()
        self.embedding_model = embedding_model or model_config.get("text_embedding", "all-MiniLM-L6-v2")
        self.use_vision_model = use_vision_model if use_vision_model is not None else rag_config.get("use_vision_model", False)
        self.use_clip_embeddings = use_clip_embeddings if use_clip_embeddings is not None else rag_config.get("use_clip_embeddings", True)
        
        # Initialize embeddings manager
        logger.info(f"Initializing {self.embedding_model} embeddings on cpu")
        self.embeddings = EmbeddingsManager(self.embedding_model, device="cpu")
        
        # Initialize image storage manager
        self.image_storage = ImageStorageManager()
        logger.info("Image storage manager initialized")
        
        # Initialize CLIP for image embeddings if enabled
        self.clip_model = None
        self.clip_preprocess = None
        if use_clip_embeddings:
            try:
                import clip
                import torch
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                clip_model_name = model_config.get("image_embedding", "ViT-B/32")
                self.clip_model, self.clip_preprocess = clip.load(clip_model_name, device=device)
                self.clip_device = device
                logger.info(f"CLIP model {clip_model_name} loaded on {device}")
            except Exception as e:
                logger.warning(f"Could not initialize CLIP: {e}")
                self.use_clip_embeddings = False
        
        # Vision model for image analysis (if enabled)
        self.vision_engine = None
        if use_vision_model:
            try:
                from ..factory_models.multimodal_search import MultimodalSearchEngine
                self.vision_engine = MultimodalSearchEngine()
                logger.info("Vision model initialized for image analysis")
            except Exception as e:
                logger.warning(f"Could not initialize vision model: {e}")
        
        # This will store learned column mappings across files
        self.column_patterns = {
            'item_code': [],
            'item_name': [],
            'quantity': [],
            'image': [],
            'brand': [],
            'color': [],
            'material': [],
            'price': [],
            'category': []
        }
        
        # Semantic understanding of column types
        self.column_keywords = {
            'item_code': ['code', 'id', 'sku', 'item', 'product', 'ref', 'number', 's.no', 'sno', 'serial'],
            'item_name': ['name', 'description', 'title', 'product', 'item', 'desc', 'tag'],
            'quantity': ['qty', 'quantity', 'stock', 'available', 'inventory', 'count', 'units'],
            'image': ['image', 'img', 'photo', 'picture', 'pic'],
            'brand': ['brand', 'manufacturer', 'company', 'maker'],
            'color': ['color', 'colour', 'shade'],
            'material': ['material', 'fabric', 'type', 'composition'],
            'price': ['price', 'cost', 'rate', 'amount', 'value'],
            'category': ['category', 'type', 'class', 'group']
        }
    
    def detect_header_row(self, df: pd.DataFrame) -> int:
        """Intelligently detect which row contains the headers"""
        
        # Check each of the first 5 rows for header-like content
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            
            # Count how many cells look like headers (text, not numbers)
            header_like = 0
            for val in row:
                if pd.notna(val):
                    val_str = str(val).lower().strip()
                    # Check if it matches any known column keywords
                    for col_type, keywords in self.column_keywords.items():
                        if any(kw in val_str for kw in keywords):
                            header_like += 1
                            break
            
            # If most cells look like headers, this is likely the header row
            if header_like >= len(row) * 0.3:  # At least 30% match
                logger.info(f"Detected header row at index {i}")
                return i
        
        # Default to first row
        return 0
    
    def identify_column_type(self, column_name: str, sample_values: List) -> str:
        """Identify what type of data a column contains based on name and values"""
        
        col_lower = str(column_name).lower().strip()
        
        # First try to match by column name
        for col_type, keywords in self.column_keywords.items():
            if any(keyword in col_lower for keyword in keywords):
                return col_type
        
        # If no name match, analyze the data
        if sample_values:
            # Check if mostly numbers (could be quantity or price)
            numeric_count = sum(1 for v in sample_values[:10] if pd.notna(v) and str(v).replace('.', '').isdigit())
            if numeric_count > len(sample_values[:10]) * 0.7:
                # Likely quantity if integers, price if decimals
                has_decimals = any('.' in str(v) for v in sample_values[:10] if pd.notna(v))
                return 'price' if has_decimals else 'quantity'
        
        return 'other'
    
    def extract_embedded_images(self, excel_file: str) -> Dict[int, Dict]:
        """Extract embedded images from Excel and map to rows"""
        images_by_row = {}
        
        try:
            with zipfile.ZipFile(excel_file, 'r') as zip_ref:
                # Find all media files
                media_files = [f for f in zip_ref.namelist() if 'xl/media/' in f]
                
                if media_files:
                    logger.info(f"Found {len(media_files)} embedded images in {excel_file}")
                    
                    # Try to load workbook to get image positions
                    try:
                        import openpyxl
                        wb = openpyxl.load_workbook(excel_file)
                        ws = wb.active
                        
                        # Map images to their row positions
                        if hasattr(ws, '_images') and ws._images:
                            for idx, img in enumerate(ws._images):
                                if hasattr(img, 'anchor') and hasattr(img.anchor, '_from'):
                                    row = img.anchor._from.row + 1  # 1-based indexing
                                    
                                    # Get the actual image data
                                    if idx < len(media_files):
                                        image_data = zip_ref.read(media_files[idx])
                                        base64_data = base64.b64encode(image_data).decode('utf-8')
                                        
                                        images_by_row[row] = {
                                            'base64': base64_data,
                                            'filename': os.path.basename(media_files[idx]),
                                            'row': row
                                        }
                                        logger.debug(f"Mapped image to row {row}")
                        
                        wb.close()
                        
                    except Exception as e:
                        logger.warning(f"Could not map image positions: {e}")
                        # Fall back to sequential mapping
                        for idx, media_file in enumerate(media_files):
                            image_data = zip_ref.read(media_file)
                            base64_data = base64.b64encode(image_data).decode('utf-8')
                            
                            # Estimate row based on image index
                            estimated_row = 2 + idx  # Start from row 2 (after header)
                            images_by_row[estimated_row] = {
                                'base64': base64_data,
                                'filename': os.path.basename(media_file),
                                'row': estimated_row
                            }
                
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
        
        return images_by_row
    
    def generate_clip_embedding(self, base64_image: str) -> Optional[List[float]]:
        """Generate CLIP embedding from base64 image
        
        Args:
            base64_image: Base64 encoded image string
            
        Returns:
            CLIP embedding as list of floats, or None if failed
        """
        if not self.clip_model or not base64_image:
            return None
        
        try:
            import torch
            from PIL import Image as PILImage
            
            # Decode base64 to PIL Image
            image_data = base64.b64decode(base64_image)
            image = PILImage.open(io.BytesIO(image_data))
            
            # Preprocess and encode with CLIP
            image_input = self.clip_preprocess(image).unsqueeze(0).to(self.clip_device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                # Convert to list
                embedding = image_features.cpu().numpy()[0].tolist()
            
            return embedding
            
        except Exception as e:
            logger.warning(f"Error generating CLIP embedding: {e}")
            return None
    
    def generate_tag_name_from_image(self, image_data: Dict, brand: str = "") -> str:
        """Use vision model to generate tag name from image"""
        if not self.vision_engine or not image_data:
            return ""
        
        try:
            prompt = f"""Analyze this product tag image from {brand} and provide:
            1. The tag name or product description visible in the image
            2. Any product code or SKU visible
            3. The type of tag (e.g., price tag, size label, brand tag)
            
            Respond with just the tag name/description in a few words."""
            
            # Analyze using vision model
            analysis = self.vision_engine.analyze_tag_image(
                image_base64=image_data['base64'],
                custom_prompt=prompt
            )
            
            if analysis and 'description' in analysis:
                desc = analysis['description']
                tag_name = desc.split('\n')[0] if '\n' in desc else desc
                tag_name = tag_name.strip()[:100]  # Limit length
                logger.info(f"Generated tag name from image: {tag_name}")
                return tag_name
                
        except Exception as e:
            logger.warning(f"Could not generate tag name from image: {e}")
        
        return ""
    
    def handle_size_variations(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """Handle multiple rows for size variations of the same item"""
        
        # Find the main identifier columns
        id_cols = []
        for col, col_type in column_mapping.items():
            if col_type in ['item_code', 'item_name']:
                id_cols.append(col)
        
        if not id_cols:
            return df
        
        # Group consecutive rows with same item but different sizes
        processed_rows = []
        current_item = None
        size_rows = []
        
        for idx, row in df.iterrows():
            # Check if this is a size variation row (has size but no name)
            has_size = False
            for col in df.columns:
                if 'size' in str(col).lower() and pd.notna(row[col]):
                    has_size = True
                    break
            
            has_identifier = any(pd.notna(row.get(col)) for col in id_cols)
            
            if has_identifier:
                # New item found - process any accumulated size rows first
                if current_item is not None and size_rows:
                    combined = self._combine_size_rows(current_item, size_rows, df.columns)
                    processed_rows[-1] = combined  # Replace last item with combined
                    size_rows = []
                
                current_item = row
                processed_rows.append(row.to_dict())
                
            elif has_size and current_item is not None:
                # This is a size variation of the current item
                size_rows.append(row)
            else:
                # Standalone row or continuation
                processed_rows.append(row.to_dict())
        
        # Process any remaining size rows
        if current_item is not None and size_rows:
            combined = self._combine_size_rows(current_item, size_rows, df.columns)
            processed_rows[-1] = combined
        
        return pd.DataFrame(processed_rows)
    
    def _combine_size_rows(self, main_row: pd.Series, size_rows: List[pd.Series], columns) -> Dict:
        """Combine main item row with its size variations"""
        combined = main_row.to_dict() if hasattr(main_row, 'to_dict') else dict(main_row)
        
        # Collect all sizes and quantities
        sizes = []
        quantities = []
        
        # Find size and quantity columns
        size_cols = [c for c in columns if 'size' in str(c).lower()]
        qty_cols = [c for c in columns if any(q in str(c).lower() for q in ['qty', 'quantity'])]
        
        # Add main row size if exists
        for size_col in size_cols:
            if pd.notna(combined.get(size_col)):
                sizes.append(str(combined[size_col]))
        
        for qty_col in qty_cols:
            if pd.notna(combined.get(qty_col)):
                quantities.append(float(combined[qty_col]) if str(combined[qty_col]).replace('.','').isdigit() else 0)
        
        # Add size variations
        for size_row in size_rows:
            for size_col in size_cols:
                if pd.notna(size_row.get(size_col)):
                    sizes.append(str(size_row[size_col]))
            
            for qty_col in qty_cols:
                if pd.notna(size_row.get(qty_col)):
                    val = size_row[qty_col]
                    quantities.append(float(val) if str(val).replace('.','').isdigit() else 0)
        
        # Update combined row
        if sizes:
            combined['all_sizes'] = ', '.join(sizes)
            combined['size_count'] = len(sizes)
        
        if quantities:
            combined['total_quantity'] = sum(quantities)
        
        return combined
    
    def read_excel_intelligently(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """Read Excel file and automatically detect structure"""
        
        logger.info(f"Intelligently reading: {file_path}")
        
        # First read to detect structure
        df_raw = pd.read_excel(file_path, header=None)
        
        # Detect header row
        header_row = self.detect_header_row(df_raw)
        
        # Re-read with correct header
        if header_row > 0:
            df = pd.read_excel(file_path, header=header_row)
        else:
            df = pd.read_excel(file_path)
        
        # Now map columns to our standard types
        column_mapping = {}
        
        for col in df.columns:
            if 'Unnamed' not in str(col):  # Skip unnamed columns
                col_type = self.identify_column_type(col, df[col].tolist())
                if col_type != 'other':
                    column_mapping[col] = col_type
                    # Learn this pattern for future use
                    if str(col).lower() not in self.column_patterns[col_type]:
                        self.column_patterns[col_type].append(str(col).lower())
        
        logger.info(f"Detected column mapping: {column_mapping}")
        return df, column_mapping
    
    def create_searchable_text(self, row_data: Dict[str, Any], file_brand: str) -> str:
        """Create rich searchable text from row data"""
        
        parts = []
        
        # Brand (from filename or data)
        brand = row_data.get('brand', file_brand)
        if brand:
            parts.append(f"Brand: {brand}")
        
        # Item name/description (most important)
        if row_data.get('item_name'):
            name = str(row_data['item_name']).strip()
            parts.append(name)
            parts.append(f"Product: {name}")
            
            # Extract features from name
            name_lower = name.lower()
            
            # Material detection
            materials = ['cotton', 'polyester', 'silk', 'wool', 'leather', 'satin', 'paper', 'plastic']
            found_materials = [m for m in materials if m in name_lower]
            if found_materials:
                parts.append(f"Material: {', '.join(found_materials)}")
            
            # Color detection
            colors = ['black', 'white', 'blue', 'red', 'green', 'yellow', 'gold', 'silver', 'brown']
            found_colors = [c for c in colors if c in name_lower]
            if found_colors:
                parts.append(f"Color: {', '.join(found_colors)}")
            
            # Type detection
            if 'tag' in name_lower:
                parts.append("Type: tag")
            if 'thread' in name_lower:
                parts.append("Type: thread")
            if 'label' in name_lower:
                parts.append("Type: label")
        
        # Item code
        if row_data.get('item_code'):
            code = str(row_data['item_code']).strip()
            if code and code.lower() not in ['nan', 'none', 'n/a']:
                parts.append(f"Code: {code}")
                parts.append(f"SKU: {code}")
        
        # Quantity/Stock
        if row_data.get('quantity') is not None:
            qty = row_data['quantity']
            if pd.notna(qty) and str(qty).replace('.', '').isdigit():
                qty_int = int(float(qty))
                parts.append(f"Stock: {qty_int} units")
                if qty_int > 0:
                    parts.append("In stock")
                    parts.append("Available")
                else:
                    parts.append("Out of stock")
        
        # Additional mapped fields
        for field in ['color', 'material', 'category']:
            if row_data.get(field):
                value = str(row_data[field]).strip()
                if value and value.lower() not in ['nan', 'none', 'n/a']:
                    parts.append(f"{field.capitalize()}: {value}")
        
        # Create natural language description
        if row_data.get('item_name') and brand:
            natural = f"This is a {brand} product: {row_data['item_name']}"
            if row_data.get('item_code'):
                natural += f" with code {row_data['item_code']}"
            parts.append(natural)
        
        return " | ".join(parts)
    
    def ingest_excel_file(self, file_path: str, batch_size: int = 50) -> Dict[str, Any]:
        """Ingest a single Excel file with intelligent mapping and image extraction"""
        
        try:
            # Extract brand from filename
            filename = os.path.basename(file_path)
            brand = filename.split('.')[0].upper()
            brand = re.sub(r'STOCK.*|20\d{2}', '', brand).strip()
            
            logger.info(f"Processing {filename} for brand: {brand}")
            
            # Extract embedded images first
            images_by_row = self.extract_embedded_images(file_path)
            logger.info(f"Extracted {len(images_by_row)} embedded images")
            
            # Read Excel intelligently
            df, column_mapping = self.read_excel_intelligently(file_path)
            
            if df.empty or not column_mapping:
                logger.warning(f"No valid data or columns found in {file_path}")
                return {
                    "status": "error",
                    "file": file_path,
                    "error": "No valid data or columns detected"
                }
            
            # Handle size variations
            df = self.handle_size_variations(df, column_mapping)
            
            # Process rows
            documents = []
            metadatas = []
            ids = []
            items_with_images = 0
            items_with_generated_names = 0
            rows_recovered = 0
            
            for idx, row in df.iterrows():
                # Map row data to standard fields
                row_data = {'brand': brand}
                for col, col_type in column_mapping.items():
                    if col in row and pd.notna(row[col]):
                        row_data[col_type] = row[col]
                
                # Add combined size data if available
                if 'all_sizes' in row and pd.notna(row.get('all_sizes')):
                    row_data['sizes'] = row['all_sizes']
                if 'total_quantity' in row and pd.notna(row.get('total_quantity')):
                    row_data['quantity'] = row['total_quantity']
                
                # Check if row has an associated image
                excel_row = idx + 2  # Assuming header at row 1
                image_data = images_by_row.get(excel_row)
                
                # Handle missing tag name
                if not row_data.get('item_name') or str(row_data.get('item_name')).strip() == '':
                    # Try to recover the row using other data
                    if row_data.get('item_code'):
                        # Use item code as fallback name
                        row_data['item_name'] = f"{brand} Item {row_data['item_code']}"
                        row_data['name_source'] = 'code_fallback'
                        rows_recovered += 1
                        logger.debug(f"Recovered row {idx} using item code")
                    elif image_data and self.vision_engine:
                        # Try to generate tag name from image
                        generated_name = self.generate_tag_name_from_image(image_data, brand)
                        if generated_name:
                            row_data['item_name'] = generated_name
                            row_data['name_source'] = 'image_analysis'
                            items_with_generated_names += 1
                            rows_recovered += 1
                            logger.info(f"Generated tag name for row {idx}: {generated_name}")
                    elif row_data.get('quantity'):
                        # If has quantity but no name, create generic entry
                        row_data['item_name'] = f"{brand} Unidentified Item (Row {idx})"
                        row_data['name_source'] = 'quantity_fallback'
                        rows_recovered += 1
                    
                    # If still no name, skip this row
                    if not row_data.get('item_name'):
                        logger.debug(f"Skipping row {idx} - no recoverable data")
                        continue
                
                # Create searchable text
                text = self.create_searchable_text(row_data, brand)
                
                # Create metadata
                metadata = {
                    'brand': brand,
                    'source_file': filename,
                    'row_index': idx,
                    'excel_row': excel_row
                }
                
                # Add mapped fields to metadata
                for field in ['item_code', 'item_name', 'quantity', 'color', 'material', 'category', 'sizes']:
                    if row_data.get(field):
                        metadata[field] = str(row_data[field])
                
                # Handle image data if available
                if image_data:
                    # Generate unique image ID
                    image_id = self.image_storage.generate_image_id(
                        image_data['base64'], idx, brand
                    )
                    
                    # Generate CLIP embedding for the image
                    clip_embedding = None
                    if self.use_clip_embeddings:
                        clip_embedding = self.generate_clip_embedding(image_data['base64'])
                        if clip_embedding:
                            logger.debug(f"Generated CLIP embedding for row {idx}")
                    
                    # Store full image with embedding
                    image_stored = self.image_storage.store_image(
                        image_id=image_id,
                        base64_data=image_data['base64'],
                        metadata={
                            'brand': brand,
                            'item_name': row_data.get('item_name', ''),
                            'item_code': row_data.get('item_code', ''),
                            'source_file': filename,
                            'excel_row': excel_row,
                            'row_index': idx
                        },
                        embedding=clip_embedding,
                        text_description=text
                    )
                    
                    if image_stored:
                        # Store reference to image in main metadata
                        metadata['has_image'] = True
                        metadata['image_id'] = image_id
                        metadata['has_clip_embedding'] = clip_embedding is not None
                        items_with_images += 1
                        logger.debug(f"Stored full image for row {idx} with ID: {image_id}")
                    else:
                        logger.warning(f"Failed to store image for row {idx}")
                
                # Add name source if generated/recovered
                if row_data.get('name_source'):
                    metadata['name_source'] = row_data['name_source']
                
                # Create unique ID
                doc_id = f"{brand}_{idx}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
                
                documents.append(text)
                metadatas.append(metadata)
                ids.append(doc_id)
            
            if not documents:
                logger.warning(f"No valid items found in {file_path}")
                return {
                    "status": "error",
                    "file": file_path,
                    "error": "No valid items to ingest"
                }
            
            # Batch process embeddings and add to ChromaDB
            total_added = 0
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_meta = metadatas[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                
                # Create embeddings
                embeddings = self.embeddings.encode_documents(batch_docs)
                
                # Add to ChromaDB
                self.chroma_client.collection.add(
                    embeddings=embeddings.tolist(),
                    documents=batch_docs,
                    metadatas=batch_meta,
                    ids=batch_ids
                )
                
                total_added += len(batch_docs)
                logger.info(f"Added batch {i//batch_size + 1}, total: {total_added}/{len(documents)}")
            
            logger.info(f"Successfully ingested {total_added} items from {file_path}")
            logger.info(f"  - Items with images: {items_with_images}")
            logger.info(f"  - Items with generated names: {items_with_generated_names}")
            logger.info(f"  - Rows recovered: {rows_recovered}")
            
            return {
                "status": "success",
                "file": file_path,
                "items_ingested": total_added,
                "items_with_images": items_with_images,
                "items_with_generated_names": items_with_generated_names,
                "rows_recovered": rows_recovered,
                "column_mapping": column_mapping,
                "brand": brand
            }
            
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "file": file_path,
                "error": str(e)
            }
    
    def ingest_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        """Ingest all Excel files in a folder"""
        
        results = []
        excel_files = list(Path(folder_path).glob("*.xlsx")) + list(Path(folder_path).glob("*.xls"))
        
        logger.info(f"Found {len(excel_files)} Excel files to ingest")
        
        for file_path in excel_files:
            result = self.ingest_excel_file(str(file_path))
            results.append(result)
            
            # Log learned patterns
            logger.info(f"Learned column patterns so far: {self.column_patterns}")
        
        return results
    
    def get_learned_mappings(self) -> Dict[str, List[str]]:
        """Get the column patterns learned across all files"""
        return self.column_patterns