from fastapi import APIRouter, BackgroundTasks, Request, status, HTTPException, Depends, Form, Cookie
from app.database import Session, get_database
from app.schemas import UserOut, UserCreate, RequestLogin, VerifyOtp, RequestRecoverAccessKey, ResetAccessKey
from app.models import User, PendingUser, PasswordResetToken
from typing import Annotated
from app.utils import hash_password, generate_otp, hash_token, verify_password, generate_reset_token
from app.auth import create_access_token, timedelta, timezone, datetime
from itsdangerous import URLSafeSerializer
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.config import Config


# Initialize serializer for secure cookie signing
serializer = URLSafeSerializer(Config.SECRET_KEY)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")




# GET ROUTES - Page Rendering --- --- ---

@router.get("/signup", response_class=HTMLResponse)
async def show_signup_page(request: Request, error: str = Cookie(None, alias="error")):
    """Render the signup page with any stored error messages"""
    response = templates.TemplateResponse("signup.html", {
        "request": request,
        "error": error
    })
    response.delete_cookie(key="error")  # Clear after displaying
    return response


@router.get("/login", response_class=HTMLResponse)
async def show_login_page(
    request: Request, 
    error: str = Cookie(None, alias="error"), 
    success_msg: str = Cookie(None, alias="message")
):
    """Render login page with error/success messages from cookies"""
    response = templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "success_msg": success_msg
    })
    
    # Clean up cookies after displaying
    if error:
        response.delete_cookie(key="error")
    if success_msg:
        response.delete_cookie(key="success_message")
    return response


@router.get("/verify-otp", response_class=HTMLResponse)
async def show_otp_page(
    request: Request, 
    error: str = Cookie(None, alias="error"), 
    pending_email: str = Cookie(None, alias="pending_user_token")
):
    """
    Show OTP verification page.
    Redirects to signup if user arrives here without proper session.
    """
    # Prevent direct access without going through signup
    if not pending_email and error is None:
        return RedirectResponse(url="/auth/signup", status_code=303)

    response = templates.TemplateResponse("verify-otp.html", {
        "request": request,
        "error": error
    })
    
    if error:
        response.delete_cookie(key="error")
    return response


@router.get("/recover-access-key")
async def show_recover_password_page(
    request: Request, 
    message: str | None = Cookie(alias="response", default=None) 
):
    """Display password recovery form with status message"""
    context = {"request": request, "message": message}
    response = templates.TemplateResponse("forgot-password.html", context)
    
    if message:
        response.delete_cookie(key="response")  # One-time message
    return response


@router.get("/reset-access-key")
async def show_password_reset_page(
    request: Request, 
    token: str | None = None, 
    db: Session = Depends(get_database)
):
    """
    Display password reset form.
    Validates reset token before allowing password change.
    """
    if not token:
        return RedirectResponse(url="/", status_code=303)
    
    hashed_token = hash_token(token)
    resetRequest = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == hashed_token
    ).first()

    if resetRequest:
        # Valid token - show reset form
        return templates.TemplateResponse("password-reset.html", {
            "request": request, 
            "error": None,
            "token": token,  # Pass token back for form submission
        })
    else:
        # Invalid/expired token
        return templates.TemplateResponse("password-reset.html", {
            "request": request, 
            "error": "This link has expired or is invalid. Please request a new one.",
            "token": None
        })




# POST ROUTES - Form Processing --- --- ---

@router.post("/signup", response_model=UserOut)
def signup(
    background_tasks: BackgroundTasks,
    user: Annotated[UserCreate, Form()], 
    db: Session = Depends(get_database)
):
    """
    Handle new user registration.
    Creates pending user record and sends OTP for verification.
    """
    # Check if user already exists in main database
    existing_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()

    if existing_user:
        # Handle duplicate email or username with appropriate messages
        response = RedirectResponse(url="/auth/signup", status_code=303)
        error_msg = "Cosmic address already exist" if existing_user.email == user.email \
                   else "Stellar signature already claimed"
        
        response.set_cookie(
            key="error",
            value=error_msg,
            httponly=True,
            samesite="lax",
            secure=True,
            max_age=300
        )
        return response

    # Check if already in pending registration
    pending_exists = db.query(PendingUser).filter(
        (PendingUser.email == user.email) | (PendingUser.username == user.username)
    ).first()

    if not pending_exists:
        # Create new pending user with OTP
        hashed_password = hash_password(user.password)
        generated_otp = generate_otp()
        
        new_pending = PendingUser(
            username=user.username, 
            email=user.email, 
            password=hashed_password,
            otp_code=generated_otp
        )

        db.add(new_pending)
        db.commit()
        db.refresh(new_pending)

        # In production: send email with OTP
        # background_tasks.add_task(send_otp_email, new_pending.email, generated_otp)
        print(f"OTP for {user.email}: {generated_otp}")

    # Create secure session token for pending user
    signed_id = serializer.dumps(new_pending.id)
    
    # Redirect to OTP verification
    redirect = RedirectResponse(url="/auth/verify-otp/", status_code=303)
    redirect.set_cookie(
        key="pending_user_token", 
        value=signed_id,
        httponly=True,
        secure=True, 
        samesite="Lax",
        max_age=300  # 5 minute window for OTP entry
    )
    return redirect


@router.post("/login")
def login(
    credential: Annotated[RequestLogin, Form()], 
    db: Session = Depends(get_database)
):
    """Authenticate user and issue JWT access token"""
    user = db.query(User).filter(User.email == credential.email).first() 
    
    # Validate credentials
    if not user or not verify_password(credential.password, user.password): 
        response = RedirectResponse(url="/auth/login", status_code=303)
        response.set_cookie(
            key="error",
            value="Invalid Cosmic address or Access key",
            httponly=True,
            samesite="lax",
            secure=True,
            max_age=300
        )
        return response
    
    # Generate access token
    access_token = create_access_token({"sub": str(user.id)})
    
    # Set auth cookie and redirect to dashboard
    response = RedirectResponse(url="/nexus/dashboard", status_code=303)
    response.set_cookie(
        key="Authorization", 
        value=f"Bearer {access_token}", 
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=3600  # 1 hour session
    )
    return response


@router.post("/verify-otp")
async def verify_otp(
    data: Annotated[VerifyOtp, Form()], 
    pending_user_token: str = Cookie(None, alias="pending_user_token"),
    db: Session = Depends(get_database)
):
    """Verify OTP and complete user registration"""
    if not pending_user_token:
        response = RedirectResponse(url="/auth/verify-otp", status_code=303)
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
        # Retrieve pending user from signed token
        user_id = serializer.loads(pending_user_token)
        pending_user = db.get(PendingUser, user_id)
        
        # Validate OTP
        if not pending_user or pending_user.otp_code != data.otp:
            response = RedirectResponse(url="/auth/verify-otp", status_code=303)
            response.set_cookie(
                key="error",
                value="Invalid OTP, try again",
                httponly=True,
                samesite="lax",
                secure=True,
                max_age=300
            )
            return response
            
        # Move from pending to active user
        register_user = User(
            username=pending_user.username,
            email=pending_user.email,
            password=pending_user.password
        )
        db.add(register_user)
        db.delete(pending_user)  # Clean up pending record
        db.commit()
        db.refresh(register_user)

        # Issue access token for immediate login
        access_token = create_access_token({"sub": str(register_user.id)})

        response = RedirectResponse(url="/nexus/dashboard", status_code=303)
        response.set_cookie(
            key="Authorization", 
            value=f"Bearer {access_token}", 
            httponly=True,
            samesite="lax",
            secure=True,
            max_age=3600
        )
        
        # Clean up pending session cookie
        response.delete_cookie("pending_user_token")
        return response

    except Exception as e:
        db.rollback()
        print(f"Database Error during OTP verification: {e}")
        raise


@router.post("/logout")
async def logout():
    """Clear authentication cookies and session data"""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Remove auth cookie
    response.delete_cookie(
        key="Authorization",
        path="/",
        httponly=True,
        samesite="lax"
    )

    # Clear browser storage
    response.headers["Clear-Site-Data"] = '"cache", "cookies", "storage"'
    return response


@router.post("/recover-access-key")
async def send_recovery_instruction(
    request: Request,
    identifier: Annotated[RequestRecoverAccessKey, Form()],
    background_task: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """Initiate password reset process"""
    user_exist = db.query(User).filter(User.email == identifier.email).first()
    pending_reset_user = db.query(PasswordResetToken).filter(
        PasswordResetToken.email == identifier.email
    ).first()
    
    # Create reset token if user exists and no pending request
    if not pending_reset_user and user_exist:
        unique_reset_token = generate_reset_token()
        expire_in = datetime.now(timezone.utc) + timedelta(minutes=10)

        identifier_data = PasswordResetToken(
            email=identifier.email,
            token=hash_token(unique_reset_token),
            expires_at=expire_in
        )

        db.add(identifier_data)
        db.commit()
        db.refresh(identifier_data)

        # Generate reset link (in production, send via email)
        scheme = request.url.scheme
        host = request.headers.get("host")
        reset_link = f"{scheme}://{host}/auth/reset-access-key?token={unique_reset_token}"
        print(f"Reset link for {identifier.email}: {reset_link}")
        # background_task.add_task(send_reset_link_email, user_exist.email, reset_link)
    
    # Always show same message for security (prevent email enumeration)
    response = RedirectResponse(url="/auth/recover-access-key", status_code=303)
    response.set_cookie(
        key="response", 
        value="If this email is registered, you will receive a reset link shortly.", 
        httponly=True,
        samesite="lax",
        secure=True, 
        max_age=300 
    )
    return response


@router.post("/reset-access-key")
async def reset_password(
    incoming_credential: Annotated[ResetAccessKey, Form()], 
    db: Session = Depends(get_database)
):
    """Process password reset with valid token"""
    hashed_token = hash_token(incoming_credential.reset_token)
    
    # Find valid reset request
    reset_request = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == hashed_token
    ).first()

    if not reset_request:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    try:
        # Update user password
        user = db.query(User).filter(User.email == reset_request.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        user.password = hash_password(incoming_credential.new_password)
        
        # Delete used token (one-time use)
        db.delete(reset_request)
        db.commit()
        
        # Notify user and redirect to login
        response = RedirectResponse(url="/auth/login", status_code=303)
        response.set_cookie(
            key="message",
            value="Access Key Recalibrated",
            max_age=300,
            secure=True,
            httponly=True,
            samesite="lax"
        )
        return response

    except Exception as e:
        db.rollback()
        print(f"Error during password reset: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")