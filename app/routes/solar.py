from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import SolarData, Alert, db, ActivityLog
from app.utils.prediction_engine import get_solar_prediction
import datetime

solar_bp = Blueprint('solar', __name__)

@solar_bp.route('/solar', methods=['GET', 'POST'])
@login_required
def index():
    # If POST: user manually inputs solar generation details
    if request.method == 'POST':
        try:
            date_str = request.form.get('date')
            record_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            temp = float(request.form.get('temperature'))
            humidity = float(request.form.get('humidity'))
            cloud_cover = float(request.form.get('cloud_cover'))
            irradiance = float(request.form.get('irradiance'))
            hour = int(request.form.get('hour'))
            month = record_date.month
            actual_output = float(request.form.get('solar_output'))

            # AI prediction context
            predicted_output = get_solar_prediction(
                temp=temp,
                humidity=humidity,
                cloud_cover=cloud_cover,
                irradiance=irradiance,
                hour=hour,
                month=month
            )

            # Compute efficiency score
            efficiency_score = 0.0
            if predicted_output > 0:
                efficiency_score = round((actual_output / predicted_output) * 100, 1)

            # Create record
            record = SolarData(
                date=record_date,
                temperature=temp,
                humidity=humidity,
                cloud_cover=cloud_cover,
                irradiance=irradiance,
                hour=hour,
                month=month,
                solar_output=actual_output,
                predicted_output=predicted_output,
                efficiency_score=efficiency_score
            )
            db.session.add(record)
            db.session.commit()

            # Automatic alerts check (Step 14 / Efficiency Drop / low output / maintenance alerts)
            # Scenario 1: Low efficiency drop (dirty panels/shading)
            if efficiency_score < 75:
                # Severity depends on drop depth
                severity = 'danger' if efficiency_score < 60 else 'warning'
                alert_msg = f"Low performance detected. Efficiency fell to {efficiency_score}% on {record_date} at hour {hour}. Actual output was {actual_output} kW vs expected prediction {predicted_output} kW. Possible panel cleaning or maintenance check required."
                
                # Check for repeated drops (previous 3 entries in last 5 matches showing low efficiency)
                low_eff_records = SolarData.query.order_by(SolarData.date.desc(), SolarData.hour.desc()).limit(5).all()
                low_eff_count = sum(1 for r in low_eff_records if r.efficiency_score and r.efficiency_score < 75)
                
                if low_eff_count >= 3:
                    new_alert = Alert(
                        alert_type='maintenance',
                        title='Predictive Maintenance: Recurring Low Efficiency Detected',
                        message=f"{alert_msg} Notice: Performance drop has happened repeatedly (3 out of the last 5 records). System recommends immediate panel cleaning and inspecting for cable degradation.",
                        severity='danger',
                        user_id=current_user.id
                    )
                else:
                    new_alert = Alert(
                        alert_type='efficiency_drop',
                        title='Performance Efficiency Alert',
                        message=alert_msg,
                        severity=severity,
                        user_id=current_user.id
                    )
                db.session.add(new_alert)

            # Scenario 2: Low Output
            elif actual_output < 1.0 and predicted_output > 2.5:
                new_alert = Alert(
                    alert_type='low_output',
                    title='Critical Output Warning',
                    message=f"Critical output shortfall detected: Generated {actual_output} kW but ML predicted {predicted_output} kW.",
                    severity='danger',
                    user_id=current_user.id
                )
                db.session.add(new_alert)

            # Log action
            log = ActivityLog(
                action=f"Added Solar record: {record_date} {hour}:00, Output: {actual_output} kW",
                user_email=current_user.email,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

            flash('Solar generation record saved successfully!', 'success')
            return redirect(url_for('solar.index'))

        except ValueError as e:
            flash(f'Error processing your input data: {str(e)}', 'danger')
            return redirect(url_for('solar.index'))

    # GET request: load records
    import datetime as _dt
    records = SolarData.query.order_by(SolarData.date.desc(), SolarData.hour.desc()).all()
    today_str = _dt.date.today().strftime('%Y-%m-%d')
    return render_template('solar.html', records=records, today_str=today_str)

@solar_bp.route('/solar/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    record = SolarData.query.get_or_404(record_id)
    
    # Log Action
    log = ActivityLog(
        action=f"Deleted Solar record ID {record_id} of date {record.date}",
        user_email=current_user.email,
        ip_address=request.remote_addr
    )
    
    db.session.delete(record)
    db.session.add(log)
    db.session.commit()
    
    flash('Solar record deleted successfully.', 'success')
    return redirect(url_for('solar.index'))
