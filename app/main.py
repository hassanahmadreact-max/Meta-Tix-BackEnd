# app/main.py
from fastapi import FastAPI
from app.controller import auth, events, admin, booking, user ,organizer
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.models.database import SessionLocal # Import your DB session maker!
from app.services.booking_services import release_expired_bookings
from fastapi.middleware.cors import CORSMiddleware

# --- THE BACKGROUND TASK ---
async def cart_cleanup_loop():
    """Runs continuously in the background while the server is alive."""
    while True:
         
        # We need to manually open a database session for background tasks
        db = SessionLocal() 
        try:
            release_expired_bookings(db)
        except Exception as e:
            print(f"Error in Cart Sniper: {e}")
        finally:
            db.close() # Always close the connection!
        # Wait 5 minutes (300 seconds) between each sweep
        await asyncio.sleep(300)

# --- FASTAPI LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # What happens when the server STARTS:
    print("🚀 Starting Background Tasks...")
    task = asyncio.create_task(cart_cleanup_loop())
    
    yield # The server is running here!
    
    # What happens when the server STOPS:
    print("🛑 Shutting down Background Tasks...")
    task.cancel()

# --- APP INIT ---
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # This tells FastAPI to accept requests from your React port!
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"], # Allows POST, GET, PUT, DELETE, etc.
    allow_headers=["*"], # Allows the Authorization header to pass through
)

# Connect the "wires" from the controller
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(organizer.router, prefix="/organizer", tags=["Organizer"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(booking.router, prefix="/booking", tags=["Booking"])

@app.get("/")
def root():
    return {"message": "Ticket System is Underconstruction!"}