import streamlit as st
from api_client import login

if "token" not in st.session_state:
    st.session_state["token"] = None
    st.session_state["username"] = None

# --- Auth Gate ---
if st.session_state["token"] is None:
    # Show login form
    st.title("🔐 Login to AI Weather Dashboard")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            token = login(username, password)
            if token:
                st.session_state["token"] = token
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid credentials")
else:
    # Show the actual app
    st.title("AI Weather Dashboard")
    # ... dashboard content using st.session_state["token"] 
# --- Sidebar ---
with st.sidebar:
    st.write(f"Logged in as **{st.session_state['username']}**")
    if st.button("Logout"):
        st.session_state["token"] = None
        st.session_state["username"] = None
        st.rerun()
