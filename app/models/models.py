from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import enum

# --- ENUMS --- 
class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    ORGANIZER = "Organizer"
    CUSTOMER = "Customer"

class EventStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"

# --- TABLES ---

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    created_at = Column(DateTime, server_default=func.now())
    is_organizer_pending = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Relationship to Events (Organizer's events)
    events = relationship("Event", back_populates="organizer")


class Venue(Base):
    __tablename__ = "venues"
    venue_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    address = Column(Text)
    total_capacity = Column(Integer, nullable=False)

    # Relationship to Events (Venue hosts many events)
    events = relationship("Event", back_populates="venue")


class Event(Base):
    __tablename__ = "events"
    event_id = Column(Integer, primary_key=True)
    organizer_id = Column(Integer, ForeignKey("users.user_id")) # Explicit Integer type is safer
    venue_id = Column(Integer, ForeignKey("venues.venue_id"))   # Explicit Integer type is safer
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(EventStatus), default=EventStatus.PENDING)
    rejection_reason = Column(Text)
    isactive = Column(Boolean, default=True)

    # --- RELATIONSHIPS (The Fix!) ---
    organizer = relationship("User", back_populates="events")
    venue = relationship("Venue", back_populates="events")
    
    # Children relationships (One-to-Many)
    schedules = relationship("EventSchedule", back_populates="event", cascade="all, delete-orphan")
    tiers = relationship("TicketTier", back_populates="event", cascade="all, delete-orphan")


class EventSchedule(Base):
    __tablename__ = "event_schedules"
    schedule_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    schedule_name = Column(String(100))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # Relationship back to Event
    event = relationship("Event", back_populates="schedules")


class TicketTier(Base):
    __tablename__ = "ticket_tiers"
    tier_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    tier_name = Column(String(100), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=False)
    available_quantity = Column(Integer, nullable=False)

    # Relationship back to Event
    event = relationship("Event", back_populates="tiers")


class Booking(Base):
    __tablename__ = "bookings"
    booking_id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.user_id"))
    tier_id = Column(Integer, ForeignKey("ticket_tiers.tier_id")) 
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum("Pending", "Confirmed", "Cancelled", name="booking_status"), default="Pending")
    created_at = Column(DateTime, server_default=func.now())
    tickets = relationship("Ticket", back_populates="booking")

    tier = relationship("TicketTier")

    @property
    def event(self):
        if self.tier and self.tier.event:
            return {
                "title": self.tier.event.title,
                "venue_name": self.tier.event.venue.name if self.tier.event.venue else "TBA"
            }
        return None

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True)
    booking_id = Column(ForeignKey("bookings.booking_id"), unique=True)
    transaction_id = Column(String(255))
    payment_method = Column(String(50), default="Card")
    status = Column(Enum("Successful", "Failed", name="payment_status"), default="Successful")
    timestamp = Column(DateTime, server_default=func.now())
    


class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id = Column(Integer, primary_key=True)
    booking_id = Column(ForeignKey("bookings.booking_id"))
    tier_id = Column(ForeignKey("ticket_tiers.tier_id"))
    purchased_price = Column(Numeric(10, 2), nullable=False)
    seat_identifier = Column(String(50))
    qr_code_hash = Column(String(255), unique=True, nullable=False)
    status = Column(Enum("Valid", "Scanned", "Cancelled", name="ticket_status"), default="Valid")
    booking = relationship("Booking", back_populates="tickets")