from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Prediction, db, ActivityLog
from app.utils.prediction_engine import get_solar_prediction, get_smart_recommendation
import datetime

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/prediction', methods=['GET', 'POST'])
@login_required
def index():
    prediction_result = None
    recommendations = []
    
    # Defaults for form
    inputs = {
        'temperature': 32.0,
        'humidity': 60.0,
        'cloud_cover': 10.0,
        'irradiance': 850.0,
        'hour': 12,
        'month': datetime.date.today().month,
        'actual_output': ''
    }

    if request.method == 'POST':
        try:
            temp = float(request.form.get('temperature'))
            humidity = float(request.form.get('humidity'))
            cloud_cover = float(request.form.get('cloud_cover'))
            irradiance = float(request.form.get('irradiance'))
            hour = int(request.form.get('hour'))
            month = int(request.form.get('month'))
            actual_str = request.form.get('actual_output')
            actual_output = float(actual_str) if actual_str else None

            # Perform prediction
            predicted_output = get_solar_prediction(
                temp=temp,
                humidity=humidity,
                cloud_cover=cloud_cover,
                irradiance=irradiance,
                hour=hour,
                month=month
            )

            # Compute simulated efficiency score if actual is given
            eff_score = None
            if actual_output is not None and predicted_output > 0:
                eff_score = round((actual_output / predicted_output) * 100, 1)

            # Smart Recommendations based on prediction
            recommendations = get_smart_recommendation(predicted_output)

            # Log prediction to DB
            pred_record = Prediction(
                temperature=temp,
                humidity=humidity,
                cloud_cover=cloud_cover,
                irradiance=irradiance,
                hour=hour,
                month=month,
                predicted_output=predicted_output,
                actual_output=actual_output,
                efficiency_score=eff_score,
                recommendation="; ".join(recommendations),
                user_id=current_user.id
            )
            db.session.add(pred_record)

            # Log action
            log = ActivityLog(
                action=f"Calculated prediction: Output {predicted_output} kW for inputs: T={temp}, H={humidity}",
                user_email=current_user.email,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

            prediction_result = {
                'predicted_output': predicted_output,
                'actual_output': actual_output,
                'efficiency_score': eff_score,
                'efficiency_label': 'Excellent' if eff_score and eff_score >= 95 else ('Good' if eff_score and eff_score >= 85 else ('Moderate' if eff_score and eff_score >= 70 else 'Poor')) if eff_score else None
            }

            # Retain inputs for the template view
            inputs = {
                'temperature': temp,
                'humidity': humidity,
                'cloud_cover': cloud_cover,
                'irradiance': irradiance,
                'hour': hour,
                'month': month,
                'actual_output': actual_str
            }

        except ValueError as e:
            flash(f"Error in prediction input calculations: {str(e)}", "danger")

    # Load past queries
    past_predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).limit(10).all()

    return render_template(
        'prediction.html',
        inputs=inputs,
        prediction_result=prediction_result,
        recommendations=recommendations,
        past_predictions=past_predictions
    )
