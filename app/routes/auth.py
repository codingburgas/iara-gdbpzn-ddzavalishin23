from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..models import User
from .. import db
from sqlalchemy.exc import IntegrityError  # ADDED for duplicate handling

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/SignIn', methods=['GET', 'POST'])
def SignIn():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('uname')).first()
        # Now check_password exists!
        if user and user.check_password(request.form.get('pass')):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('SignIn.html')


@auth_bp.route('/SignUp', methods=['GET', 'POST'])
def SignUp():
    if request.method == 'POST':
        # FIXED: Save first_name and last_name from the form
        new_user = User(
            username=request.form.get('uname'),
            first_name=request.form.get('fname'),
            last_name=request.form.get('lname')
        )
        new_user.set_password(request.form.get('pass'))
        db.session.add(new_user)

        # FIXED: Handle duplicate username gracefully
        try:
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.SignIn'))
        except IntegrityError:
            db.session.rollback()
            flash('Username already exists. Please choose another.', 'error')

    return render_template('SignUp.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))