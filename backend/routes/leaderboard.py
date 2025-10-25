from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError
from models import db, User, PointsLog

leaderboard_bp = Blueprint('leaderboard_bp', __name__, url_prefix='/api/leaderboard')


def get_leaderboard_within_period(start_date=None, end_date=None, limit=50, page=1, per_page=20):
    try:
        query = db.session.query(
            User.id,
            User.username,
            func.coalesce(func.sum(PointsLog.points_change), 0).label('total_points')
        ).join(
            PointsLog, User.id == PointsLog.user_id
        )

        if start_date:
            query = query.filter(PointsLog.created_at >= start_date)
        if end_date:
            query = query.filter(PointsLog.created_at <= end_date)

        query = query.group_by(User.id, User.username).order_by(desc('total_points'))

        leaderboard = query.paginate(page=page, per_page=per_page, error_out=False)

        results = []
        for rank, (user_id, username, total_points) in enumerate(
            leaderboard.items, start=1 + (page - 1) * per_page
        ):
            results.append({
                "rank": rank,
                "user_id": user_id,
                "username": username,
                "points": total_points
            })

        return {
            "leaderboard": results,
            "page": page,
            "total_pages": leaderboard.pages,
            "total_players": leaderboard.total
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        return {"error": "Database error occurred", "details": str(e)}, 500
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e)}, 500


@leaderboard_bp.route('/weekly', methods=['GET'])
def get_weekly_leaderboard():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if page < 1 or per_page < 1:
            return jsonify({"error": "Invalid pagination parameters"}), 400

        start_date = datetime.utcnow() - timedelta(days=7)
        leaderboard_data = get_leaderboard_within_period(start_date=start_date, page=page, per_page=per_page)

        if "error" in leaderboard_data:
            return jsonify(leaderboard_data), 500

        return jsonify({
            "type": "weekly",
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            **leaderboard_data
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch weekly leaderboard", "details": str(e)}), 500


@leaderboard_bp.route('/monthly', methods=['GET'])
def get_monthly_leaderboard():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if page < 1 or per_page < 1:
            return jsonify({"error": "Invalid pagination parameters"}), 400

        start_date = datetime.utcnow() - timedelta(days=30)
        leaderboard_data = get_leaderboard_within_period(start_date=start_date, page=page, per_page=per_page)

        if "error" in leaderboard_data:
            return jsonify(leaderboard_data), 500

        return jsonify({
            "type": "monthly",
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            **leaderboard_data
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch monthly leaderboard", "details": str(e)}), 500


@leaderboard_bp.route('/allTime', methods=['GET'])
def get_all_time_leaderboard():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if page < 1 or per_page < 1:
            return jsonify({"error": "Invalid pagination parameters"}), 400

        leaderboard_data = get_leaderboard_within_period(page=page, per_page=per_page)

        if "error" in leaderboard_data:
            return jsonify(leaderboard_data), 500

        return jsonify({
            "type": "allTime",
            "start_date": None,
            "end_date": datetime.utcnow().isoformat(),
            **leaderboard_data
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch all-time leaderboard", "details": str(e)}), 500
