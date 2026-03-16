from app.models.database import get_db
from app import schema
from app.services import admin_services
from app.api import deps
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from sqlalchemy import func
from app.models import models

router = APIRouter()

@router.get("/my-sales", response_model=schema.OrganizerSalesResponse)
def get_my_sales(db: Session = Depends(get_db), current_user = Depends(deps.get_current_user)):
    
    events = db.query(models.Event).filter(models.Event.organizer_id == current_user.user_id).all()
    
    total_platform_revenue = 0
    total_platform_tickets = 0
    events_response = []

    for event in events:
        event_revenue = 0
        event_tickets = 0
        tiers_response = []
        
        for tier in event.tiers:
            # 🚨 THE FIX: Use func.sum(quantity) instead of .count()
            # .scalar() gets the actual number, and "or 0" prevents it from breaking if no tickets are sold yet
            sold_count = db.query(func.sum(models.Booking.quantity))\
                           .filter(models.Booking.tier_id == tier.tier_id)\
                           .scalar() or 0
            
            # Calculate revenue for this specific tier
            tier_revenue = sold_count * tier.current_price
            
            event_tickets += sold_count
            event_revenue += tier_revenue
            
            tiers_response.append({
                "tier_name": tier.tier_name,
                "price": tier.current_price,
                "total_capacity": tier.available_quantity + sold_count, 
                "tickets_sold": sold_count
            })

        total_platform_revenue += event_revenue
        total_platform_tickets += event_tickets
        
        events_response.append({
            "event_id": event.event_id,
            "name": event.title,
            "status": event.status, 
            "tickets_sold": event_tickets,
            "revenue": event_revenue,
            "tiers": tiers_response
        })

    return {
        "total_events_created": len(events),
        "total_revenue": total_platform_revenue,
        "total_tickets_sold": total_platform_tickets,
        "events": events_response
    }
