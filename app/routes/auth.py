from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, ActivityLog
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('auth.register'))

        # First ever user always becomes admin
        if User.query.count() == 0:
            role = 'admin'

        new_user = User(name=name, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)

        log = ActivityLog(action=f"New registration: {email}", user_email=email, ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()

        flash('Registration successful! You can now sign in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.index'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Incorrect credentials. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        if not user.is_active_user:
            flash('Your account has been suspended. Contact the administrator.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)

        log = ActivityLog(action="Successful login", user_email=email, ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()

        flash(f'Welcome back, {user.name}!', 'success')

        if user.is_admin():
            return redirect(url_for('admin.index'))
        return redirect(url_for('dashboard.index'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log = ActivityLog(action="User logged out", user_email=current_user.email, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    logout_user()
    flash('You have been signed out successfully.', 'success')
    return redirect(url_for('auth.login'))
