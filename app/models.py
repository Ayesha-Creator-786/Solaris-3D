from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # user or admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active_user = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'


class SolarData(db.Model):
    __tablename__ = 'solar_data'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    cloud_cover = db.Column(db.Float)
    irradiance = db.Column(db.Float)
    hour = db.Column(db.Integer)
    month = db.Column(db.Integer)
    solar_output = db.Column(db.Float)
    predicted_output = db.Column(db.Float)
    efficiency_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def efficiency(self):
        if self.predicted_output and self.predicted_output > 0 and self.solar_output:
            return round((self.solar_output / self.predicted_output) * 100, 1)
        return None

    @property
    def efficiency_label(self):
        e = self.efficiency
        if e is None:
            return 'Unknown'
        if e >= 95:
            return 'Excellent'
        elif e >= 85:
            return 'Good'
        elif e >= 70:
            return 'Moderate'
        else:
            return 'Poor'


class WeatherData(db.Model):
    __tablename__ = 'weather_data'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    cloud_cover = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Prediction(db.Model):
    __tablename__ = 'predictions'
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    cloud_cover = db.Column(db.Float)
    irradiance = db.Column(db.Float)
    hour = db.Column(db.Integer)
    month = db.Column(db.Integer)
    predicted_output = db.Column(db.Float)
    actual_output = db.Column(db.Float)
    efficiency_score = db.Column(db.Float)
    recommendation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50))   # low_output, efficiency_drop, weather_risk, maintenance
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    severity = db.Column(db.String(20))     # info, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(20))  # daily, weekly, monthly
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    user_email = db.Column(db.String(150))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
