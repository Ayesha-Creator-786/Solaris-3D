from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models import SolarData, db
from sqlalchemy import func
import datetime

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
@login_required
def index():
    # Return structured analytics page page
    return render_template('analytics.html')

@analytics_bp.route('/api/analytics-data')
@login_required
def api_data():
    # 1. Fetch Daily Generation for past 15 calendar days
    daily_results = db.session.query(
        SolarData.date,
        func.sum(SolarData.solar_output).label('actual'),
        func.sum(SolarData.predicted_output).label('predicted'),
        func.avg(SolarData.efficiency_score).label('efficiency')
    ).group_by(SolarData.date).order_by(SolarData.date.desc()).limit(15).all()
    
    # Needs chronological ordering for chart visualization
    daily_results.reverse()

    daily_labels = [r[0].strftime('%b %d') for r in daily_results]
    daily_actual = [round(float(r[1]), 2) for r in daily_results]
    daily_predicted = [round(float(r[2]), 2) for r in daily_results]
    daily_efficiency = [round(float(r[3] or 0), 1) for r in daily_results]

    # 2. Weather Impact Analysis: Irradiance vs Actual Output correlation data
    weather_impact = db.session.query(
        SolarData.irradiance,
        SolarData.solar_output,
        SolarData.cloud_cover
    ).order_by(SolarData.date.desc()).limit(100).all()

    weather_points = [
        {'x': round(float(w[0]), 1), 'y': round(float(w[1]), 2), 'cloud': int(w[2])}
        for w in weather_impact if w[0] is not None and w[1] is not None
    ]

    # 3. Monthly Generation Trends
    monthly_results = db.session.query(
        SolarData.month,
        func.sum(SolarData.solar_output).label('actual'),
        func.sum(SolarData.predicted_output).label('predicted')
    ).group_by(SolarData.month).order_by(SolarData.month.asc()).all()

    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    
    monthly_labels = [month_names.get(m[0], f"Month {m[0]}") for m in monthly_results]
    monthly_actual = [round(float(m[1]), 2) for m in monthly_results]
    monthly_predicted = [round(float(m[2]), 2) for m in monthly_results]

    return jsonify({
        'daily': {
            'labels': daily_labels,
            'actual': daily_actual,
            'predicted': daily_predicted,
            'efficiency': daily_efficiency
        },
        'weather_impact': weather_points,
        'monthly': {
            'labels': monthly_labels,
            'actual': monthly_actual,
            'predicted': monthly_predicted
        }
    })
