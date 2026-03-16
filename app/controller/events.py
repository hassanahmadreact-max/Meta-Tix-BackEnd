from app.models import models
from app.models.database import get_db
from app import schema
from app.services import event_services
from app.api import deps
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from fastapi import Query


router = APIRouter()

@router.post("/create_event", response_model=schema.EventResponse)
def create_event(event: schema.EventCreate, db: Session = Depends(get_db),current_user : models.User = Depends(deps.get_current_user)):
    
    
    if current_user.role not in [models.UserRole.ORGANIZER, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only organizers can create events")
    
    if db.query(models.Venue).filter(models.Venue.venue_id == event.venue_id).first() is None:
        raise HTTPException(status_code=400, detail="Venue does not exist")
    
    return event_services.create_event(db=db, event=event, organizer_id=current_user.user_id)
    
@router.get("/all_events", response_model=List[schema.EventLandingPageResponse])
 # Make sure this is imported at the top!

def get_all_events(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="How many events to skip"),
    limit: int = Query(10, ge=1, le=100, description="How many events to return per page")
): 
    # 1. Fetch events WITH both the venue AND schedules loaded!
    events = db.query(models.Event).options(
        joinedload(models.Event.venue),
        joinedload(models.Event.schedules)  # 🚨 Added this line to eagerly load schedules!
    ).filter(
        models.Event.isactive == True,
        models.Event.status == "Approved" 
    ).offset(skip).limit(limit).all()

    # 2. Manually map the database objects to your Pydantic schema
    results = []
    for e in events:
        
        # 🚨 First, extract the schedules into a clean list of dictionaries
        mapped_schedules = []
        for s in e.schedules:
            mapped_schedules.append({
                "schedule_name": s.schedule_name,
                "start_time": s.start_time,
                "end_time": s.end_time
            })

        # 🚨 Then, add that list to your final output dictionary!
        results.append({
            "event_id": e.event_id,
            "title": e.title,
            "description": e.description,
            "status": e.status,
            "venue_name": e.venue.name if e.venue else "TBA",
            "city": e.venue.city if e.venue else "TBA",
            "schedules": mapped_schedules  # <--- Hand the schedules to Pydantic/React!
        })
    
    return results

@router.patch("/cancel/{event_id}")
def cancel_event_endpoint(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):

    return event_services.cancel_event(
        db=db, 
        event_id=event_id, 
        current_user=current_user
    )


@router.get("/venues")
def get_all_venues(db: Session = Depends(get_db)):
    return db.query(models.Venue).all()

@router.get("/{event_id}") # (If you don't use @router, it might be @app.get("/events/{event_id}"))
def get_single_event(event_id: int, db: Session = Depends(get_db)):
    # 1. We must EAGERLY LOAD the tiers, otherwise the React modal will be empty!
    event = db.query(models.Event).options(
        joinedload(models.Event.venue),
        joinedload(models.Event.tiers) # 🚨 Grabs the ticket pricing!
    ).filter(models.Event.event_id == event_id).first()
    
    # 2. Safety net
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    return event


