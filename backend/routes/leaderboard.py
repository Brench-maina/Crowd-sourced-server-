from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, RoleEnum, Leaderboard
from sqlalchemy import desc
from datetime import datetime, timedelta

leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/leaderboard')


def get_leaderboard_data(current_user_id, page=1, per_page=20, days_ago=None):
    """
    Helper function to get leaderboard data
    If days_ago is None, returns all-time leaderboard
    Otherwise returns leaderboard for the specified time period
    """
    # Get leaderboard with user info
    query = (
        db.session.query(Leaderboard, User)
        .join(User, Leaderboard.user_id == User.id)
        .filter(User.role == RoleEnum.learner)
    )
    
    # For time-based leaderboards, we would need to filter by date
    # This requires PointsLog entries with created_at timestamps
    # For now, we'll use the all-time leaderboard for all timeframes
    # TODO: Implement time-based filtering using PointsLog
    
    query = query.order_by(Leaderboard.rank)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get current user's leaderboard entry
    current_user_entry = (
        db.session.query(Leaderboard, User)
        .join(User, Leaderboard.user_id == User.id)
        .filter(Leaderboard.user_id == current_user_id)
        .first()
    )
    
    # Get total learners count
    total_learners = (
        db.session.query(Leaderboard)
        .join(User, Leaderboard.user_id == User.id)
        .filter(User.role == RoleEnum.learner)
        .count()
    )
    
    # Format leaderboard data
    leaderboard_data = []
    for leaderboard_entry, user in paginated.items:
        leaderboard_data.append({
            "rank": leaderboard_entry.rank,
            "user_id": user.id,
            "username": user.username,
            "points": user.points,
            "xp": user.xp,
            "level": (user.xp // 500) + 1,
            "is_current_user": user.id == current_user_id
        })
    
    # Calculate current user stats
    current_user_data = None
    if current_user_entry:
        entry, user = current_user_entry
        
        # Find next rank user to calculate points gap
        next_rank_entry = (
            db.session.query(Leaderboard, User)
            .join(User, Leaderboard.user_id == User.id)
            .filter(
                User.role == RoleEnum.learner,
                Leaderboard.rank == entry.rank - 1
            )
            .first()
        )
        
        points_to_next_rank = None
        if next_rank_entry:
            _, next_user = next_rank_entry
            points_to_next_rank = next_user.points - user.points + 1
        
        current_user_data = {
            "rank": entry.rank,
            "points": user.points,
            "xp": user.xp,
            "points_to_next_rank": points_to_next_rank,
            "total_learners": total_learners
        }
    
    return {
        "leaderboard": leaderboard_data,
        "current_user": current_user_data,
        "page": page,
        "total_pages": paginated.pages,
        "total_players": paginated.total
    }


@leaderboard_bp.route('/weekly', methods=['GET'])
@jwt_required()
def get_weekly_leaderboard():
    """Get weekly leaderboard (last 7 days)"""
    try:
        current_user_id = int(get_jwt_identity())
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        data = get_leaderboard_data(current_user_id, page, per_page, days_ago=7)
        
        return jsonify({
            "type": "weekly",
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            **data
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to load weekly leaderboard: {str(e)}"}), 500


@leaderboard_bp.route('/monthly', methods=['GET'])
@jwt_required()
def get_monthly_leaderboard():
    """Get monthly leaderboard (last 30 days)"""
    try:
        current_user_id = int(get_jwt_identity())
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        data = get_leaderboard_data(current_user_id, page, per_page, days_ago=30)
        
        return jsonify({
            "type": "monthly",
            "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            **data
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to load monthly leaderboard: {str(e)}"}), 500


@leaderboard_bp.route('/allTime', methods=['GET'])
@jwt_required()
def get_all_time_leaderboard():
    """Get all-time leaderboard"""
    try:
        current_user_id = int(get_jwt_identity())
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        data = get_leaderboard_data(current_user_id, page, per_page, days_ago=None)
        
        return jsonify({
            "type": "allTime",
            **data
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to load all-time leaderboard: {str(e)}"}), 500


@leaderboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_leaderboard_stats():
    """Get overall leaderboard statistics"""
    try:
        total_learners = User.query.filter(User.role == RoleEnum.learner).count()
        total_xp = db.session.query(db.func.sum(User.xp)).filter(User.role == RoleEnum.learner).scalar() or 0
        total_points = db.session.query(db.func.sum(User.points)).filter(User.role == RoleEnum.learner).scalar() or 0
        avg_xp = total_xp // total_learners if total_learners > 0 else 0
        avg_points = total_points // total_learners if total_learners > 0 else 0
        
        # Top performer by XP
        top_xp_performer = (
            User.query
            .filter(User.role == RoleEnum.learner)
            .order_by(desc(User.xp))
            .first()
        )
        
        # Top performer by Points (leaderboard winner)
        top_points_performer = (
            db.session.query(User)
            .join(Leaderboard, User.id == Leaderboard.user_id)
            .filter(User.role == RoleEnum.learner)
            .order_by(Leaderboard.rank)
            .first()
        )
        
        return jsonify({
            "total_learners": total_learners,
            "total_xp_earned": total_xp,
            "total_points_earned": total_points,
            "average_xp": avg_xp,
            "average_points": avg_points,
            "top_xp_performer": {
                "username": top_xp_performer.username,
                "xp": top_xp_performer.xp,
                "level": (top_xp_performer.xp // 500) + 1
            } if top_xp_performer else None,
            "top_points_leader": {
                "username": top_points_performer.username,
                "points": top_points_performer.points,
                "xp": top_points_performer.xp
            } if top_points_performer else None
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to load stats: {str(e)}"}), 500