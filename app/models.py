from . import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # ADDED: First and Last name columns to match the SignUp form
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)

    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # ADDED: The missing method that was causing login to crash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Incident(db.Model):
    __tablename__ = 'incidents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    # Връзка към служителите (един инцидент има много служители)
    workers = db.relationship('User', backref='current_incident', lazy=True)