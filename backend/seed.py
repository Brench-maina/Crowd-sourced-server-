from app import app, db
from models import (
    User, RoleEnum, Badge, LearningPath, Module, Quiz, Question, Choice,
    CommunityPost, CommunityComment, UserProgress, UserBadge, Leaderboard,
    PlatformEvent, UserChallenge, ChallengeParticipation, PointsLog,
    LearningResource, UserQuizAttempt, UserQuizAnswer, ContentStatusEnum
)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def seed_database():
    print("🔄 Resetting database...")
    db.drop_all()
    db.create_all()

    # === USERS ===
    users = [
        User(
            username="admin",
            email="admin@learnplatform.com",
            password_hash=generate_password_hash("admin123"),
            role=RoleEnum.admin,
            created_at=datetime.utcnow() - timedelta(days=5)
        ),
        User(
            username="contributor",
            email="contributor@learnplatform.com",
            password_hash=generate_password_hash("contrib123"),
            role=RoleEnum.contributor,
            created_at=datetime.utcnow() - timedelta(days=5)
        ),
        User(
            username="learner",
            email="learner@learnplatform.com",
            password_hash=generate_password_hash("learner123"),
            role=RoleEnum.learner,
            created_at=datetime.utcnow() - timedelta(days=4)
        )
    ]
    db.session.add_all(users)
    db.session.commit()
    print("✅ Users added.")

    # === BADGES ===
    badges = [
        Badge(key="beginner", name="Beginner", description="Awarded for completing your first module"),
        Badge(key="contributor", name="Contributor", description="Awarded for creating content"),
        Badge(key="quiz_master", name="Quiz Master", description="Awarded for completing 10 quizzes"),
    ]  
    db.session.add_all(badges)
    db.session.commit()
    print("✅ Badges added.")

    # === LEARNING PATHS & MODULES ===
    # FIXED: Added creator_id, status, and is_published
    lp1 = LearningPath(
        title="Python Basics", 
        description="Learn the basics of Python programming.",
        creator_id=users[1].id,  # Contributor created this
        status=ContentStatusEnum.approved,
        is_published=True,
        created_at=datetime.utcnow()
    )
    lp2 = LearningPath(
        title="Web Development", 
        description="Introduction to building websites.",
        creator_id=users[1].id,  # Contributor created this
        status=ContentStatusEnum.approved,
        is_published=True,
        created_at=datetime.utcnow()
    )

    db.session.add_all([lp1, lp2])
    db.session.commit()

    m1 = Module(title="Variables & Data Types", description="Understanding variables and data types in Python.", learning_path_id=lp1.id)
    m2 = Module(title="Control Flow", description="If statements, loops, and logic.", learning_path_id=lp1.id)
    m3 = Module(title="HTML Fundamentals", description="Learn HTML structure and elements.", learning_path_id=lp2.id)

    db.session.add_all([m1, m2, m3])
    db.session.commit()
    print("✅ Learning Paths and Modules added.")

    # === LEARNING RESOURCES ===
    resources = [
        LearningResource(
            title="Python Official Docs", 
            type="documentation",
            url="https://docs.python.org/3/", 
            module_id=m1.id
        ),
        LearningResource(
            title="W3Schools HTML", 
            type="tutorial",
            url="https://www.w3schools.com/html/", 
            module_id=m3.id
        )
    ]
    db.session.add_all(resources)
    db.session.commit()
    print("✅ Learning Resources added.")

    # === QUIZZES ===
    quiz1 = Quiz(title="Python Basics Quiz", module_id=m1.id)
    db.session.add(quiz1)
    db.session.commit()

    q1 = Question(text="What is the correct file extension for Python files?", quiz_id=quiz1.id)
    q2 = Question(text="Which keyword is used to define a function in Python?", quiz_id=quiz1.id)

    db.session.add_all([q1, q2])
    db.session.commit()

    c1 = Choice(text=".py", is_correct=True, question_id=q1.id)
    c2 = Choice(text=".python", is_correct=False, question_id=q1.id)
    c3 = Choice(text="def", is_correct=True, question_id=q2.id)
    c4 = Choice(text="function", is_correct=False, question_id=q2.id)

    db.session.add_all([c1, c2, c3, c4])
    db.session.commit()
    print("✅ Quizzes, Questions, and Choices added.")

    # === COMMUNITY POSTS & COMMENTS ===
    post = CommunityPost(title="Learning Python", content="Python is so fun!", author_id=users[2].id)
    db.session.add(post)
    db.session.commit()
    
    comment = CommunityComment(content="Absolutely! Keep going 🚀", author_id=users[1].id, post_id=post.id)
    db.session.add(comment)
    db.session.commit()
    print("✅ Community Posts and Comments added.")

    # === USER PROGRESS, BADGES & LEADERBOARD ===
    progress = UserProgress(user_id=users[2].id, module_id=m1.id, completion_percent=100)
    user_badge = UserBadge(user_id=users[2].id, badge_id=badges[0].id)
    leaderboard = Leaderboard(user_id=users[2].id, total_points=120)

    db.session.add_all([progress, user_badge, leaderboard])
    db.session.commit()
    print("✅ Progress, Badges, and Leaderboard added.")

    # === EVENTS, CHALLENGES, PARTICIPATION ===
    event = PlatformEvent(
        name="Hackathon 2025", 
        description="A fun coding challenge!", 
        start_date=datetime.utcnow().date(),
        end_date=datetime.utcnow().date() + timedelta(days=7)
    )
    db.session.add(event)
    db.session.commit()

    challenge = UserChallenge(
        title="Python Challenge",
        description="Complete Python modules within 3 days!",
        quiz_id=quiz1.id
    )
    db.session.add(challenge)
    db.session.commit()

    participation = ChallengeParticipation(
        user_id=users[2].id,
        challenge_id=challenge.id,
        event_id=event.id,
        started_at=datetime.utcnow() - timedelta(days=2)
    )
    db.session.add(participation)
    db.session.commit()
    print("✅ Events, Challenges, and Participation added.")

    # === POINTS LOG ===
    points = PointsLog(
        user_id=users[2].id,
        points_change=50,
        reason="Completed Python Basics Module"
    )
    db.session.add(points)
    db.session.commit()

    print("🎉 Seeding complete!")
    print("\n📝 Login credentials:")
    print("   Admin: admin@learnplatform.com / admin123")
    print("   Contributor: contributor@learnplatform.com / contrib123")
    print("   Learner: learner@learnplatform.com / learner123")


if __name__ == "__main__":
    with app.app_context():
        seed_database()