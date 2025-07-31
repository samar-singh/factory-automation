#!/usr/bin/env python3
"""Test Gmail integration with service account"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_gmail_connection(user_email):
    """Test if we can connect to Gmail"""
    
    print(f"Testing Gmail connection for: {user_email}")
    
    try:
        # Load service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            'gmail_credentials.json',
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        
        # Delegate to user's email
        delegated_credentials = credentials.with_subject(user_email)
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=delegated_credentials)
        
        # Try to list messages
        results = service.users().messages().list(
            userId='me',
            maxResults=5
        ).execute()
        
        messages = results.get('messages', [])
        print(f"\n✓ Successfully connected to Gmail!")
        print(f"Found {len(messages)} recent messages")
        
        # Get details of first message
        if messages:
            msg = service.users().messages().get(
                userId='me',
                id=messages[0]['id']
            ).execute()
            
            # Extract headers
            headers = {}
            for header in msg['payload'].get('headers', []):
                if header['name'] in ['From', 'Subject', 'Date']:
                    headers[header['name']] = header['value']
            
            print("\nMost recent email:")
            print(f"From: {headers.get('From', 'N/A')}")
            print(f"Subject: {headers.get('Subject', 'N/A')}")
            print(f"Date: {headers.get('Date', 'N/A')}")
        
        return True
        
    except HttpError as error:
        print(f"\n✗ Gmail API Error: {error}")
        print("\nPossible issues:")
        print("1. Service account needs domain-wide delegation enabled")
        print("2. User email needs to be in the same domain")
        print("3. Scopes need to be authorized in Google Workspace admin")
        return False
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

def main():
    print("="*70)
    print("GMAIL SERVICE ACCOUNT TEST")
    print("="*70)
    
    print("\nThis test requires:")
    print("1. A Google Workspace domain")
    print("2. Service account with domain-wide delegation")
    print("3. Authorized scopes in Admin console")
    
    email = input("\nEnter email address to test (or press Enter to skip): ").strip()
    
    if email and '@' in email:
        test_gmail_connection(email)
    else:
        print("\nSkipping Gmail test.")
        print("\nTo test Gmail integration, you need to:")
        print("1. Enable domain-wide delegation for the service account")
        print("2. Add the service account client ID to Google Workspace admin")
        print("3. Authorize the Gmail scope")

if __name__ == "__main__":
    main()