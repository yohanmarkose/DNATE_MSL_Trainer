# FILE: utils/signup.py

import streamlit as st
import requests

def show_signup(API_URL):
    st.header("Sign Up")

    # User Information
    signup_username = st.text_input("Username", key="signup_username")
    signup_password = st.text_input("Password", type="password", key="signup_password")
    
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("Email")
    
    age = st.number_input("Age", min_value=1, max_value=120, step=1)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])

    height = st.number_input("Height (in cm)", min_value=50.0, max_value=250.0, step=0.5)
    weight = st.number_input("Weight (in kg)", min_value=10.0, max_value=300.0, step=0.5)

    chronic_conditions = ["Cholesterol", "CKD", "Gluten", "Hypertension", "Type2", "Polycystic", "Obesity"]
    chronic_condition = st.selectbox("Chronic Condition", chronic_conditions)

    activity_level = st.selectbox("Activity Level", [
        "Sedentary", 
        "Lightly Active", 
        "Moderately Active", 
        "Very Active", 
        "Extra Active"
    ])

    location = st.text_input("Location")

    if st.button("Sign Up"):
        if all([signup_username, signup_password, first_name, last_name, email, age, gender, height, weight, chronic_condition, activity_level, location]):
            try:
                payload = {
                    "username": signup_username,
                    "password": signup_password,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "age": age,
                    "gender": gender,
                    "height": height,
                    "weight": weight,
                    "chronic_condition": chronic_condition,
                    "activity_level": activity_level,
                    "location": location
                }

                response = requests.post(f"{API_URL}/users/signup", json=payload)

                if response.status_code == 200:
                    data = response.json()

                    # Show BMI and TDEE
                    st.success("Registration successful! Please login.")
                    st.markdown(f"**Your BMI:** `{data.get('bmi')}`")
                    st.markdown(f"**BMI Category:** `{data.get('bmi_category')}`")
                    st.markdown(f"**Your Estimated TDEE:** `{data.get('tdee')} kcal/day`")

                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", "Registration failed.")
                        st.error(f"Error: {error_msg}")
                    except:
                        st.error(f"Registration failed with status code: {response.status_code}")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("⚠️ Please fill in all fields.")
