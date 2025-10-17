import streamlit as st
import requests
import random
from datetime import datetime

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

# Initialize session state
if 'selected_persona' not in st.session_state:
    st.session_state.selected_persona = None
if 'selected_question' not in st.session_state:
    st.session_state.selected_question = None
if 'user_response' not in st.session_state:
    st.session_state.user_response = ""
if 'evaluation_result' not in st.session_state:
    st.session_state.evaluation_result = None

st.set_page_config(page_title="MSL Practice Gym", layout="wide")

st.title("🏋️ DNATE MSL Practice Gym")

# Create tabs
tab1, track, tab3, tab4 = st.tabs(["🎯 Practice", "📊 Track", "📚 Learn", "💬 Sessions"])

# TAB 1: PRACTICE
with tab1:
    st.header("Practice Session")
    
    # New Session Button
    if st.session_state.user_response or st.session_state.evaluation_result:
        # User has work in progress
        if st.button("🔄 Start New Session", type="primary"):
            st.warning("⚠️ Starting a new session will clear your current work.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, start new", use_container_width=True):
                    st.session_state.selected_persona = None
                    st.session_state.selected_question = None
                    st.session_state.user_response = ""
                    st.session_state.evaluation_result = None
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.rerun()
    else:
        # No work in progress, safe to reset
        if st.button("🔄 Start New Session", type="primary"):
            st.session_state.selected_persona = None
            st.session_state.selected_question = None
            st.session_state.user_response = ""
            st.session_state.evaluation_result = None
            st.rerun()
    
    # Persona Selection
    st.subheader("Select Physician Persona")
    personas = requests.get(f"{API_BASE_URL}/personas").json()
    
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
    
    if st.session_state.selected_persona:
        # Change this?
        st.success(f"Selected: {next(p['name'] for p in personas if p['id'] == st.session_state.selected_persona)}")
        
        # Get persona details
        persona_details = requests.get(f"{API_BASE_URL}/personas/{st.session_state.selected_persona}").json()
        
        with st.expander("👤 View Persona Details"):
            st.write(f"**Practice Setting:** {persona_details['practice_setting']['type']}")
            st.write(f"**Communication Style:** {persona_details['communication_style']['tone']}")
            st.write("**Priorities:**")
            for priority in persona_details['priorities'][:3]:
                st.write(f"- {priority}")
        
        # Filters
        st.subheader("2. Filter Questions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            difficulty = st.selectbox(
                "Difficulty",
                ["All", "low", "medium", "high"]
            )
        
        with col2:
            if st.session_state.selected_persona:
                categories_response = requests.get(
                    f"{API_BASE_URL}/categories",
                    params={"persona_id": st.session_state.selected_persona}
                ).json()
            else:
                categories_response = requests.get(f"{API_BASE_URL}/categories").json()
            category = st.selectbox(
                "Category",
                ["All"] + list(categories_response .keys())
            )
        
        # Get filtered questions
        params = {"persona_id": st.session_state.selected_persona}
        if difficulty != "All":
            params["difficulty"] = difficulty
        if category != "All":
            params["category"] = category
        
        questions = requests.get(f"{API_BASE_URL}/questions", params=params).json()
        
        st.write(f"**{len(questions)} questions available**")
        
        # Question Selection
        st.subheader("3. Select Question")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if questions:
                selected_q = st.selectbox(
                    "Choose a question",
                    questions,
                    format_func=lambda q: f"{q['category']} - {q['question'][:80]}..."
                )
        
        with col2:
            if st.button("🎲 Random Question") and questions:
                selected_q = random.choice(questions)
                st.session_state.selected_question = selected_q
                st.rerun()
        
        if questions:
            if st.button("Select This Question"):
                st.session_state.selected_question = selected_q
                st.rerun()
        
        # Question Card
        # Set up a story based on the selected persona and question
        if st.session_state.selected_question:
            q = st.session_state.selected_question
            st.divider()
            st.subheader("📖 Scenario Context")
            
            with st.spinner("Generating realistic scenario..."):
                scenario = requests.get(
                    f"{API_BASE_URL}/scenario/{q['id']}/{st.session_state.selected_persona}"
                ).json()
            
            st.markdown(f"""
            <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px; border-left: 5px solid #1f77b4;">
                <p><strong>Category:</strong> {q['category']}</p>
                <p><strong>Difficulty:</strong> {q['difficulty'].upper()}</p>
                <p><strong>Context:</strong> {q['context']}</p>
                <p><strong>Estimated Time:</strong> {q['estimated_response_time']} seconds</p>
            </div>
            <div style="padding: 15px; background-color: #e8f4f8; border-radius: 10px; border-left: 5px solid #2196F3;">
                <p style="margin: 0; font-style: italic;">{scenario['scenario']}</p>
                <p style="margin: 0; font-style: italic; font-weight: bold;">{q['question']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
                    
            # Response Input
            st.subheader("5. Your Response")
            
            user_response = st.text_area(
                "Type your response as an MSL:",
                value=st.session_state.user_response,
                height=200,
                key="response_input"
            )
                
            if st.button("✅ Submit Response", type="primary"):
                if user_response.strip():
                    # Evaluate response
                    payload = {
                        "question_id": q["id"],
                        "persona_id": st.session_state.selected_persona,
                        "user_response": user_response
                    }
                    
                    with st.spinner("Evaluating your response..."):
                        result = requests.post(f"{API_BASE_URL}/evaluate", json=payload).json()
                        st.session_state.evaluation_result = result
                        st.session_state.user_response = user_response
                        st.rerun()
                else:
                    st.error("Please provide a response before submitting.")
            
            # Show Evaluation
            if st.session_state.evaluation_result:
                result = st.session_state.evaluation_result
                
                st.divider()
                st.subheader("📈 Evaluation Results")
                
                # Score display
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

# TAB 2: TRACK (Progress Dashboard)
with track:
    inject_custom_css()
    
    st.header("📊 Progress Dashboard")
    
    # Fetch all required data
    try:
        progress = requests.get(f"{API_BASE_URL}/progress/detailed").json()
        milestones_data = requests.get(f"{API_BASE_URL}/progress/milestones").json()
        timeline = requests.get(f"{API_BASE_URL}/progress/timeline").json()
        heatmap_data = requests.get(f"{API_BASE_URL}/progress/heatmap").json()
        personas = requests.get(f"{API_BASE_URL}/personas").json()
    except Exception as e:
        st.error(f"Unable to load progress data. Make sure backend is running.")
        st.stop()
    
    # SECTION 1: Gamification Hero
    # st.markdown("---")
    level, streak = st.columns([2, 1])
    
    with level:
        render_level_card(progress)
    
    with streak:
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

# TAB 3: LEARN
with tab3:
    st.header("📚 Model Answers")
    
    # Add persona selector
    personas = requests.get(f"{API_BASE_URL}/personas").json()
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
                            if answer.get('persona_tailored'):
                                st.success(f"✨ Answer tailored for {answer.get('persona_name', 'selected persona')}")
                            else:
                                st.info("📝 Generic answer")
                            
                            st.write("**Model Answer:**")
                            st.markdown(f"<div style='padding: 15px; background-color: #f0f2f6; border-radius: 5px;'>{answer['model_answer']}</div>", unsafe_allow_html=True)
                            
                            st.write("")
                            st.write("**Key Points to Cover:**")
                            for point in answer['key_points']:
                                st.write(f"✓ {point}")
                            
                            if answer.get('reasoning'):
                                st.write("")
                                with st.expander("💡 Reasoning & Strategy"):
                                    st.write(answer['reasoning'])
            
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
                import traceback
                with st.expander("Show error details"):
                    st.code(traceback.format_exc())

# TAB 4: SESSIONS
with tab4:
    st.header("💬 Your Practice Sessions")
    
    sessions = requests.get(f"{API_BASE_URL}/sessions").json()
    
    if not sessions:
        st.info("No sessions yet. Start practicing!")
    else:
        sessions_sorted = sorted(sessions, key=lambda x: x['timestamp'], reverse=True)
        
        for session in sessions_sorted:
            personas = requests.get(f"{API_BASE_URL}/personas").json()
            questions = requests.get(f"{API_BASE_URL}/questions").json()
            
            persona_name = next((p['name'] for p in personas if p['id'] == session['persona_id']), "Unknown")
            question = next((q for q in questions if q['id'] == session['question_id']), None)
            
            with st.expander(f"**{session['timestamp'][:10]}** - {persona_name} - Score: {session['score']:.1f}"):
                if question:
                    st.write(f"**Question:** {question['question']}")
                st.write(f"**Category:** {session['category']}")
                st.write(f"**Your Response:**")
                st.write(session['user_response'])
                st.write(f"**Score:** {session['score']:.1f}/100")