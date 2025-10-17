import streamlit as st
import requests
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
# from utils.home import show_home


# Add this at the top of your main file, after imports
def render_auth_page():
    """Render login/signup page"""
    st.title("🏋️ DNATE MSL Practice Gym")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        render_login()
    
    with tab2:
        render_signup()

def render_login():
    """Render login form"""
    st.subheader("Welcome Back!")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.error("Please fill in all fields")
            else:
                with st.spinner("Logging in..."):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/login",
                            json={"email": email, "password": password}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.username = email
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")

def render_signup():
    """Render signup form"""
    st.subheader("Create Your Account")
    
    with st.form("signup_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Sign Up", type="primary", use_container_width=True)
        
        if submit:
            if not all([first_name, last_name, email, password, password_confirm]):
                st.error("Please fill in all fields")
            elif password != password_confirm:
                st.error("Passwords don't match")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters")
            else:
                with st.spinner("Creating account..."):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/signup",
                            json={
                                "first_name": first_name,
                                "last_name": last_name,
                                "email": email,
                                "password": password
                            }
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.username = email
                            st.success("Account created successfully!")
                            st.rerun()
                        else:
                            error_detail = response.json().get("detail", "Signup failed")
                            st.error(error_detail)
                    except Exception as e:
                        st.error(f"Signup failed: {str(e)}")

def render_logout_button():
    """Render logout button in sidebar"""
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        with st.spinner("Logging out..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                requests.post(f"{API_BASE_URL}/logout", headers=headers)
            except:
                pass  # Logout locally even if API call fails
            
            st.session_state.token = None
            st.session_state.username = None
            st.rerun()


#--------#

from components.track_dashboard import (
    inject_custom_css,
    render_level_card,
    render_streak_card,
    render_key_metrics,
    render_goal_progress,
    render_score_trend_chart,
    render_category_radar_chart,
    render_practice_heatmap,
    render_achievements_grid,
    render_category_breakdown,
    render_persona_breakdown
)

API_BASE_URL = "http://localhost:8000"


st.set_page_config(
    page_title="Chronic Disease Management",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== SESSION STATE INIT ==========
if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.username = None

if "nav_selection" not in st.session_state and st.session_state.token is not None:
    st.session_state.nav_selection = "Home"

# ============= SESSION STATE INITIALIZATION =============

def init_session_state():
    """Initialize session state variables"""
    if 'selected_persona' not in st.session_state:
        st.session_state.selected_persona = None
    if 'selected_question' not in st.session_state:
        st.session_state.selected_question = None
    if 'user_response' not in st.session_state:
        st.session_state.user_response = ""
    if 'evaluation_result' not in st.session_state:
        st.session_state.evaluation_result = None
    if 'current_scenario' not in st.session_state:  # NEW
        st.session_state.current_scenario = None


def reset_session():
    """Reset practice session state"""
    st.session_state.selected_persona = None
    st.session_state.selected_question = None
    st.session_state.user_response = ""
    st.session_state.evaluation_result = None
    st.session_state.current_scenario = None

# ============= API HELPER FUNCTIONS =============

def fetch_personas() -> List[Dict[str, Any]]:
    """Fetch all personas from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/personas")
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch personas: {e}")
        return []


def fetch_persona_details(persona_id: str) -> Optional[Dict[str, Any]]:
    """Fetch detailed persona information"""
    try:
        response = requests.get(f"{API_BASE_URL}/personas/{persona_id}")
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch persona details: {e}")
        return None


def fetch_questions(persona_id: str, difficulty: str = "All", category: str = "All") -> List[Dict[str, Any]]:
    """Fetch filtered questions from API"""
    try:
        params = {"persona_id": persona_id}
        if difficulty != "All":
            params["difficulty"] = difficulty
        if category != "All":
            params["category"] = category
        
        response = requests.get(f"{API_BASE_URL}/questions", params=params)
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch questions: {e}")
        return []


def fetch_categories(persona_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch categories, optionally filtered by persona"""
    try:
        params = {"persona_id": persona_id} if persona_id else {}
        response = requests.get(f"{API_BASE_URL}/categories", params=params)
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch categories: {e}")
        return {}


def fetch_scenario(question_id: int, persona_id: str) -> Optional[Dict[str, Any]]:
    """Fetch scenario context for a question"""
    try:
        response = requests.get(f"{API_BASE_URL}/scenario/{question_id}/{persona_id}")
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch scenario: {e}")
        return None


def submit_evaluation(question_id: int, persona_id: str, user_response: str) -> Optional[Dict[str, Any]]:
    """Submit user response for evaluation"""
    try:
        payload = {
            "question_id": question_id,
            "persona_id": persona_id,
            "user_response": user_response
        }
        response = requests.post(
            f"{API_BASE_URL}/evaluate",
            json=payload,
            headers=get_auth_headers()
        )
        
        if response.status_code == 401:
            st.error("Session expired. Please login again.")
            st.session_state.token = None
            st.rerun()
            
        return response.json()
    except Exception as e:
        st.error(f"Failed to evaluate response: {e}")
        return None


def fetch_model_answer(question_id: int, persona_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch model answer for a question"""
    try:
        params = {"persona_id": persona_id} if persona_id else {}
        response = requests.get(f"{API_BASE_URL}/model-answer/{question_id}", params=params)
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch model answer: {e}")
        return None


def fetch_sessions() -> List[Dict[str, Any]]:
    """Fetch all practice sessions"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/sessions",
            headers=get_auth_headers()
        )
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch sessions: {e}")
        return []


# ============= UI COMPONENT FUNCTIONS =============

def render_persona_selection():
    """Render persona selection UI"""
    st.subheader("1. Select Physician Persona")
    personas = fetch_personas()
    
    col1, col2, col3 = st.columns(3)
    
    for idx, persona in enumerate(personas):
        col = [col1, col2, col3][idx]
        with col:
            if st.button(
                f"**{persona['name']}**\n\n{persona['title']}\n\n{persona['specialty']}",
                key=f"persona_{persona['id']}",
                use_container_width=True
            ):
                st.session_state.selected_persona = persona['id']
                st.rerun()
    
    return personas


def render_persona_details(persona_id: str, personas: List[Dict[str, Any]]):
    """Render selected persona details"""
    persona_name = next((p['name'] for p in personas if p['id'] == persona_id), "Unknown")
    st.success(f"Selected: {persona_name}")
    
    persona_details = fetch_persona_details(persona_id)
    if persona_details:
        with st.expander("👤 View Persona Details"):
            st.write(f"**Practice Setting:** {persona_details['practice_setting']['type']}")
            st.write(f"**Communication Style:** {persona_details['communication_style']['tone']}")
            st.write("**Priorities:**")
            for priority in persona_details['priorities'][:3]:
                st.write(f"- {priority}")


def render_question_filters(persona_id: str) -> tuple[str, str]:
    """Render question filter controls and return selected values"""
    st.subheader("2. Filter Questions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        difficulty = st.selectbox(
            "Difficulty",
            ["All", "low", "medium", "high"]
        )
    
    with col2:
        categories_response = fetch_categories(persona_id)
        category = st.selectbox(
            "Category",
            ["All"] + list(categories_response.keys())
        )
    
    return difficulty, category


def render_question_selection(persona_id: str, difficulty: str, category: str) -> Optional[Dict[str, Any]]:
    """Render question selection UI"""
    questions = fetch_questions(persona_id, difficulty, category)
    
    st.write(f"**{len(questions)} questions available**")
    st.subheader("3. Select Question")
    
    if not questions:
        st.warning("No questions available with selected filters.")
        return None
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Put random button FIRST, before selectbox
        if st.button("🎲 Random Question"):
            selected_q = random.choice(questions)
            st.session_state.selected_question = selected_q
            st.session_state.current_scenario = None
            st.session_state.evaluation_result = None
            st.session_state.user_response = ""
            st.rerun()
    
    with col1:
        # Find index of currently selected question for selectbox
        default_index = 0
        if st.session_state.selected_question:
            try:
                default_index = next(
                    i for i, q in enumerate(questions) 
                    if q['id'] == st.session_state.selected_question['id']
                )
            except StopIteration:
                default_index = 0
        
        selected_q = st.selectbox(
            "Choose a question",
            questions,
            index=default_index,
            format_func=lambda q: f"{q['category']} - {q['question'][:80]}..."
        )
    
    if st.button("Select This Question"):
        st.session_state.selected_question = selected_q
        st.session_state.current_scenario = None
        st.session_state.evaluation_result = None
        st.session_state.user_response = ""
        st.rerun()
    
    return selected_q

def render_scenario_context(question: Dict[str, Any], persona_id: str):
    """Render scenario context for selected question"""
    st.divider()
    st.subheader("📖 Scenario Context")
    
    # Generate scenario only if not cached or question changed
    scenario_key = f"{question['id']}_{persona_id}"
    
    if (st.session_state.current_scenario is None or 
        st.session_state.current_scenario.get('key') != scenario_key):
        
        with st.spinner("Generating realistic scenario..."):
            scenario = fetch_scenario(question['id'], persona_id)
        
        if scenario:
            # Cache the scenario with a unique key
            st.session_state.current_scenario = {
                'key': scenario_key,
                'data': scenario
            }
    
    # Use cached scenario
    if st.session_state.current_scenario:
        scenario = st.session_state.current_scenario['data']
        
        st.markdown(f"""
        <div style="padding: 15px; background-color: #e8f4f8; border-radius: 10px; border-left: 5px solid #2196F3;">
            <p style="margin: 5; font-style: italic;">{scenario['scenario']}</p>
            <p style="margin: 0; font-weight: bold; font-size: 16;">{question['question']}</p>
        </div> <br>
        <div style="padding: 15px; background-color: #f0f2f6; border-radius: 10px; border-left: 5px solid #1f77b4;">
            <p style="margin: 0;"><strong>Category:</strong> {question['category']}</p>
            <p style="margin: 0;"><strong>Difficulty:</strong> {question['difficulty'].upper()}</p>
            <p style="margin: 0;"><strong>Context:</strong> {question['context']}</p>
            <p style="margin: 0;"><strong>Estimated Time:</strong> {question['estimated_response_time']} seconds</p>
        </div>
        """, unsafe_allow_html=True)

def render_response_input(question: Dict[str, Any], persona_id: str):
    """Render response input and submission"""
    if st.session_state.selected_question is not None:
        st.divider()
        st.subheader("5. Your Response")
        
        user_responses = st.text_area(
            "Type your response as an MSL:",
            value=st.session_state.user_response,  # This reads from session state
            height=200,
            key="response_input",
            placeholder="Write your response here..."
        )
        
        if st.button("✅ Submit Response", type="primary"):
            if user_responses.strip():
                with st.spinner("Evaluating your response..."):
                    # Save to session state only when submitting
                    st.session_state.user_response = user_responses
                    result = submit_evaluation(question['id'], persona_id, user_responses)
                    if result:
                        st.session_state.evaluation_result = result
                        st.rerun()
            else:
                st.error("Please provide a response before submitting.")

def render_evaluation_results(result: Dict[str, Any]):
    """Render evaluation results"""
    st.divider()
    st.subheader("📈 Evaluation Results")
    
    score = result['score']
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Your Score", f"{score:.1f}/100")
    
    with col2:
        if score >= 80:
            st.success("Excellent! 🌟")
        elif score >= 60:
            st.info("Good! 👍")
        else:
            st.warning("Needs Work 📝")
    
    st.write("**Feedback:**", result['feedback'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**✅ Priorities Covered:**")
        if result['priorities_covered']:
            for p in result['priorities_covered']:
                st.write(f"- {p}")
        else:
            st.write("None")
    
    with col2:
        st.write("**✅ Engagement Points Covered:**")
        if result['engagement_points_covered']:
            for e in result['engagement_points_covered']:
                st.write(f"- {e}")
        else:
            st.write("None")
    
    if result['missing_points']:
        st.write("**❌ Consider Adding:**")
        for m in result['missing_points'][:5]:
            st.write(f"- {m}")


# ============= TAB RENDERING FUNCTIONS =============

def render_practice_tab():
    """Render the Practice tab"""
    st.header("Practice Session")
    
    # New Session Button
    if st.button("🔄 Start New Session", type="primary"):
        reset_session()
        st.rerun()
    
    # Persona Selection
    personas = render_persona_selection()
    
    if st.session_state.selected_persona:
        render_persona_details(st.session_state.selected_persona, personas)
        
        # Question Filters
        difficulty, category = render_question_filters(st.session_state.selected_persona)
        
        # Question Selection
        selected_q = render_question_selection(
            st.session_state.selected_persona,
            difficulty,
            category
        )
        
        # Question Card and Response
        if st.session_state.selected_question:
            st.session_state.user_response = ""  # Reset user response on new question selections
            q = st.session_state.selected_question
            
            render_scenario_context(q, st.session_state.selected_persona)
            render_response_input(q, st.session_state.selected_persona)
            
            # Show Evaluation
            if st.session_state.evaluation_result:
                render_evaluation_results(st.session_state.evaluation_result)


def render_track_tab():
    """Render the Track tab"""
    inject_custom_css()
    
    st.header("📊 Progress Dashboard")
    
    # Fetch all required data with authentication
    try:
        headers = get_auth_headers()
        
        progress = requests.get(
            f"{API_BASE_URL}/progress/detailed",
            headers=headers
        ).json()
        
        milestones_data = requests.get(
            f"{API_BASE_URL}/progress/milestones",
            headers=headers
        ).json()
        
        timeline = requests.get(
            f"{API_BASE_URL}/progress/timeline",
            headers=headers
        ).json()
        
        heatmap_data = requests.get(
            f"{API_BASE_URL}/progress/heatmap",
            headers=headers
        ).json()
        
        personas = fetch_personas()
    except Exception as e:
        st.error(f"Unable to load progress data: {str(e)}")
        st.stop()

    # SECTION 1: Gamification Hero  
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_level_card(progress)
    
    with col2:
        render_streak_card(
            progress.get('current_streak_days', 0),
            progress.get('longest_streak_days', 0)
        )
    
    # SECTION 2: Key Metrics
    st.markdown("---")
    st.subheader("📈 Key Metrics")
    render_key_metrics(progress)
    
    # SECTION 3: Goals Progress
    st.markdown("---")
    render_goal_progress(progress)
    
    # SECTION 4: Interactive Charts
    if progress.get('total_sessions', 0) > 0:
        st.markdown("---")
        st.subheader("📊 Performance Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            render_score_trend_chart(timeline)
        
        with col2:
            render_category_radar_chart(progress.get('category_stats', {}))
        
        st.markdown("---")
        st.subheader("📅 Practice Calendar")
        render_practice_heatmap(heatmap_data)
    else:
        st.markdown("---")
        st.info("📊 Complete your first practice session to see analytics!")
    
    # SECTION 5: Achievements
    st.markdown("---")
    st.subheader(f"🏆 Achievements ({milestones_data['total_achieved']}/{milestones_data['total_available']})")
    render_achievements_grid(milestones_data['milestones'])
    
    # SECTION 6: Detailed Breakdown
    st.markdown("---")
    st.subheader("📋 Detailed Performance")
    
    if progress.get('category_stats'):
        render_category_breakdown(progress['category_stats'])
    
    st.markdown("---")
    
    if progress.get('persona_stats'):
        render_persona_breakdown(progress['persona_stats'], personas)

def render_learn_tab():
    """Render the Learn tab"""
    st.header("📚 Model Answers")
    
    # Add persona selector
    personas = fetch_personas()
    selected_persona_learn = st.selectbox(
        "Select Persona (optional - for tailored answers)",
        ["None"] + [f"{p['name']} ({p['specialty']})" for p in personas],
        key="learn_persona"
    )
    
    persona_id_param = None
    if selected_persona_learn != "None":
        persona_id_param = next(p['id'] for p in personas if f"{p['name']} ({p['specialty']})" == selected_persona_learn)
    
    # Get all questions for category filter
    questions_list = requests.get(f"{API_BASE_URL}/questions").json()
    categories = sorted(list(set(q['category'] for q in questions_list)))
    
    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + categories
    )
    
    # Build params for API call
    params = {}
    if persona_id_param:
        params["persona_id"] = persona_id_param
    if category_filter != "All":
        params["category"] = category_filter
    
    if st.button("📖 Get Model Answers", type="primary"):
        with st.spinner("Loading model answers..."):
            try:
                response = requests.get(
                    f"{API_BASE_URL}/model-answers",
                    params=params
                )
                
                if response.status_code != 200:
                    st.error(f"Error: Server returned status {response.status_code}")
                    st.stop()
                
                data = response.json()
                answers = data.get("answers", [])
                
                if not answers:
                    st.warning("No model answers found for the selected filters.")
                    if "message" in data:
                        st.info(data["message"])
                else:
                    st.success(f"✅ Found {len(answers)} model answer(s)")
                    
                    # Group answers by question_id to prefer persona-specific over generic
                    answers_by_question = {}
                    for answer in answers:
                        q_id = answer['question_id']
                        # Prefer persona-tailored answers over generic
                        if q_id not in answers_by_question or answer.get('persona_tailored'):
                            answers_by_question[q_id] = answer
                    
                    # Display answers sorted by category
                    sorted_answers = sorted(answers_by_question.values(), key=lambda x: (x['category'], x['question_id']))
                    
                    for answer in sorted_answers:
                        with st.expander(f"**{answer['category']}** - {answer['question']}"):
                            
                            # Question Context Section
                            st.markdown("### 📋 Question Context")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Difficulty", answer.get('difficulty', 'N/A').upper())
                            with col2:
                                st.metric("Estimated Time", f"{answer.get('estimated_response_time', 'N/A')}s")
                            with col3:
                                st.metric("Category", answer['category'])
                            
                            st.write("**Context:**")
                            st.info(answer.get('context', 'No context provided'))
                            
                            st.divider()
                            
                            # Persona Details Section (if persona-tailored)
                            if answer.get('persona_tailored'):
                                st.markdown("### 👤 Physician Persona")
                                st.success(f"✨ Answer tailored for **{answer.get('persona_name', 'Unknown')}**")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Specialty:**", answer.get('persona_specialty', 'N/A'))
                                    st.write("**Practice Setting:**", answer.get('persona_practice_setting', 'N/A'))
                                with col2:
                                    st.write("**Communication Style:**", answer.get('persona_communication_style', 'N/A'))
                                
                                if answer.get('persona_priorities'):
                                    st.write("**Top Priorities:**")
                                    for priority in answer['persona_priorities']:
                                        st.write(f"• {priority}")
                                
                                st.divider()
                            else:
                                st.info("📝 Generic answer (not tailored to specific persona)")
                                st.divider()
                            
                            # Model Answer Section
                            st.markdown("### 💡 Model Answer")
                            st.markdown(f"<div style='padding: 20px; background-color: #f0f2f6; border-radius: 10px; border-left: 5px solid #1f77b4;'>{answer['model_answer']}</div>", unsafe_allow_html=True)
                            
                            st.write("")
                            
                            # Key Points Section
                            st.markdown("### ✅ Key Points to Cover")
                            for idx, point in enumerate(answer['key_points'], 1):
                                st.write(f"{idx}. {point}")
                            
                            st.write("")
                            
                            # Reasoning Section
                            if answer.get('reasoning'):
                                with st.expander("💡 Strategy & Reasoning"):
                                    st.write(answer['reasoning'])
            
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
                import traceback
                with st.expander("Show error details"):
                    st.code(traceback.format_exc())


def render_sessions_tab():
    """Render the Sessions tab"""
    st.header("💬 Your Practice Sessions")
    
    sessions = fetch_sessions()
    
    if not sessions:
        st.info("No sessions yet. Start practicing!")
        return
    
    # Sessions is a list of session documents, each with an 'interactions' array
    personas = fetch_personas()
    all_questions = requests.get(f"{API_BASE_URL}/questions").json()
    
    # Display each session
    for session in sessions:
        session_date = session.get('login_time', 'Unknown date')
        interactions = session.get('interactions', [])
        
        if not interactions:
            continue
        
        st.subheader(f"📅 Session: {session_date[:10] if isinstance(session_date, str) else 'Unknown'}")
        st.write(f"**Total Interactions:** {len(interactions)}")
        
        # Sort interactions by timestamp
        sorted_interactions = sorted(
            interactions, 
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )
        
        for idx, interaction in enumerate(sorted_interactions, 1):
            persona_name = next(
                (p['name'] for p in personas if p['id'] == interaction.get('persona_id')), 
                "Unknown"
            )
            
            question_obj = next(
                (q for q in all_questions if q['id'] == interaction.get('question_id')), 
                None
            )
            
            score = interaction.get('score', 0)
            timestamp = interaction.get('timestamp', 'Unknown')[:16]  # Show date and time
            
            with st.expander(
                f"**{idx}. {timestamp}** | {persona_name} | Score: {score:.1f}/100"
            ):
                if question_obj:
                    st.write(f"**Question:** {question_obj.get('question', 'N/A')}")
                    st.write(f"**Category:** {interaction.get('category', 'N/A')}")
                    st.write(f"**Difficulty:** {question_obj.get('difficulty', 'N/A').upper()}")
                else:
                    st.write(f"**Category:** {interaction.get('category', 'N/A')}")
                
                st.divider()
                
                st.write("**Your Response:**")
                st.info(interaction.get('user_response', 'No response recorded'))
                
                st.divider()
                
                # Score visualization
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.metric("Score", f"{score:.1f}/100")
                with col2:
                    if score >= 80:
                        st.success("Excellent! 🌟")
                    elif score >= 60:
                        st.info("Good! 👍")
                    else:
                        st.warning("Needs Work 📝")
        
        st.markdown("---")


def get_auth_headers():
    """Get authentication headers for API calls"""
    if not st.session_state.token:
        st.error("Not authenticated. Please login.")
        st.stop()
    return {"Authorization": f"Bearer {st.session_state.token}"}

# ============= MAIN APPLICATION =============

def main():
    """Main application entry point"""
    st.set_page_config(page_title="MSL Practice Gym", layout="wide")
    
    # Check if user is authenticated
    if st.session_state.token is None:
        render_auth_page()
        return
    
    # Show logout button in sidebar
    with st.sidebar:
        st.write(f"👤 **{st.session_state.username}**")
        render_logout_button()
    
    # Initialize session state
    init_session_state()
    
    st.title("🏋️ DNATE MSL Practice Gym")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Practice", "📊 Track", "📚 Learn", "💬 Sessions"])
    
    # Render tabs
    with tab1:
        render_practice_tab()
    
    with tab2:
        render_track_tab()
    
    with tab3:
        render_learn_tab()
    
    with tab4:
        render_sessions_tab()


if __name__ == "__main__":
    main()