from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import secrets

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

USERS = {"admin": "password123"}
tokens = {}  # token -> username mapping
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

@app.post("/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if USERS.get(form_data.username) != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_hex(32)
    tokens[token] = form_data.username
    return {"access_token": token, "token_type": "bearer"}
