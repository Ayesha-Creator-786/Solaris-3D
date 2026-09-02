from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import SolarData, WeatherData, Alert, db
from sqlalchemy import func
import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')

    # ── Stats ──────────────────────────────────────────────────────────────
    total_output = db.session.query(func.sum(SolarData.solar_output)).scalar() or 0.0
    daily_generation = (
        db.session.query(func.sum(SolarData.solar_output))
        .filter(SolarData.date == today).scalar() or 0.0
    )
    start_of_month = today.replace(day=1)
    monthly_generation = (
        db.session.query(func.sum(SolarData.solar_output))
        .filter(SolarData.date >= start_of_month).scalar() or 0.0
    )

    stats = {
        'total_output': round(float(total_output), 2),
        'daily_generation': round(float(daily_generation), 2),
        'monthly_generation': round(float(monthly_generation), 2),
    }

    # ── Weather ────────────────────────────────────────────────────────────
    weather = WeatherData.query.order_by(WeatherData.recorded_at.desc()).first()

    # ── Alerts (last 5 unread) ─────────────────────────────────────────────
    alerts = (
        Alert.query
        .filter_by(user_id=current_user.id, is_read=False)
        .order_by(Alert.created_at.desc())
        .limit(5).all()
    )

    # ── Recent solar records for chart ────────────────────────────────────
    recent_solar = (
        SolarData.query
        .order_by(SolarData.date.asc(), SolarData.hour.asc())
        .limit(15).all()
    )

    # ── Efficiency ─────────────────────────────────────────────────────────
    predicted_sum = db.session.query(func.sum(SolarData.predicted_output)).scalar() or 0.0
    actual_sum    = db.session.query(func.sum(SolarData.solar_output)).scalar() or 0.0
    efficiency_avg = round((float(actual_sum) / float(predicted_sum)) * 100, 1) if predicted_sum else 100.0

    if efficiency_avg >= 92:
        status_label, status_class = 'Excellent', 'text-success'
    elif efficiency_avg >= 82:
        status_label, status_class = 'Good', 'text-info'
    elif efficiency_avg >= 70:
        status_label, status_class = 'Moderate', 'text-warning'
    else:
        status_label, status_class = 'Poor', 'text-danger'

    return render_template(
        'dashboard.html',
        stats=stats,
        weather=weather,
        alerts=alerts,
        recent_solar=recent_solar,
        efficiency_avg=efficiency_avg,
        status_label=status_label,
        status_class=status_class,
        today_str=today_str,
    )
