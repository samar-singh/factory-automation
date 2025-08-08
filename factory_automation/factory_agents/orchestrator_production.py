"""Production Orchestrator with Real Gmail Integration"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional

from .orchestrator_v3_agentic import AgenticOrchestratorV3
from .gmail_production_agent import GmailProductionAgent
from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class ProductionOrchestrator(AgenticOrchestratorV3):
    """Production orchestrator that monitors real Gmail inbox"""
    
    def __init__(
        self, 
        chromadb_client: ChromaDBClient,
        gmail_credentials_path: Optional[str] = None,
        attachment_storage_path: Optional[str] = None,
        polling_interval: int = 60  # seconds
    ):
        """Initialize production orchestrator
        
        Args:
            chromadb_client: Vector database client
            gmail_credentials_path: Path to Gmail service account credentials
            attachment_storage_path: Where to store downloaded attachments
            polling_interval: How often to check for new emails (seconds)
        """
        # Initialize base orchestrator WITHOUT mock Gmail
        super().__init__(chromadb_client, use_mock_gmail=False)
        
        # Set up production Gmail agent
        if gmail_credentials_path and os.path.exists(gmail_credentials_path):
            self.gmail_agent = GmailProductionAgent(
                credentials_path=gmail_credentials_path,
                attachment_dir=attachment_storage_path
            )
            self.has_gmail = True
            logger.info("Production Gmail agent initialized")
        else:
            self.gmail_agent = None
            self.has_gmail = False
            logger.warning("Gmail credentials not provided - email monitoring disabled")
        
        self.polling_interval = polling_interval
        self.is_monitoring = False
        self._monitoring_task = None
    
    async def start_email_monitoring(self):
        """Start monitoring Gmail inbox for new orders"""
        if not self.has_gmail:
            logger.error("Cannot start monitoring - Gmail not configured")
            return
        
        self.is_monitoring = True
        logger.info(f"Starting Gmail monitoring (polling every {self.polling_interval} seconds)")
        
        # Start monitoring in background
        self._monitoring_task = asyncio.create_task(self._monitor_gmail())
    
    async def _monitor_gmail(self):
        """Background task to monitor Gmail"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_monitoring:
            try:
                # Fetch unread emails
                logger.debug("Checking for new emails...")
                emails = self.gmail_agent.fetch_unread_orders(max_results=5)
                
                if emails:
                    logger.info(f"Found {len(emails)} new order emails")
                    
                    # Process each email
                    for email_data in emails:
                        try:
                            logger.info(f"Processing email: {email_data['subject']}")
                            
                            # The email_data already has file paths in attachments
                            # Process using the parent orchestrator
                            result = await self.process_email(email_data)
                            
                            if result.get('success'):
                                logger.info(f"Successfully processed: {email_data['message_id']}")
                                
                                # Log what was done
                                if 'recommended_action' in result:
                                    action = result['recommended_action']
                                    logger.info(f"Action taken: {action}")
                                    
                                    # You can add notifications here
                                    if action == 'human_review':
                                        await self._notify_human_review_needed(email_data)
                                    elif action == 'auto_approve':
                                        await self._notify_auto_approved(email_data)
                            else:
                                logger.error(f"Failed to process: {email_data['message_id']}")
                                logger.error(f"Error: {result.get('error')}")
                        
                        except Exception as e:
                            logger.error(f"Error processing email {email_data['message_id']}: {e}")
                
                # Reset error counter on successful check
                consecutive_errors = 0
                
                # Clean up old attachments periodically (every 10 checks)
                if hasattr(self, '_check_count'):
                    self._check_count += 1
                    if self._check_count % 10 == 0:
                        self.gmail_agent.cleanup_old_attachments(days_old=7)
                else:
                    self._check_count = 1
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in Gmail monitoring: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"Too many consecutive errors ({consecutive_errors}), stopping monitor")
                    self.is_monitoring = False
                    break
            
            # Wait before next check
            await asyncio.sleep(self.polling_interval)
        
        logger.info("Gmail monitoring stopped")
    
    async def stop_monitoring(self):
        """Stop email monitoring"""
        self.is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring stopped")
    
    async def _notify_human_review_needed(self, email_data: Dict[str, Any]):
        """Send notification that human review is needed"""
        # In production, this could:
        # - Send a Slack message
        # - Send an email notification
        # - Update a dashboard
        # - Create a ticket in a task management system
        logger.info(f"NOTIFICATION: Human review needed for order from {email_data['from']}")
    
    async def _notify_auto_approved(self, email_data: Dict[str, Any]):
        """Send notification that order was auto-approved"""
        # In production, this could:
        # - Send confirmation email to customer
        # - Update inventory system
        # - Create production order
        logger.info(f"NOTIFICATION: Order auto-approved from {email_data['from']}")
    
    def get_attachment_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed attachments"""
        if not self.gmail_agent:
            return {"error": "Gmail not configured"}
        
        stats = {
            "attachment_directory": str(self.gmail_agent.attachment_dir),
            "total_size_mb": 0,
            "file_count": 0,
            "message_folders": 0
        }
        
        # Calculate storage usage
        for item in self.gmail_agent.attachment_dir.iterdir():
            if item.is_dir():
                stats["message_folders"] += 1
                for file in item.iterdir():
                    if file.is_file():
                        stats["file_count"] += 1
                        stats["total_size_mb"] += file.stat().st_size / (1024 * 1024)
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats


# Example usage for production deployment
async def main():
    """Example of how to run in production"""
    
    # Check for required environment variables
    gmail_creds = os.getenv("GMAIL_SERVICE_ACCOUNT_PATH", "credentials/gmail-service-account.json")
    attachment_dir = os.getenv("ATTACHMENT_STORAGE_PATH", "/var/factory_automation/attachments")
    
    if not os.path.exists(gmail_creds):
        print(f"⚠️  Gmail credentials not found at: {gmail_creds}")
        print("   Set GMAIL_SERVICE_ACCOUNT_PATH environment variable")
        return
    
    # Initialize ChromaDB
    chromadb_client = ChromaDBClient()
    
    # Create production orchestrator
    orchestrator = ProductionOrchestrator(
        chromadb_client=chromadb_client,
        gmail_credentials_path=gmail_creds,
        attachment_storage_path=attachment_dir,
        polling_interval=60  # Check every minute
    )
    
    # Start monitoring
    await orchestrator.start_email_monitoring()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(60)
            
            # Print statistics every minute
            stats = orchestrator.get_attachment_statistics()
            print(f"Attachment storage: {stats['file_count']} files, {stats['total_size_mb']} MB")
            
    except KeyboardInterrupt:
        print("\nStopping orchestrator...")
        await orchestrator.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())