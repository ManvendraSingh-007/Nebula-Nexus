from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, Form, Cookie, status

from database import Base, engine, get_database, Session
import models, schemas, utils, auth
from typing import List, Annotated

from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


Base.metadata.create_all(bind=engine)
# Tells the database to create any tables defined in my code that are missing.
# It uses the "engine" connection to know which database to talk to.

app = FastAPI()
# Initialize the FastAPI framework. 
# This variable 'app' is the core of the project and will handle all incoming requests.

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# GET ---


@app.get("/", response_class=HTMLResponse)
async def show_home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/login/", response_class=HTMLResponse)
async def show_login_page(request: Request):
    # Render the file from the templates folder
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup/", response_class=HTMLResponse)
async def show_signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def show_about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

# Fetches a list of all users from the database.
@app.get("/users/", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_database)):
    return db.query(models.User).all()

# Protected route: Uses auth.get_current_user to ensure only logged-in users see their info.
@app.get("/users/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {
        "email": current_user.email,
        "username": current_user.username
    }


@app.get("/dashboard/", response_class=HTMLResponse)
async def dashboard(request: Request, access_token: Annotated[str | None, Cookie()] = None):
    if not access_token:
        return RedirectResponse(url="/login/", status_code=303)
    
    try:
        # 1. CLEAN THE TOKEN STRING
        # Strip double quotes that browsers often wrap around cookie values
        clean_token = access_token.strip('"') 
        
        # 2. REMOVE THE PREFIX
        if clean_token.startswith("Bearer "):
            clean_token = clean_token.replace("Bearer ", "")
            
        # 3. VERIFY
        # Pass the cleaned string to your verification function
        user_email = auth.verify_access_token(clean_token) 
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user": user_email
        })
    except Exception as e:
        # If it fails, check your terminal for this print message:
        print(f"DEBUG: Token verification failed: {e}")
        return RedirectResponse(url="/login/", status_code=303)



@app.get("/logout/")
async def logout():
    # 1. Redirect to login page
    response = RedirectResponse(url="/login/", status_code=status.HTTP_303_SEE_OTHER)
    
    # 2. Instruct the browser to delete the cookie
    # Important: 'Path' must match the path where the cookie was originally set
    response.delete_cookie(key="access_token", path="/")
    
    return response



# POST ---

# Route to register a new user.
@app.post("/signup/", response_model=schemas.UserOut)
def create_user(user: Annotated[schemas.UserCreate, Form()], db: Session = Depends(get_database)):
    # Encrypt the plain text password before storing it.
    hashed_password = utils.hash_password(user.password)
    
    # Map the validated incoming data to the Database Model.
    new_user = models.User(
        username=user.username, 
        email=user.email, 
        password=hashed_password)
    
    # 1. Add the object to the session. 2. Save it to DB. 3. Get the new ID/data back.
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse(url="/login/", status_code=status.HTTP_303_SEE_OTHER)



# Route to verify credentials and issue a security token.
@app.post("/login/")
def login(credential: Annotated[schemas.RequestLogin, Form()], db: Session = Depends(get_database)): 
    user = db.query(models.User).filter(models.User.email == credential.email).first() 
    
    if not user or not utils.verify_password(credential.password, user.password): 
        raise HTTPException(status_code=404, detail="Invalid Credential") 
    
    access_token = auth.create_access_token({"sub": str(user.email)})
    
    # 1. Create the redirect object
    response = RedirectResponse(url="/dashboard/", status_code=303)
    
    # 2. Set the cookie on THAT instance
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,
        samesite="lax",
        secure=False  # Set to True if using HTTPS (production)
    )
    return response




# PUT ---

# Protected route: Updates the profile of the currently logged-in user.
@app.put("/users/me", response_model=schemas.UserOut)
def update_me(
    updated: schemas.UpdateUser,
    db: Session = Depends(get_database),
    current_user: models.User = Depends(auth.get_current_user),
    ):
    # Overwrite current data with new data from the request.
    current_user.username = updated.username
    current_user.password = utils.hash_password(updated.password)

    db.commit() # Save changes to the existing record.
    db.refresh(current_user)

    return current_user





# DELETE ---

# Protected route: Permanently removes the current user's account from the database.
@app.delete("/users/me")
def delete_me(to_delete_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_database)):
    db.delete(to_delete_user)
    db.commit()
    return {"detail": "User deleted successfully"}