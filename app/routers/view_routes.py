from fastapi import APIRouter, Request, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Annotated

from app.database import Session, get_database
from app.auth import verify_access_token
from app.models import User

# Initialize router
router = APIRouter(tags=["Pages"])

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")


@router.get("/", response_class=HTMLResponse)
async def show_home_page(request: Request):
    """Render the landing/home page"""
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/about", response_class=HTMLResponse)
async def show_about_page(request: Request):
    """Render the about/chat information page"""
    return templates.TemplateResponse("chat.html", {"request": request})


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
        # Clean and validate the token
        clean_token = access_token.strip('"') 
        if clean_token.startswith("Bearer "):
            clean_token = clean_token.replace("Bearer ", "")
            
        # Verify token and extract user ID
        user_id = verify_access_token(clean_token)
        if not user_id:
            raise ValueError("Invalid or expired token")
        
        # Fetch user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise ValueError("User not found in database")
        
        # Render dashboard with user data
        response = templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user": user.username,
            "sender_id": user.id,
            "email": user.email
        })

        # Prevent caching to ensure fresh data
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Vary"] = "Cookie"

        return response

    except (ValueError, Exception) as e:
        # Log error and redirect to login on failure
        print(f"Dashboard access failed: {e}")
        return RedirectResponse(url="/login", status_code=303)