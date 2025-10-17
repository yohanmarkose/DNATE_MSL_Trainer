import streamlit as st
import requests
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

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
        response = requests.post(f"{API_BASE_URL}/evaluate", json=payload)
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
        response = requests.get(f"{API_BASE_URL}/sessions")
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
    
    with col1:
        selected_q = st.selectbox(
            "Choose a question",
            questions,
            format_func=lambda q: f"{q['category']} - {q['question'][:80]}..."
        )
        if selected_q != st.session_state.selected_question:
            st.session_state.current_scenario = None  # NEW: Clear cached scenario
            st.session_state.selected_question = None
            st.session_state.evaluation_result = None
            st.session_state.user_response = ""
    
    with col2:
        if st.button("🎲 Random Question"):
            selected_q = random.choice(questions)
            st.session_state.selected_question = selected_q
            st.session_state.current_scenario = None  # NEW: Clear cached scenario
            st.rerun()
    
    if st.button("Select This Question"):
        st.session_state.user_response = None
        st.session_state.selected_question = selected_q
        st.session_state.current_scenario = None  # NEW: Clear cached scenario
        st.session_state.evaluation_result = None
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
    
    # Fetch all required data
    try:
        progress = requests.get(f"{API_BASE_URL}/progress/detailed").json()
        milestones_data = requests.get(f"{API_BASE_URL}/progress/milestones").json()
        timeline = requests.get(f"{API_BASE_URL}/progress/timeline").json()
        heatmap_data = requests.get(f"{API_BASE_URL}/progress/heatmap").json()
        personas = fetch_personas()
    except Exception as e:
        st.error(f"Unable to load progress data. Make sure backend is running.")
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
    
    # Initialize cache in session state
    if 'model_answers_cache' not in st.session_state:
        st.session_state.model_answers_cache = {}
    if 'learn_tab_initialized' not in st.session_state:
        st.session_state.learn_tab_initialized = False
    
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
    
    # Clear cache when persona changes
    if 'last_selected_persona' not in st.session_state:
        st.session_state.last_selected_persona = None
    
    if st.session_state.last_selected_persona != persona_id_param:
        st.session_state.model_answers_cache = {}
        st.session_state.last_selected_persona = persona_id_param
        st.session_state.learn_tab_initialized = False
    
    questions = fetch_questions(persona_id_param or personas[0]['id'] if personas else None)
    
    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + categories
    )
    
    # Build params for API call
    params = {}
    if persona_id_param:
        params["persona_id"] = persona_id_param
    if category_filter != "All":
        filtered_questions = [q for q in questions if q['category'] == category_filter]
    else:
        filtered_questions = questions
    
    # Auto-generate answers on first load
    if not st.session_state.learn_tab_initialized:
        st.info("📚 Loading model answers for all questions...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, q in enumerate(questions):
            cache_key = f"{q['id']}_{persona_id_param}"
            
            if cache_key not in st.session_state.model_answers_cache:
                status_text.text(f"Generating answer {idx + 1}/{len(questions)}: {q['category']}")
                model_ans = fetch_model_answer(q['id'], persona_id_param)
                if model_ans:
                    st.session_state.model_answers_cache[cache_key] = model_ans
            
            progress_bar.progress((idx + 1) / len(questions))
        
        progress_bar.empty()
        status_text.empty()
        st.session_state.learn_tab_initialized = True
        st.success("✅ All model answers loaded!")
    
    # Show cache status
    st.caption(f"📦 {len(st.session_state.model_answers_cache)} answers cached")
    
    # Display questions with cached answers
    for q in filtered_questions:
        cache_key = f"{q['id']}_{persona_id_param}"
        
        with st.expander(f"**{q['category']}** - {q['question']}"):
            model_ans = st.session_state.model_answers_cache.get(cache_key)
            
            if model_ans:
                if model_ans.get('persona_tailored'):
                    st.success("✨ Answer tailored for selected persona")
                
                st.write("**Model Answer:**")
                st.info(model_ans['model_answer'])
                
                st.write("**Key Themes to Cover:**")
                for point in model_ans['key_points']:
                    st.write(f"- {point}")
            else:
                st.warning("⚠️ Answer not available in cache")

def render_sessions_tab():
    """Render the Sessions tab"""
    st.header("💬 Your Practice Sessions")
    
    sessions = fetch_sessions()
    
    if not sessions:
        st.info("No sessions yet. Start practicing!")
        return
    
    sessions_sorted = sorted(sessions, key=lambda x: x['timestamp'], reverse=True)
    personas = fetch_personas()
    questions = fetch_questions(personas[0]['id'] if personas else None)
    
    for session in sessions_sorted:
        persona_name = next((p['name'] for p in personas if p['id'] == session['persona_id']), "Unknown")
        question = next((q for q in questions if q['id'] == session['question_id']), None)
        
        with st.expander(f"**{session['timestamp'][:10]}** - {persona_name} - Score: {session['score']:.1f}"):
            if question:
                st.write(f"**Question:** {question['question']}")
            st.write(f"**Category:** {session['category']}")
            st.write(f"**Your Response:**")
            st.write(session['user_response'])
            st.write(f"**Score:** {session['score']:.1f}/100")


# ============= MAIN APPLICATION =============

def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    
    # Page config
    st.set_page_config(page_title="MSL Practice Gym", layout="wide")
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