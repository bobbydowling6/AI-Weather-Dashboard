import secrets  # <-- Added missing import
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import streamlit as st

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Assuming your secrets.toml has a dictionary of users, e.g.:
# [database.users]
# admin = "password123"
try:
    users_db = dict(st.secrets["database"]["users"])
except Exception:
    # Fallback or single user setup if structured differently
    users_db = {st.secrets["database"]["username"]: st.secrets["database"]["password"]}

tokens = {}  # token -> username mapping
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

@app.post("/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Check if the user exists and the password matches
    if form_data.username not in users_db or users_db[form_data.username] != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = secrets.token_hex(32)
    tokens[token] = form_data.username
    return {"access_token": token, "token_type": "bearer"}