# app/api/v1/endpoints/offers.py
from fastapi import APIRouter, Depends, HTTPException 
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import RoleChecker
from app.models.models import UserRole, Offer
from app.schemas.offer import OfferCreate, OfferResponse
from typing import List
from sqlalchemy import select 

router = APIRouter()

@router.post("/", response_model=OfferResponse, dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
async def create_offer(offer_in: OfferCreate, db: AsyncSession = Depends(get_db)):
    db_offer = Offer(**offer_in.model_dump())
    db.add(db_offer)
    await db.commit()
    await db.refresh(db_offer)
    return db_offer

@router.get("/", response_model=List[OfferResponse])
async def list_offers(db: AsyncSession = Depends(get_db)):
    # Optional: You can filter out inactive offers here if you don't want admins to see them,
    # but usually admins want to see historical inactive offers. We'll return all.
    result = await db.execute(select(Offer).order_by(Offer.id.desc()))
    return result.scalars().all()

# --- THE NEW ENDPOINT ---
@router.delete("/{offer_id}", dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
async def delete_offer(offer_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-deletes an offer so it no longer applies to future orders."""
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalars().first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    offer.is_active = False # Soft delete
    await db.commit()
    
    return {"message": "Offer successfully deactivated"}

# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.db.session import get_db
# from app.api.deps import RoleChecker
# from app.models.models import UserRole, Offer
# from app.schemas.offer import OfferCreate, OfferResponse
# from typing import List
# from sqlalchemy import select 


# router = APIRouter()

# @router.post("/", response_model=OfferResponse, dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
# async def create_offer(offer_in: OfferCreate, db: AsyncSession = Depends(get_db)):
#     db_offer = Offer(**offer_in.model_dump())
#     db.add(db_offer)
#     await db.commit()
#     await db.refresh(db_offer)
#     return db_offer

# @router.get("/", response_model=List[OfferResponse])
# async def list_offers(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Offer))
#     return result.scalars().all()