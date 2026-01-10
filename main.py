from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, Form, Cookie, status, BackgroundTasks

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


@app.get("/login", response_class=HTMLResponse)
async def show_login_page(request: Request, error: str = None):
    # Render the file from the templates folder
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })

@app.get("/signup", response_class=HTMLResponse)
async def show_signup_page(request: Request, error: str = None, error_type: str = None):
     # Provide a default empty list if no error exists
    error_data = [error, error_type] if error else [False, False]
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "error": error_data
    })

@app.get("/about", response_class=HTMLResponse)
async def show_about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/verify-otp", response_class=HTMLResponse)
async def show_otp_page(request: Request, error: str | None = None):
    return templates.TemplateResponse("verify-otp.html", {
        "request": request,
        "error": error
    })

@app.get("/registered", response_class=HTMLResponse)
async def show_success_registed(request: Request):
    return templates.TemplateResponse("register-successful.html", {"request": request})

# Fetches a list of all users from the database.
@app.get("/users", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_database)):
    return db.query(models.User).all()

# Protected route: Uses auth.get_current_user to ensure only logged-in users see their info.
@app.get("/users/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {
        "email": current_user.email,
        "username": current_user.username
    }


@app.get("/dashboard", response_class=HTMLResponse)
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
        user_email, username = auth.verify_access_token(clean_token)
        
        response = templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user": username,
            "email": user_email
        })

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"


        return response

    except Exception as e:
        # If it fails, check your terminal for this print message:
        print(f"DEBUG: Token verification failed: {e}")
        return RedirectResponse(url="/login", status_code=303)



@app.get("/logout")
async def logout():
    # 1. Redirect to home page
    response = RedirectResponse(url="/", status_code=303)
    
    # 2. Instruct the browser to delete the cookie
    # Important: 'Path' must match the path where the cookie was originally set
    response.delete_cookie(key="access_token", path="/")
    return response



# POST --- --- --- --- --- ---


# Route to register a new user.
@app.post("/signup", response_model=schemas.UserOut)
def create_user(
        background_tasks: BackgroundTasks,
        user: Annotated[schemas.UserCreate, Form()], 
        db: Session = Depends(get_database)
    ):

    existing_email = db.query(models.User).filter(models.User.email == user.email).first()
    existing_username = db.query(models.User).filter(models.User.username == user.username).first()

    # check if email already exist if yes then show error
    if existing_email:
        return RedirectResponse(
            url="/signup?error=Cosmic Address already registered&error_type=email", 
            status_code=303  # <--- CRITICAL FIX
        )

    # check if username already exist if yes then show error
    if existing_username:
        return RedirectResponse(
            url="/signup?error=Stellar Signature already claimed&error_type=username", 
            status_code=303  # <--- CRITICAL FIX
        )


    # check if the user exist in pending user
    if db.query(models.PendingUser).filter(
        (models.PendingUser.email == user.email) | (models.PendingUser.username == user.username)).first():
        redirect = RedirectResponse(url="/verify-otp", status_code=303)
        redirect.set_cookie(
            key="pending_verification_email", 
            value=user.email, # Set a secure cookie containing the email
            httponly=False, # httponly=True: Prevents JS access (XSS protection)
            secure=False, # secure=True: Only sends over HTTPS, False for now
             # samesite="Lax", # samesite="Lax": Prevents CSRF while allowing redirects
            max_age=300  # Expires in 5 minutes (matching your TTL)
        )
        return redirect

    # if user does not exist
    else:
        # Encrypt the plain text password before storing it.
        hashed_password = utils.hash_password(user.password)
        generated_otp = utils.generate_otp()
        pending_user = models.PendingUser(
            username=user.username, 
            email=user.email, 
            password=hashed_password,
            otp_code=generated_otp
        )

        db.add(pending_user)
        db.commit()
        db.refresh(pending_user)

        # background_tasks.add_task(utils.send_otp_email, user.email, generated_otp)
        redirect = RedirectResponse(url="/verify-otp", status_code=303)
        redirect.set_cookie(
            key="pending_verification_email", 
            value=user.email, # Set a secure cookie containing the email
            httponly=True, # httponly=True: Prevents JS access (XSS protection)
            secure=False, # secure=True: Only sends over HTTPS, False for now
            samesite="Lax", # samesite="Lax": Prevents CSRF while allowing redirects
            max_age=300  # Expires in 5 minutes (matching your TTL)
        )
        return redirect



# Route to verify credentials and issue a security token.
@app.post("/login")
def login(credential: Annotated[schemas.RequestLogin, Form()], db: Session = Depends(get_database)): 
    # checks for user email in db
    user = db.query(models.User).filter(models.User.email == credential.email).first() 
    
    # if no email found or if the password does not match -> redirect to login with the exception
    if not user or not utils.verify_password(credential.password, user.password): 
        return RedirectResponse(
            url="/login?error=Invalid Cosmic Address or Access Key", 
            status_code=303
        )
    
    # if everything found issue a access token
    access_token = auth.create_access_token({"email": str(user.email), "user": str(user.username)})
    
    # 1. Create the redirect object
    response = RedirectResponse(url="/dashboard", status_code=303)
    
    # 2. Set the cookie on THAT instance
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,
        samesite="lax",
        secure=False  # Set to True if using HTTPS (production)
    )
    return response


@app.post("/verify-otp")
async def verify_otp(
        data: Annotated[schemas.VerifyOtp, Form()], 
        pending_email: str = Cookie(None, alias="pending_verification_email"),
        db: Session = Depends(get_database)
    ):

    if not pending_email:
        return RedirectResponse(url="/verify-otp?error=Otp expired", status_code=303)
    
    # check the user with corrosponding pending_email
    user = db.query(models.PendingUser).filter(models.PendingUser.email == pending_email).first()

    try:
        # if yes
        if user:
            if data.otp == user.otp_code:
                register_user = models.User(
                    username=user.username,
                    email=user.email,
                    password=user.password
                )

                db.add(register_user)
                db.commit()
                db.refresh(register_user)


                return RedirectResponse(url="/registered", status_code=303)

            # if otp does not match
            else:
                return RedirectResponse(url="/verify-otp?error=Invalid otp", status_code=303)
        
    except Exception as e:
        print(e)
    
            



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