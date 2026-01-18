from fastapi import APIRouter, Request, Cookie, Depends
from app.database import Session, get_database
from app.auth import verify_access_token
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.models import User
from typing import Annotated

router = APIRouter(tags=["Authentication"])

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")

@router.get("/", response_class=HTMLResponse)
async def show_home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/about", response_class=HTMLResponse)
async def show_about_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@router.get("/nexus/dashboard", response_class=HTMLResponse)
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
        user_id = verify_access_token(clean_token)
        if not user_id:
            raise Exception("User does not exist in db")
        
        user= db.query(User).filter(User.id == int(user_id)).first()

        
        response = templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user": user.username,
            "sender_id": user.id,
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