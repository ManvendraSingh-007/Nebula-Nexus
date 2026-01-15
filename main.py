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



# Exception --- --- --- --- ---

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




# GET --- --- --- --- ---


@app.get("/", response_class=HTMLResponse)
async def show_home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def show_login_page(request: Request, error: str = Cookie(None, alias="error")):
    # Render the file from the templates folder
    response = templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })
    response.delete_cookie(key="error")
    return response

@app.get("/signup", response_class=HTMLResponse)
async def show_signup_page(request: Request, error: str = Cookie(None, alias="error")):
    response = templates.TemplateResponse("signup.html", {
        "request": request,
        "error": error
    })
    response.delete_cookie(key="error")
    return response

@app.get("/about", response_class=HTMLResponse)
async def show_about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/verify-otp", response_class=HTMLResponse)
async def show_otp_page(request: Request, error: str = Cookie(None, alias="error"), pending_email: str = Cookie(None, alias="pending_user_token")):
     # 1. If NO cookie and NO error: They just randomly typed the URL
    if not pending_email and error == None:
        return RedirectResponse(url="/signup/", status_code=303)

    # 2. If NO cookie but there IS an error: They were here, but it expired
    if not pending_email:
        response = templates.TemplateResponse("verify-otp.html", {
            "request": request,
            "error": error
        })
        response.delete_cookie(key="error")
        return response
    
    response = templates.TemplateResponse("verify-otp.html", {
        "request": request,
        "error": error
    })
    response.delete_cookie(key="error")
    return response

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
async def show_dashboard(
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


@app.get("/recover-access-key")
async def show_recover_password_page(
    request: Request, 
    message: str | None = Cookie(default=None) 
):
    # Pass it as 'message' to the HTML
    context = {"request": request, "message": message}
    response = templates.TemplateResponse("forgot-password.html", context)
    
    if message:
        response.delete_cookie(key="message")
        
    return response


@app.get("/reset-access-key")
async def show_password_reset_page(
        request: Request, 
        token: str | None = None, 
        db: Session = Depends(get_database)
    ):
    # 1. If NO token is provided at all
    if not token:
        return RedirectResponse(url="/", status_code=303)

    # 2. Look for the token in the DB
    resetRequest = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.token == token).first()

    # 3. Validation Logic
    if resetRequest:
        # SUCCESS: Show the form to enter the new password
        return templates.TemplateResponse("password-reset.html", {
            "request": request, 
            "error": None,
            "token": token, # Pass the token so the form can submit it back
        })
    else:
        # RENDER the page with an error message (NO REDIRECT)
        return templates.TemplateResponse("password-reset.html", {
            "request": request, 
            "error": "This link has expired or is an invalid one. Please request a new one.",
            "token": None
        })


# POST --- --- --- --- --- ---


# Route to register a new user.
@app.post("/signup", response_model=schemas.UserOut)
def signup(
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
            response = RedirectResponse(url="/signup", status_code=303)
            response.set_cookie(
                key="error",
                value="Cosmic address already exist, return to base?",
                httponly=True,
                samesite="lax",
                secure=True,
                max_age=300
            )

            return response
        
        if existing_user.username == user.username:
            response = RedirectResponse(url="/signup", status_code=303)
            response.set_cookie(
                key="error",
                value="Stellar signature already claimed, pick different",
                httponly=True,
                samesite="lax",
                secure=True,
                max_age=300
            )

            return response


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
        response = RedirectResponse(url="/login", status_code=303)
        response.set_cookie(
            key="error",
            value="Invalid Cosmic address or Access key",
            httponly=True,
            samesite="lax",
            secure=True,
            max_age=300
        )

        return response
    
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
        response = RedirectResponse(url="/verify-otp", status_code=303)
        response.set_cookie(
            key="error",
            value="Session expired, Signup again",
            httponly=True,
            samesite="lax",
            secure=True,
            max_age=300
        )

        return response

    try:
         # 1. Unsign the ID
        user_id = serializer.loads(pending_user_token)

        # 2. Fetch by ID (using .get() - Efficient)
        pending_user = db.get(models.PendingUser, user_id)
        
        if not pending_user or pending_user.otp_code != data.otp:
            # redirect if user not found or if the otp is invalid
            response = RedirectResponse(url="/verify-otp", status_code=303)
            response.set_cookie(
                key="error",
                value="Invalid otp, try again",
                httponly=True,
                samesite="lax",
                secure=True,
                max_age=300
            )

            return response
            
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

        # Create Token (Use 'sub' id)
        access_token = auth.create_access_token({
            "sub": str(register_user.id)
        })

        # Create the response
        response = RedirectResponse(url="/nexus/dashboard", status_code=303)

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
    
            


@app.post("/recover-access-key")
async def recover_access_key(
        request: Request,
        identifier: Annotated[schemas.RequestRecoverAccessKey, Form()],
        background_task: BackgroundTasks,
        db: Session = Depends(get_database)
    ):
    # check if the identifier exist 
    user_exist = db.query(models.User).filter(models.User.email == identifier.email).first()
    if user_exist:
        unique_reset_token = utils.generate_reset_token()
        expire_in = auth.datetime.now(auth.timezone.utc) + auth.timedelta(minutes=15)

        identifier_data = models.PasswordResetToken(
            email=identifier.email,
            token=unique_reset_token,
            expires_at=expire_in
        )

        db.add(identifier_data)
        db.commit()
        db.refresh(identifier_data)

        scheme = request.url.scheme # http or https
        host = request.headers.get("host")
        reset_link = f"{scheme}://{host}/reset-access-key?token={unique_reset_token}"
        background_task.add_task(utils.send_reset_link_email, user_exist.email, reset_link)
    
    response = RedirectResponse(url="/recover-access-key", status_code=303)
    response.set_cookie(
        key="response", 
        value="If this email is registered, you will receive a reset link shortly.", 
        httponly=True,
        samesite="lax",
        secure=True, 
        max_age=300 
    )

    return response




# PUT --- --- --- --- --- ---

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