from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.users import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=['auth'])

@router.post("/register",response_model=UserRead, status_code=201)
def register(user_in : UserCreate,db : Session= Depends(get_db)):
    existing = db.query(User).filter(
            (User.email== user_in.email) | (User.username == user_in.username)
            ).first()
    if existing:
        raise HTTPException (400,"Email or username already registered")
    user = User(
            email = user_in.email,
            username = user_in.username,
            password_hash = hash_password(user_in.password)
            )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(form_data : OAuth2PasswordRequestForm = Depends(), db: Session= Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(401, detail="Invalid email or password")
    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token)

@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
