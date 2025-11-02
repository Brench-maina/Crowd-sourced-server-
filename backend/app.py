from flask import Flask, request
from flask_cors import CORS
from models import db
from flask_migrate import Migrate
from routes import register_blueprints
from flask_jwt_extended import JWTManager
import os

app = Flask(__name__)

# -------------------- Config --------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crowd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'supersecret')

# -------------------- CORS --------------------
CORS(
    app,
    resources={r"/*": {"origins": "http://localhost:5173"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)

# -------------------- Handle Preflight OPTIONS --------------------
@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        headers = resp.headers

        headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
        headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        headers['Access-Control-Allow-Credentials'] = 'true'

        return resp

# -------------------- Extensions --------------------
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# -------------------- Blueprints --------------------
register_blueprints(app)

@app.route("/")
def home():
    return {"message": "Backend running!"}

if __name__ == "__main__":
    app.run(port=5555, debug=True, threaded=True)
