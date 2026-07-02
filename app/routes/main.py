from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from functools import wraps
from datetime import datetime, timezone

from ..models import (
    Incident, User, Vehicle, Shift, CrewAssignment,
    LeaveRequest, IncidentAssignment
)
from .. import db

main_bp = Blueprint('main', __name__)


# ============================================================================
# DECORATORS
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.SignIn'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.SignIn'))
        user = User.query.get(session['user_id'])
        if user.role != 'admin':
            flash('Достъпът е само за администратори.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)

    return decorated_function


def admin_or_operator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.SignIn'))
        user = User.query.get(session['user_id'])
        if user.role not in ['admin', 'operator']:
            flash('Достъпът е само за администратори и оператори.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)

    return decorated_function


# ============================================================================
# PUBLIC ROUTES
# ============================================================================

@main_bp.route('/')
def index():
    return render_template('index.html')


# ============================================================================
# DASHBOARD
# ============================================================================

@main_bp.route('/dashboard')
@login_required
def dashboard():
    current_user = User.query.get(session['user_id'])
    active_shifts = Shift.query.filter_by(status='active').all()
    all_vehicles = Vehicle.query.filter_by(status='active').all()
    all_users = User.query.all()

    users_with_status = []
    available_count = 0
    unavailable_count = 0

    for user in all_users:
        is_available = user.is_available_now()
        if is_available:
            available_count += 1
        else:
            unavailable_count += 1

        active_leave = LeaveRequest.query.filter(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status == 'approved',
            LeaveRequest.start_date <= datetime.now(timezone.utc),
            LeaveRequest.end_date >= datetime.now(timezone.utc)
        ).first()

        users_with_status.append({
            'user': user,
            'is_available': is_available,
            'current_assignment': user.get_current_shift(),
            'active_leave': active_leave
        })

    active_incidents = Incident.query.filter(
        Incident.status.in_(['pending', 'dispatched', 'in_progress'])
    ).all()

    return render_template(
        'dashboard.html',
        current_user=current_user,
        active_shifts=active_shifts,
        all_vehicles=all_vehicles,
        users_with_status=users_with_status,
        available_count=available_count,
        unavailable_count=unavailable_count,
        active_incidents=active_incidents
    )


# ============================================================================
# MAP
# ============================================================================

@main_bp.route('/map')
@login_required
def map():
    current_user = User.query.get(session['user_id'])

    focused_incident = None
    incidents = []

    if current_user.vehicle_id:
        vehicle_assignment = IncidentAssignment.query.filter(
            IncidentAssignment.vehicle_id == current_user.vehicle_id,
            IncidentAssignment.status.in_(['assigned', 'en_route', 'on_scene'])
        ).first()
        if vehicle_assignment:
            focused_incident = Incident.query.get(vehicle_assignment.incident_id)

    if focused_incident:
        other_incidents = Incident.query.filter(
            Incident.status.in_(['pending', 'dispatched', 'in_progress']),
            Incident.id != focused_incident.id
        ).all()
        incidents = [focused_incident] + other_incidents
    else:
        incidents = Incident.query.filter(
            Incident.status.in_(['pending', 'dispatched', 'in_progress'])
        ).all()

    incidents_data = []
    for inc in incidents:
        incidents_data.append({
            'id': inc.id,
            'name': inc.name,
            'lat': inc.lat,
            'lng': inc.lng,
            'incident_type': inc.incident_type,
            'status': inc.status,
        })

    focused_incident_id = focused_incident.id if focused_incident else None

    return render_template(
        'map.html',
        incidents=incidents,
        incidents_data=incidents_data,
        focused_incident_id=focused_incident_id
    )


# ============================================================================
# INCIDENT MANAGEMENT (ADMIN + OPERATOR)
# ============================================================================

@main_bp.route('/incident/new', methods=['GET', 'POST'])
@admin_or_operator_required
def new_incident():
    if request.method == 'POST':
        name = request.form.get('name')
        incident_type = request.form.get('incident_type')
        severity = request.form.get('severity', 'medium')
        address = request.form.get('address')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        description = request.form.get('description')
        hazardous_materials = request.form.get('hazardous_materials')
        reported_by = request.form.get('reported_by', '112')

        if not name or not incident_type or not lat or not lng:
            flash('Моля, попълнете задължителните полета (Име, Тип, Координати).', 'error')
            return render_template('incident_form.html')

        incident = Incident(
            name=name,
            incident_type=incident_type,
            severity=severity,
            address=address,
            lat=float(lat),
            lng=float(lng),
            description=description,
            hazardous_materials=hazardous_materials,
            reported_by=reported_by,
            status='pending'
        )
        db.session.add(incident)
        db.session.commit()

        flash(f'Произшествие "{name}" беше създадено успешно.', 'success')
        return redirect(url_for('main.incident_detail', incident_id=incident.id))

    return render_template('incident_form.html')


@main_bp.route('/incident/<int:incident_id>')
@login_required
def incident_detail(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    assigned_vehicle_ids = [
        ass.vehicle_id for ass in incident.assignments
        if ass.status in ['assigned', 'en_route', 'on_scene']
    ]

    if assigned_vehicle_ids:
        available_vehicles = Vehicle.query.filter(
            Vehicle.status == 'active',
            ~Vehicle.id.in_(assigned_vehicle_ids)
        ).all()
    else:
        available_vehicles = Vehicle.query.filter_by(status='active').all()

    return render_template(
        'incident_detail.html',
        incident=incident,
        available_vehicles=available_vehicles
    )


@main_bp.route('/incident/<int:incident_id>/assign', methods=['POST'])
@admin_required
def assign_crew(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    vehicle_id = request.form.get('vehicle_id')

    if not vehicle_id:
        flash('Моля, изберете автомобил за изпращане.', 'error')
        return redirect(url_for('main.incident_detail', incident_id=incident.id))

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        flash('Невалиден автомобил.', 'error')
        return redirect(url_for('main.incident_detail', incident_id=incident.id))

    assignment = IncidentAssignment(
        incident_id=incident.id,
        vehicle_id=vehicle.id,
        assignment_type='crew',
        status='assigned'
    )
    db.session.add(assignment)

    if incident.status == 'pending':
        incident.status = 'dispatched'

    db.session.commit()
    flash(f'Автомобил {vehicle.plate_number} беше изпратен успешно.', 'success')
    return redirect(url_for('main.incident_detail', incident_id=incident.id))


@main_bp.route('/incident/<int:incident_id>/resolve', methods=['POST'])
@admin_required
def resolve_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    incident.status = 'resolved'
    incident.resolved_at = datetime.now(timezone.utc)

    for assignment in incident.assignments:
        assignment.status = 'completed'

    db.session.commit()
    flash('Произшествието е маркирано като разрешено.', 'success')
    return redirect(url_for('main.incident_detail', incident_id=incident.id))


# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

@main_bp.route('/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    pending = User.query.filter_by(is_approved=False).all()
    approved = User.query.filter_by(is_approved=True, is_active=True).all()
    vehicles = Vehicle.query.filter_by(status='active').all()
    return render_template('admin_dashboard.html', pending=pending, approved=approved, vehicles=vehicles)


@main_bp.route('/admin/approve/<int:user_id>', methods=['POST'])
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    vehicle_id = request.form.get('vehicle_id')
    if not vehicle_id:
        flash('Моля, изберете автомобил (екип).', 'error')
        return redirect(url_for('main.admin_dashboard'))

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        flash('Невалиден автомобил.', 'error')
        return redirect(url_for('main.admin_dashboard'))

    user.is_approved = True
    user.vehicle_id = vehicle.id
    user.approved_by_id = session['user_id']
    user.approved_at = datetime.now(timezone.utc)
    db.session.commit()

    flash(f'Потребителят {user.full_name} беше одобрен и добавен към автомобил {vehicle.plate_number}.', 'success')
    return redirect(url_for('main.admin_dashboard'))


@main_bp.route('/admin/reassign/<int:user_id>', methods=['POST'])
@admin_required
def reassign_user(user_id):
    user = User.query.get_or_404(user_id)
    vehicle_id = request.form.get('vehicle_id')

    if not vehicle_id:
        flash('Моля, изберете автомобил.', 'error')
        return redirect(url_for('main.admin_dashboard'))

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        flash('Невалиден автомобил.', 'error')
        return redirect(url_for('main.admin_dashboard'))

    old_vehicle = user.vehicle
    user.vehicle_id = vehicle.id
    db.session.commit()

    flash(
        f'Потребителят {user.full_name} беше преместен от {old_vehicle.plate_number if old_vehicle else "няма"} на {vehicle.plate_number}.',
        'success')
    return redirect(url_for('main.admin_dashboard'))


@main_bp.route('/admin/remove/<int:user_id>', methods=['POST'])
@admin_required
def remove_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session['user_id']:
        flash('Не можете да премахнете собствения си акаунт.', 'error')
        return redirect(url_for('main.admin_dashboard'))

    user.is_active = False
    db.session.commit()
    flash(f'Потребителят {user.full_name} беше премахнат от системата.', 'success')
    return redirect(url_for('main.admin_dashboard'))


@main_bp.route('/admin/vehicle', methods=['POST'])
@admin_required
def create_vehicle():
    plate_number = request.form.get('plate_number')
    vehicle_type = request.form.get('vehicle_type')
    capacity = request.form.get('capacity')

    if not plate_number or not vehicle_type:
        flash('Моля, попълнете номер и тип на автомобила.', 'error')
        return redirect(url_for('main.admin_dashboard'))

    if Vehicle.query.filter_by(plate_number=plate_number).first():
        flash('Автомобил с този номер вече съществува.', 'error')
        return redirect(url_for('main.admin_dashboard'))

    vehicle = Vehicle(
        plate_number=plate_number,
        vehicle_type=vehicle_type,
        capacity=int(capacity) if capacity else None,
        status='active'
    )
    db.session.add(vehicle)
    db.session.commit()

    flash(f'Автомобил {plate_number} беше създаден успешно.', 'success')
    return redirect(url_for('main.admin_dashboard'))


# ============================================================================
# USER PROFILE
# ============================================================================

# ============================================================================
# USER PROFILE
# ============================================================================

@main_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    user = User.query.get(session['user_id'])

    shifts = CrewAssignment.query.filter(
        CrewAssignment.user_id == user.id,
        CrewAssignment.status == 'active'
    ).join(Shift).filter(Shift.end_time >= datetime.now(timezone.utc)).order_by(Shift.start_time).all()

    leaves = LeaveRequest.query.filter_by(user_id=user.id).order_by(LeaveRequest.created_at.desc()).all()

    return render_template('profile.html', user=user, shifts=shifts, leaves=leaves)


@main_bp.route('/profile/update-email', methods=['POST'])
@login_required
def update_email():
    user = User.query.get(session['user_id'])
    email = request.form.get('email')
    password = request.form.get('password')

    if not password:
        flash('Въведете текущата си парола.', 'error')
        return redirect(url_for('main.profile'))
    if not user.check_password(password):
        flash('Грешна парола.', 'error')
        return redirect(url_for('main.profile'))

    user.email = email if email else None
    db.session.commit()
    flash('Имейлът беше обновен успешно.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/profile/update-phone', methods=['POST'])
@login_required
def update_phone():
    user = User.query.get(session['user_id'])
    phone = request.form.get('phone')
    password = request.form.get('password')

    if not password:
        flash('Въведете текущата си парола.', 'error')
        return redirect(url_for('main.profile'))
    if not user.check_password(password):
        flash('Грешна парола.', 'error')
        return redirect(url_for('main.profile'))

    user.phone = phone if phone else None
    db.session.commit()
    flash('Телефонът беше обновен успешно.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/profile/update-password', methods=['POST'])
@login_required
def update_password():
    user = User.query.get(session['user_id'])
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not old_password or not new_password or not confirm_password:
        flash('Всички полета за парола са задължителни.', 'error')
        return redirect(url_for('main.profile'))
    if new_password != confirm_password:
        flash('Новите пароли не съвпадат.', 'error')
        return redirect(url_for('main.profile'))
    if not user.check_password(old_password):
        flash('Грешна стара парола.', 'error')
        return redirect(url_for('main.profile'))

    user.set_password(new_password)
    db.session.commit()
    flash('Паролата беше сменена успешно.', 'success')
    return redirect(url_for('main.profile'))
# ============================================================================
# LEAVE REQUESTS
# ============================================================================

@main_bp.route('/leave/request', methods=['POST'])
@login_required
def request_leave():
    user = User.query.get(session['user_id'])
    leave_type = request.form.get('leave_type')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    reason = request.form.get('reason')

    if not all([leave_type, start_date_str, end_date_str]):
        flash('Моля, попълнете всички задължителни полета.', 'error')
        return redirect(url_for('main.profile'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Невалиден формат на дата.', 'error')
        return redirect(url_for('main.profile'))

    if start_date > end_date:
        flash('Началната дата не може да бъде след крайната.', 'error')
        return redirect(url_for('main.profile'))

    # Check for overlapping approved leave (optional)
    overlapping = LeaveRequest.query.filter(
        LeaveRequest.user_id == user.id,
        LeaveRequest.status == 'approved',
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).first()
    if overlapping:
        flash('Вече имате одобрен отпуск в този период.', 'error')
        return redirect(url_for('main.profile'))

    leave = LeaveRequest(
        user_id=user.id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status='pending'
    )
    db.session.add(leave)
    db.session.commit()
    flash('Заявката за отпуск беше изпратена успешно.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/admin/leaves')
@admin_required
def admin_leaves():
    pending = LeaveRequest.query.filter_by(status='pending').order_by(LeaveRequest.created_at.desc()).all()
    # Also fetch approved/rejected for history (optional)
    # We'll show all for simplicity
    all_leaves = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).all()
    return render_template('admin_leaves.html', pending=pending, all_leaves=all_leaves)


@main_bp.route('/admin/leave/<int:leave_id>/approve', methods=['POST'])
@admin_required
def approve_leave(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    leave.status = 'approved'
    leave.approved_by = session['user_id']
    leave.approved_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f'Отпускът на {leave.user.full_name} беше одобрен.', 'success')
    return redirect(url_for('main.admin_leaves'))


@main_bp.route('/admin/leave/<int:leave_id>/reject', methods=['POST'])
@admin_required
def reject_leave(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    leave.status = 'rejected'
    db.session.commit()
    flash(f'Отпускът на {leave.user.full_name} беше отхвърлен.', 'success')
    return redirect(url_for('main.admin_leaves'))