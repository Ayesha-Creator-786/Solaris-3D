from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Alert, db, ActivityLog

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/alerts')
@login_required
def index():
    # Return all alerts
    all_alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at.desc()).all()
    # Also log the viewing of notifications
    return render_template('alerts.html', alerts=all_alerts)

@alerts_bp.route('/alerts/read/<int:alert_id>', methods=['POST'])
@login_required
def mark_read(alert_id):
    alert = Alert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    alert.is_read = True
    db.session.commit()
    return redirect(url_for('alerts.index'))

@alerts_bp.route('/alerts/delete/<int:alert_id>', methods=['POST'])
@login_required
def delete_alert(alert_id):
    alert = Alert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    db.session.delete(alert)
    db.session.commit()
    flash('Notification deleted.', 'info')
    return redirect(url_for('alerts.index'))
