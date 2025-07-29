#!/usr/bin/env python3
"""Create sample inventory data with images for testing - simplified version."""

import os
import json
import asyncio
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Sample tag data
SAMPLE_TAGS = [
    {
        "tag_code": "BLU-CTN-23",
        "description": "Blue Cotton Tag 2x3 inches",
        "size": "2x3",
        "color": "blue",
        "material": "cotton",
        "price": 5.50,
        "stock": 1000
    },
    {
        "tag_code": "RED-SLK-34",
        "description": "Red Silk Tag 3x4 inches",
        "size": "3x4",
        "color": "red",
        "material": "silk",
        "price": 8.75,
        "stock": 500
    },
    {
        "tag_code": "GRN-PLY-25",
        "description": "Green Polyester Tag 2x5 inches",
        "size": "2x5",
        "color": "green",
        "material": "polyester",
        "price": 6.25,
        "stock": 750
    },
    {
        "tag_code": "YLW-CTN-22",
        "description": "Yellow Cotton Tag 2x2 inches",
        "size": "2x2",
        "color": "yellow",
        "material": "cotton",
        "price": 4.50,
        "stock": 1200
    },
    {
        "tag_code": "BLK-LTH-45",
        "description": "Black Leather Tag 4x5 inches",
        "size": "4x5",
        "color": "black",
        "material": "leather",
        "price": 15.00,
        "stock": 300
    },
    {
        "tag_code": "WHT-PVC-33",
        "description": "White PVC Tag 3x3 inches",
        "size": "3x3",
        "color": "white",
        "material": "pvc",
        "price": 5.00,
        "stock": 800
    },
    {
        "tag_code": "PRP-SLK-24",
        "description": "Purple Silk Tag 2x4 inches",
        "size": "2x4",
        "color": "purple",
        "material": "silk",
        "price": 9.00,
        "stock": 400
    },
    {
        "tag_code": "ORG-CTN-35",
        "description": "Orange Cotton Tag 3x5 inches",
        "size": "3x5",
        "color": "orange",
        "material": "cotton",
        "price": 7.00,
        "stock": 600
    },
    {
        "tag_code": "BRN-LTH-23",
        "description": "Brown Leather Tag 2x3 inches",
        "size": "2x3",
        "color": "brown",
        "material": "leather",
        "price": 12.00,
        "stock": 350
    },
    {
        "tag_code": "GLD-MTL-22",
        "description": "Gold Metallic Tag 2x2 inches",
        "size": "2x2",
        "color": "gold",
        "material": "metallic",
        "price": 10.00,
        "stock": 250
    }
]

# Color mappings for tag generation
COLOR_MAP = {
    "blue": (0, 0, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "yellow": (255, 255, 0),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "purple": (128, 0, 128),
    "orange": (255, 165, 0),
    "brown": (139, 69, 19),
    "gold": (255, 215, 0)
}

def create_tag_image(tag_data, output_dir):
    """Create a simple tag image."""
    # Parse size (e.g., "2x3" -> width=2*100, height=3*100)
    width_inch, height_inch = map(int, tag_data["size"].split("x"))
    width = width_inch * 100
    height = height_inch * 100
    
    # Get color
    bg_color = COLOR_MAP.get(tag_data["color"], (200, 200, 200))
    
    # Create image
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Add border
    border_color = (0, 0, 0) if tag_data["color"] != "black" else (255, 255, 255)
    draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=3)
    
    # Add text
    text_color = (255, 255, 255) if tag_data["color"] in ["black", "blue", "purple", "brown"] else (0, 0, 0)
    
    # Try to use a default font, fallback to PIL default if not available
    try:
        font_size = min(width, height) // 10
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        font = ImageFont.load_default()
    
    # Add tag code
    draw.text((10, 10), tag_data["tag_code"], fill=text_color, font=font)
    
    # Add material
    draw.text((10, height-30), tag_data["material"].upper(), fill=text_color, font=font)
    
    # Add size in center
    size_text = tag_data["size"] + " inches"
    bbox = draw.textbbox((0, 0), size_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text(((width-text_width)//2, (height-text_height)//2), size_text, fill=text_color, font=font)
    
    # Save image
    filename = f"{tag_data['tag_code']}.png"
    filepath = output_dir / filename
    img.save(filepath)
    
    return str(filepath)

def create_sample_inventory():
    """Create sample inventory with images and load into ChromaDB."""
    print("Creating sample inventory data...")
    
    # Create images directory
    images_dir = Path("./sample_images")
    images_dir.mkdir(exist_ok=True)
    
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(
        path="./chroma_data",
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    print("✓ ChromaDB client created")
    
    # Create or get inventory collection
    collection = client.get_or_create_collection(
        name="tag_inventory",
        metadata={"hnsw:space": "cosine"}
    )
    print("✓ Inventory collection ready")
    
    # Initialize text encoder
    print("Loading text encoder...")
    text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Text encoder loaded")
    
    # Create images and add to database
    for i, tag_data in enumerate(SAMPLE_TAGS):
        print(f"\nProcessing {tag_data['tag_code']}...")
        
        # Create image
        image_path = create_tag_image(tag_data, images_dir)
        print(f"  ✓ Created image: {image_path}")
        
        # Generate text embedding
        text_desc = f"{tag_data['tag_code']} {tag_data['description']} {tag_data['material']}"
        text_embedding = text_encoder.encode(text_desc).tolist()
        
        # Add to ChromaDB
        metadata = {
            **tag_data,
            "image_path": image_path,
            "has_image": True
        }
        
        doc_id = f"tag_{tag_data['tag_code']}"
        document = f"{tag_data['tag_code']} {tag_data['description']} {tag_data['size']}"
        
        collection.add(
            documents=[document],
            embeddings=[text_embedding],
            metadatas=[metadata],
            ids=[doc_id]
        )
        print(f"  ✓ Added to database")
    
    # Get collection info
    count = collection.count()
    print(f"\n✓ Sample inventory created successfully!")
    print(f"  Total items in inventory: {count}")
    
    # Test search
    print("\nTesting search functionality...")
    test_query = "blue cotton tag"
    query_embedding = text_encoder.encode(test_query).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    
    print(f"\nSearch results for '{test_query}':")
    for i in range(len(results['ids'][0])):
        metadata = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        print(f"{i+1}. {metadata['tag_code']} - {metadata['description']}")
        print(f"   Similarity: {1 - distance:.3f}")
    
    # Save inventory data for reference
    with open("sample_inventory.json", "w") as f:
        json.dump(SAMPLE_TAGS, f, indent=2)
    print("\n✓ Saved inventory data to sample_inventory.json")

if __name__ == "__main__":
    create_sample_inventory()