
from datetime import datetime, date, timedelta
import enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

db = SQLAlchemy()


# Enums 
class RoleEnum(enum.Enum):
    admin = "admin"
    contributor = "contributor"
    learner = "learner"


class ContentStatusEnum(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

# Association Tables 
path_contributors = db.Table(
    "path_contributors",
    db.Column("path_id", db.Integer, db.ForeignKey("learning_path.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True)
)

path_followers = db.Table(
    "path_followers",
    db.Column("path_id", db.Integer, db.ForeignKey("learning_path.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True)
)


# Core Models
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(RoleEnum), nullable=False, default=RoleEnum.learner)
    points = db.Column(db.Integer, default=0, nullable=False, index=True)
    xp = db.Column(db.Integer, default=0, nullable=False)
    streak_days = db.Column(db.Integer, default=0)
    last_streak_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_paths = db.relationship("LearningPath",back_populates="creator",lazy="dynamic",cascade="all, delete-orphan",foreign_keys="LearningPath.creator_id")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    contributions = db.relationship("LearningPath", secondary=path_contributors, back_populates="contributors")
    followed_paths = db.relationship("LearningPath", secondary=path_followers, back_populates="followers")
    badges = db.relationship("UserBadge", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    progress = db.relationship("UserProgress", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    posts = db.relationship("CommunityPost", back_populates="author", cascade="all, delete-orphan", lazy="dynamic")
    comments = db.relationship("CommunityComment", back_populates="author", cascade="all, delete-orphan", lazy="dynamic")
    leaderboard_entry = db.relationship("Leaderboard", back_populates="user", uselist=False, cascade="all, delete-orphan")

    #  Methods 
    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "points": self.points,
            "xp": self.xp,
            "streak_days": self.streak_days,
            "badges": [badge.badge.name for badge in self.badges],
        }

    def update_streak(self):
        """Update daily login/activity streaks."""
        today = date.today()
        if self.last_streak_date == today:
            return
        if self.last_streak_date == today - timedelta(days=1):
            self.streak_days += 1
        else:
            self.streak_days = 1
        self.last_streak_date = today
        db.session.commit()

    @validates("email")
    def validate_email(self, key, email):
        if "@" not in email:
            raise ValueError("Invalid email format.")
        return email

class LearningPath(db.Model):
    __tablename__ = "learning_path"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(ContentStatusEnum), default=ContentStatusEnum.pending)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    creator = db.relationship("User", foreign_keys=[creator_id], back_populates="created_paths")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    contributors = db.relationship("User", secondary=path_contributors, back_populates="contributions")
    followers = db.relationship("User", secondary=path_followers, back_populates="followed_paths")
    modules = db.relationship("Module", back_populates="learning_path", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'creator_id': self.creator_id,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'module_count': self.modules.count() if self.modules else 0,
            'contributor_count': len(self.contributors) if self.contributors else 0,
        }

    
class LearningResource(db.Model):
    __tablename__ = "learning_resource"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., video, reading, quiz
    url = db.Column(db.String(512), nullable=True)  # Made nullable for reading/quiz types
    description = db.Column(db.Text)
    content = db.Column(db.Text) 
    duration = db.Column(db.String(50))  
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"))

    module = db.relationship("Module", back_populates="resources")
     
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'url': self.url,
            'description': self.description,
            'content': self.content,  
            'duration': self.duration,  
            'module_id': self.module_id
        }
class Module(db.Model):
    __tablename__ = "module"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    learning_path_id = db.Column(db.Integer, db.ForeignKey("learning_path.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    learning_path = db.relationship("LearningPath", back_populates="modules")
    quizzes = db.relationship("Quiz", back_populates="module", lazy="dynamic", cascade="all, delete-orphan")
    progress_records = db.relationship("UserProgress", back_populates="module", lazy="dynamic", cascade="all, delete-orphan")
    resources = db.relationship("LearningResource", back_populates="module", lazy="dynamic")
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'learning_path_id': self.learning_path_id,
            'learning_path_title': self.learning_path.title if self.learning_path else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resource_count': self.resources.count() if self.resources else 0,
            'quiz_count': self.quizzes.count() if self.quizzes else 0
        }


class Quiz(db.Model):
    __tablename__ = "quiz"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"))
    passing_score = db.Column(db.Integer, default=70)

    module = db.relationship("Module", back_populates="quizzes")
    questions = db.relationship("Question", back_populates="quiz", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'module_id': self.module_id,
            'module_title': self.module.title if self.module else None,
            'passing_score': self.passing_score,
            'question_count': self.questions.count() if self.questions else 0
        }


class Question(db.Model):
    __tablename__ = "question"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"))
    text = db.Column(db.Text, nullable=False)

    quiz = db.relationship("Quiz", back_populates="questions")
    choices = db.relationship("Choice", back_populates="question", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'quiz_title': self.quiz.title if self.quiz else None,
            'text': self.text,
            'choice_count': self.choices.count() if self.choices else 0
        }



class Choice(db.Model):
    __tablename__ = "choice"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"))
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    question = db.relationship("Question", back_populates="choices")

    def to_dict(self):
        return {
            'id': self.id,
            'question_id': self.question_id,
            'text': self.text,
            'is_correct': self.is_correct
        }
    def to_public_dict(self):
        """Return choice data without revealing correctness."""
        return {
            'id': self.id,
            'question_id': self.question_id,
            'text': self.text
        }
    
    def __repr__(self):
        return f"<Choice id={self.id} text='{self.text[:30]}...' correct={self.is_correct}>"
    
class UserQuizAttempt(db.Model):
    __tablename__ = "user_quiz_attempt"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"))
    score = db.Column(db.Integer)  # Percentage
    passed = db.Column(db.Boolean)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    user = db.relationship("User", backref="quiz_attempts")
    quiz = db.relationship("Quiz", backref="attempts")
    answers = db.relationship("UserQuizAnswer", back_populates="attempt", cascade="all, delete-orphan")

class UserQuizAnswer(db.Model):
    __tablename__ = "user_quiz_answer"
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("user_quiz_attempt.id"))
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"))
    choice_id = db.Column(db.Integer, db.ForeignKey("choice.id"))  # Which choice user selected
    is_correct = db.Column(db.Boolean)  # Was their answer correct?
    
    attempt = db.relationship("UserQuizAttempt", back_populates="answers")
    question = db.relationship("Question")
    selected_choice = db.relationship("Choice")    


class UserProgress(db.Model):
    __tablename__ = "user_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"))
    completion_percent = db.Column(db.Integer, default=0)
    last_score = db.Column(db.Integer, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="progress")
    module = db.relationship("Module", back_populates="progress_records")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else None,
            'module_id': self.module_id,
            'completion_percent': self.completion_percent,
            'last_score': self.last_score,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

# Community 
class CommunityPost(db.Model):
    __tablename__ = "community_post"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("CommunityComment", back_populates="post", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self):
        return {
            'id': self.id,
            'author_id': self.author_id,
            'author_username': self.author.username if self.author else None,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'comment_count': self.comments.count() if self.comments else 0
        }

class CommunityComment(db.Model):
    __tablename__ = "community_comment"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_post.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship("CommunityPost", back_populates="comments")
    author = db.relationship("User", back_populates="comments")

    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'author_id': self.author_id,
            'author_username': self.author.username if self.author else None,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Badge(db.Model):
    __tablename__ = "badge"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("UserBadge", back_populates="badge", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserBadge(db.Model):
    __tablename__ = "user_badge"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    badge_id = db.Column(db.Integer, db.ForeignKey("badge.id"))
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="badges")
    badge = db.relationship("Badge", back_populates="users")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else None,
            'badge_id': self.badge_id,
            'badge_name': self.badge.name if self.badge else None,
            'awarded_at': self.awarded_at.isoformat() if self.awarded_at else None
        }

class Leaderboard(db.Model):
    __tablename__ = "leaderboard"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    total_points = db.Column(db.Integer, default=0, nullable=False)
    rank = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="leaderboard_entry")

    def  to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else None,
            'total_points': self.total_points,
            'rank': self.rank,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    @staticmethod
    def update_leaderboard():
        """Recalculate ranks whenever points change."""
        entries = Leaderboard.query.order_by(Leaderboard.total_points.desc()).all()
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank
        db.session.commit()

class PlatformEvent(db.Model):
    __tablename__ = "platform_event"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reward_points = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participations = db.relationship("ChallengeParticipation", back_populates="event", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'reward_points': self.reward_points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'participants_count': len(self.participations) if self.participations else 0
        }
    
class UserChallenge(db.Model):
    __tablename__ = "user_challenge"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    xp_reward = db.Column(db.Integer, default=50)
    points_reward = db.Column(db.Integer, default=20)
    duration_days = db.Column(db.Integer, default=7)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    challenge_type = db.Column(db.String(50), default="quiz")

    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=True)

    participations = db.relationship("ChallengeParticipation", back_populates="challenge", cascade="all, delete-orphan")
    quiz = db.relationship("Quiz")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'xp_reward': self.xp_reward,
            'points_reward': self.points_reward,
            'challenge_type': self.challenge_type,
            'quiz_id': self.quiz_id,
            'quiz_title': self.quiz.title if self.quiz else None,
            'duration_days': self.duration_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ChallengeParticipation(db.Model):
    __tablename__ = "challenge_participation"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    challenge_id = db.Column(db.Integer, db.ForeignKey("user_challenge.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("platform_event.id"), nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    progress_percent = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)

    user = db.relationship("User")
    challenge = db.relationship("UserChallenge", back_populates="participations")
    event = db.relationship("PlatformEvent", back_populates="participations")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else None,
            'challenge_id': self.challenge_id,
            'challenge_title': self.challenge.title if self.challenge else None,
            'event_id': self.event_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress_percent': self.progress_percent,
            'is_completed': self.is_completed
        }

class PointsLog(db.Model):
    __tablename__ = "points_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    points_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_username:': self.user.username if self.user else None,
            'points_change': self.points_change,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
class ContentFlag(db.Model):
    __tablename__ = "content_flag"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("community_post.id"), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("community_comment.id"), nullable=True)
    reason = db.Column(db.String(255))
    status = db.Column(db.Enum(ContentStatusEnum), default=ContentStatusEnum.pending)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reporter = db.relationship("User")
    post = db.relationship("CommunityPost")
    comment = db.relationship("CommunityComment")

    def to_dict(self):
        return {
            'id': self.id,
            'reporter_id': self.reporter_id,
            'reporter_username': self.reporter.username if self.reporter else None,
            'post_id': self.post_id,
            'post_title': self.post.title if self.post else None,
            'comment_id': self.comment_id,
            'flagged_content': (
                self.comment.content if self.comment else 
                self.post.content if self.post else None
            ),
            'reason': self.reason,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
class UserModeration(db.Model):
    __tablename__ = "user_moderation"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    target_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(50))  
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("User", foreign_keys=[admin_id])
    target_user = db.relationship("User", foreign_keys=[target_user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'target_user_id': self.target_user_id,
            'target_username': self.target_user.username if self.target_user else None,
            'action': self.action,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }