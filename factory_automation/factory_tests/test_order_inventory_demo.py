#!/usr/bin/env python3
"""Demo: Email Order to Inventory Matching with RAG"""

import chromadb
from chromadb.config import Settings
from datetime import datetime

def simulate_email_orders():
    """Simulate email orders for testing"""
    return [
        {
            'customer': 'Fashion House Delhi',
            'email': 'orders@fashionhouse.com',
            'subject': 'Urgent Order - Tags Required',
            'body': '''Dear Sir/Madam,

We need the following items urgently:
- 500 VH TRS tags in size 32
- 300 FM Linen blend tags
- 200 Wotnot boys tags

Please confirm availability and send quotation.

Regards,
Fashion House'''
        },
        {
            'customer': 'Garment Exports Ltd',
            'email': 'purchase@garmentexports.com', 
            'subject': 'Tag Order for Export',
            'body': '''Hi,

Please process our order for:
- 1000 VH tags with Navy and gold font
- 400 FM Flex-knit denim tags

This is for our export order. Need delivery by next week.

Thanks'''
        }
    ]

def extract_order_lines(email_body):
    """Extract order lines from email body"""
    lines = []
    for line in email_body.split('\n'):
        line = line.strip()
        if line.startswith('-') and 'tags' in line.lower():
            lines.append(line[1:].strip())
    return lines

def search_inventory(query, collection):
    """Search inventory using ChromaDB"""
    results = collection.query(
        query_texts=[query],
        n_results=3,
        include=['documents', 'metadatas', 'distances']
    )
    
    matches = []
    if results['ids'][0]:
        for i in range(len(results['ids'][0])):
            matches.append({
                'item': results['metadatas'][0][i].get('trim_name', 'N/A'),
                'code': results['metadatas'][0][i].get('trim_code', 'N/A'),
                'brand': results['metadatas'][0][i].get('brand', 'N/A'),
                'stock': results['metadatas'][0][i].get('stock', 0),
                'score': 1 - results['distances'][0][i]
            })
    return matches

def main():
    print("="*80)
    print("FACTORY AUTOMATION: Email Order → Inventory Matching Demo")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Using: RAG with ChromaDB + all-MiniLM-L6-v2 embeddings")
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(
        path="./chroma_data",
        settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_collection("tag_inventory")
    print(f"\nInventory Database: {collection.count()} items loaded")
    
    # Process email orders
    emails = simulate_email_orders()
    
    for email_idx, email in enumerate(emails, 1):
        print(f"\n{'='*80}")
        print(f"EMAIL ORDER #{email_idx}")
        print(f"{'='*80}")
        print(f"From: {email['customer']} <{email['email']}>")
        print(f"Subject: {email['subject']}")
        print(f"\nEmail Body:")
        print("-"*40)
        print(email['body'])
        print("-"*40)
        
        # Extract order lines
        order_lines = extract_order_lines(email['body'])
        print(f"\nExtracted {len(order_lines)} order lines:")
        for line in order_lines:
            print(f"  • {line}")
        
        # Match each order line with inventory
        print(f"\n{'INVENTORY MATCHING RESULTS':^80}")
        print("="*80)
        
        order_summary = {
            'matched': 0,
            'partial': 0,
            'not_found': 0,
            'total_value': 0
        }
        
        for line_idx, order_line in enumerate(order_lines, 1):
            print(f"\n{line_idx}. Order: {order_line}")
            
            # Extract quantity if mentioned
            import re
            qty_match = re.search(r'(\d+)\s+', order_line)
            quantity_needed = int(qty_match.group(1)) if qty_match else 1
            
            # Search inventory
            matches = search_inventory(order_line, collection)
            
            if matches:
                best_match = matches[0]
                print(f"\n   Best Match Found:")
                print(f"   Item: {best_match['item']}")
                print(f"   Code: {best_match['code']}")
                print(f"   Brand: {best_match['brand']}")
                print(f"   Available Stock: {best_match['stock']} units")
                print(f"   Match Confidence: {best_match['score']:.1%}")
                
                # Check stock availability
                if best_match['stock'] >= quantity_needed:
                    status = "✓ AVAILABLE - Can fulfill order"
                    order_summary['matched'] += 1
                else:
                    status = f"⚠ INSUFFICIENT STOCK (Need {quantity_needed}, Have {best_match['stock']})"
                    order_summary['partial'] += 1
                
                print(f"   Status: {status}")
                
                # Show alternatives if score is low
                if best_match['score'] < 0.7 and len(matches) > 1:
                    print("\n   Alternative Options:")
                    for alt in matches[1:3]:
                        print(f"   - {alt['item']} (Stock: {alt['stock']}, Score: {alt['score']:.1%})")
            else:
                print("   ✗ No matching items found in inventory")
                order_summary['not_found'] += 1
        
        # Order Summary
        print(f"\n{'ORDER SUMMARY':^80}")
        print("="*80)
        print(f"Total Order Lines: {len(order_lines)}")
        print(f"Fully Matched: {order_summary['matched']} ({order_summary['matched']/len(order_lines)*100:.0f}%)")
        print(f"Partial Match: {order_summary['partial']} ({order_summary['partial']/len(order_lines)*100:.0f}%)")
        print(f"Not Found: {order_summary['not_found']} ({order_summary['not_found']/len(order_lines)*100:.0f}%)")
        
        if order_summary['matched'] == len(order_lines):
            print("\nRecommendation: ✓ AUTO-APPROVE - All items available")
        elif order_summary['not_found'] == 0:
            print("\nRecommendation: 👁 MANUAL REVIEW - Some items have insufficient stock")
        else:
            print("\nRecommendation: ⚠ MANUAL INTERVENTION - Some items not found")
    
    # System Summary
    print(f"\n{'='*80}")
    print("SYSTEM CAPABILITIES DEMONSTRATED")
    print("="*80)
    print("✓ Email parsing and order extraction")
    print("✓ Natural language order matching using RAG")
    print("✓ Stock availability checking")
    print("✓ Confidence scoring for matches")
    print("✓ Alternative suggestions for low-confidence matches")
    print("✓ Automated vs manual routing decisions")
    
    print("\nNEXT STEPS:")
    print("1. Connect Gmail API for real email polling")
    print("2. Implement Gradio dashboard for manual reviews")
    print("3. Add order confirmation and PDF generation")
    print("4. Integrate payment tracking")

if __name__ == "__main__":
    main()