"""Inventory Reconciliation Agent - Handles discrepancies between data sources"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import text

# Note: These models would need to be created in your database
# from ..factory_database.models import Inventory, InventoryAudit, ReconciliationLog
from ..factory_config.settings import settings
from ..factory_database.connection import get_db
from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class DataSource(str, Enum):
    """Source of inventory data"""

    EXCEL = "excel"  # Employee-maintained Excel (source of truth)
    CHROMADB = "chromadb"  # Vector database for search
    POSTGRESQL = "postgresql"  # Transactional database
    MANUAL = "manual"  # Manual adjustment


class ReconciliationAction(str, Enum):
    """Actions to take when discrepancies found"""

    UPDATE_POSTGRESQL = "update_postgresql"
    UPDATE_CHROMADB = "update_chromadb"
    ALERT_HUMAN = "alert_human"
    AUTO_SYNC = "auto_sync"
    INVESTIGATE = "investigate"


class DiscrepancyType(str, Enum):
    """Types of discrepancies"""

    QUANTITY_MISMATCH = "quantity_mismatch"
    ITEM_MISSING = "item_missing"
    PRICE_MISMATCH = "price_mismatch"
    METADATA_MISMATCH = "metadata_mismatch"


class InventoryReconciliationAgent:
    """
    Handles inventory reconciliation between Excel (source of truth),
    ChromaDB (search), and PostgreSQL (transactions)
    """

    def __init__(self, chromadb_client: ChromaDBClient):
        self.chromadb_client = chromadb_client
        self.excel_source_path = Path(
            settings.get("inventory_excel_path", "./inventory")
        )
        self.reconciliation_threshold = settings.get(
            "reconciliation_threshold", 10
        )  # Units

    async def perform_reconciliation(
        self, excel_file_path: Optional[str] = None, auto_fix: bool = False
    ) -> Dict[str, Any]:
        """
        Perform full inventory reconciliation

        Strategy:
        1. Excel is the source of truth (maintained by employees)
        2. PostgreSQL tracks real-time transactions
        3. ChromaDB is for search only (can be rebuilt)

        Returns reconciliation report with actions taken
        """

        reconciliation_id = f"RECON-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting reconciliation {reconciliation_id}")

        # Step 1: Load data from all sources
        excel_data = await self._load_excel_inventory(excel_file_path)
        postgresql_data = await self._load_postgresql_inventory()
        chromadb_data = await self._load_chromadb_inventory()

        # Step 2: Find discrepancies
        discrepancies = self._find_discrepancies(
            excel_data, postgresql_data, chromadb_data
        )

        # Step 3: Determine actions based on business rules
        actions = self._determine_actions(discrepancies, auto_fix)

        # Step 4: Execute actions if auto_fix is enabled
        if auto_fix:
            execution_results = await self._execute_actions(actions)
        else:
            execution_results = {
                "status": "review_required",
                "actions_pending": actions,
            }

        # Step 5: Log reconciliation
        await self._log_reconciliation(
            reconciliation_id, discrepancies, actions, execution_results
        )

        # Step 6: Generate report
        report = self._generate_report(
            reconciliation_id,
            excel_data,
            postgresql_data,
            chromadb_data,
            discrepancies,
            actions,
            execution_results,
        )

        return report

    async def _load_excel_inventory(
        self, file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load inventory from Excel (source of truth)"""
        try:
            if not file_path:
                # Find the most recent Excel file
                excel_files = list(self.excel_source_path.glob("*.xlsx"))
                if not excel_files:
                    raise FileNotFoundError("No Excel inventory files found")
                file_path = max(excel_files, key=lambda f: f.stat().st_mtime)

            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets

            inventory_data = {}
            for sheet_name, sheet_df in df.items():
                # Standardize column names
                sheet_df.columns = sheet_df.columns.str.lower().str.replace(" ", "_")

                # Process each row
                for _, row in sheet_df.iterrows():
                    product_code = str(row.get("product_code", row.get("tag_code", "")))
                    if product_code:
                        inventory_data[product_code] = {
                            "source": "excel",
                            "sheet": sheet_name,
                            "quantity": int(row.get("quantity", row.get("stock", 0))),
                            "price": float(row.get("price", 0)),
                            "description": str(row.get("description", "")),
                            "brand": str(row.get("brand", "")),
                            "last_updated": datetime.fromtimestamp(
                                Path(file_path).stat().st_mtime
                            ),
                            "raw_data": row.to_dict(),
                        }

            logger.info(f"Loaded {len(inventory_data)} items from Excel")
            return inventory_data

        except Exception as e:
            logger.error(f"Error loading Excel inventory: {e}")
            return {}

    async def _load_postgresql_inventory(self) -> Dict[str, Any]:
        """Load current inventory from PostgreSQL"""
        inventory_data = {}

        try:
            with get_db() as session:
                # Query current inventory levels
                query = text(
                    """
                    SELECT 
                        product_code,
                        quantity_available,
                        quantity_reserved,
                        price,
                        description,
                        brand,
                        last_updated
                    FROM inventory
                    WHERE active = true
                """
                )

                results = session.execute(query)

                for row in results:
                    inventory_data[row.product_code] = {
                        "source": "postgresql",
                        "quantity_available": row.quantity_available,
                        "quantity_reserved": row.quantity_reserved,
                        "quantity_total": row.quantity_available
                        + row.quantity_reserved,
                        "price": float(row.price) if row.price else 0,
                        "description": row.description,
                        "brand": row.brand,
                        "last_updated": row.last_updated,
                    }

            logger.info(f"Loaded {len(inventory_data)} items from PostgreSQL")
            return inventory_data

        except Exception as e:
            logger.error(f"Error loading PostgreSQL inventory: {e}")
            return {}

    async def _load_chromadb_inventory(self) -> Dict[str, Any]:
        """Load inventory data from ChromaDB metadata"""
        inventory_data = {}

        try:
            # Get all documents from ChromaDB
            collection = self.chromadb_client.collection

            # Fetch all items (you might want to paginate for large datasets)
            results = collection.get(include=["metadatas", "documents"])

            if results and results["ids"]:
                for i, item_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i] if results["metadatas"] else {}

                    product_code = metadata.get(
                        "product_code", metadata.get("tag_code", "")
                    )
                    if product_code:
                        inventory_data[product_code] = {
                            "source": "chromadb",
                            "id": item_id,
                            "quantity": int(
                                metadata.get("stock", metadata.get("quantity", 0))
                            ),
                            "description": metadata.get("description", ""),
                            "brand": metadata.get("brand", ""),
                            "document": (
                                results["documents"][i] if results["documents"] else ""
                            ),
                            "metadata": metadata,
                        }

            logger.info(f"Loaded {len(inventory_data)} items from ChromaDB")
            return inventory_data

        except Exception as e:
            logger.error(f"Error loading ChromaDB inventory: {e}")
            return {}

    def _find_discrepancies(
        self,
        excel_data: Dict[str, Any],
        postgresql_data: Dict[str, Any],
        chromadb_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Find discrepancies between data sources"""
        discrepancies = []

        # Get all unique product codes
        all_codes = (
            set(excel_data.keys())
            | set(postgresql_data.keys())
            | set(chromadb_data.keys())
        )

        for product_code in all_codes:
            excel_item = excel_data.get(product_code)
            pg_item = postgresql_data.get(product_code)
            chroma_item = chromadb_data.get(product_code)

            # Check if item exists in all sources
            if not excel_item:
                # Item not in Excel (source of truth) - might be obsolete
                discrepancies.append(
                    {
                        "product_code": product_code,
                        "type": DiscrepancyType.ITEM_MISSING,
                        "source_missing": DataSource.EXCEL,
                        "exists_in": [
                            DataSource.POSTGRESQL if pg_item else None,
                            DataSource.CHROMADB if chroma_item else None,
                        ],
                        "severity": "high",
                        "message": f"Item {product_code} not found in Excel (source of truth)",
                    }
                )
                continue

            # Excel exists, check other sources
            if not pg_item:
                discrepancies.append(
                    {
                        "product_code": product_code,
                        "type": DiscrepancyType.ITEM_MISSING,
                        "source_missing": DataSource.POSTGRESQL,
                        "excel_quantity": excel_item["quantity"],
                        "severity": "high",
                        "message": f"Item {product_code} in Excel but not in PostgreSQL",
                    }
                )

            if not chroma_item:
                discrepancies.append(
                    {
                        "product_code": product_code,
                        "type": DiscrepancyType.ITEM_MISSING,
                        "source_missing": DataSource.CHROMADB,
                        "excel_quantity": excel_item["quantity"],
                        "severity": "medium",  # ChromaDB can be rebuilt
                        "message": f"Item {product_code} in Excel but not in ChromaDB",
                    }
                )

            # Check quantity discrepancies
            if excel_item and pg_item:
                excel_qty = excel_item["quantity"]
                pg_qty = pg_item.get(
                    "quantity_total", pg_item.get("quantity_available", 0)
                )

                if abs(excel_qty - pg_qty) > self.reconciliation_threshold:
                    discrepancies.append(
                        {
                            "product_code": product_code,
                            "type": DiscrepancyType.QUANTITY_MISMATCH,
                            "excel_quantity": excel_qty,
                            "postgresql_quantity": pg_qty,
                            "difference": excel_qty - pg_qty,
                            "severity": (
                                "high" if abs(excel_qty - pg_qty) > 100 else "medium"
                            ),
                            "message": f"Quantity mismatch: Excel={excel_qty}, PostgreSQL={pg_qty}",
                        }
                    )

            # Check ChromaDB quantity
            if excel_item and chroma_item:
                excel_qty = excel_item["quantity"]
                chroma_qty = chroma_item["quantity"]

                if excel_qty != chroma_qty:
                    discrepancies.append(
                        {
                            "product_code": product_code,
                            "type": DiscrepancyType.QUANTITY_MISMATCH,
                            "excel_quantity": excel_qty,
                            "chromadb_quantity": chroma_qty,
                            "difference": excel_qty - chroma_qty,
                            "severity": "low",  # ChromaDB is just for search
                            "message": f"ChromaDB out of sync: Excel={excel_qty}, ChromaDB={chroma_qty}",
                        }
                    )

        return discrepancies

    def _determine_actions(
        self, discrepancies: List[Dict[str, Any]], auto_fix: bool
    ) -> List[Dict[str, Any]]:
        """
        Determine actions based on business rules

        Rules:
        1. Excel is source of truth - always trust Excel quantities
        2. PostgreSQL differences might indicate pending orders not reflected in Excel
        3. ChromaDB can always be rebuilt from Excel
        """
        actions = []

        for disc in discrepancies:
            product_code = disc["product_code"]
            disc_type = disc["type"]

            if disc_type == DiscrepancyType.ITEM_MISSING:
                if disc["source_missing"] == DataSource.EXCEL:
                    # Item not in Excel - investigate or remove from other systems
                    actions.append(
                        {
                            "action": ReconciliationAction.ALERT_HUMAN,
                            "product_code": product_code,
                            "reason": "Item exists in system but not in Excel",
                            "recommendation": "Verify with warehouse team",
                            "auto_executable": False,
                        }
                    )

                elif disc["source_missing"] == DataSource.POSTGRESQL:
                    # Add to PostgreSQL from Excel
                    actions.append(
                        {
                            "action": ReconciliationAction.UPDATE_POSTGRESQL,
                            "product_code": product_code,
                            "operation": "insert",
                            "source": DataSource.EXCEL,
                            "auto_executable": auto_fix,
                            "data": {"quantity": disc["excel_quantity"]},
                        }
                    )

                elif disc["source_missing"] == DataSource.CHROMADB:
                    # Rebuild ChromaDB entry
                    actions.append(
                        {
                            "action": ReconciliationAction.UPDATE_CHROMADB,
                            "product_code": product_code,
                            "operation": "insert",
                            "source": DataSource.EXCEL,
                            "auto_executable": True,  # Always safe to rebuild ChromaDB
                        }
                    )

            elif disc_type == DiscrepancyType.QUANTITY_MISMATCH:
                if "postgresql_quantity" in disc:
                    # PostgreSQL vs Excel mismatch
                    difference = disc["difference"]

                    if abs(difference) > 100:
                        # Large discrepancy - needs human review
                        actions.append(
                            {
                                "action": ReconciliationAction.ALERT_HUMAN,
                                "product_code": product_code,
                                "reason": f"Large quantity discrepancy: {difference} units",
                                "excel_quantity": disc["excel_quantity"],
                                "postgresql_quantity": disc["postgresql_quantity"],
                                "recommendation": "Verify pending orders and physical stock",
                                "auto_executable": False,
                            }
                        )
                    else:
                        # Small discrepancy - can auto-sync if enabled
                        actions.append(
                            {
                                "action": ReconciliationAction.UPDATE_POSTGRESQL,
                                "product_code": product_code,
                                "operation": "update_quantity",
                                "new_quantity": disc["excel_quantity"],
                                "old_quantity": disc["postgresql_quantity"],
                                "source": DataSource.EXCEL,
                                "auto_executable": auto_fix,
                                "requires_audit": True,
                            }
                        )

                if "chromadb_quantity" in disc:
                    # ChromaDB out of sync - always update
                    actions.append(
                        {
                            "action": ReconciliationAction.UPDATE_CHROMADB,
                            "product_code": product_code,
                            "operation": "update_metadata",
                            "new_quantity": disc["excel_quantity"],
                            "auto_executable": True,
                        }
                    )

        return actions

    async def _execute_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute reconciliation actions"""
        results = {"executed": [], "failed": [], "skipped": []}

        for action in actions:
            if not action.get("auto_executable", False):
                results["skipped"].append(
                    {"action": action, "reason": "Requires manual approval"}
                )
                continue

            try:
                if action["action"] == ReconciliationAction.UPDATE_POSTGRESQL:
                    success = await self._update_postgresql(action)

                elif action["action"] == ReconciliationAction.UPDATE_CHROMADB:
                    success = await self._update_chromadb(action)

                elif action["action"] == ReconciliationAction.AUTO_SYNC:
                    success = await self._auto_sync(action)

                else:
                    success = False

                if success:
                    results["executed"].append(action)
                else:
                    results["failed"].append(action)

            except Exception as e:
                logger.error(f"Error executing action: {e}")
                action["error"] = str(e)
                results["failed"].append(action)

        return results

    async def _update_postgresql(self, action: Dict[str, Any]) -> bool:
        """Update PostgreSQL inventory"""
        try:
            with get_db() as session:
                product_code = action["product_code"]

                if action["operation"] == "insert":
                    # Add new inventory item
                    # Note: You'd need to implement the Inventory model
                    pass  # Implementation depends on your model

                elif action["operation"] == "update_quantity":
                    # Update quantity
                    session.execute(
                        text(
                            """
                            UPDATE inventory 
                            SET quantity_available = :new_qty,
                                last_reconciled = NOW(),
                                reconciliation_notes = :notes
                            WHERE product_code = :code
                        """
                        ),
                        {
                            "new_qty": action["new_quantity"],
                            "code": product_code,
                            "notes": f"Reconciled from Excel on {datetime.now()}",
                        },
                    )

                # Create audit log
                if action.get("requires_audit"):
                    session.execute(
                        text(
                            """
                            INSERT INTO inventory_audit 
                            (product_code, action, old_value, new_value, source, timestamp)
                            VALUES (:code, :action, :old, :new, :source, NOW())
                        """
                        ),
                        {
                            "code": product_code,
                            "action": "reconciliation",
                            "old": str(action.get("old_quantity", "")),
                            "new": str(action.get("new_quantity", "")),
                            "source": "excel_reconciliation",
                        },
                    )

                session.commit()
                logger.info(f"Updated PostgreSQL for {product_code}")
                return True

        except Exception as e:
            logger.error(f"PostgreSQL update failed: {e}")
            return False

    async def _update_chromadb(self, action: Dict[str, Any]) -> bool:
        """Update ChromaDB metadata"""
        try:
            collection = self.chromadb_client.collection
            product_code = action["product_code"]

            if action["operation"] == "update_metadata":
                # Update existing item metadata
                # First, find the item
                results = collection.get(where={"product_code": product_code})

                if results and results["ids"]:
                    item_id = results["ids"][0]
                    current_metadata = results["metadatas"][0]

                    # Update quantity in metadata
                    current_metadata["quantity"] = action["new_quantity"]
                    current_metadata["stock"] = action["new_quantity"]
                    current_metadata["last_reconciled"] = datetime.now().isoformat()

                    # Update in ChromaDB
                    collection.update(ids=[item_id], metadatas=[current_metadata])

                    logger.info(f"Updated ChromaDB metadata for {product_code}")
                    return True

            elif action["operation"] == "insert":
                # Rebuild from Excel data
                # This would require re-ingestion logic
                pass  # Implementation depends on your ingestion process

            return True

        except Exception as e:
            logger.error(f"ChromaDB update failed: {e}")
            return False

    async def _log_reconciliation(
        self,
        reconciliation_id: str,
        discrepancies: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        results: Dict[str, Any],
    ):
        """Log reconciliation to database"""
        try:
            with get_db() as session:
                session.execute(
                    text(
                        """
                        INSERT INTO reconciliation_log 
                        (reconciliation_id, timestamp, discrepancies_found, 
                         actions_proposed, actions_executed, results, status)
                        VALUES (:id, NOW(), :disc, :actions, :executed, :results, :status)
                    """
                    ),
                    {
                        "id": reconciliation_id,
                        "disc": len(discrepancies),
                        "actions": len(actions),
                        "executed": len(results.get("executed", [])),
                        "results": json.dumps(results),
                        "status": (
                            "completed" if not results.get("failed") else "partial"
                        ),
                    },
                )
                session.commit()

        except Exception as e:
            logger.error(f"Failed to log reconciliation: {e}")

    def _generate_report(
        self,
        reconciliation_id: str,
        excel_data: Dict,
        postgresql_data: Dict,
        chromadb_data: Dict,
        discrepancies: List,
        actions: List,
        results: Dict,
    ) -> Dict[str, Any]:
        """Generate comprehensive reconciliation report"""

        report = {
            "reconciliation_id": reconciliation_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_items_excel": len(excel_data),
                "total_items_postgresql": len(postgresql_data),
                "total_items_chromadb": len(chromadb_data),
                "discrepancies_found": len(discrepancies),
                "actions_proposed": len(actions),
                "actions_executed": len(results.get("executed", [])),
                "actions_failed": len(results.get("failed", [])),
                "actions_pending": len(results.get("skipped", [])),
            },
            "discrepancies": {
                "high_severity": [
                    d for d in discrepancies if d.get("severity") == "high"
                ],
                "medium_severity": [
                    d for d in discrepancies if d.get("severity") == "medium"
                ],
                "low_severity": [
                    d for d in discrepancies if d.get("severity") == "low"
                ],
            },
            "actions": {
                "executed": results.get("executed", []),
                "failed": results.get("failed", []),
                "pending_approval": results.get("skipped", []),
            },
            "recommendations": self._generate_recommendations(discrepancies, results),
        }

        return report

    def _generate_recommendations(
        self, discrepancies: List[Dict[str, Any]], results: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on reconciliation results"""
        recommendations = []

        # Count high severity issues
        high_severity = [d for d in discrepancies if d.get("severity") == "high"]
        if high_severity:
            recommendations.append(
                f"⚠️ {len(high_severity)} high-severity discrepancies require immediate attention"
            )

        # Check for systematic issues
        missing_in_pg = [
            d for d in discrepancies if d.get("source_missing") == DataSource.POSTGRESQL
        ]
        if len(missing_in_pg) > 10:
            recommendations.append(
                "📊 Many items missing from PostgreSQL - consider full database sync"
            )

        # Check failed actions
        if results.get("failed"):
            recommendations.append(
                f"❌ {len(results['failed'])} actions failed - manual intervention required"
            )

        # Suggest ChromaDB rebuild if many discrepancies
        chroma_issues = [
            d
            for d in discrepancies
            if d.get("source_missing") == DataSource.CHROMADB
            or "chromadb_quantity" in d
        ]
        if len(chroma_issues) > 20:
            recommendations.append(
                "🔄 Consider rebuilding ChromaDB from Excel for better search accuracy"
            )

        # Check for pending orders impact
        large_discrepancies = [
            d
            for d in discrepancies
            if d.get("type") == DiscrepancyType.QUANTITY_MISMATCH
            and abs(d.get("difference", 0)) > 100
        ]
        if large_discrepancies:
            recommendations.append(
                "📦 Large quantity discrepancies detected - verify pending orders"
            )

        if not recommendations:
            recommendations.append("✅ Inventory systems are well synchronized")

        return recommendations

    async def setup_auto_reconciliation(self, schedule: str = "daily"):
        """Setup automatic reconciliation schedule"""
        # This would integrate with a scheduler like Celery or APScheduler
        pass
