"""Pydantic models for AI extraction - designed for OpenAI structured outputs"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CustomerInformation(BaseModel):
    """Customer information as extracted by AI"""

    company: Optional[str] = Field(default=None, description="Company name")
    contact_person: Optional[str] = Field(
        default=None, description="Contact person name"
    )
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")

    model_config = ConfigDict(extra="forbid")  # No extra fields allowed


class OrderItemAI(BaseModel):
    """Order item as extracted by AI - handles various formats"""

    # Primary fields - at least one tag identifier required
    tag_code: Optional[str] = Field(
        default=None, description="Single tag code (e.g., TBALWBL0009N)"
    )
    tag_codes: Optional[List[str]] = Field(
        default=None, description="Multiple tag codes"
    )

    # Tag type as string (AI returns "Fit Tag", "Price Tag", etc.)
    tag_type: str = Field(
        default="price_tag",
        description="Type of tag (Fit Tag, Price Tag, Care Label, etc.)",
    )

    # Quantity - just use int with default
    quantity: int = Field(
        default=1, ge=1, description="Quantity ordered (must be positive)"
    )

    # Additional fields AI might extract
    fit: Optional[str] = Field(
        default=None, description="Fit type (Bootcut, Slim, Regular, etc.)"
    )
    brand: Optional[str] = Field(default=None, description="Brand name")
    remarks: Optional[str] = Field(
        default=None, description="Special remarks or requirements"
    )
    color: Optional[str] = Field(default=None, description="Color specification")
    size: Optional[str] = Field(default=None, description="Size specification")
    material: Optional[str] = Field(default=None, description="Material type")

    # Note: Removed fit_mappings fields as they cause OpenAI schema validation issues
    # The fit information is captured in the 'fit' field above

    model_config = ConfigDict(extra="forbid")  # Strict validation for OpenAI


class ProformaInvoiceDetails(BaseModel):
    """Proforma invoice details"""

    invoice_number: Optional[str] = Field(default=None, alias="number")
    invoice_date: Optional[str] = Field(default=None, alias="date")
    total_amount: Optional[float] = Field(default=None, alias="amount")  # No Union
    payment_terms: Optional[str] = Field(default=None)

    model_config = ConfigDict(
        populate_by_name=True, extra="forbid"  # Strict validation for OpenAI
    )


class DeliveryRequirements(BaseModel):
    """Delivery requirements"""

    urgency: Optional[str] = Field(
        default="normal", description="Urgency level (urgent, normal, low)"
    )
    delivery_date: Optional[str] = Field(default=None, alias="date")
    required_date: Optional[str] = Field(default=None)
    special_instructions: Optional[str] = Field(default=None)

    model_config = ConfigDict(
        populate_by_name=True, extra="forbid"  # Strict validation
    )


class AIExtractedOrder(BaseModel):
    """Complete order as extracted by AI - structured for OpenAI API"""

    # Primary customer information
    customer_information: CustomerInformation = Field(
        description="Customer company and contact details"
    )

    # Order items - required field
    order_items: List[OrderItemAI] = Field(
        description="List of items being ordered (tags, labels, etc.)",
        min_length=1,  # Ensure at least one item
    )

    # Optional fields
    proforma_invoice_details: Optional[ProformaInvoiceDetails] = Field(
        None, description="Proforma invoice information if mentioned"
    )

    delivery_requirements: Optional[DeliveryRequirements] = Field(
        None, description="Delivery date and urgency information"
    )

    # Brand and PO information
    brand: Optional[str] = Field(None, description="Primary brand for the order")
    po_number: Optional[str] = Field(
        None, description="Purchase order number if provided"
    )
    purchase_order_number: Optional[str] = Field(
        None, description="Alternative field for PO number"
    )

    # Additional context
    special_instructions: Optional[str] = Field(
        None, description="Any special requirements or instructions"
    )
    missing_information: Optional[List[str]] = Field(
        default_factory=list, description="Information that could not be extracted"
    )

    model_config = ConfigDict(
        # Use the new Pydantic v2 config
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",  # Required for OpenAI structured outputs
        json_schema_extra={
            "example": {
                "customer_information": {
                    "company": "ABC Garments",
                    "contact_person": "John Doe",
                    "email": "john@abc.com",
                    "phone": "1234567890",
                },
                "order_items": [
                    {
                        "tag_code": "TBALWBL0009N",
                        "tag_type": "Fit Tag",
                        "quantity": 1000,
                        "brand": "Allen Solly",
                    }
                ],
                "delivery_requirements": {
                    "urgency": "urgent",
                    "delivery_date": "2024-12-25",
                },
            }
        },
    )

    def get_customer_info(self) -> CustomerInformation:
        """Get customer info - now always available as required field"""
        return self.customer_information

    def get_order_items(self) -> List[OrderItemAI]:
        """Get order items - now always available as required field"""
        return self.order_items

    def get_delivery_info(self) -> DeliveryRequirements:
        """Get delivery info - returns object or creates default"""
        if self.delivery_requirements:
            return self.delivery_requirements

        # Return default if not provided
        return DeliveryRequirements(
            urgency="normal", special_instructions=self.special_instructions
        )

    def get_brand(self) -> Optional[str]:
        """Get brand information"""
        return self.brand
