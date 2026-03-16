from sqlalchemy.orm import Session
from app.models import models
from app import schema
from app.core import security
from datetime import datetime, timedelta
from fastapi import HTTPException



def get_event_by_id(db: Session, event_id: int):
    return db.query(models.Event).filter(models.Event.event_id == event_id).first()

def create_event(db: Session , event: schema.EventCreate, organizer_id: int):
    db_event = models.Event(
        title=event.title,
        description=event.description,
        venue_id=event.venue_id,
        organizer_id=organizer_id,
        status="Pending",  
        isactive=True
    )
    db.add(db_event)
    db.flush()
    
    for schedule in event.schedules:
        db_schedule = models.EventSchedule(
            event_id=db_event.event_id,
            schedule_name=schedule.schedule_name,
            start_time=schedule.start_time,
            end_time=schedule.end_time
        )
        db.add(db_schedule)
    
    for tier in event.tiers:
        db_tier = models.TicketTier(
            event_id=db_event.event_id,
            tier_name=tier.tier_name,
            current_price=tier.current_price,
            available_quantity=tier.available_quantity
        )
        db.add(db_tier)
    
    db.commit()
    db.refresh(db_event)
    return db_event



def cancel_event(db: Session, event_id: int, current_user: models.User):
    # 1. Fetch the Event
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
        
    if event.status == models.EventStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Event is already cancelled.")

    # --- 2. ROLE-BASED BUSINESS LOGIC ---
    
    if current_user.role == "Organizer":
        # Rule A: Organizers can only cancel their OWN events
        if event.organizer_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="You can only cancel your own events.")
            
        # Rule B: Organizers cannot cancel within 48 hours
        first_schedule = db.query(models.EventSchedule).filter(
            models.EventSchedule.event_id == event_id
        ).order_by(models.EventSchedule.start_time.asc()).first()

        if first_schedule:
            deadline = datetime.now() + timedelta(days=2) 
            if first_schedule.start_time <= deadline:
                raise HTTPException(
                    status_code=400, 
                    detail="Too late to cancel! You must cancel at least 48 hours before start time."
                )

    elif current_user.role == "Admin":
        # Admins have God Mode. They bypass ownership checks and time limits.
        pass 
        
    else:
        # Customers cannot cancel events at all
        raise HTTPException(status_code=403, detail="Customers cannot cancel events.")

    # --- 3. EXECUTE CANCELLATION ---
    event.status = models.EventStatus.CANCELLED
    event.isactive = False        # Soft delete for safety
    db.commit()
    db.refresh(event)
    
    return event