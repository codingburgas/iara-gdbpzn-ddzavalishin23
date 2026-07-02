from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..models import User
from .. import db
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/SignIn', methods=['GET', 'POST'])
def SignIn():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('uname')).first()
        if user and user.check_password(request.form.get('pass')):
            if not user.is_approved:
                flash('Вашият профил все още не е одобрен. Моля, изчакайте администратор.', 'error')
                return render_template('SignIn.html')
            if not user.is_active:
                flash('Вашият профил е деактивиран. Свържете се с администратор.', 'error')
                return render_template('SignIn.html')
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.dashboard'))
        flash('Грешно потребителско име или парола.', 'error')
    return render_template('SignIn.html')


@auth_bp.route('/SignUp', methods=['GET', 'POST'])
def SignUp():
    if request.method == 'POST':
        username = request.form.get('uname')
        first_name = request.form.get('fname')
        last_name = request.form.get('lname')
        password = request.form.get('pass')
        phone = request.form.get('phone')

        # Validate required fields
        if not all([username, first_name, last_name, password, phone]):
            flash('Всички полета са задължителни.', 'error')
            return render_template('SignUp.html')

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Потребителското име вече съществува.', 'error')
            return render_template('SignUp.html')

        new_user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            is_approved=False,
            is_active=True
        )
        new_user.set_password(password)
        db.session.add(new_user)

        try:
            db.session.commit()
            flash('Регистрацията е успешна. Чакайте одобрение от администратор.', 'success')
            return redirect(url_for('auth.SignIn'))
        except IntegrityError:
            db.session.rollback()
            flash('Възникна грешка. Моля, опитайте отново.', 'error')

    return render_template('SignUp.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))