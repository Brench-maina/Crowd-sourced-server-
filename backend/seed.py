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

    users = [
        User(
            username="admin",
            email="admin@learnplatform.com",
            password_hash=generate_password_hash("admin123"),
            role=RoleEnum.admin,
            xp=1200,      # XP from activities
            points=950,   # Points slightly lower
            streak_days=10,
            created_at=datetime.utcnow() - timedelta(days=30)
        ),
        User(
            username="contributor",
            email="contributor@learnplatform.com",
            password_hash=generate_password_hash("contrib123"),
            role=RoleEnum.contributor,
            xp=600,       # XP from creating content
            points=400,   # Lower points
            streak_days=5,
            created_at=datetime.utcnow() - timedelta(days=25)
        ),
        User(
            username="learner",
            email="learner@learnplatform.com",
            password_hash=generate_password_hash("learner123"),
            role=RoleEnum.learner,
            # 2 modules complete: 2×50 = 100 points, 2×100 = 200 XP
            # 2 quizzes passed: 2×20 = 40 points, 2×150 = 300 XP
            # 15 days login: 15×5 = 75 points, 0 XP
            # 1 badge earned: 1×10 = 10 points
            # Total: 225 points, 500 XP
            xp=500,       
            points=225,   
            streak_days=15,
            created_at=datetime.utcnow() - timedelta(days=20)
        ),
        User(
            username="alice",
            email="alice@learnplatform.com",
            password_hash=generate_password_hash("alice123"),
            role=RoleEnum.learner,
            # 4 modules complete: 4×50 = 200 points, 4×100 = 400 XP
            # 4 quizzes passed: 4×20 = 80 points, 4×150 = 600 XP
            # 20 days login: 20×5 = 100 points, 0 XP
            # 2 badges earned: 2×10 = 20 points
            # Streak bonus: 200 XP (7-day streak)
            # Total: 400 points, 1200 XP
            xp=1200,      
            points=400,   
            streak_days=20,
            created_at=datetime.utcnow() - timedelta(days=35)
        ),
        User(
            username="bob",
            email="bob@learnplatform.com",
            password_hash=generate_password_hash("bob123"),
            role=RoleEnum.learner,
            xp=250,
            points=120,
            streak_days=8,
            created_at=datetime.utcnow() - timedelta(days=15)
        ),
        User(
            username="charlie",
            email="charlie@learnplatform.com",
            password_hash=generate_password_hash("charlie123"),
            role=RoleEnum.learner,
            xp=2700,      
            points=795,   
            streak_days=30,
            created_at=datetime.utcnow() - timedelta(days=40)
        )
    ]
    db.session.add_all(users)
    db.session.commit()
    print("✅ Users added.")


    badges = [
        Badge(key="first_module", name="First Module Completed", description="Awarded for completing your first module"),
        Badge(key="module_explorer", name="Module Explorer", description="Awarded for completing 5 modules"),
        Badge(key="first_quiz", name="First Quiz Completed", description="Awarded for completing your first quiz"),
        Badge(key="quiz_master", name="Quiz Master", description="Awarded for completing 10 quizzes"),
        Badge(key="streak_30_days", name="Monthly Master", description="Awarded for 30-day learning streak"),
        Badge(key="path_completer", name="Pathfinder", description="Awarded for completing a learning path"),
        Badge(key="first_challenge_participation", name="Challenge Rookie", description="Awarded for participating in first challenge"),
        Badge(key="first_challenge_completed", name="Challenge Champion", description="Awarded for completing first challenge"),
    ]  
    db.session.add_all(badges)
    db.session.commit()
    print("✅ Badges added.")

    
    lp1 = LearningPath(
        title="Python Basics", 
        description="Learn the basics of Python programming.",
        creator_id=users[1].id,
        status=ContentStatusEnum.approved,
        is_published=True,
        created_at=datetime.utcnow()
    )
    lp2 = LearningPath(
        title="Web Development", 
        description="Introduction to building websites.",
        creator_id=users[1].id,
        status=ContentStatusEnum.approved,
        is_published=True,
        created_at=datetime.utcnow()
    )
    lp3 = LearningPath(
        title="Data Science Fundamentals", 
        description="Learn data analysis and visualization.",
        creator_id=users[1].id,
        status=ContentStatusEnum.approved,
        is_published=True,
        created_at=datetime.utcnow()
    )

    db.session.add_all([lp1, lp2, lp3])
    db.session.commit()

    m1 = Module(title="Variables & Data Types", description="Understanding variables and data types in Python.", learning_path_id=lp1.id)
    m2 = Module(title="Control Flow", description="If statements, loops, and logic.", learning_path_id=lp1.id)
    m3 = Module(title="Functions", description="Creating and using functions in Python.", learning_path_id=lp1.id)
    m4 = Module(title="HTML Fundamentals", description="Learn HTML structure and elements.", learning_path_id=lp2.id)
    m5 = Module(title="CSS Basics", description="Style your web pages with CSS.", learning_path_id=lp2.id)
    m6 = Module(title="JavaScript Intro", description="Add interactivity to your websites.", learning_path_id=lp2.id)
    m7 = Module(title="Pandas Basics", description="Data manipulation with Pandas.", learning_path_id=lp3.id)

    db.session.add_all([m1, m2, m3, m4, m5, m6, m7])
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
            module_id=m4.id
        ),
        LearningResource(
            title="MDN CSS Guide", 
            type="documentation",
            url="https://developer.mozilla.org/en-US/docs/Web/CSS", 
            module_id=m5.id
        )
    ]
    db.session.add_all(resources)
    db.session.commit()
    
    #quizzes, questions, choices
    quiz1 = Quiz(title="Python Basics Quiz", module_id=m1.id)
    quiz2 = Quiz(title="Control Flow Quiz", module_id=m2.id)
    quiz3 = Quiz(title="HTML Quiz", module_id=m4.id)
    
    db.session.add_all([quiz1, quiz2, quiz3])
    db.session.commit()

    q1 = Question(text="What is the correct file extension for Python files?", quiz_id=quiz1.id)
    q2 = Question(text="Which keyword is used to define a function in Python?", quiz_id=quiz1.id)
    q3 = Question(text="What does HTML stand for?", quiz_id=quiz3.id)

    db.session.add_all([q1, q2, q3])
    db.session.commit()

    c1 = Choice(text=".py", is_correct=True, question_id=q1.id)
    c2 = Choice(text=".python", is_correct=False, question_id=q1.id)
    c3 = Choice(text="def", is_correct=True, question_id=q2.id)
    c4 = Choice(text="function", is_correct=False, question_id=q2.id)
    c5 = Choice(text="HyperText Markup Language", is_correct=True, question_id=q3.id)
    c6 = Choice(text="High Tech Modern Language", is_correct=False, question_id=q3.id)

    db.session.add_all([c1, c2, c3, c4, c5, c6])
    db.session.commit()
   
   
    post1 = CommunityPost(title="Learning Python", content="Python is so fun!", author_id=users[2].id, created_at=datetime.utcnow() - timedelta(days=5))
    post2 = CommunityPost(title="Web Dev Tips", content="Just finished my first website!", author_id=users[3].id, created_at=datetime.utcnow() - timedelta(days=3))
    post3 = CommunityPost(title="Data Science Journey", content="Starting my data science journey today!", author_id=users[5].id, created_at=datetime.utcnow() - timedelta(days=1))
    
    db.session.add_all([post1, post2, post3])
    db.session.commit()
    
    comment1 = CommunityComment(content="Absolutely! Keep going 🚀", author_id=users[1].id, post_id=post1.id)
    comment2 = CommunityComment(content="Great work! Share the link!", author_id=users[2].id, post_id=post2.id)
    comment3 = CommunityComment(content="Exciting! Data science is amazing!", author_id=users[4].id, post_id=post3.id)
    
    db.session.add_all([comment1, comment2, comment3])
    db.session.commit()
   


    progress_data = [
        # Learner (2 modules complete)
        UserProgress(user_id=users[2].id, module_id=m1.id, completion_percent=100),
        UserProgress(user_id=users[2].id, module_id=m2.id, completion_percent=100),
        UserProgress(user_id=users[2].id, module_id=m3.id, completion_percent=50),
        
        # Alice (4 modules complete)
        UserProgress(user_id=users[3].id, module_id=m1.id, completion_percent=100),
        UserProgress(user_id=users[3].id, module_id=m2.id, completion_percent=100),
        UserProgress(user_id=users[3].id, module_id=m3.id, completion_percent=100),
        UserProgress(user_id=users[3].id, module_id=m4.id, completion_percent=100),
        UserProgress(user_id=users[3].id, module_id=m5.id, completion_percent=75),
        
        # Bob (1 module complete)
        UserProgress(user_id=users[4].id, module_id=m1.id, completion_percent=100),
        UserProgress(user_id=users[4].id, module_id=m4.id, completion_percent=80),
        
        # Charlie (6 modules complete - TOP PERFORMER)
        UserProgress(user_id=users[5].id, module_id=m1.id, completion_percent=100),
        UserProgress(user_id=users[5].id, module_id=m2.id, completion_percent=100),
        UserProgress(user_id=users[5].id, module_id=m3.id, completion_percent=100),
        UserProgress(user_id=users[5].id, module_id=m4.id, completion_percent=100),
        UserProgress(user_id=users[5].id, module_id=m5.id, completion_percent=100),
        UserProgress(user_id=users[5].id, module_id=m6.id, completion_percent=100),
        UserProgress(user_id=users[5].id, module_id=m7.id, completion_percent=90),
    ]
    
    db.session.add_all(progress_data)
    db.session.commit()

    user_badges = [
        # Learner (1 badge)
        UserBadge(user_id=users[2].id, badge_id=badges[0].id, awarded_at=datetime.utcnow() - timedelta(days=18)),  # first_module
        
        # Alice (2 badges)
        UserBadge(user_id=users[3].id, badge_id=badges[0].id, awarded_at=datetime.utcnow() - timedelta(days=30)),  # first_module
        UserBadge(user_id=users[3].id, badge_id=badges[2].id, awarded_at=datetime.utcnow() - timedelta(days=25)),  # first_quiz
        
        # Bob (1 badge)
        UserBadge(user_id=users[4].id, badge_id=badges[0].id, awarded_at=datetime.utcnow() - timedelta(days=10)),  # first_module
        
        # Charlie (5 badges - TOP PERFORMER)
        UserBadge(user_id=users[5].id, badge_id=badges[0].id, awarded_at=datetime.utcnow() - timedelta(days=35)),  # first_module
        UserBadge(user_id=users[5].id, badge_id=badges[1].id, awarded_at=datetime.utcnow() - timedelta(days=25)),  # module_explorer
        UserBadge(user_id=users[5].id, badge_id=badges[2].id, awarded_at=datetime.utcnow() - timedelta(days=30)),  # first_quiz
        UserBadge(user_id=users[5].id, badge_id=badges[4].id, awarded_at=datetime.utcnow() - timedelta(days=10)),  # streak_30_days
        UserBadge(user_id=users[5].id, badge_id=badges[7].id, awarded_at=datetime.utcnow() - timedelta(days=5)),   # first_challenge_completed
    ]
    
    db.session.add_all(user_badges)
    db.session.commit()

    
    # Create leaderboard entries directly (only for learners)
    leaderboard_entries = [
        Leaderboard(user_id=users[5].id, total_points=users[5].points),  # Charlie - 795
        Leaderboard(user_id=users[3].id, total_points=users[3].points),  # Alice - 400
        Leaderboard(user_id=users[2].id, total_points=users[2].points),  # Learner - 225
        Leaderboard(user_id=users[4].id, total_points=users[4].points),  # Bob - 120
    ]
    
    db.session.add_all(leaderboard_entries)
    db.session.commit()
    
    # Calculate and assign ranks based on total_points
    Leaderboard.update_leaderboard()
    

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

    participations = [
        ChallengeParticipation(
            user_id=users[2].id,
            challenge_id=challenge.id,
            event_id=event.id,
            started_at=datetime.utcnow() - timedelta(days=2)
        ),
        ChallengeParticipation(
            user_id=users[3].id,
            challenge_id=challenge.id,
            event_id=event.id,
            started_at=datetime.utcnow() - timedelta(days=2),
            completed_at=datetime.utcnow() - timedelta(days=1)
        ),
        ChallengeParticipation(
            user_id=users[5].id,
            challenge_id=challenge.id,
            event_id=event.id,
            started_at=datetime.utcnow() - timedelta(days=2),
            completed_at=datetime.utcnow() - timedelta(hours=12),
            is_completed=True
        )
    ]
    
    db.session.add_all(participations)
    db.session.commit()



    # Accurate tracking of how users earned their points
    points_logs = [
        # Learner (
        PointsLog(user_id=users[2].id, points_change=50, reason="complete_module: Module 1", created_at=datetime.utcnow() - timedelta(days=10)),
        PointsLog(user_id=users[2].id, points_change=50, reason="complete_module: Module 2", created_at=datetime.utcnow() - timedelta(days=8)),
        PointsLog(user_id=users[2].id, points_change=40, reason="pass_quiz: 2 quizzes (20 pts each)", created_at=datetime.utcnow() - timedelta(days=7)),
        PointsLog(user_id=users[2].id, points_change=75, reason="daily_login: 15 days (5 pts each)", created_at=datetime.utcnow() - timedelta(days=1)),
        PointsLog(user_id=users[2].id, points_change=10, reason="Badge earned: first_module", created_at=datetime.utcnow() - timedelta(days=18)),
        
        # Alice (
        PointsLog(user_id=users[3].id, points_change=200, reason="complete_module: 4 modules (50 pts each)", created_at=datetime.utcnow() - timedelta(days=15)),
        PointsLog(user_id=users[3].id, points_change=80, reason="pass_quiz: 4 quizzes (20 pts each)", created_at=datetime.utcnow() - timedelta(days=10)),
        PointsLog(user_id=users[3].id, points_change=100, reason="daily_login: 20 days (5 pts each)", created_at=datetime.utcnow() - timedelta(days=2)),
        PointsLog(user_id=users[3].id, points_change=20, reason="Badges earned: first_module + first_quiz", created_at=datetime.utcnow() - timedelta(days=25)),
        
        # Bob 
        PointsLog(user_id=users[4].id, points_change=50, reason="complete_module: Module 1", created_at=datetime.utcnow() - timedelta(days=7)),
        PointsLog(user_id=users[4].id, points_change=20, reason="pass_quiz: 1 quiz", created_at=datetime.utcnow() - timedelta(days=6)),
        PointsLog(user_id=users[4].id, points_change=40, reason="daily_login: 8 days (5 pts each)", created_at=datetime.utcnow() - timedelta(days=1)),
        PointsLog(user_id=users[4].id, points_change=10, reason="Badge earned: first_module", created_at=datetime.utcnow() - timedelta(days=10)),
        
        # Charlie 
        PointsLog(user_id=users[5].id, points_change=300, reason="complete_module: 6 modules (50 pts each)", created_at=datetime.utcnow() - timedelta(days=20)),
        PointsLog(user_id=users[5].id, points_change=120, reason="pass_quiz: 6 quizzes (20 pts each)", created_at=datetime.utcnow() - timedelta(days=15)),
        PointsLog(user_id=users[5].id, points_change=200, reason="complete_challenge: Python Challenge", created_at=datetime.utcnow() - timedelta(days=10)),
        PointsLog(user_id=users[5].id, points_change=125, reason="daily_login: 25 days (5 pts each)", created_at=datetime.utcnow() - timedelta(days=1)),
        PointsLog(user_id=users[5].id, points_change=50, reason="Badges earned: 5 badges (10 pts each)", created_at=datetime.utcnow() - timedelta(days=5)),
    ]
    
    db.session.add_all(points_logs)
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        seed_database()