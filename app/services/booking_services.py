# app/services/booking_services.py

from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from app.models import models
from app import schema

def process_reservation(db: Session, user_id: int, request: schema.TicketPurchaseRequest):
    """
    STEP 1: The Hold. 
    Reserves inventory and creates a Pending Booking. No tickets generated yet.
    """
    event = db.query(models.Event).filter(models.Event.event_id == request.event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
        
    if event.status != "Approved" or event.isactive == False:
        raise HTTPException(
            status_code=400, 
            detail="Tickets cannot be purchased for this event right now. It may be pending or cancelled."
        )
    
    tier = db.query(models.TicketTier).filter(
        models.TicketTier.tier_id == request.tier_id,
        models.TicketTier.event_id == request.event_id
    ).first()

    if not tier:
        raise HTTPException(status_code=404, detail="Ticket Tier not found")

    if tier.available_quantity < request.quantity:
        raise HTTPException(status_code=400, detail=f"Sold out! Only {tier.available_quantity} left.")

    expected_total = float(tier.current_price * request.quantity)
    
    if request.payment_amount != expected_total:
        raise HTTPException(status_code=400, detail="Payment Amount Mismatch.")

    try:
        # 1. Create Pending Booking
        new_booking = models.Booking(
            user_id=user_id,
            tier_id=tier.tier_id,      
            quantity=request.quantity, 
            total_amount=expected_total,
            status="Pending"
        )
        db.add(new_booking)

        # 2. Deduct Inventory (Temporarily hold the seats)
        tier.available_quantity -= request.quantity
        
        db.commit()
        db.refresh(new_booking)
        
        # Attach empty tickets list because they haven't paid yet
        new_booking.tickets = [] 
        return new_booking

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def process_payment_and_generate_tickets(db: Session, booking_id: int, user_id: int, payment_method: str):
    """
    STEP 2: The Checkout.
    Verifies payment, creates the Payment record, and generates the Tickets.
    """
    booking = db.query(models.Booking).filter(
        models.Booking.booking_id == booking_id,
        models.Booking.user_id == user_id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.status == "Confirmed":
        raise HTTPException(status_code=400, detail="This booking is already paid for!")

    try:
        # 1. Create Payment Record
        # Using slice [:8] so the transaction string easily fits in your String(255) column
        tx_id = f"TXN-{booking.booking_id}-{user_id}-{uuid.uuid4().hex[:8]}"
        new_payment = models.Payment(
            booking_id=booking.booking_id, 
            payment_method=payment_method,
            transaction_id=tx_id,
            status="Successful" # Matches your Payment Enum exactly
        )
        db.add(new_payment)

        # 2. GENERATE TICKETS!
        generated_tickets = []
        unit_price = booking.total_amount / booking.quantity

        for _ in range(booking.quantity):
            qr_string = f"{booking.tier_id}-{uuid.uuid4()}"
            new_ticket = models.Ticket(
                booking_id=booking.booking_id,
                tier_id=booking.tier_id,
                purchased_price=unit_price,
                qr_code_hash=qr_string,
                status="Valid" # Matches your Ticket Enum exactly
            )
            db.add(new_ticket)
            generated_tickets.append(new_ticket)

        # 3. Finalize Booking
        booking.status = "Confirmed"
        db.commit()
        
        return {
            "message": "Payment successful! Tickets generated.",
            "transaction_id": tx_id,
            "tickets_generated": len(generated_tickets)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def get_user_bookings(db: Session, user_id: int):
    # 🚨 This is where the joinedload query actually lives!
    bookings = db.query(models.Booking).options(
        joinedload(models.Booking.tickets),
        joinedload(models.Booking.tier).joinedload(models.TicketTier.event).joinedload(models.Event.venue)
    ).filter(
        models.Booking.user_id == user_id
    ).all()
    
    return bookings
def release_expired_bookings(db: Session):
    """
    Finds pending bookings older than 15 minutes, cancels them, 
    and returns the inventory to the ticket tier.
    """
    # Calculate the cutoff time (15 minutes ago)
    expiration_time = datetime.now() - timedelta(minutes=15)

    latest_pending = db.query(models.Booking).filter(models.Booking.status == "Pending").first()
    if latest_pending:
        print(f"🕵️ DB Cart Created At: {latest_pending.created_at}", flush=True)
        print(f"⏰ Python Cutoff Time : {expiration_time}", flush=True)
    
    # 1. Find all expired carts
    expired_bookings = db.query(models.Booking).filter(
        models.Booking.status == "Pending",
        models.Booking.created_at <= expiration_time
    ).all()

    if not expired_bookings:
        return # Nothing to clean up!

    # 2. Process each abandoned cart
    for booking in expired_bookings:
        # Mark the booking as dead
        booking.status = "Cancelled"
        
        # Give the tickets back to the tier
        tier = db.query(models.TicketTier).filter(
            models.TicketTier.tier_id == booking.tier_id
        ).first()
        
        if tier:
            tier.available_quantity += booking.quantity

    # 3. Save all the changes at once
    db.commit()
    print(f"🧹 Cart Sniper: Released {len(expired_bookings)} abandoned bookings back to inventory.")
    return expired_bookings