from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.models import models
from app.models.database import get_db
from app import schema
from app.services import user_services
from app.core import security
from app.api import deps
# Import the tools to verify and hash passwords
from app.core.security import verify_password, get_password_hash 

router = APIRouter()

# --- 1. REGISTER ---
@router.post("/registeration", response_model=schema.UserResponse)
def create_user(user: schema.UserCreate, db: Session = Depends(get_db)):
    db_user = user_services.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_services.create_user(db=db, user=user)

# --- 2. LOGIN ---
@router.post("/login", response_model=schema.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_services.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- 3. CHANGE PASSWORD (NEW) ---
@router.patch("/change-password")
def change_password(
    password_data: schema.ChangePasswordRequest, # Ensure this is in schema.py
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Verifies old password and sets the new one.
    """
    # A. Verify Old Password
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    # B. Prevent reusing the same password
    if password_data.old_password == password_data.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as old password")

    # C. Hash & Save
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}