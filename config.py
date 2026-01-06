import os
from dotenv import load_dotenv

# Load environment variables from the .env file.
load_dotenv()

# The secret password used to sign and verify security tokens (JWT).
SECRET_KEY = os.getenv("SECRET_KEY") 

# The hashing algorithm used to encrypt the tokens (defaults to HS256).
ALGORITHM = os.getenv("ALGORITHM", "HS256") 

# How long a login token remains valid (in minutes) before the user is logged out (default = 30)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))