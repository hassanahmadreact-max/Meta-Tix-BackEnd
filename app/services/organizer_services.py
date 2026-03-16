from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import models
from app import schema
from fastapi import HTTPException, status
from datetime import datetime, timedelta


def get_organizer_sales(db: Session, organizer_id: int):
    # 1. Fetch all events owned by this specific organizer
    events = db.query(models.Event).filter(models.Event.organizer_id == organizer_id).all()
    
    event_list = []
    grand_total_revenue = 0
    grand_total_tickets = 0
    total_events_counts = len(events)

    for event in events:
        # 2. Join Tickets through TicketTiers to calculate sales for this event
        stats = db.query(
            func.count(models.Ticket.ticket_id).label("sold"),
            func.sum(models.Ticket.purchased_price).label("rev")
        ).join(models.TicketTier).filter(models.TicketTier.event_id == event.event_id).first()

        sold = stats.sold or 0
        rev = float(stats.rev or 0)
        
        grand_total_revenue += rev
        grand_total_tickets += sold
        
        event_list.append({
            "event_id": event.event_id,
            "name": event.title,
            "tickets_sold": sold,
            "revenue": rev
        })

    return {
        "total_events_created": total_events_counts,
        "total_revenue": grand_total_revenue,
        "total_tickets_sold": grand_total_tickets,
        "events": event_list
    }

