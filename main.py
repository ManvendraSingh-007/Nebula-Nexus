from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, Form, Cookie, status, BackgroundTasks

from database import Base, engine, get_database, Session
import models, schemas, utils, auth, config
from typing import List, Annotated

from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from itsdangerous import URLSafeSerializer



Base.metadata.create_all(bind=engine)
# Tells the database to create any tables defined in my code that are missing.
# It uses the "engine" connection to know which database to talk to.

app = FastAPI()
# Initialize the FastAPI framework. 
# This variable 'app' is the core of the project and will handle all incoming requests.

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

serializer = URLSafeSerializer(config.Config.SECRET_KEY)



# Exception --- --- ---

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "404.html", 
        {"request": request}, 
        status_code=404
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):

    # Check if the user tried to visit /logout specifically
    if request.url.path == "/logout":
        # Redirect them back to the dashboard or home
        return RedirectResponse(url="/nexus/dashboard", status_code=303)
    
    # For any other 405, show a custom error page or redirect to home
    return templates.TemplateResponse("405.html", {"request": request}, status_code=405)




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
async def show_signup_page(request: Request, error: str = None):
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "error": error
    })

@app.get("/about", response_class=HTMLResponse)
async def show_about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/verify-otp", response_class=HTMLResponse)
async def show_otp_page(request: Request, error: str | None = None, pending_email: str = Cookie(None, alias="pending_user_token")):
     # 1. If NO cookie and NO error in URL: They just randomly typed the URL
    if not pending_email and error == None:
        return RedirectResponse(url="/signup/", status_code=303)

    # 2. If NO cookie but there IS an error: They were here, but it expired
    if not pending_email:
        return templates.TemplateResponse("verify-otp.html", {
            "request": request, 
            "error": "Your session has expired. Please sign up again."
        })
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


@app.get("/nexus/dashboard", response_class=HTMLResponse)
async def dashboard(
        request: Request, 
        access_token: Annotated[str | None, Cookie(alias="Authorization")] = None, 
        db: Session = Depends(get_database)
    ):
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
        user_id = auth.verify_access_token(clean_token)
        if not user_id:
            raise Exception("User does not exist in db")
        
        user= db.query(models.User).filter(models.User.id == int(user_id)).first()

        
        response = templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user": user.username,
            "email": user.email
        })

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Vary"] = "Cookie"


        return response

    except Exception as e:
        db.rollback()
        # If it fails, check your terminal for this print message:
        print(f"DEBUG: Token verification failed: {e}")
        return RedirectResponse(url="/login", status_code=303)



@app.post("/logout")
async def logout():
    # 303 See Other is the correct status for redirecting after a POST
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Securely wipe the token
    response.delete_cookie(
        key="Authorization",
        path="/",
        httponly=True,
        samesite="lax"
    )

    response.headers["Clear-Site-Data"] = '"cache", "cookies", "storage"'
    return response



# POST --- --- --- --- --- ---


# Route to register a new user.
@app.post("/signup", response_model=schemas.UserOut)
def create_user(
        background_tasks: BackgroundTasks,
        user: Annotated[schemas.UserCreate, Form()], 
        db: Session = Depends(get_database)
    ):

    # 1. check if a user exist with same credential already in db using email and username from the new user
    existing_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()

    if existing_user:
        # 2. check for email and username matches
        if existing_user.email == user.email:
            return RedirectResponse(
                url="/signup?error=Cosmic Address already registered", 
                status_code=303
            )
        
        if existing_user.username == user.username:
            return RedirectResponse(
                url="/signup?error=Stellar Signature already claimed", 
                status_code=303
            )


    # 1. check if the new user exist in the pending_user tabel
    pending_exists = db.query(models.PendingUser).filter(
        (models.PendingUser.email == user.email) | (models.PendingUser.username == user.username)
    ).first()

    # 2. If the user does NOT exist, create them
    if not pending_exists:
        hashed_password = utils.hash_password(user.password)
        generated_otp = utils.generate_otp()
        
        new_pending = models.PendingUser(
            username=user.username, 
            email=user.email, 
            password=hashed_password,
            otp_code=generated_otp
        )

        db.add(new_pending)
        db.commit()
        db.refresh(new_pending)

        # Send email in background
        background_tasks.add_task(utils.send_otp_email, new_pending.email, generated_otp)

    # 3. Sign the ID
    signed_id = serializer.dumps(new_pending.id)
    
    # 4. Final Step: Handle Redirect and Cookie (Executed for both New and Existing users)
    redirect = RedirectResponse(url="/verify-otp/", status_code=303)
    redirect.set_cookie(
        key="pending_user_token", 
        value=signed_id,
        httponly=True,  # Set to True for security!
        secure=True, 
        samesite="Lax",
        max_age=300
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
    access_token = auth.create_access_token({"sub": str(user.id)})
    
    # 1. Create the redirect object
    response = RedirectResponse(url="/nexus/dashboard", status_code=303)
    
    # 2. Set the cookie on THAT instance
    response.set_cookie(
        key="Authorization", 
        value=f"Bearer {access_token}", 
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=3600
    )
    return response


@app.post("/verify-otp")
async def verify_otp(
        data: Annotated[schemas.VerifyOtp, Form()], 
        pending_user_token: str = Cookie(None, alias="pending_user_token"),
        db: Session = Depends(get_database)
    ):

    if not pending_user_token:
        return RedirectResponse(url="/verify-otp?error=Session expired, signup again", status_code=303)

    try:
         # 1. Unsign the ID
        user_id = serializer.loads(pending_user_token)

        # 2. Fetch by ID (using .get() - Efficient)
        pending_user = db.get(models.PendingUser, user_id)
        
        if not pending_user or pending_user.otp_code != data.otp:
            # redirect if user not found or if the otp is invalid
            return RedirectResponse(url="/verify-otp?error=Invalid otp, try again", status_code=303)
        
        # Create new user
        register_user = models.User(
            username=pending_user.username,
            email=pending_user.email,
            password=pending_user.password
        )
        db.add(register_user)
        
        # Delete pending user
        db.delete(pending_user) 
        
        # Commit both at once
        db.commit()
        db.refresh(register_user)

        # Create the response
        response = RedirectResponse(url="/registered", status_code=303)
        
        # Create Token (Use 'sub' id)
        access_token = auth.create_access_token({
            "sub": str(register_user.id)
        })

        # Set Cookie
        response.set_cookie(
            key="Authorization", 
            value=f"Bearer {access_token}", 
            httponly=True,
            samesite="lax",
            secure=True,  #
            max_age=3600  # Set an expiration ( 1 hour)
        )
        
        # 5. Clean up the pending cookie
        response.delete_cookie("pending_user_token")
        return response

    except Exception as e:
        db.rollback() #  roll back if anything fails
        print(f"Database Error: {e}")
    
            



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