from fastapi import APIRouter, Request, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated
from sqlalchemy import func
from app.database import Session, get_database
from app.auth import verify_access_token
from app.models import User, Message
from .chat_routes import manager

# Initialize router
router = APIRouter(tags=["Pages"])

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")


@router.get("/", response_class=HTMLResponse)
async def show_home_page(request: Request):
    """Render the landing/home page"""
    return templates.TemplateResponse("view/home.html", {"request": request})


@router.get("/about", response_class=HTMLResponse)
async def show_about_page(request: Request):
    """Render the about/chat information page"""
    return templates.TemplateResponse("view/about.html", {"request": request})


@router.get("/nexus/dashboard", response_class=HTMLResponse)
async def show_dashboard(
    request: Request, 
    access_token: Annotated[str | None, Cookie(alias="Authorization")] = None, 
    db: Session = Depends(get_database)
):
    """
    Protected dashboard route.
    Requires valid authentication token to access.
    """
    # Redirect to login if no token provided
    if not access_token:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    try: 
        # Verify token and extract user ID
        user_id = verify_access_token(access_token)
        if not user_id:
            raise ValueError("Invalid or expired token")
        
        # Fetch user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise ValueError("User not found in database")
        
        # Render dashboard with user data
        response = templates.TemplateResponse("chat/dashboard.html", {
            "request": request, 
            "user_id": user.id,
            "user_name": user.username
        })

        # Prevent caching to ensure fresh data
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Vary"] = "Cookie"

        return response

    except Exception as e:
        import traceback
        print(traceback.format_exc()) # This will show the EXACT line that failed
        raise e # This will stop the app and show the error in the browser
    

@router.get("/nexus/chat/dm/{receiver_id}", response_class=HTMLResponse)
async def show_chat_page(
    request: Request, 
    receiver_id: int,
    access_token: Annotated[str | None, Cookie(alias="Authorization")] = None,
    db: Session = Depends(get_database)
):
    if not access_token:
        return RedirectResponse(url="/", status_code=303)
    # 1. Reuse your auth logic to get current user
    current_user_id = verify_access_token(access_token)
    print(current_user_id)
    
    # 2. Fetch the person you are talking to
    receiver = db.query(User).filter(User.id == receiver_id).first()
    current_user = db.query(User).filter(User.id == int(current_user_id)).first()

    if not receiver:
        return RedirectResponse(url="/nexus/dashboard", status_code=303)
    
    is_online = receiver.id in manager.active_connections

    return templates.TemplateResponse("chat/simpleChat.html", {
        "request": request,
        "user_id": current_user.id,
        "user_name": current_user.username,
        "receiver_id": receiver.id,
        "receiver_name": receiver.username,
        "is_online": is_online
    })