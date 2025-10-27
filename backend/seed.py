from app import app, db
from models import (
    User, RoleEnum, Badge, LearningPath, Module, Quiz, Question, Choice,
    CommunityPost, CommunityComment, UserProgress, UserBadge, Leaderboard,
    ContentStatusEnum
)
from werkzeug.security import generate_password_hash
from sqlalchemy.engine import Engine


def is_remote_database(engine: Engine):
    """Detect if connected to Render/PostgreSQL."""
    url = str(engine.url)
    return "render.com" in url or "postgresql" in url


def seed_database():
    """Seed only if database is empty."""
    # Check if data exists
    if User.query.first():
        print("Database already contains data — skipping seeding.")
        return

    # --- USERS ---
    users = [
        User(
            username="admin",
            email="admin@learnplatform.com",
            password_hash=generate_password_hash("admin123"),
            role=RoleEnum.admin,
            points=1500,
            xp=2500
        ),
        User( # --- BADGES ---
            username="creator",
            email="creator@gmail.com",
            password_hash=generate_password_hash("creator123"),
            role=RoleEnum.contributor,
            points=700,
            xp=1200
        ),
        User(
            username="learner",
            email="learner@gmail.com",
            password_hash=generate_password_hash("learner123"),
            role=RoleEnum.learner,
            points=350,
            xp=600
        )
    ]
    db.session.add_all(users)
    db.session.commit()

    admin = users[0]
    contributor = users[1]
    learner = users[2]

    
    badges = [
        Badge(key="first_login", name="First Login", description="Welcome!"),
        Badge(key="first_module", name="Module Explorer", description="Completed first module"),
        Badge(key="streak_7_days", name="Weekly Warrior", description="7-day streak")
    ]
    db.session.add_all(badges)
    db.session.commit()

    
    path = LearningPath(
        title="Python Fundamentals",
        description="Learn Python basics",
        creator_id=contributor.id,
        status=ContentStatusEnum.approved,
        is_published=True
    )
    db.session.add(path)
    db.session.commit()

   
    module = Module(
        title="Intro to Python",
        description="Variables, data types, syntax",
        learning_path_id=path.id
    )
    db.session.add(module)
    db.session.commit()

  
    quiz = Quiz(title="Python Basics Quiz", module_id=module.id)
    db.session.add(quiz)
    db.session.commit()

    q1 = Question(quiz_id=quiz.id, text="What is the correct way to declare a variable in Python?")
    q2 = Question(quiz_id=quiz.id, text="Which keyword is used to define a function?")
    db.session.add_all([q1, q2])
    db.session.commit()

    choices = [
        Choice(question_id=q1.id, text="x = 5", is_correct=True),
        Choice(question_id=q1.id, text="int x = 5", is_correct=False),
        Choice(question_id=q2.id, text="def", is_correct=True),
        Choice(question_id=q2.id, text="function", is_correct=False)
    ]
    db.session.add_all(choices)
    db.session.commit()

    
    post = CommunityPost(
        title="How to learn Flask?",
        content="Any tips for beginners?",
        author_id=learner.id
    )
    db.session.add(post)
    db.session.commit()

    
    comment = CommunityComment(
        content="Check Flask documentation and tutorials!",
        author_id=contributor.id,
        post_id=post.id
    )
    db.session.add(comment)
    db.session.commit()

   
    progress = UserProgress(user_id=learner.id, module_id=module.id, completion_percent=50)
    db.session.add(progress)
    db.session.commit()

    
    user_badge = UserBadge(user_id=learner.id, badge_id=badges[0].id)
    db.session.add(user_badge)
    db.session.commit()

  
    leaderboard_entries = [
        Leaderboard(user_id=u.id, total_points=u.points)
        for u in users
    ]
    db.session.add_all(leaderboard_entries)
    db.session.commit()
    Leaderboard.update_leaderboard()

    print("Database seeded successfully!")


with app.app_context():
    if is_remote_database(db.engine):
        seed_database()
    else:
        print("Skipping seeding (local database).")
