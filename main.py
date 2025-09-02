from fastapi import FastAPI, Depends
from database import Base, engine, get_database, Session
import models
import schemas


Base.metadata.create_all(bind=engine)
app = FastAPI()

@app.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_database)):
    new_user = models.User(username=user.username, email=user.email, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_database)):
    return db.query(models.User).all()