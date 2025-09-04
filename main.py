from fastapi import FastAPI, Depends, HTTPException
from database import Base, engine, get_database, Session
import models, schemas, utils, auth


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
    if not user or utils.verify_password(credential.email, user.password): 
        raise HTTPException(
            status_code=404, 
            detail="Invalid Credential"
        ) 
    
    access_token = auth.create_access_token({"sub": str(user.email)})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/users/", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_database)):
    return db.query(models.User).all()


@app.get("/users/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {
        current_user.email,
        current_user.username
    }

@app.put("/users/me", response_model=schemas.UserOut)
def update_me(
    updated: schemas.UpdateUser,
    db: Session = Depends(get_database),
    current_user: models.User = Depends(auth.get_current_user),
    ):
    current_user.username = updated.username
    current_user.password = utils.hash_password(updated.password)

    db.commit()
    db.refresh(current_user)

    return current_user

@app.delete("/users/me")
def delete_me(to_delete_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_database)):
    db.delete(to_delete_user)
    db.commit()
    return {"detail": "User deleted successfully"}