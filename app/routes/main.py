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

    # Check if the current user is actively assigned to an incident
    active_assignment = IncidentAssignment.query.filter(
        IncidentAssignment.user_id == current_user.id,
        IncidentAssignment.status.in_(['assigned', 'en_route', 'on_scene'])
    ).first()

    focused_incident = None
    incidents = []

    if active_assignment:
        # Load the focused incident
        focused_incident = Incident.query.filter(
            Incident.id == active_assignment.incident_id
        ).first()

        # Load other active incidents (excluding focused)
        other_incidents = Incident.query.filter(
            Incident.status.in_(['pending', 'dispatched', 'in_progress']),
            Incident.id != focused_incident.id
        ).all()

        incidents = [focused_incident] + other_incidents
    else:
        # Load all active incidents
        incidents = Incident.query.filter(
            Incident.status.in_(['pending', 'dispatched', 'in_progress'])
        ).all()

    return render_template(
        'map.html',
        incidents=incidents,
        focused_incident=focused_incident
    )


# ============================================================================
# INCIDENT MANAGEMENT (ADMIN ONLY)
# ============================================================================

@main_bp.route('/incident/new', methods=['GET', 'POST'])
@admin_required
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

    all_users = User.query.all()
    available_users = [u for u in all_users if u.is_available_now()]
    available_vehicles = Vehicle.query.filter_by(status='active').all()

    return render_template(
        'incident_detail.html',
        incident=incident,
        available_users=available_users,
        available_vehicles=available_vehicles
    )


@main_bp.route('/incident/<int:incident_id>/assign', methods=['POST'])
@admin_required
def assign_crew(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    user_id = request.form.get('user_id')
    vehicle_id = request.form.get('vehicle_id')

    if not user_id and not vehicle_id:
        flash('Моля, изберете служител или автомобил за изпращане.', 'error')
        return redirect(url_for('main.incident_detail', incident_id=incident.id))

    assignment = IncidentAssignment(
        incident_id=incident.id,
        user_id=int(user_id) if user_id else None,
        vehicle_id=int(vehicle_id) if vehicle_id else None,
        assignment_type='crew',
        status='assigned'
    )
    db.session.add(assignment)

    if incident.status == 'pending':
        incident.status = 'dispatched'

    db.session.commit()
    flash('Екипът беше изпратен успешно.', 'success')
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