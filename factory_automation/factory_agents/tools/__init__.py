"""Shared tools for all orchestrator versions

This module provides reusable tools that can be used by:
- orchestrator_v3_agentic.py (execution-based)
- orchestrator_v3_approval.py (approval mode with tool interception)
- Any future orchestrator versions

The tools are organized by functionality and can be configured
to work in different modes (execute vs propose).
"""

from .email_tools import EmailTools
from .inventory_tools import InventoryTools
from .order_tools import OrderTools
from .document_tools import DocumentTools
from .customer_tools import CustomerTools
from .payment_tools import PaymentTools
from .supplier_tools import SupplierTools
from .attachment_tools import AttachmentTools

__all__ = [
    'EmailTools',
    'InventoryTools',
    'OrderTools',
    'DocumentTools',
    'CustomerTools',
    'PaymentTools',
    'SupplierTools',
    'AttachmentTools',
]