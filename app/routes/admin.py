from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import User, db, ActivityLog, Report, SolarData
import os

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Administrator access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/admin')
@login_required
@admin_required
def index():
    users_count        = User.query.count()
    reports_count      = Report.query.count()
    logs_count         = ActivityLog.query.count()
    solar_records_count = SolarData.query.count()
    recent_logs        = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(15).all()
    users              = User.query.all()

    return render_template(
        'admin/dashboard.html',
        users_count=users_count,
        reports_count=reports_count,
        logs_count=logs_count,
        solar_records_count=solar_records_count,
        recent_logs=recent_logs,
        users=users,
        config=current_app.config,   # ← pass config so template can read API key / city
    )


@admin_bp.route('/admin/user/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    name     = request.form.get('name', '').strip()
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    role     = request.form.get('role', 'user')

    if not name or not email or not password:
        flash('All fields are required to create an account.', 'danger')
        return redirect(url_for('admin.index'))

    if User.query.filter_by(email=email).first():
        flash(f'An account with {email} already exists.', 'danger')
        return redirect(url_for('admin.index'))

    new_user = User(name=name, email=email, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.add(ActivityLog(
        action=f"Admin created user: {email} ({role})",
        user_email=current_user.email,
        ip_address=request.remote_addr
    ))
    db.session.commit()
    flash(f"Account for {name} created successfully!", 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/admin/user/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot suspend your own admin account.', 'danger')
        return redirect(url_for('admin.index'))
    user.is_active_user = not user.is_active_user
    status = 'activated' if user.is_active_user else 'suspended'
    db.session.add(ActivityLog(
        action=f"Admin {status} account: {user.email}",
        user_email=current_user.email,
        ip_address=request.remote_addr
    ))
    db.session.commit()
    flash(f"Account for {user.name} has been {status}.", 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own admin account.', 'danger')
        return redirect(url_for('admin.index'))
    email_del = user.email
    db.session.delete(user)
    db.session.add(ActivityLog(
        action=f"Admin deleted user: {email_del}",
        user_email=current_user.email,
        ip_address=request.remote_addr
    ))
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/admin/settings', methods=['POST'])
@login_required
@admin_required
def save_settings():
    api_key = request.form.get('openweather_api_key', '').strip()
    city    = request.form.get('weather_city', 'Karachi').strip()

    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'
    )

    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()

    new_lines, has_api, has_city = [], False, False
    for line in lines:
        if line.startswith('OPENWEATHER_API_KEY='):
            new_lines.append(f'OPENWEATHER_API_KEY={api_key}\n'); has_api = True
        elif line.startswith('WEATHER_CITY='):
            new_lines.append(f'WEATHER_CITY={city}\n'); has_city = True
        else:
            new_lines.append(line)

    if not has_api:  new_lines.append(f'OPENWEATHER_API_KEY={api_key}\n')
    if not has_city: new_lines.append(f'WEATHER_CITY={city}\n')

    with open(env_path, 'w') as f:
        f.writelines(new_lines)

    current_app.config['OPENWEATHER_API_KEY'] = api_key
    current_app.config['WEATHER_CITY']        = city

    db.session.add(ActivityLog(
        action=f"Admin updated settings — sync city: {city}",
        user_email=current_user.email,
        ip_address=request.remote_addr
    ))
    db.session.commit()
    flash('System settings saved successfully!', 'success')
    return redirect(url_for('admin.index'))
