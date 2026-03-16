# app/controller/booking.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app import schema
from app.models import models
from app.api import deps
from app.services import booking_services

router = APIRouter()

@router.post("/reserve", response_model=schema.BookingResponse)
def reserve_ticket(
    request: schema.TicketPurchaseRequest, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Step 1: Reserve the ticket and get a Pending Booking ID.
    """
    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    
    return booking_services.process_reservation(
        db=db, 
        user_id=current_user.user_id, 
        request=request
    )


@router.post("/checkout")
def checkout_booking(
    payment_data: schema.PaymentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Step 2: Pay for the Pending Booking to generate the actual tickets.
    """
    return booking_services.process_payment_and_generate_tickets(
        db=db, 
        booking_id=payment_data.booking_id, 
        user_id=current_user.user_id,
        payment_method=payment_data.payment_method
    )


@router.get("/my_tickets", response_model=List[schema.BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    View all past and current bookings.
    """
    return booking_services.get_user_bookings(
        db=db, 
        user_id=current_user.user_id
    )