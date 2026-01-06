from pydantic import BaseModel, EmailStr
# Base class that provides data validation and serialization for all inherited models.
# It ensures incoming data -> matches the defined types.

# Schema for creating a new user- requires all fields for registration.
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    class Config:
        # Allows Pydantic to read data even if it's a database object (like from SQLAlchemy) instead of just a standard Python dictionary.
        from_attributes = True

# Schema for the API response, excludes sensitive data like passwords.
class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        # Allows Pydantic to read data even if it's a database object (like from SQLAlchemy) instead of just a standard Python dictionary.
        from_attributes = True

# Schema for login requests; used to validate the credentials sent by the user.
class RequestLogin(BaseModel):
    email: EmailStr
    password: str

# Schema for login responses; defines the structure of the security token returned.
class LoginOut(BaseModel):
    access_token: str
    token_type: str

# Schema for updating user details; ensures the update payload has the correct format.
class UpdateUser(BaseModel):
    username: str
    email: EmailStr
    password: str