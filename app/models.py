from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy import Index, UniqueConstraint


# ============================================================================
# USER
# ============================================================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(50), default='firefighter')

    # Approval and vehicle assignment
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], remote_side=[id], backref='approved_users')
    vehicle = db.relationship('Vehicle', backref='crew_members')

    crew_assignments = db.relationship('CrewAssignment', backref='user', lazy='dynamic')
    leave_requests = db.relationship('LeaveRequest', foreign_keys='LeaveRequest.user_id', backref='user',
                                     lazy='dynamic')
    incident_assignments = db.relationship('IncidentAssignment', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def is_available_now(self):
        active_leave = LeaveRequest.query.filter(
            LeaveRequest.user_id == self.id,
            LeaveRequest.status == 'approved',
            LeaveRequest.start_date <= datetime.now(timezone.utc),
            LeaveRequest.end_date >= datetime.now(timezone.utc)
        ).first()
        if active_leave:
            return False
        active_assignment = CrewAssignment.query.filter(
            CrewAssignment.user_id == self.id,
            CrewAssignment.status == 'active'
        ).first()
        return active_assignment is not None

    def get_current_shift(self):
        return CrewAssignment.query.filter(
            CrewAssignment.user_id == self.id,
            CrewAssignment.status == 'active'
        ).first()

    def __repr__(self):
        return f"<User {self.username}>"


# ============================================================================
# VEHICLE
# ============================================================================

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    vehicle_type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='active')

    shifts = db.relationship('Shift', backref='vehicle', lazy='dynamic')
    incident_assignments = db.relationship('IncidentAssignment', backref='vehicle', lazy='dynamic')

    def __repr__(self):
        return f"<Vehicle {self.plate_number}>"


# ============================================================================
# SHIFT
# ============================================================================

class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    crew_assignments = db.relationship('CrewAssignment', backref='shift', lazy='dynamic')

    @property
    def is_active_now(self):
        now = datetime.now(timezone.utc)
        return self.start_time <= now <= self.end_time and self.status == 'active'

    @property
    def assigned_crew(self):
        return [ass.user for ass in self.crew_assignments.filter_by(status='active')]

    def __repr__(self):
        return f"<Shift {self.id} {self.vehicle.plate_number}>"


# ============================================================================
# CREW ASSIGNMENT
# ============================================================================

class CrewAssignment(db.Model):
    __tablename__ = 'crew_assignments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=False)
    role = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='active')
    assigned_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('user_id', 'shift_id', name='uix_user_shift'),
    )


# ============================================================================
# LEAVE REQUEST
# ============================================================================

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_leaves')


# ============================================================================
# INCIDENT
# ============================================================================

class Incident(db.Model):
    __tablename__ = 'incidents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    incident_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), default='medium')
    address = db.Column(db.String(300), nullable=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    hazardous_materials = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    reported_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)
    reported_by = db.Column(db.String(100), nullable=True)

    assignments = db.relationship('IncidentAssignment', backref='incident', lazy='dynamic')

    __table_args__ = (
        Index('idx_incident_status', 'status'),
        Index('idx_incident_type', 'incident_type'),
        Index('idx_incident_reported_at', 'reported_at'),
    )


# ============================================================================
# INCIDENT ASSIGNMENT
# ============================================================================

class IncidentAssignment(db.Model):
    __tablename__ = 'incident_assignments'
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    assignment_type = db.Column(db.String(50), default='crew')
    status = db.Column(db.String(20), default='assigned')
    assigned_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_lat = db.Column(db.Float, nullable=True)
    last_lng = db.Column(db.Float, nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.CheckConstraint('user_id IS NOT NULL OR vehicle_id IS NOT NULL', name='check_assignment_entity'),
        Index('idx_incident_assignment_status', 'status'),
    )