from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import engine, Base
from app.routers import auth_routes, view_routes, chat_routes, user_routes

# 1. Create Tables
Base.metadata.create_all(bind=engine)

# 2. Initialize App
app = FastAPI()

# 3. Mount Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 4. Include Routers
app.include_router(auth_routes.router)
app.include_router(view_routes.router)
app.include_router(chat_routes.router)
app.include_router(user_routes.router)





# Exception Handlers --- --- --- --- ---
@app.exception_handler(404) 
async def not_found_handler(request: Request, exc: Exception):
    return templates.TemplateResponse("exceptions/404.html", {"request": request}, status_code=404)

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: Exception):

    # Check if the user tried to visit /auth/logout specifically
    if request.url.path == "/auth/logout":
        # Redirect them back to the dashboard or home
        return auth_routes.RedirectResponse(url="/nexus/dashboard", status_code=303)
    
    # For any other 405, show a custom error page or redirect to home
    return templates.TemplateResponse("exceptions/405.html", {"request": request}, status_code=405)