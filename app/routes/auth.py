from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..models import User
from .. import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/SignIn', methods=['GET', 'POST'])
def SignIn():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('uname')).first()
        if user and user.check_password(request.form.get('pass')):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('SignIn.html')

@auth_bp.route('/SignUp', methods=['GET', 'POST'])
def SignUp():
    if request.method == 'POST':
        new_user = User(username=request.form.get('uname'))
        new_user.set_password(request.form.get('pass'))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('auth.SignIn'))
    return render_template('SignUp.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))