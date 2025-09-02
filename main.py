from fastapi import FastAPI, Depends, HTTPException
from database import Base, engine, get_database, Session
import models, schemas, utils


Base.metadata.create_all(bind=engine)
app = FastAPI()

@app.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_database)):

    hashed_password = utils.hash_password(user.password)
    new_user = models.User(
        username=user.username, 
        email=user.email, 
        password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login/", response_model=schemas.LoginOut)
def login(credential: schemas.RequestLogin, db: Session = Depends(get_database)): 
    user = db.query(models.User).filter(models.User.email == credential.email).first() 
    if not user or not utils.verify_password: 
        raise HTTPException(status_code=404, detail="Invalid Credential") 
    
    return { "email": user.email, "description": "login success" }

@app.get("/users/", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_database)):
    return db.query(models.User).all()