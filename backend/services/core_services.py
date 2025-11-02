from datetime import datetime
from sqlalchemy import func
from models import (
    db,
    User,
    Badge,
    UserBadge,
    PointsLog,
    UserProgress,
    LearningPath,
    Module,
    ChallengeParticipation,
    Leaderboard
)
from utils.constants import POINTS_CONFIG, XP_CONFIG, BADGE_RULES


class PointsService:
    """Handles awarding of points and XP for user actions."""

    @staticmethod
    def award_points(user, action, metadata=None):
        """Award points and XP for a given user action."""
        if action not in POINTS_CONFIG:
            raise ValueError(f"Unknown action: {action}")

        points = POINTS_CONFIG[action]
        xp = XP_CONFIG.get(action, 0)

        # Update user stats
        user.points = (user.points or 0) + points
        if xp > 0:
            user.xp = (user.xp or 0) + xp

        # Log the transaction
        points_log = PointsLog(
            user_id=user.id,
            points_change=points,
            reason=f"{action}: {metadata}" if metadata else action
        )
        db.session.add(points_log)

        # Check for badge unlocks (but don't commit yet)
        awarded_badges = BadgeService.check_badges(user, action)

        # Update leaderboard
        LeaderboardService.update_user_rank(user)

        # Commit everything together
        db.session.commit()

        return {
            "points": points,
            "xp": xp,
            "action": action,
            "badges_awarded": awarded_badges
        }

    @staticmethod
    def award_xp_only(user, action, metadata=None):
        """Award only XP without points (for streak bonuses)"""
        xp = XP_CONFIG.get(action, 0)
        if xp > 0:
            user.xp = (user.xp or 0) + xp
            db.session.commit()
        return {"xp": xp, "action": action}

    @staticmethod
    def award_daily_login(user):
        """Award daily login points and handle streaks"""
        user.update_streak()  
        
        result = PointsService.award_points(user, 'daily_login')

        # Handle streak milestones (XP only, no points)
        if user.streak_days == 7:
            PointsService.award_xp_only(user, 'daily_streak_7_days')
        elif user.streak_days == 30:
            PointsService.award_xp_only(user, 'daily_streak_30_days')
            
        return result


class BadgeService:

    @staticmethod
    def check_badges(user, action, metadata=None):
        """Check and award badges based on user action"""
        awarded_badges = []

        # Direct trigger badges (first-time achievements)
        trigger_map = {
            "complete_module": "first_module",
            "complete_quiz": "first_quiz",
            "create_learning_path": "first_learning_path",
            "daily_login": "first_login",
            "participate_challenge": "first_challenge_participation",
            "complete_challenge": "first_challenge_completed"
        }

        if action in trigger_map:
            badge_key = trigger_map[action]
            
            # IMPORTANT: Only award challenge badges if it's actually a challenge
            if action in ["participate_challenge", "complete_challenge"]:
                # Verify this is a real challenge by checking metadata or challenge participation
                if not metadata or "challenge" not in str(metadata).lower():
                    # Check if user actually has challenge participation
                    has_challenges = ChallengeParticipation.query.filter_by(user_id=user.id).first()
                    if not has_challenges:
                        # Skip challenge badges if no actual challenge participation
                        pass
                    else:
                        if not BadgeService.has_badge(user, badge_key):
                            BadgeService.award_badge(user, badge_key)
                            awarded_badges.append(badge_key)
                else:
                    if not BadgeService.has_badge(user, badge_key):
                        BadgeService.award_badge(user, badge_key)
                        awarded_badges.append(badge_key)
            else:
                # Non-challenge badges - award normally
                if not BadgeService.has_badge(user, badge_key):
                    BadgeService.award_badge(user, badge_key)
                    awarded_badges.append(badge_key)

        # Check milestone badges (excluding challenge badges that shouldn't be checked here)
        awarded_badges.extend(BadgeService._check_milestone_badges(user))

        return awarded_badges

    @staticmethod
    def _check_milestone_badges(user):
        """Evaluate milestone-based badges"""
        badges = []

        # 5 completed modules
        completed_modules = UserProgress.query.filter_by(
            user_id=user.id, completion_percent=100
        ).count()
        if completed_modules >= 5 and not BadgeService.has_badge(user, "module_explorer"):
            BadgeService.award_badge(user, badge_key="module_explorer", skip_points=True)
            badges.append("module_explorer")

        # 30-day streak badge
        if user.streak_days >= 30 and not BadgeService.has_badge(user, "streak_30_days"):
            BadgeService.award_badge(user, badge_key="streak_30_days", skip_points=True)
            badges.append("streak_30_days")

        # Path Completer (completed at least 1 learning path)
        completed_paths = BadgeService._get_completed_learning_paths(user)
        if completed_paths >= 1 and not BadgeService.has_badge(user, "path_completer"):
            BadgeService.award_badge(user, badge_key="path_completer", skip_points=True)
            badges.append("path_completer")

        # Quiz Master (10 completed quizzes)
        # Note: This counts completed modules as a proxy - you should track quiz attempts separately
        if completed_modules >= 10 and not BadgeService.has_badge(user, "quiz_master"):
            BadgeService.award_badge(user, badge_key="quiz_master", skip_points=True)
            badges.append("quiz_master")

        # Challenge badges
        participated_challenges = ChallengeParticipation.query.filter_by(user_id=user.id).count()
        if participated_challenges >= 5 and not BadgeService.has_badge(user, "challenge_warrior"):
            BadgeService.award_badge(user, badge_key="challenge_warrior", skip_points=True)
            badges.append("challenge_warrior")

        completed_challenges = ChallengeParticipation.query.filter_by(
            user_id=user.id, is_completed=True
        ).count()
        if completed_challenges >= 3 and not BadgeService.has_badge(user, "challenge_conqueror"):
            BadgeService.award_badge(user, badge_key="challenge_conqueror", skip_points=True)
            badges.append("challenge_conqueror")

        return badges

    @staticmethod
    def _get_completed_learning_paths(user):
        """Count completed learning paths (all modules complete)"""
        # Get all learning paths
        all_paths = LearningPath.query.all()
        completed_count = 0
        
        for path in all_paths:
            # Get all modules in this path
            path_modules = Module.query.filter_by(learning_path_id=path.id).all()
            if not path_modules:
                continue
                
            # Check if user completed all modules in this path
            completed_modules_in_path = 0
            for module in path_modules:
                progress = UserProgress.query.filter_by(
                    user_id=user.id,
                    module_id=module.id,
                    completion_percent=100
                ).first()
                if progress:
                    completed_modules_in_path += 1
            
            # If all modules completed, count this path
            if completed_modules_in_path == len(path_modules):
                completed_count += 1
        
        return completed_count

    @staticmethod
    def has_badge(user, badge_key):
        """Check if user already has this badge"""
        return (
            UserBadge.query.join(Badge)
            .filter(UserBadge.user_id == user.id, Badge.key == badge_key)
            .first()
            is not None
        )

    @staticmethod
    def award_badge(user, badge_key, skip_points=False):
        """Grant a badge to a user"""
        # Check if badge exists in rules
        rule = BADGE_RULES.get(badge_key)
        if not rule:
            raise ValueError(f"Badge '{badge_key}' not defined in BADGE_RULES")

        # Get or create badge
        badge = Badge.query.filter_by(key=badge_key).first()
        if not badge:
            badge = Badge(
                key=badge_key,
                name=rule["name"],
                description=rule["description"]
            )
            db.session.add(badge)
            db.session.flush()

        # Create user badge record
        user_badge = UserBadge(
            user_id=user.id,
            badge_id=badge.id,
            awarded_at=datetime.utcnow()
        )
        db.session.add(user_badge)

        # Award badge points (only if not skipped to avoid double-counting)
        if not skip_points:
            badge_points = POINTS_CONFIG.get('earn_badge', 10)
            user.points = (user.points or 0) + badge_points
            
            # Log badge points
            points_log = PointsLog(
                user_id=user.id,
                points_change=badge_points,
                reason=f"Badge earned: {badge.name}"
            )
            db.session.add(points_log)
            
            # Update leaderboard
            LeaderboardService.update_user_rank(user)

        return badge_key

    @staticmethod
    def get_user_badge_progress(user_id):
        """Return a user's progress toward each badge"""
        user = User.query.get(user_id)
        if not user:
            return {}
            
        progress = {}

        # Module badges
        completed_modules = UserProgress.query.filter_by(
            user_id=user_id, completion_percent=100
        ).count()
        progress["first_module"] = completed_modules >= 1
        progress["module_explorer"] = {
            "current": completed_modules,
            "target": 5,
            "completed": completed_modules >= 5
        }

        # Quiz badges (using module completion as proxy)
        progress["first_quiz"] = completed_modules >= 1
        progress["quiz_master"] = {
            "current": completed_modules,
            "target": 10,
            "completed": completed_modules >= 10
        }

        # Learning path badges
        created_paths = LearningPath.query.filter_by(creator_id=user_id).count()
        completed_paths = BadgeService._get_completed_learning_paths(user)
        progress["first_learning_path"] = created_paths >= 1
        progress["path_completer"] = completed_paths >= 1

        # Streak badges
        progress["streak_30_days"] = user.streak_days >= 30

        # Challenge badges
        participated = ChallengeParticipation.query.filter_by(user_id=user_id).count()
        completed = ChallengeParticipation.query.filter_by(user_id=user_id, is_completed=True).count()
        progress["first_challenge_participation"] = participated >= 1
        progress["challenge_warrior"] = {
            "current": participated,
            "target": 5,
            "completed": participated >= 5
        }
        progress["first_challenge_completed"] = completed >= 1
        progress["challenge_conqueror"] = {
            "current": completed,
            "target": 3,
            "completed": completed >= 3
        }

        return progress


class LeaderboardService:
    @staticmethod
    def update_user_rank(user):
        """Update or create leaderboard entry for user"""
        entry = Leaderboard.query.filter_by(user_id=user.id).first()
        if not entry:
            entry = Leaderboard(user_id=user.id, total_points=user.points)
            db.session.add(entry)
        else:
            entry.total_points = user.points
        
        # Don't commit here - let the caller commit
        # This prevents premature commits during batch operations

    @staticmethod
    def update_all_ranks():
        """Recalculate ranks for all users based on points"""
        entries = Leaderboard.query.order_by(Leaderboard.total_points.desc()).all()
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank
        db.session.commit()

    @staticmethod
    def get_top_users(limit=10):
        """Get top N users from leaderboard"""
        return (
            Leaderboard.query.join(User)
            .order_by(Leaderboard.rank)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_user_rank(user_id):
        """Get rank for specific user"""
        entry = Leaderboard.query.filter_by(user_id=user_id).first()
        return entry.rank if entry else None

    @staticmethod
    def get_leaderboard_page(page=1, per_page=20):
        """Get paginated leaderboard"""
        return (
            Leaderboard.query.join(User)
            .order_by(Leaderboard.rank)
            .paginate(page=page, per_page=per_page, error_out=False)
        )
    
    @staticmethod
    def rebuild_leaderboard():
        """Rebuild entire leaderboard from user data (for fixing inconsistencies)"""
        # Clear existing leaderboard
        Leaderboard.query.delete()
        
        # Get all users with points
        users = User.query.filter(User.points > 0).all()
        
        for user in users:
            entry = Leaderboard(user_id=user.id, total_points=user.points)
            db.session.add(entry)
        
        db.session.commit()
        
        # Update ranks
        LeaderboardService.update_all_ranks()