"""
features/gamification.py
Handles all gamification logic: XP, levels, streaks, milestones
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# ============= CONSTANTS =============

MILESTONES = {
    "first_session": {
        "name": "First Steps",
        "description": "Complete your first practice session",
        "xp": 50,
        "icon": "🎯",
        "check": lambda stats: stats["total_sessions"] >= 1
    },
    "10_sessions": {
        "name": "Consistent Learner",
        "description": "Complete 10 practice sessions",
        "xp": 100,
        "icon": "📚",
        "check": lambda stats: stats["total_sessions"] >= 10
    },
    "50_sessions": {
        "name": "Dedicated MSL",
        "description": "Complete 50 practice sessions",
        "xp": 500,
        "icon": "🏆",
        "check": lambda stats: stats["total_sessions"] >= 50
    },
    "perfect_score": {
        "name": "Perfect Response",
        "description": "Score 95+ on any question",
        "xp": 200,
        "icon": "💯",
        "check": lambda stats: any(score >= 95 for score in stats.get("scores_history", []))
    },
    "7_day_streak": {
        "name": "Week Warrior",
        "description": "Practice for 7 consecutive days",
        "xp": 300,
        "icon": "🔥",
        "check": lambda stats: stats.get("current_streak_days", 0) >= 7
    },
    "all_categories": {
        "name": "Well Rounded",
        "description": "Practice all 7 categories",
        "xp": 250,
        "icon": "🌟",
        "check": lambda stats: len(stats.get("category_stats", {})) >= 7
    },
    "all_personas": {
        "name": "People Person",
        "description": "Practice with all 3 personas",
        "xp": 150,
        "icon": "👥",
        "check": lambda stats: len(stats.get("persona_stats", {})) >= 3
    },
    "high_achiever": {
        "name": "High Achiever",
        "description": "Maintain 80+ average score",
        "xp": 400,
        "icon": "⭐",
        "check": lambda stats: stats.get("average_score", 0) >= 80 and stats.get("total_sessions", 0) >= 5
    },
}

XP_THRESHOLDS = [0, 100, 300, 600, 1000]


# ============= LEVEL & XP FUNCTIONS =============

def calculate_level(xp: int) -> int:
    """Calculate level based on XP"""
    for level, threshold in enumerate(XP_THRESHOLDS[1:], start=1):
        if xp < threshold:
            return level
    return len(XP_THRESHOLDS)


def xp_for_next_level(current_xp: int) -> int:
    """Calculate XP threshold for next level"""
    for threshold in XP_THRESHOLDS[1:]:
        if current_xp < threshold:
            return threshold
    return XP_THRESHOLDS[-1]


def xp_progress_to_next_level(current_xp: int) -> Dict[str, Any]:
    """Calculate detailed XP progress information"""
    current_level = calculate_level(current_xp)
    next_level_xp = xp_for_next_level(current_xp)
    current_level_xp = XP_THRESHOLDS[current_level - 1] if current_level > 0 else 0
    
    xp_in_level = current_xp - current_level_xp
    xp_needed_for_level = next_level_xp - current_level_xp
    
    progress_percent = (xp_in_level / xp_needed_for_level * 100) if xp_needed_for_level > 0 else 100
    
    return {
        "current_level": current_level,
        "current_xp": current_xp,
        "next_level": current_level + 1 if current_level < len(XP_THRESHOLDS) else current_level,
        "next_level_xp": next_level_xp,
        "xp_remaining": next_level_xp - current_xp,
        "progress_percent": progress_percent,
        "is_max_level": current_xp >= XP_THRESHOLDS[-1]
    }


# ============= STREAK FUNCTIONS =============

def calculate_streak(practice_dates: List[str]) -> Tuple[int, int]:
    """Calculate current and longest streak from practice dates"""
    if not practice_dates:
        return 0, 0
    
    try:
        dates = sorted(list(set([
            datetime.fromisoformat(d).date() 
            for d in practice_dates
        ])))
    except (ValueError, AttributeError):
        return 0, 0
    
    if not dates:
        return 0, 0
    
    longest_streak = 1
    temp_streak = 1
    
    for i in range(1, len(dates)):
        diff = (dates[i] - dates[i-1]).days
        
        if diff == 1:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1
    
    today = datetime.now().date()
    last_practice = dates[-1]
    days_since = (today - last_practice).days
    
    if days_since == 0:
        current_streak = temp_streak
    elif days_since == 1:
        current_streak = temp_streak
    else:
        current_streak = 0
    
    return current_streak, longest_streak


# ============= MILESTONE FUNCTIONS =============

def check_and_award_milestones(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check which milestones should be awarded and update stats"""
    newly_achieved = []
    achieved_milestones = stats.get("milestones_achieved", [])
    
    for milestone_id, milestone in MILESTONES.items():
        if milestone_id in achieved_milestones:
            continue
        
        try:
            if milestone["check"](stats):
                achieved_milestones.append(milestone_id)
                stats["experience_points"] = stats.get("experience_points", 0) + milestone["xp"]
                
                newly_achieved.append({
                    "id": milestone_id,
                    "name": milestone["name"],
                    "description": milestone["description"],
                    "xp": milestone["xp"],
                    "icon": milestone["icon"]
                })
        except Exception as e:
            print(f"Error checking milestone {milestone_id}: {e}")
            continue
    
    stats["milestones_achieved"] = achieved_milestones
    stats["level"] = calculate_level(stats.get("experience_points", 0))
    
    return newly_achieved


def get_all_milestones_with_status(achieved_milestone_ids: List[str]) -> List[Dict[str, Any]]:
    """Get all milestones with their achievement status"""
    milestones_list = []
    
    for milestone_id, milestone in MILESTONES.items():
        milestones_list.append({
            "id": milestone_id,
            "name": milestone["name"],
            "description": milestone["description"],
            "xp": milestone["xp"],
            "icon": milestone["icon"],
            "achieved": milestone_id in achieved_milestone_ids
        })
    
    return milestones_list


# ============= SESSION COUNTING FUNCTIONS =============

# def count_sessions_in_period(sessions: List[Dict[str, Any]], start_date: datetime, end_date: datetime = None) -> int:
#     """Count sessions within a date range"""
#     if end_date is None:
#         end_date = datetime.now()
    
#     count = 0
#     for session in sessions:
#         try:
#             session_date = datetime.fromisoformat(session.get("timestamp", ""))
#             if start_date <= session_date <= end_date:
#                 count += 1
#         except (ValueError, TypeError):
#             continue
    
#     return count


# def get_sessions_today(sessions: List[Dict[str, Any]]) -> int:
#     """Count sessions from today"""
#     today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
#     return count_sessions_in_period(sessions, today_start)


# def get_sessions_this_week(sessions: List[Dict[str, Any]]) -> int:
#     """Count sessions from this week (Monday-Sunday)"""
#     today = datetime.now()
#     week_start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
#     return count_sessions_in_period(sessions, week_start)

# ============= SESSION COUNTING FUNCTIONS =============

def count_interactions_in_period(sessions: List[Dict[str, Any]], start_date: datetime, end_date: datetime = None) -> int:
    """Count interactions within a date range from session documents"""
    if end_date is None:
        end_date = datetime.utcnow()
    
    count = 0
    
    # Sessions is a list of session documents, each containing an 'interactions' array
    for session in sessions:
        interactions = session.get("interactions", [])
        
        for interaction in interactions:
            try:
                # Parse timestamp from interaction
                timestamp_str = interaction.get("timestamp", "")
                interaction_date = datetime.fromisoformat(timestamp_str)
                
                if start_date <= interaction_date <= end_date:
                    count += 1
            except (ValueError, TypeError, AttributeError):
                continue
    
    return count


def get_sessions_today(sessions: List[Dict[str, Any]]) -> int:
    """Count interactions from today"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.utcnow()
    return count_interactions_in_period(sessions, today_start, today_end)


def get_sessions_this_week(sessions: List[Dict[str, Any]]) -> int:
    """Count interactions from this week (Monday-Sunday)"""
    today = datetime.utcnow()
    week_start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = datetime.utcnow()
    return count_interactions_in_period(sessions, week_start, week_end)

# ============= GOAL FUNCTIONS =============

def calculate_goal_progress(current: int, target: int) -> Dict[str, Any]:
    """Calculate goal progress metrics"""
    progress_percent = min((current / target * 100) if target > 0 else 0, 100)
    remaining = max(target - current, 0)
    
    return {
        "current": current,
        "target": target,
        "progress_percent": progress_percent,
        "remaining": remaining,
        "achieved": current >= target
    }


# ============= STATISTICS FUNCTIONS =============

def calculate_improvement_rate(scores: List[float], window: int = 5) -> float:
    """Calculate improvement rate over recent sessions"""
    if len(scores) < window * 2:
        return 0.0
    
    recent_scores = scores[-window:]
    previous_scores = scores[-window*2:-window]
    
    recent_avg = sum(recent_scores) / len(recent_scores)
    previous_avg = sum(previous_scores) / len(previous_scores)
    
    return recent_avg - previous_avg