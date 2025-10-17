import streamlit as st
import requests

def show_login(API_URL):
    st.header("Login")
    login_username = st.text_input("Username", key="login_username")
    login_password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login"):
        if login_username and login_password:
            try:
                response = requests.post(
                    f"{API_URL}/users/token",
                    data={
                        "username": login_username,
                        "password": login_password
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.token = token_data["access_token"]
                    st.session_state.username = login_username
                    
                    # Set default navigation to home when logging in
                    st.session_state.nav_selection = "Home"
                    
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Login failed. Please check your credentials.")
                    if response.status_code != 401:  # If not unauthorized, show more details
                        st.error(f"Status: {response.status_code}")
                        st.error(f"Response: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please enter both username and password.")