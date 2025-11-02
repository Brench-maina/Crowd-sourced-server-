from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
from models import db, LearningPath, ContentStatusEnum, User, UserProgress, Module, LearningResource, Quiz, UserQuizAttempt, Question
from utils.role_required import role_required
from services.core_services import PointsService

learning_paths_bp = Blueprint('learning_paths_bp', __name__)


def get_current_user():
    identity = get_jwt_identity()
    user_id = identity["id"] if isinstance(identity, dict) else identity
    return User.query.get(user_id), user_id

#create Learning Path
@learning_paths_bp.route('/paths', methods=['POST'])
@jwt_required()
def create_learning_path():
    try:
        user, user_id = get_current_user()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        if not title or len(title) < 5:
            return jsonify({"error": "Title must be at least 5 characters long"}), 400
        if not description:
            return jsonify({"error": "Description is required"}), 400
        
        new_path = LearningPath(
            title=title,
            description=description,
            creator_id=user_id,
            status=ContentStatusEnum.pending,
            is_published=False,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_path)
        db.session.commit()
        
        return jsonify({
            "message": "Learning path created successfully",
            "path": {
                "id": new_path.id,
                "title": new_path.title,
                "description": new_path.description,
                "status": new_path.status.value,
                "is_published": new_path.is_published
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create learning path: {str(e)}"}), 500

# GET All Published Learning Paths
@learning_paths_bp.route("/paths", methods=["GET"])
def get_learning_paths():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    status_filter = request.args.get("status")

    current_user = None
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = identity["id"] if isinstance(identity, dict) else identity
            current_user = User.query.get(user_id)
    except:
        pass

    query = LearningPath.query

    # Only admins can see unpublished paths
    if not (current_user and current_user.role == "admin"):
        query = query.filter(LearningPath.is_published == True)
    elif status_filter:
        if status_filter == "published":
            query = query.filter(LearningPath.is_published == True)
        elif status_filter == "pending":
            query = query.filter(LearningPath.is_published == False)

    paths_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    paths_list = [{
        "id": lp.id,
        "title": lp.title,
        "description": lp.description,
        "is_published": lp.is_published,
        "is_following": lp in current_user.followed_paths if current_user else False
    } for lp in paths_paginated.items]

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": paths_paginated.total,
        "paths": paths_list
    })

# GET Modules for a Learning Path
@learning_paths_bp.route('/<int:path_id>/modules', methods=['GET'])
@jwt_required()
def get_path_modules(path_id):
    try:
        path = LearningPath.query.get_or_404(path_id)
        user, user_id = get_current_user()
        
        # Check permissions
        if int(path.creator_id) != int(user_id) and user.role != "admin":
            if not path.is_published:
                return jsonify({"error": "Access denied"}), 403
        
        modules = Module.query.filter_by(learning_path_id=path_id).order_by(Module.id).all()
        
        modules_list = []
        for module in modules:
            resource_count = LearningResource.query.filter_by(module_id=module.id).count()
            quiz_count = Quiz.query.filter_by(module_id=module.id).count()
            
            module_dict = {
                "id": module.id,
                "title": module.title,
                "description": module.description,
                "resource_count": resource_count,
                "quiz_count": quiz_count
            }
            
            if path in user.followed_paths:
                progress = UserProgress.query.filter_by(user_id=user_id, module_id=module.id).first()
                module_dict["is_completed"] = progress.completion_percent == 100 if progress else False
                module_dict["completion_percent"] = progress.completion_percent if progress else 0
            else:
                module_dict["is_completed"] = False
                module_dict["completion_percent"] = 0
            
            modules_list.append(module_dict)
        
        return jsonify(modules_list), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch modules: {str(e)}"}), 500

# create Module
@learning_paths_bp.route('/<int:path_id>/modules', methods=['POST'])
@jwt_required()
def create_module(path_id):
    try:
        user, user_id = get_current_user()
        path = LearningPath.query.get_or_404(path_id)
        
        if int(path.creator_id) != int(user_id) and user.role != "admin":
            return jsonify({"error": "Only the path creator can add modules"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        if not title or len(title) < 3:
            return jsonify({"error": "Module title must be at least 3 characters"}), 400
        
        new_module = Module(title=title, description=description, learning_path_id=path_id)
        db.session.add(new_module)
        db.session.commit()
        
        return jsonify({
            "message": "Module created successfully",
            "module": {"id": new_module.id, "title": new_module.title, "description": new_module.description}
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create module: {str(e)}"}), 500
    
  # GET Module Details 
@learning_paths_bp.route('/modules/<int:module_id>', methods=['GET'])
@jwt_required()
def get_module_details(module_id):
    try:
        module = Module.query.get_or_404(module_id)
        path = LearningPath.query.get_or_404(module.learning_path_id)
        user, user_id = get_current_user()
        
        # Check access
        has_access = (
            path.is_published or 
            int(path.creator_id) == int(user_id) or 
            user.role == "admin" or 
            path in user.followed_paths
        )
        if not has_access:
            return jsonify({"error": "Access denied"}), 403
        
        # Get resources
        resources = LearningResource.query.filter_by(module_id=module_id).all()
        resources_list = [{
            "id": r.id,
            "title": r.title,
            "type": r.type,
            "url": r.url,
            "description": getattr(r, 'description', None)
        } for r in resources]
        
        # Get quizzes - SIMPLIFIED
        quizzes = Quiz.query.filter_by(module_id=module_id).all()
        quizzes_list = []
        for quiz in quizzes:
            question_count = Question.query.filter_by(quiz_id=quiz.id).count()
            user_attempt = UserQuizAttempt.query.filter_by(
                user_id=user_id, quiz_id=quiz.id
            ).first()  # Just get any attempt
            
            quizzes_list.append({
                "id": quiz.id,
                "title": quiz.title,
                "description": getattr(quiz, 'description', None),
                "question_count": question_count,
                "has_attempted": user_attempt is not None,
                "last_score": user_attempt.score if user_attempt else None
            })
        
        # Get progress
        progress = UserProgress.query.filter_by(user_id=user_id, module_id=module_id).first()
        
        return jsonify({
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "resources": resources_list,
            "quizzes": quizzes_list,
            "is_completed": progress.completion_percent == 100 if progress else False,
            "completion_percent": progress.completion_percent if progress else 0,
            "learning_path": {"id": path.id, "title": path.title}
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch module details: {str(e)}"}), 500
    
# Update Module
@learning_paths_bp.route('/modules/<int:module_id>', methods=['PUT'])
@jwt_required()
def update_module(module_id):
    try:
        user, user_id = get_current_user()
        module = Module.query.get_or_404(module_id)
        path = LearningPath.query.get_or_404(module.learning_path_id)
        
        if int(path.creator_id) != int(user_id) and user.role != "admin":
            return jsonify({"error": "Not authorized to update this module"}), 403

        data = request.get_json()
        module.title = data.get("title", module.title)
        module.description = data.get("description", module.description)
        db.session.commit()

        return jsonify({
            "message": "Module updated successfully",
            "module": {"id": module.id, "title": module.title, "description": module.description}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Delete Module
@learning_paths_bp.route('/modules/<int:module_id>', methods=['DELETE'])
@jwt_required()
def delete_module(module_id):
    try:
        user, user_id = get_current_user()
        module = Module.query.get_or_404(module_id)
        path = LearningPath.query.get_or_404(module.learning_path_id)

        if int(path.creator_id) != int(user_id) and user.role != "admin":
            return jsonify({"error": "Not authorized to delete this module"}), 403

        db.session.delete(module)
        db.session.commit()
        return jsonify({"message": "Module deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete module: {str(e)}"}), 500

# Start Module
@learning_paths_bp.route('/modules/<int:module_id>/start', methods=['POST'])
@jwt_required()
def start_module(module_id):
    try:
        user, user_id = get_current_user()
        module = Module.query.get_or_404(module_id)
        path = LearningPath.query.get_or_404(module.learning_path_id)
        
        if path not in user.followed_paths:
            return jsonify({"error": "You must follow the learning path first"}), 403
        
        progress = UserProgress.query.filter_by(user_id=user_id, module_id=module_id).first()
        
        if not progress:
            progress = UserProgress(user_id=user_id, module_id=module_id, completion_percent=0)
            db.session.add(progress)
            db.session.commit()
            return jsonify({"message": "Module started", "completion_percent": 0}), 200
        
        return jsonify({"message": "Module already in progress", "completion_percent": progress.completion_percent}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to start module: {str(e)}"}), 500

# Complete Module
@learning_paths_bp.route('/modules/<int:module_id>/complete', methods=['POST'])
@jwt_required()
def complete_module(module_id):
    try:
        user, user_id = get_current_user()
        module = Module.query.get_or_404(module_id)
        path = LearningPath.query.get_or_404(module.learning_path_id)
        
        if path not in user.followed_paths:
            return jsonify({"error": "You must follow the learning path first"}), 403
        
        progress = UserProgress.query.filter_by(user_id=user_id, module_id=module_id).first()
        
        if not progress:
            progress = UserProgress(user_id=user_id, module_id=module_id, completion_percent=100)
            db.session.add(progress)
        else:
            progress.completion_percent = 100
        
        db.session.commit()
        
        # Award points
        try:
            PointsService.award_points(user, 'complete_module')
        except Exception as e:
            print(f"Failed to award points: {e}")
        
        # Calculate path completion
        all_modules = Module.query.filter_by(learning_path_id=path.id).all()
        completed_count = sum(1 for m in all_modules 
                            if UserProgress.query.filter_by(user_id=user_id, module_id=m.id, completion_percent=100).first())
        
        path_completion = int((completed_count / len(all_modules)) * 100) if all_modules else 0
        
        return jsonify({
            "message": "Module marked as complete",
            "path_completion_percentage": path_completion,
            "completed_modules": completed_count,
            "total_modules": len(all_modules)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to complete module: {str(e)}"}), 500

# Follow Path
@learning_paths_bp.route('/paths/<int:path_id>/follow', methods=['POST'])
@jwt_required()
def follow_path(path_id):
    try:
        user, _ = get_current_user()
        path = LearningPath.query.get_or_404(path_id)

        if path in user.followed_paths:
            return jsonify({"message": "Already following this path"}), 200

        user.followed_paths.append(path)
        db.session.commit()
        return jsonify({"message": "Successfully followed path", "path": {"id": path.id, "title": path.title}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to follow learning path: {str(e)}"}), 500

# Unfollow Path
@learning_paths_bp.route('/paths/<int:path_id>/unfollow', methods=['POST'])
@jwt_required()
def unfollow_path(path_id):
    try:
        user, _ = get_current_user()
        path = LearningPath.query.get_or_404(path_id)

        if path not in user.followed_paths:
            return jsonify({"error": "Not following this path"}), 400

        user.followed_paths.remove(path)
        db.session.commit()
        return jsonify({"message": "Unfollowed learning path", "path": {"id": path.id, "title": path.title}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to unfollow learning path"}), 500

# GET My Paths
@learning_paths_bp.route("/my-paths", methods=["GET"])
@jwt_required()
def get_my_learning_paths():
    try:
        user, user_id = get_current_user()
        followed_paths = []

        for path in user.followed_paths:
            if path.is_published:
                completed = sum(1 for m in path.modules 
                              if UserProgress.query.filter_by(user_id=user_id, module_id=m.id, completion_percent=100).first())
                total = len(path.modules)
                
                followed_paths.append({
                    "id": path.id,
                    "title": path.title,
                    "description": path.description,
                    "completion_percentage": int((completed / total) * 100) if total > 0 else 0
                })

        return jsonify(followed_paths), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve followed paths: {str(e)}"}), 500

# Update Learning Path
@learning_paths_bp.route('/paths/<int:path_id>', methods=['PUT'])
@jwt_required()
def update_learning_path(path_id):
    try:
        user, user_id = get_current_user()
        path = LearningPath.query.get_or_404(path_id)

        if int(path.creator_id) != int(user_id) and user.role != "admin":
            return jsonify({"error": "Not authorized to edit this learning path"}), 403

        data = request.get_json()
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()

        if not title or len(title) < 5:
            return jsonify({"error": "Title must be at least 5 characters long"}), 400
        if not description:
            return jsonify({"error": "Description is required"}), 400

        path.title = title
        path.description = description
        path.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "message": "Learning path updated successfully",
            "path": {"id": path.id, "title": path.title, "description": path.description, 
                    "is_published": path.is_published, "status": path.status.value}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update learning path: {str(e)}"}), 500

# Delete Learning Path
@learning_paths_bp.route('/paths/<int:path_id>', methods=['DELETE'])
@jwt_required()
def delete_learning_path(path_id):
    try:
        user, user_id = get_current_user()
        path = LearningPath.query.get_or_404(path_id)

        if int(path.creator_id) != int(user_id) and user.role != "admin":
            return jsonify({"error": "Not authorized to delete this path"}), 403

        db.session.delete(path)
        db.session.commit()
        return jsonify({"message": "Learning path deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete path: {str(e)}"}), 500

# Admin Review Path
@learning_paths_bp.route('/admin/paths/<int:path_id>/review', methods=['PUT'])
@jwt_required()
@role_required("admin")
def review_learning_path(path_id):
    try:
        user, user_id = get_current_user()
        path = LearningPath.query.get_or_404(path_id)
        data = request.get_json()
        
        action = data.get("action")
        reason = data.get("reason", "")

        if not action:
            return jsonify({"error": "Action is required"}), 400

        if action == "approve":
            path.status = ContentStatusEnum.approved
            path.is_published = True
            path.reviewed_by = user_id
            path.rejection_reason = None
            
            if path.creator:
                try:
                    PointsService.award_points(path.creator, 'learning_path_approved')
                except Exception as e:
                    print(f"Failed to award points: {e}")
            
        elif action == "reject":
            if not reason.strip():
                return jsonify({"error": "Rejection reason is required"}), 400
            path.status = ContentStatusEnum.rejected
            path.is_published = False
            path.rejection_reason = reason
            path.reviewed_by = user_id
        else:
            return jsonify({"error": "Invalid action. Use 'approve' or 'reject'"}), 400

        db.session.commit()
        return jsonify({
            "message": f"Learning path {action}d successfully",
            "path": {"id": path.id, "title": path.title, "status": path.status.value, "is_published": path.is_published}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to review learning path: {str(e)}"}), 500

# Admin Get Pending Paths
@learning_paths_bp.route('/admin/paths/pending', methods=['GET'])
@jwt_required()
@role_required("admin")
def get_pending_paths():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    pending = LearningPath.query.filter_by(status=ContentStatusEnum.pending).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "pending_paths": [{
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "creator": p.creator.username if p.creator else "Unknown",
            "module_count": p.modules.count(),
            "created_at": p.created_at.isoformat()
        } for p in pending.items],
        "page": page,
        "total_pages": pending.pages,
        "total_items": pending.total
    }), 200

# Contributor Stats
@learning_paths_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_contributor_stats():
    try:
        user, user_id = get_current_user()
        paths = LearningPath.query.filter_by(creator_id=user_id).all()
        
        total_paths = len(paths)
        approved_paths = sum(1 for p in paths if p.status == ContentStatusEnum.approved)
        total_views = sum(getattr(p, "views", 0) for p in paths)
        
        xp = getattr(user, "xp", 0)
        level = xp // 1000 + 1
        
        # Calculate avg rating
        ratings = [p.rating for p in paths if hasattr(p, "rating") and p.rating is not None]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

        return jsonify({
            "xp": xp,
            "level": level,
            "total_resources": total_paths,
            "approved_resources": approved_paths,
            "total_views": total_views,
            "avg_rating": avg_rating
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500