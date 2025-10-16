"""
frontend/components/track_dashboard.py
UI components for the Track dashboard tab
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any


# ============= STYLING =============

def inject_custom_css():
    """Inject custom CSS for dashboard styling"""
    st.markdown("""
    <style>
    .big-metric {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        color: white;
        margin: 10px 0;
    }
    .streak-box {
        text-align: center;
        padding: 20px;
        border-radius: 15px;
        color: white;
    }
    .achievement-card {
        text-align: center;
        padding: 15px;
        border-radius: 10px;
        margin: 5px;
    }
    .achievement-unlocked {
        background-color: #51cf66;
        border: 3px solid gold;
    }
    .achievement-locked {
        background-color: #e9ecef;
        opacity: 0.6;
    }
    .goal-card {
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    </style>
    """, unsafe_allow_html=True)


# ============= COMPONENTS =============

def render_level_card(progress: Dict[str, Any]):
    """Render the level and XP progress card"""
    level = progress.get('current_level', 1)
    xp = progress.get('current_xp', 0)
    xp_remaining = progress.get('xp_remaining', 100)
    progress_percent = progress.get('progress_percent', 0)
    
    st.markdown(f"""
    <div class="big-metric">
        <h1>🏅 Level {level} MSL Practitioner</h1>
        <p style="font-size: 24px; margin: 10px 0;">{xp} XP</p>
        <div style="background: rgba(255,255,255,0.3); border-radius: 10px; height: 25px; margin: 15px 0;">
            <div style="background: white; height: 25px; width: {progress_percent:.1f}%; border-radius: 10px; transition: width 0.3s;"></div>
        </div>
        <p style="font-size: 16px;">{xp_remaining} XP to Level {level + 1}</p>
    </div>
    """, unsafe_allow_html=True)


def render_streak_card(streak: int, longest: int):
    """Render the streak card with fire emojis"""
    if streak == 0:
        emoji = "💤"
        message = "Start your streak today!"
        color = "#95a5a6"
    elif streak < 3:
        emoji = "🔥"
        message = "Keep it going!"
        color = "#e74c3c"
    elif streak < 7:
        emoji = "🔥🔥"
        message = "You're on fire!"
        color = "#e67e22"
    else:
        emoji_count = min(streak, 10)
        emoji = "🔥" * emoji_count
        message = "Unstoppable!"
        color = "#d35400"
    
    st.markdown(f"""
    <div class="big-metric" style="background-color: {color};">
        <div style="font-size: 48px;">{emoji}</div>
        <h2>{streak} Day Streak!</h2>
        <p>{message}</p>
        <p style="font-size: 14px; margin-top: 10px;">Longest: {longest} days</p>
    </div>
    """, unsafe_allow_html=True)


def render_key_metrics(progress: Dict[str, Any]):
    """Render key metrics in 4 columns"""
    col1, col2, col3, col4 = st.columns(4)
    
    total_sessions = progress.get('total_sessions', 0)
    avg_score = progress.get('average_score', 0)
    practice_time = int(progress.get('total_practice_time_minutes', 0))
    categories_practiced = len(progress.get('category_stats', {}))
    sessions_today = progress.get('sessions_today', 0)
    improvement = progress.get('improvement_rate', 0)
    
    with col1:
        st.metric(
            "Total Sessions",
            total_sessions,
            delta=f"+{sessions_today} today" if sessions_today > 0 else None
        )
    
    with col2:
        st.metric(
            "Average Score",
            f"{avg_score:.1f}",
            delta=f"{improvement:+.1f}" if improvement != 0 else None
        )
    
    with col3:
        st.metric("Practice Time", f"{practice_time} min")
    
    with col4:
        st.metric("Categories", f"{categories_practiced}/7")


# def render_goal_progress(progress: Dict[str, Any]):
#     """Render daily and weekly goal progress"""
#     st.subheader("🎯 Your Goals")
    
#     col1, col2 = st.columns(2)
    
#     daily_goal = progress.get('daily_goal_progress', {})
#     weekly_goal = progress.get('weekly_goal_progress', {})
    
#     with col1:
#         st.markdown('<div class="goal-card">', unsafe_allow_html=True)
#         st.write("**Daily Goal**")
#         st.progress(daily_goal.get('progress_percent', 0) / 100)
#         st.write(f"{daily_goal.get('current', 0)}/{daily_goal.get('target', 3)} sessions today")
        
#         if daily_goal.get('achieved', False):
#             st.success("✅ Daily goal achieved!")
#         st.markdown('</div>', unsafe_allow_html=True)
    
#     with col2:
#         st.markdown('<div class="goal-card">', unsafe_allow_html=True)
#         st.write("**Weekly Goal**")
#         st.progress(weekly_goal.get('progress_percent', 0) / 100)
#         st.write(f"{weekly_goal.get('current', 0)}/{weekly_goal.get('target', 15)} sessions this week")
        
#         if weekly_goal.get('achieved', False):
#             st.success("✅ Weekly goal achieved!")
#         st.markdown('</div>', unsafe_allow_html=True)

def render_goal_progress(progress: Dict[str, Any]):
    """Render daily and weekly goal progress"""
    st.subheader("🎯 Your Goals")
    
    # Add custom CSS for containers
    st.markdown("""
    <style>
    div[data-testid="stContainer"] {
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #0077E6 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    daily_goal = progress.get('daily_goal_progress', {})
    weekly_goal = progress.get('weekly_goal_progress', {})
    
    # Daily Goal
    with col1:
        with st.container(border=True):
            st.write("**Daily Goal**")
            st.progress(daily_goal.get('progress_percent', 0) / 100)
            st.write(f"{daily_goal.get('current', 0)}/{daily_goal.get('target', 3)} sessions today")
            
            if daily_goal.get('achieved', False):
                st.success("✅ Daily goal achieved!")
    
    # Weekly Goal
    with col2:
        with st.container(border=True):
            st.write("**Weekly Goal**")
            st.progress(weekly_goal.get('progress_percent', 0) / 100)
            st.write(f"{weekly_goal.get('current', 0)}/{weekly_goal.get('target', 15)} sessions this week")
            
            if weekly_goal.get('achieved', False):
                st.success("✅ Weekly goal achieved!")
                
def render_score_trend_chart(timeline: List[Dict[str, Any]]):
    """Render score trend line chart"""
    if not timeline:
        st.info("Complete more sessions to see your progress trend!")
        return
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=[t['session_number'] for t in timeline],
        y=[t['score'] for t in timeline],
        mode='lines+markers',
        name='Score',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8, color='#764ba2'),
        hovertemplate='<b>Session %{x}</b><br>Score: %{y:.1f}<extra></extra>'
    ))
    
    avg_score = sum(t['score'] for t in timeline) / len(timeline)
    fig.add_hline(
        y=avg_score,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Avg: {avg_score:.1f}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title="Score Trend Over Time",
        xaxis_title="Session Number",
        yaxis_title="Score",
        yaxis_range=[0, 105],
        height=400,
        hovermode='x unified',
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_category_radar_chart(category_stats: Dict[str, Dict[str, Any]]):
    """Render category performance radar chart"""
    if not category_stats:
        st.info("Practice more categories to see performance radar!")
        return
    
    categories = list(category_stats.keys())
    scores = [category_stats[cat]['avg_score'] for cat in categories]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=categories,
        fill='toself',
        name='Average Score',
        line=dict(color='#764ba2', width=2),
        fillcolor='rgba(118, 75, 162, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        title="Performance by Category",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_practice_heatmap(heatmap_data: List[Dict[str, Any]]):
    """Render practice frequency heatmap"""
    if not heatmap_data:
        st.info("Start practicing to see your activity calendar!")
        return
    
    df = pd.DataFrame(heatmap_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    fig = px.bar(
        df,
        x='date',
        y='count',
        title='Practice Activity Calendar',
        labels={'count': 'Sessions', 'date': 'Date'},
        color='count',
        color_continuous_scale='Greens'
    )
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Sessions",
        height=300,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_achievements_grid(milestones: List[Dict[str, Any]]):
    """Render achievements in a grid layout"""
    for i in range(0, len(milestones), 4):
        cols = st.columns(4)
        
        for j, col in enumerate(cols):
            if i + j < len(milestones):
                milestone = milestones[i + j]
                
                with col:
                    if milestone['achieved']:
                        st.markdown(f"""
                        <div class="achievement-card achievement-unlocked">
                            <div style="font-size: 50px;">{milestone['icon']}</div>
                            <h4 style="margin: 10px 0; color: white;">{milestone['name']}</h4>
                            <p style="font-size: 12px; margin: 5px 0; color: white;">{milestone['description']}</p>
                            <p style="margin-top: 10px; color: white;"><strong>+{milestone['xp']} XP</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="achievement-card achievement-locked">
                            <div style="font-size: 50px; filter: grayscale(100%);">{milestone['icon']}</div>
                            <h4 style="margin: 10px 0; color: #868e96;">{milestone['name']}</h4>
                            <p style="font-size: 12px; margin: 5px 0; color: #868e96;">🔒 Locked</p>
                        </div>
                        """, unsafe_allow_html=True)


def render_category_breakdown(category_stats: Dict[str, Dict[str, Any]]):
    """Render detailed category performance breakdown"""
    st.write("**Performance by Category**")
    
    for category, stats in sorted(category_stats.items(), key=lambda x: x[1]['avg_score'], reverse=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"**{category}**")
            st.progress(stats['avg_score'] / 100)
        
        with col2:
            st.write(f"{stats['avg_score']:.1f} avg")
            st.write(f"{stats['count']} sessions")


def render_persona_breakdown(persona_stats: Dict[str, Dict[str, Any]], personas: List[Dict[str, Any]]):
    """Render detailed persona performance breakdown"""
    st.write("**Performance by Persona**")
    
    for persona_id, stats in sorted(persona_stats.items(), key=lambda x: x[1]['avg_score'], reverse=True):
        persona_name = next((p['name'] for p in personas if p['id'] == persona_id), persona_id)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"**{persona_name}**")
            st.progress(stats['avg_score'] / 100)
        
        with col2:
            st.write(f"{stats['avg_score']:.1f} avg")
            st.write(f"{stats['count']} sessions")