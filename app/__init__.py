from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'solariq-secret-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///solariq.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['OPENWEATHER_API_KEY'] = os.getenv('OPENWEATHER_API_KEY', '')
    app.config['WEATHER_CITY'] = os.getenv('WEATHER_CITY', 'Karachi')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.solar import solar_bp
    from app.routes.weather import weather_bp
    from app.routes.analytics import analytics_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp
    from app.routes.prediction import prediction_bp
    from app.routes.alerts import alerts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(solar_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(alerts_bp)

    with app.app_context():
        db.create_all()
        from app.utils.seed import seed_database
        seed_database()

    return app
