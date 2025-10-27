from flask import Flask
from models import db
from flask_migrate import Migrate
from flask_cors import CORS
from routes import register_blueprints
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

# ✅ Load environment variables first
load_dotenv()


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crowd.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'supersecret')


CORS(app)
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)


register_blueprints(app)

#Automatically run migrations when app starts (optional, for Render)
with app.app_context():
    from flask_migrate import upgrade
    try:
        upgrade()
        print("Database migrated successfully on startup")
    except Exception as e:
        print("Migration skipped or failed:", e)


@app.route("/")
def home():
    return {"message": "Crowd Sourced Learning Backend is running!"}


if __name__ == "__main__":
    app.run(port=5555, debug=True)
