from models import db, Quiz, Question, Choice, UserProgress, Module, UserChallenge
from services.core_services import PointsService
from datetime import datetime

class QuizService:
    @staticmethod
    def evaluate_quiz(user, quiz_id, user_answers):
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            raise ValueError("Quiz not found.")

        total_questions = quiz.questions.count()
        correct_answers = 0

        for question in quiz.questions:
            chosen_choice_id = user_answers.get(str(question.id)) or user_answers.get(question.id)
            if not chosen_choice_id:
                continue

            selected_choice = Choice.query.get(chosen_choice_id)
            if selected_choice and selected_choice.is_correct:
                correct_answers += 1

        score_percent = int((correct_answers / total_questions) * 100)
        passed = score_percent >= quiz.passing_score

        # Update module progress
        if quiz.module:
            module = quiz.module
            progress = UserProgress.query.filter_by(user_id=user.id, module_id=module.id).first()
            if not progress:
                progress = UserProgress(user_id=user.id, module_id=module.id)

            progress.last_score = score_percent
            progress.completion_percent = 100 if passed else 50
            if passed:
                progress.completed_at = datetime.utcnow()
            db.session.add(progress)
            db.session.commit()

        # Handle challenge-linked quiz
        challenge = UserChallenge.query.filter_by(quiz_id=quiz.id).first()
        
        # AWARD POINTS BASED ON CORRECT ANSWERS (ALWAYS)
        if challenge:
            participation = challenge.participations.filter_by(user_id=user.id).first()
            if participation:
                participation.progress_percent = 100
                participation.is_completed = passed
                participation.completed_at = datetime.utcnow() if passed else None
                db.session.add(participation)
                db.session.commit()
            
            # Award challenge points based on performance
            QuizService._award_challenge_points(user, challenge, correct_answers, total_questions, passed)
        else:
            # Award regular quiz points based on performance
            QuizService._award_quiz_points(user, quiz, correct_answers, total_questions, passed)

        return {
            "quiz_id": quiz.id,
            "score_percent": score_percent,
            "passed": passed,
            "total_questions": total_questions,
            "correct_answers": correct_answers
        }

   