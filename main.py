import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import User
from schemas import RegisterSchema, LoginSchema
from auth_utils import hash_password, verify_password, create_token

# ================= APP =================
app = FastAPI(title="Auth API")

# ================= STATIC =================
os.makedirs("uploads/profiles", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ================= DB =================
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= REGISTER =================
@app.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
        image=None,
    )
    db.add(user)
    db.commit()

    return {"message": "Registration successful"}

# ================= LOGIN =================
@app.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.email)

    return {
        "access_token": token,
        "user": {
            "name": user.name,
            "email": user.email,
            "image_url": (
                f"http://192.168.68.123:8000{user.image}"
                if user.image else None
            )
        }
    }

# ================= UPLOAD IMAGE =================
@app.post("/upload-profile-image/{email}")
def upload_profile_image(
    email: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    filename = f"{email}_{file.filename}"
    path = f"uploads/profiles/{filename}"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user.image = f"/uploads/profiles/{filename}"
    db.commit()

    return {
        "image_url": f"http://192.168.68.123:8000{user.image}"
    }
