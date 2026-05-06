from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.models.models import Offer, LaundryItem, ItemServicePrice
from typing import List, Dict
from fastapi import HTTPException


async def calculate_order_price(db: AsyncSession, items_input: List[Dict]) -> Dict:
    subtotal = 0.0
    processed_items = []

    # 1. Calculate Subtotal and capture exact unit prices
    for entry in items_input:
        cat_id = entry.get("service_category_id")
        custom_price = entry.get("unit_price") 
        
        if not cat_id:
            raise HTTPException(status_code=400, detail="Missing service category for item")

        if custom_price is not None:
            final_item_price = custom_price
        else:
            stmt = select(ItemServicePrice).where(
                ItemServicePrice.item_id == entry["item_id"],
                ItemServicePrice.service_category_id == cat_id
            )
            res = await db.execute(stmt)
            service_price = res.scalars().first()
            
            if not service_price:
                raise HTTPException(status_code=400, detail="Pricing matrix not found")
                
            base_price = service_price.price
            final_item_price = base_price
            
            # Apply Item-Level Discount
            if getattr(service_price, 'is_discount_active', False):
                d_val = getattr(service_price, 'discount_value', 0.0)
                d_type = getattr(service_price, 'discount_type', 'PERCENTAGE')
                if d_type == "PERCENTAGE":
                    final_item_price = base_price * (1 - (d_val / 100.0))
                else:
                    final_item_price = max(0.0, base_price - d_val)
                    
        subtotal += final_item_price * entry["quantity"]
        
        # Capture the EXACT computed price so the DB saves it correctly
        processed_items.append({
            "item_id": entry["item_id"],
            "service_category_id": cat_id,
            "quantity": entry["quantity"],
            "unit_price": final_item_price 
        })

    # 2. Find Applicable Global Offers (Safe Date Checking)
    now = datetime.utcnow()
    offer_query = await db.execute(
        select(Offer).where(
            Offer.is_active == True,
            Offer.min_order_amount <= subtotal
        )
    )
    offers = offer_query.scalars().all()
    
    valid_offers = []
    for o in offers:
        if o.start_date and o.end_date:
            # Strip timezone info safely to prevent Postgres mismatch errors
            s_date = o.start_date.replace(tzinfo=None)
            e_date = o.end_date.replace(tzinfo=None)
            if s_date <= now <= e_date:
                valid_offers.append(o)
        else:
            valid_offers.append(o)

    discount = 0.0
    if valid_offers:
        calculated_discounts = []
        for o in valid_offers:
            if getattr(o, "discount_type", "FIXED") == "PERCENTAGE":
                calculated_discounts.append(subtotal * (o.discount_amount / 100.0))
            else:
                calculated_discounts.append(o.discount_amount)
        discount = max(calculated_discounts) if calculated_discounts else 0.0

    return {
        "subtotal": subtotal,
        "discount_applied": discount,
        "final_total": max(0, subtotal - discount),
        "processed_items": processed_items # NEW: Returning exact cart lines
    }