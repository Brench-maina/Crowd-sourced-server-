from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import (
    db, Quiz, Question, Choice, UserQuizAttempt, UserQuizAnswer, 
    User, UserChallenge, UserProgress, ChallengeParticipation
)
from utils.role_required import role_required
from services.core_services import PointsService, BadgeService
from services.quiz_services import QuizService

quizzes_bp = Blueprint("quizzes_bp", __name__)

#GET all quizzes for a module
@quizzes_bp.route("/<int:module_id>/quizzes", methods=["GET"])
@jwt_required()
def get_quizzes(module_id):
    quizzes = Quiz.query.filter_by(module_id=module_id).all()
    return jsonify([q.to_dict() for q in quizzes]), 200


#GET a specific quiz (with questions)
@quizzes_bp.route("/<int:module_id>/quizzes/<int:quiz_id>", methods=["GET"])
@jwt_required()
def get_quiz(module_id, quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, module_id=module_id).first_or_404()
    questions_data = [
        {
            "id": q.id,
            "text": q.text,
            "choices": [c.to_public_dict() for c in q.choices]
        } for q in quiz.questions
    ]
    return jsonify({
        "id": quiz.id,
        "title": quiz.title,
        "module_id": quiz.module_id,
        "questions": questions_data
    }), 200


#CREATE a quiz under a module
@quizzes_bp.route("/<int:module_id>/quizzes", methods=["POST"])
@jwt_required()
@role_required("admin", "contributor")
def create_quiz(module_id):
    data = request.get_json()
    title = data.get("title")
    passing_score = data.get("passing_score", 70)
    
    if not title:
        return jsonify({"error": "Quiz title is required"}), 400
    
    new_quiz = Quiz(title=title, module_id=module_id, passing_score=passing_score)
    db.session.add(new_quiz)
    db.session.commit()
    return jsonify(new_quiz.to_dict()), 201


#ADD a question to a quiz
@quizzes_bp.route("/<int:module_id>/quizzes/<int:quiz_id>/questions", methods=["POST"])
@jwt_required()
@role_required("admin", "contributor")
def add_question(module_id, quiz_id):
    data = request.get_json()
    text = data.get("text")
    choices = data.get("choices", []) 
    
    if not text or not choices:
        return jsonify({"error": "Question text and choices are required"}), 400
    
    quiz = Quiz.query.filter_by(id=quiz_id, module_id=module_id).first_or_404()
    
    question = Question(text=text, quiz_id=quiz.id)
    db.session.add(question)
    db.session.commit()
    
    for choice_data in choices:
        choice = Choice(
            text=choice_data["text"],
            is_correct=choice_data.get("is_correct", False),
            question_id=question.id
        )
        db.session.add(choice)
    db.session.commit()
    
    return jsonify(question.to_dict()), 201


#SUBMIT quiz attempt
@quizzes_bp.route("/<int:module_id>/quizzes/<int:quiz_id>/attempt", methods=["POST"])
@jwt_required()
def submit_quiz(module_id, quiz_id):
    current_user = get_jwt_identity()
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user
    
    data = request.get_json()
    answers = data.get("answers", [])
    
    if not answers:
        return jsonify({"error": "Answers required"}), 400
    
    quiz = Quiz.query.filter_by(id=quiz_id, module_id=module_id).first_or_404()
    user = User.query.get(user_id)
    
    attempt = UserQuizAttempt(user_id=user_id, quiz_id=quiz_id, started_at=datetime.utcnow())
    db.session.add(attempt)
    db.session.flush()
    
    correct_count = 0
    for ans in answers:
        question = Question.query.get(ans["question_id"])
        choice = Choice.query.get(ans["choice_id"])
        if not question or not choice:
            continue
        
        is_correct = choice.is_correct
        if is_correct:
            correct_count += 1
        
        user_answer = UserQuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            choice_id=choice.id,
            is_correct=is_correct
        )
        db.session.add(user_answer)
    
    total_questions = quiz.questions.count()
    score = int((correct_count / total_questions) * 100) if total_questions else 0
    passed = score >= quiz.passing_score
    
    attempt.score = score
    attempt.passed = passed
    attempt.completed_at = datetime.utcnow()
    
    if quiz.module:
        progress = UserProgress.query.filter_by(user_id=user_id, module_id=quiz.module.id).first()
        if not progress:
            progress = UserProgress(user_id=user_id, module_id=quiz.module.id)
        
        progress.last_score = score
        progress.completion_percent = 100 if passed else 50
        if passed:
            progress.completed_at = datetime.utcnow()
        db.session.add(progress)
    
    challenge = UserChallenge.query.filter_by(quiz_id=quiz_id).first()
    challenge_completed = False
    
    if challenge:
        participation = ChallengeParticipation.query.filter_by(
            user_id=user_id, 
            challenge_id=challenge.id
        ).first()
        
        if not participation:
            participation = ChallengeParticipation(
                user_id=user_id,
                challenge_id=challenge.id,
                started_at=datetime.utcnow()
            )
            BadgeService.check_badges(user, "participate_challenge")  
        
        participation.progress_percent = 100
        participation.is_completed = passed
        if passed:
            participation.completed_at = datetime.utcnow()
            challenge_completed = True
        
        db.session.add(participation)
    
    db.session.commit()
    
    if challenge and challenge_completed:
        PointsService.award_points(
            user, "complete_challenge", 
            points=challenge.points_reward,
            metadata=f"Challenge: {challenge.title}"
        )
        PointsService.award_xp_only(
            user, "complete_challenge",
            xp=challenge.xp_reward,
            metadata=f"Challenge: {challenge.title}"
        )
        if correct_count > 0:
            PointsService.award_points(
                user, "challenge_bonus",
                points=correct_count * 15,
                metadata=f"Challenge: {challenge.title} - {correct_count} correct"
            )
            PointsService.award_xp(
                user, "challenge_bonus",
                xp=correct_count * 10,
                metadata=f"Challenge: {challenge.title} - {correct_count} correct"
            )
    elif passed:
        PointsService.award_points(user, "pass_quiz", points=50, metadata=f"Quiz: {quiz.title}")
        PointsService.award_xp_only(user, "pass_quiz", xp=150, metadata=f"Quiz: {quiz.title}")
        
        if correct_count > 0:
            PointsService.award_points(
                user, "quiz_correct_answers",
                points=correct_count * 10,
                metadata=f"Quiz: {quiz.title} - {correct_count} correct"
            )
            PointsService.award_xp_only(
                user, "quiz_correct_answers",
                xp=correct_count * 5,
                metadata=f"Quiz: {quiz.title} - {correct_count} correct"
            )
        
        if correct_count == total_questions:
            PointsService.award_points(user, "quiz_perfect", points=25, metadata=f"Perfect: {quiz.title}")
            PointsService.award_xp_only(user, "quiz_perfect", xp=50, metadata=f"Perfect: {quiz.title}")
    else:
        if correct_count > 0:
            PointsService.award_points(
                user,
                "quiz_attempt",
                points=correct_count * 5,
                metadata=f"Quiz: {quiz.title} - Attempted"
            )
    
    return jsonify({
        "attempt_id": attempt.id,
        "score": attempt.score,
        "passed": attempt.passed,
        "correct_answers": correct_count,
        "total_questions": total_questions,
        "challenge_completed": challenge.title if (challenge and challenge_completed) else None
    }), 200


#GET all attempts for a quiz
@quizzes_bp.route("/<int:module_id>/quizzes/<int:quiz_id>/attempts", methods=["GET"])
@jwt_required()
def get_quiz_attempts(module_id, quiz_id):
    current_user = get_jwt_identity()
    user_id = current_user["id"] if isinstance(current_user, dict) else current_user
    
    attempts = UserQuizAttempt.query.filter_by(user_id=user_id, quiz_id=quiz_id).all()
    data = [{
        "attempt_id": a.id,
        "score": a.score,
        "passed": a.passed,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None
    } for a in attempts]
    
    return jsonify(data), 200


#Admin: Link a quiz to a challenge
@quizzes_bp.route("/challenges/<int:challenge_id>/link-quiz", methods=["POST"])
@jwt_required()
@role_required("admin")
def link_quiz_to_challenge(challenge_id):
    data = request.get_json()
    quiz_id = data.get("quiz_id")
    challenge = UserChallenge.query.get_or_404(challenge_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    
    challenge.quiz_id = quiz.id
    db.session.commit()
    
    return jsonify({
        "message": f"Quiz {quiz.title} linked to challenge {challenge.title}",
        "challenge": challenge.to_dict()
    }), 200
