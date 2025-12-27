from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))  # NEW LINE
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


    # convenience helpers
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    doctors = db.relationship('User', backref='department', lazy=True)



# ---------------- APPOINTMENT & TREATMENT ---------------- #
class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Booked')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('User', foreign_keys=[patient_id], backref='patient_appointments')
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref='doctor_appointments')

    # One-directional relationship (creates backref automatically in Treatment)
    treatment = db.relationship('Treatment', backref='appointment', uselist=False, cascade="all, delete")

class Treatment(db.Model):
    __tablename__ = 'treatments'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship('User', backref='availabilities')


def init_db():
    """
    Create all tables and seed a default admin user programmatically
    """
    db.create_all()

    admin_email = 'admin@hospital.local'
    existing = User.query.filter_by(email=admin_email).first()
    if not existing:
        admin = User(
            role='admin',
            email=admin_email,
            name='HMS Admin',
            phone='0000000000'
        )
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()
        print(f"[seed] Admin created: {admin_email} / password: Admin@123")
    
        # --- Seed sample departments ---
        departments = [
            Department(name='Cardiology', description='Heart and cardiovascular system'),
            Department(name='Neurology', description='Brain and nervous system'),
            Department(name='Orthopedics', description='Bones, joints, and muscles'),
            Department(name='Pediatrics', description='Child healthcare'),
        ]
        for dept in departments:
            existing_dept = Department.query.filter_by(name=dept.name).first()
            if not existing_dept:
                db.session.add(dept)
        print("Departments added.")
        db.session.commit()

    
    else:
        print("[seed] Admin already exists:", admin_email)
