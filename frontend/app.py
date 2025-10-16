import streamlit as st
import requests
import random
from datetime import datetime

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
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Practice", "📊 Track", "📚 Learn", "💬 Sessions"])

# TAB 1: PRACTICE
with tab1:
    st.header("Practice Session")
    
    # New Session Button
    if st.button("🔄 Start New Session", type="primary"):
        st.session_state.selected_persona = None
        st.session_state.selected_question = None
        st.session_state.user_response = ""
        st.session_state.evaluation_result = None
        st.rerun()
    
    # Persona Selection
    st.subheader("1. Select Physician Persona")
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
            categories = requests.get(f"{API_BASE_URL}/categories").json()
            category = st.selectbox(
                "Category",
                ["All"] + list(categories.keys())
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
        if st.session_state.selected_question:
            q = st.session_state.selected_question
            
            st.divider()
            st.subheader("4. Your Practice Question")
            
            with st.container():
                st.markdown(f"""
                <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px; border-left: 5px solid #1f77b4;">
                    <h3 style="margin-top: 0;">❓ {q['question']}</h3>
                    <p><strong>Category:</strong> {q['category']}</p>
                    <p><strong>Difficulty:</strong> {q['difficulty'].upper()}</p>
                    <p><strong>Context:</strong> {q['context']}</p>
                    <p><strong>Estimated Time:</strong> {q['estimated_response_time']} seconds</p>
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

# TAB 2: TRACK
with tab2:
    st.header("📊 Your Progress")
    
    progress = requests.get(f"{API_BASE_URL}/progress").json()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Sessions", progress['total_sessions'])
    
    with col2:
        st.metric("Average Score", f"{progress['average_score']:.1f}")
    
    with col3:
        if progress['scores_history']:
            trend = "📈" if len(progress['scores_history']) > 1 and progress['scores_history'][-1] > progress['scores_history'][0] else "📊"
            st.metric("Trend", trend)
    
    st.divider()
    
    # Category Performance
    if progress['category_stats']:
        st.subheader("Performance by Category")
        
        for category, stats in progress['category_stats'].items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{category}**")
                st.progress(stats['avg_score'] / 100)
            with col2:
                st.write(f"{stats['avg_score']:.1f} ({stats['count']} sessions)")
    
    st.divider()
    
    # Persona Performance
    if progress['persona_stats']:
        st.subheader("Performance by Persona")
        
        personas = requests.get(f"{API_BASE_URL}/personas").json()
        
        for persona_id, stats in progress['persona_stats'].items():
            persona_name = next((p['name'] for p in personas if p['id'] == persona_id), persona_id)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{persona_name}**")
                st.progress(stats['avg_score'] / 100)
            with col2:
                st.write(f"{stats['avg_score']:.1f} ({stats['count']} sessions)")

# TAB 3: LEARN
with tab3:
    st.header("📚 Model Answers")
    
    questions = requests.get(f"{API_BASE_URL}/questions").json()
    
    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + list(set(q['category'] for q in questions))
    )
    
    if category_filter != "All":
        questions = [q for q in questions if q['category'] == category_filter]
    
    for q in questions:
        with st.expander(f"**{q['category']}** - {q['question']}"):
            model_ans = requests.get(f"{API_BASE_URL}/model-answer/{q['id']}").json()
            
            st.write("**Model Answer:**")
            st.info(model_ans['model_answer'])
            
            st.write("**Key Points to Cover:**")
            for point in model_ans['key_points']:
                st.write(f"- {point}")
            
            st.write("**Reasoning:**")
            st.write(model_ans['reasoning'])

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