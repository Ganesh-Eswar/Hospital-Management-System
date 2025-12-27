from . import login_manager
from sqlalchemy import func
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, date, time
from .models import db, User, Appointment, Treatment, DoctorAvailability, Department

def init_routes(app):

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Login successful!', 'success')
                # Redirect based on role
                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.role == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                else:
                    return redirect(url_for('patient_dashboard'))
            else:
                flash('Invalid email or password.', 'danger')
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            password = request.form.get('password')

            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('Email already registered.', 'danger')
                return redirect(url_for('register'))

            new_user = User(role='patient', name=name, email=email, phone=phone)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html')


    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

# ---------------- ADMIN ---------------- #

    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        # --- Summary stats ---
        total_doctors = User.query.filter_by(role='doctor').count()
        total_patients = User.query.filter_by(role='patient').count()
        total_appointments = Appointment.query.count()

        # --- Appointment list (sorted by latest first) ---
        appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
        from datetime import date

        upcoming_appointments = Appointment.query \
            .filter(Appointment.date >= date.today()) \
            .filter(Appointment.status == 'Booked') \
            .order_by(Appointment.date.asc(), Appointment.time.asc()) \
            .all()

        return render_template(
            "admin_dashboard.html",
            user=current_user,
            total_doctors=total_doctors,
            total_patients=total_patients,
            total_appointments=total_appointments,
            appointments=appointments,
            upcoming_appointments=upcoming_appointments
        )
    
    @app.route('/admin/search', methods=['GET'])
    @login_required
    def admin_search():
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        query = request.args.get('q', '').strip()
        results = []

        if query:
            doctors = User.query.filter(
                User.role == 'doctor',
                User.name.ilike(f'%{query}%')
            ).all()
            patients = User.query.filter(
                User.role == 'patient',
                User.name.ilike(f'%{query}%')
            ).all()

            for d in doctors:
                results.append({'type': 'Doctor', 'name': d.name, 'email': d.email})
            for p in patients:
                results.append({'type': 'Patient', 'name': p.name, 'email': p.email})

        return jsonify(results)

    @app.route('/admin/stats_data')
    @login_required
    def admin_stats_data():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # appointments per status
        status_counts = (
            db.session.query(Appointment.status, func.count(Appointment.id))
            .group_by(Appointment.status)
            .all()
        )

        labels = [row[0] for row in status_counts]
        counts = [row[1] for row in status_counts]

        return jsonify({'labels': labels, 'counts': counts})


    from sqlalchemy.orm import aliased

    @app.route('/admin/search_appointments')
    @login_required
    def search_appointments():
        if current_user.role != 'admin':
            return jsonify([])

        q = request.args.get('q', '').strip().lower()

        Doctor = aliased(User)
        Patient = aliased(User)

        appointments = (
            db.session.query(Appointment)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .all()
        )

        results = []
        for a in appointments:
            if q in a.doctor.name.lower() or q in a.patient.name.lower():
                results.append({
                    "id": a.id,
                    "doctor": a.doctor.name,
                    "patient": a.patient.name,
                    "date": a.date.strftime("%Y-%m-%d"),
                    "time": a.time.strftime("%H:%M"),
                    "status": a.status
                })

        return jsonify(results)

    @app.route('/admin/doctors', methods=['GET', 'POST'])
    @login_required
    def manage_doctors():
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        from .models import Department

        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            password = request.form.get('password')
            department_id = request.form.get('department_id')

            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('Doctor email already exists!', 'danger')
                return redirect(url_for('manage_doctors'))

            new_doctor = User(
                role='doctor',
                name=name,
                email=email,
                phone=phone,
                department_id=department_id
            )
            new_doctor.set_password(password)
            db.session.add(new_doctor)
            db.session.commit()
            flash('Doctor added successfully!', 'success')
            return redirect(url_for('manage_doctors'))

        doctors = User.query.filter_by(role='doctor').all()
        departments = Department.query.all()
        return render_template('admin_doctors.html', doctors=doctors, departments=departments)


    @app.route('/admin/doctor/edit/<int:doctor_id>', methods=['GET', 'POST'])
    @login_required
    def edit_doctor(doctor_id):
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        from .models import Department  # import inside for safety
        doctor = User.query.get_or_404(doctor_id)
        departments = Department.query.all()

        if doctor.role != 'doctor':
            flash('Invalid doctor record.', 'danger')
            return redirect(url_for('manage_doctors'))

        if request.method == 'POST':
            doctor.name = request.form.get('name')
            doctor.email = request.form.get('email')
            doctor.phone = request.form.get('phone')
            doctor.department_id = request.form.get('department_id')

            # Optional: Update password if provided
            new_password = request.form.get('password')
            if new_password:
                doctor.set_password(new_password)

            db.session.commit()
            flash('Doctor details updated successfully!', 'success')
            return redirect(url_for('manage_doctors'))

        return render_template('edit_doctor.html', doctor=doctor, departments=departments)


    # @app.route('/admin/doctor/delete/<int:doctor_id>', methods=['POST'])
    # @login_required
    # def delete_doctor(doctor_id):
    #     if current_user.role != 'admin':
    #         flash('Unauthorized access!', 'danger')
    #         return redirect(url_for('login'))

    #     doctor = User.query.get_or_404(doctor_id)

    #     if doctor.role != 'doctor':
    #         flash('Invalid doctor record.', 'danger')
    #         return redirect(url_for('manage_doctors'))

    #     from .models import Appointment, Treatment

    #     # Step 1: Find all appointments of this doctor
    #     appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()

    #     # Step 2: For each appointment, delete its treatments first
    #     for appt in appointments:
    #         treatments = Treatment.query.filter_by(appointment_id=appt.id).all()
    #         for t in treatments:
    #             db.session.delete(t)
    #         db.session.delete(appt)  # then delete the appointment itself

    #     # Step 3: Finally, delete the doctor
    #     db.session.delete(doctor)
    #     db.session.commit()

    #     flash('Doctor and all related appointments and treatments deleted successfully!', 'info')
    #     return redirect(url_for('manage_doctors'))

    @app.route('/admin/doctor/delete/<int:doctor_id>', methods=['POST'])
    @login_required
    def delete_doctor(doctor_id):
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        doctor = User.query.get_or_404(doctor_id)

        if doctor.role != 'doctor':
            flash('Invalid doctor record.', 'danger')
            return redirect(url_for('manage_doctors'))

        # Instead of deleting doctor's data, deactivate the doctor
        doctor.is_active = False

        # Optional: Delete only *future* availability (not history)
        DoctorAvailability.query.filter_by(doctor_id=doctor_id).delete()

        db.session.commit()

        flash('Doctor deactivated. Medical records preserved.', 'info')
        return redirect(url_for('manage_doctors'))

    @app.route('/admin/users')
    @login_required
    def manage_users():
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        users = User.query.all()
        return render_template('admin_users.html', users=users)


    @app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
    @login_required
    def edit_user(user_id):
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        user = User.query.get_or_404(user_id)

        if request.method == 'POST':
            user.name = request.form.get('name')
            user.phone = request.form.get('phone')
            user.role = request.form.get('role')
            db.session.commit()
            flash('User details updated successfully!', 'success')
            return redirect(url_for('manage_users'))

        return render_template('edit_user.html', user=user)


    @app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
    @login_required
    def delete_user(user_id):
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'info')
        return redirect(url_for('manage_users'))


    @app.route('/admin/user/toggle/<int:user_id>', methods=['POST'])
    @login_required
    def toggle_user_status(user_id):
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        user = User.query.get_or_404(user_id)
        user.is_active = not user.is_active
        db.session.commit()

        status = "unblocked" if user.is_active else "blocked"
        flash(f'User {status} successfully!', 'info')
        return redirect(url_for('manage_users'))

    @app.route('/admin/analytics')
    @login_required
    def admin_analytics():
        if current_user.role != 'admin':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        doctors = User.query.filter_by(role='doctor').all()
        patients = User.query.filter_by(role='patient').all()

        return render_template(
            'admin_analytics.html',
            doctors=doctors,
            patients=patients
        )


    @app.route('/admin/analytics_data')
    @login_required
    def analytics_data():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        doctor_id = request.args.get('doctor_id')
        patient_id = request.args.get('patient_id')

        query = Appointment.query

        if doctor_id and doctor_id != "0":
            query = query.filter_by(doctor_id=int(doctor_id))

        if patient_id and patient_id != "0":
            query = query.filter_by(patient_id=int(patient_id))

        data = (
            query.with_entities(Appointment.status, func.count(Appointment.id))
            .group_by(Appointment.status)
            .all()
        )

        labels = [row[0] for row in data]
        counts = [row[1] for row in data]

        return jsonify({"labels": labels, "counts": counts})


    @app.route('/admin/cancel/<int:appointment_id>')
    @login_required
    def admin_cancel_appointment(appointment_id):
        if current_user.role != 'admin':
            flash("Unauthorized access!", "danger")
            return redirect(url_for('login'))

        appt = Appointment.query.get_or_404(appointment_id)
        appt.status = 'Cancelled'
        db.session.commit()
        
        flash("Appointment cancelled by admin.", "warning")
        return redirect(url_for('admin_dashboard'))


# ---------------- PATIENT ---------------- #

    @app.route('/patient/dashboard')
    @login_required
    def patient_dashboard():
        if current_user.role != 'patient':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        # Counts
        total_appointments = Appointment.query.filter_by(patient_id=current_user.id).count()
        upcoming_appointments = Appointment.query.filter_by(patient_id=current_user.id, status='Booked').count()
        cancelled_appointments = Appointment.query.filter_by(patient_id=current_user.id, status='Cancelled').count()

        # Recent appointments (last 5)
        recent_appointments = (
            Appointment.query
            .filter_by(patient_id=current_user.id)
            .order_by(Appointment.date.desc())
            .limit(5)
            .all()
        )

        # Find next upcoming appointment (future date, Booked)
        next_appointment = (
            Appointment.query
            .filter(
                Appointment.patient_id == current_user.id,
                Appointment.status == 'Booked',
                Appointment.date >= datetime.today().date()
            )
            .order_by(Appointment.date.asc(), Appointment.time.asc())
            .first()
        )
        today = date.today()
        now = datetime.now().time()

        upcoming_list = [
            a for a in recent_appointments 
            if a.status == "Booked"
        ]

        # return render_template(
        #     'patient_dashboard.html',
        #     user=current_user,
        #     total_appointments=total_appointments,
        #     upcoming_appointments=upcoming_appointments,
        #     cancelled_appointments=cancelled_appointments,
        #     recent_appointments=recent_appointments,
        #     next_appointment=next_appointment
        # )
        return render_template(
        "patient_dashboard.html",
        user=current_user,
        total_appointments=total_appointments,
        upcoming_appointments=upcoming_appointments,
        cancelled_appointments=cancelled_appointments,
        recent_appointments=recent_appointments,
        upcoming_list=upcoming_list
    )

    @app.route('/patient/appointments', methods=['GET', 'POST'])
    @login_required
    def patient_appointments():
        if current_user.role != 'patient':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        from .models import DoctorAvailability

        # POST – Book new appointment
        if request.method == 'POST':
            doctor_id = int(request.form.get('doctor_id'))
            date_str = request.form.get('date')
            time_str = request.form.get('time')

            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            time_obj = datetime.strptime(time_str, "%H:%M").time()

            # Get ALL availability slots for that date
            slots = DoctorAvailability.query.filter_by(
                doctor_id=doctor_id, date=date_obj
            ).all()

            if not slots:
                flash("Selected doctor is not available on this date.", "danger")
                return redirect(url_for('patient_appointments'))

            # Validate chosen time fits in ANY slot
            is_valid_time = False
            for s in slots:
                if s.start_time <= time_obj <= s.end_time:
                    is_valid_time = True
                    break

            if not is_valid_time:
                flash("Selected time is outside the doctor's available hours.", "danger")
                return redirect(url_for('patient_appointments'))

            # Check conflicts ONLY for Booked appointments
            conflict = Appointment.query.filter_by(
                doctor_id=doctor_id,
                date=date_obj,
                time=time_obj,
                status="Booked"
            ).first()

            if conflict:
                flash("That doctor already has an appointment at this time!", "danger")
                return redirect(url_for('patient_appointments'))

            # Save booking
            new_appointment = Appointment(
                patient_id=current_user.id,
                doctor_id=doctor_id,
                date=date_obj,
                time=time_obj,
                status='Booked'
            )
            db.session.add(new_appointment)
            db.session.commit()

            flash("Appointment booked successfully!", "success")
            return redirect(url_for('patient_appointments'))

        # GET — load UI
        doctors = User.query.filter_by(role='doctor', is_active=True).all()
        appointments = Appointment.query.filter_by(patient_id=current_user.id).all()

        availabilities = [
            {
                "doctor_id": a.doctor_id,
                "date": a.date.strftime("%Y-%m-%d"),
                "start_time": a.start_time.strftime("%H:%M"),
                "end_time": a.end_time.strftime("%H:%M")
            }
            for a in DoctorAvailability.query.all()
        ]

        booked_slots = [
            {
                "doctor_id": appt.doctor_id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": appt.time.strftime("%H:%M")
            }
            for appt in Appointment.query.filter_by(status="Booked").all()
        ]

        # return render_template(
        #     'patient_appointments.html',
        #     doctors=doctors,
        #     appointments=appointments,
        #     availabilities=availabilities,
        #     booked_slots=booked_slots
        # )
        return render_template(
        'patient_appointments.html',
        doctors=doctors,
        appointments=appointments,
        availabilities=availabilities,
        booked_slots=booked_slots,
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


    @app.route('/patient/treatment/<int:treatment_id>')
    @login_required
    def patient_view_report(treatment_id):

        from .models import Treatment

        treatment = Treatment.query.get_or_404(treatment_id)

        # Security: Only the owner patient should view it
        if treatment.appointment.patient_id != current_user.id:
            flash("Unauthorized access!", "danger")
            return redirect(url_for('patient_medical_history'))

        return render_template("patient_treatment_report.html", treatment=treatment)

    @app.route('/patient/doctors')
    @login_required
    def patient_view_doctors():
        if current_user.role != 'patient':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        from .models import Department, DoctorAvailability

        # Only active doctors
        doctors = User.query.filter_by(role='doctor', is_active=True).all()

        departments = {d.id: d.name for d in Department.query.all()}

        # --- Serialize doctor availabilities ---
        availabilities = [
            {
                "doctor_id": a.doctor_id,
                "date": a.date.strftime("%Y-%m-%d"),
                "start_time": a.start_time.strftime("%H:%M"),
                "end_time": a.end_time.strftime("%H:%M")
            }
            for a in DoctorAvailability.query.all()
        ]

        # --- Serialize booked slots ---
        booked_slots = [
            {
                "doctor_id": appt.doctor_id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": appt.time.strftime("%H:%M")
            }
            for appt in Appointment.query.filter_by(status="Booked").all()
        ]

        # Compute next availability per doctor
        next_availability_map = {}

        for av in DoctorAvailability.query.order_by(DoctorAvailability.date, DoctorAvailability.start_time).all():
            if av.doctor_id not in next_availability_map:
                next_availability_map[av.doctor_id] = {
                    "date": av.date.strftime("%Y-%m-%d"),
                    "start_time": av.start_time.strftime("%H:%M"),
                    "end_time": av.end_time.strftime("%H:%M")
                }


        return render_template(
            'patient_view_doctors.html',
            doctors=doctors,
            departments=departments,
            availabilities=availabilities,
            booked_slots=booked_slots,
            next_availability=next_availability_map
        )

    @app.route('/patient/departments')
    @login_required
    def patient_departments():
        if current_user.role != 'patient':
            flash("Unauthorized access!", "danger")
            return redirect(url_for('login'))

        # Get all departments
        departments = Department.query.all()

        # Prepare structured data
        dept_details = []
        for d in departments:
            doctors = User.query.filter_by(
                department_id=d.id, role="doctor", is_active=True
            ).all()

            dept_details.append({
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "doctors": doctors,
                "count": len(doctors)
            })

        return render_template("patient_departments.html", dept_details=dept_details)

    @app.route('/patient/treatments')
    @login_required
    def patient_treatments():
        if current_user.role != 'patient':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        from .models import Treatment, Appointment

        treatments = (
            Treatment.query
            .join(Appointment, Treatment.appointment_id == Appointment.id)
            .filter(Appointment.patient_id == current_user.id)
            .order_by(Appointment.date.desc())
            .all()
        )

        return render_template('patient_treatments.html', treatments=treatments)

    @app.route('/patient/cancel/<int:appointment_id>')
    @login_required
    def cancel_appointment(appointment_id):
        appt = Appointment.query.get_or_404(appointment_id)

        # allow only their own appointment
        if appt.patient_id != current_user.id:
            return "Unauthorized", 403

        # restrict cancellation of past or missed events
        now = datetime.now()
        appt_datetime = datetime.combine(appt.date, appt.time)

        if appt_datetime < now:
            flash("You cannot cancel past or missed appointments. Contact admin.", "danger")
            return redirect(url_for('patient_appointments'))

        appt.status = "Cancelled"
        db.session.commit()
        flash("Appointment cancelled successfully.", "success")
        return redirect(url_for('patient_appointments'))



    @app.route('/patient/profile', methods=['GET', 'POST'])
    @login_required
    def patient_profile():
        if current_user.role != 'patient':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        user = current_user

        if request.method == 'POST':
            user.name = request.form.get('name')
            user.phone = request.form.get('phone')

            new_password = request.form.get('password')
            if new_password:
                user.set_password(new_password)

            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('patient_profile'))

        return render_template('patient_profile.html', user=user)



# ---------------- DOCTOR ---------------- #


    @app.route('/doctor/dashboard')
    @login_required
    def doctor_dashboard():
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        # Fetch appointment stats for this doctor
        total_appointments = Appointment.query.filter_by(doctor_id=current_user.id).count()
        upcoming_appointments = Appointment.query.filter_by(
            doctor_id=current_user.id, status='Booked'
        ).count()
        completed_appointments = Appointment.query.filter_by(
            doctor_id=current_user.id, status='Completed'
        ).count()

        # Recent appointments (latest 5)
        recent_appointments = (
            Appointment.query.filter_by(doctor_id=current_user.id)
            .order_by(Appointment.date.desc(), Appointment.time.desc())
            .limit(5)
            .all()
        )

        return render_template(
            'doctor_dashboard.html',
            user=current_user,
            total_appointments=total_appointments,
            upcoming_appointments=upcoming_appointments,
            completed_appointments=completed_appointments,
            recent_appointments=recent_appointments
        )

    from datetime import date

    @app.route('/doctor/appointments', methods=['GET', 'POST'])
    @login_required
    def doctor_appointments():
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        appointments = (
            Appointment.query
            .filter_by(doctor_id=current_user.id)
            .order_by(Appointment.date, Appointment.time)
            .all()
        )

        # return render_template(
        #     'doctor_appointments.html',
        #     appointments=appointments,
        #     current_date=date.today()
        # )
        return render_template(
        'doctor_appointments.html',
        appointments=appointments,
        current_date=datetime.now().date(),
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


    @app.route('/doctor/patient/report/<int:appointment_id>')
    @login_required
    def doctor_view_report(appointment_id):
        if current_user.role != 'doctor':
            flash("Unauthorized access!", "danger")
            return redirect(url_for("login"))

        appointment = Appointment.query.get_or_404(appointment_id)

        if appointment.doctor_id != current_user.id:
            flash("You are not allowed to view this report.", "danger")
            return redirect(url_for("doctor_dashboard"))

        return render_template("doctor_view_report.html",
                            appointment=appointment,
                            treatment=appointment.treatment)

    @app.route('/doctor/complete/<int:appointment_id>', methods=['GET', 'POST'])
    @login_required
    def complete_appointment(appointment_id):
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        appt = Appointment.query.get_or_404(appointment_id)
        if appt.doctor_id != current_user.id:
            flash('This appointment is not yours!', 'danger')
            return redirect(url_for('doctor_appointments'))

        if request.method == 'POST':
            diagnosis = request.form.get('diagnosis')
            prescription = request.form.get('prescription')
            notes = request.form.get('notes')

            treatment = Treatment(
                appointment_id=appointment_id,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes
            )
            appt.status = 'Completed'
            db.session.add(treatment)
            db.session.commit()
            flash('Appointment marked as completed!', 'success')
            return redirect(url_for('doctor_appointments'))

        return render_template('complete_appointment.html', appt=appt)

    @app.route('/doctor/cancel/<int:appointment_id>')
    @login_required
    def doctor_cancel_appointment(appointment_id):
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        appt = Appointment.query.get_or_404(appointment_id)
        if appt.doctor_id != current_user.id:
            flash('This appointment is not yours!', 'danger')
            return redirect(url_for('doctor_appointments'))

        appt.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully!', 'info')
        return redirect(url_for('doctor_appointments'))


    @app.route('/doctor/patients')
    @login_required
    def doctor_patients():
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        # Get all patients who have had appointments with this doctor
        patients = (
            db.session.query(User)
            .join(Appointment, Appointment.patient_id == User.id)
            .filter(Appointment.doctor_id == current_user.id)
            .distinct()
            .all()
        )

        # For quick view, get latest appointment per patient
        latest_appointments = {}
        for p in patients:
            latest = (
                Appointment.query
                .filter_by(doctor_id=current_user.id, patient_id=p.id)
                .order_by(Appointment.date.desc(), Appointment.time.desc())
                .first()
            )
            latest_appointments[p.id] = latest

        return render_template('doctor_patients.html', patients=patients, latest_appointments=latest_appointments)

    @app.route('/doctor/patient/<int:patient_id>/history')
    @login_required
    def view_patient_history(patient_id):
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        patient = User.query.get_or_404(patient_id)
        appointments = Appointment.query.filter_by(doctor_id=current_user.id, patient_id=patient_id).all()

        return render_template('patient_history.html', patient=patient, appointments=appointments)


    @app.route('/doctor/availability', methods=['GET', 'POST'])
    @login_required
    def doctor_availability():
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        if request.method == 'POST':
            try:
                date_str = request.form.get('date')
                start_time_str = request.form.get('start_time')
                end_time_str = request.form.get('end_time')

                # Convert to datetime objects
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()

                # Validate
                if start_time >= end_time:
                    flash("Start time must be before end time!", "warning")
                    return redirect(url_for('doctor_availability'))

                # Save to DB
                new_slot = DoctorAvailability(
                    doctor_id=current_user.id,
                    date=date_obj,
                    start_time=start_time,
                    end_time=end_time
                )
                db.session.add(new_slot)
                db.session.commit()
                flash("Availability added successfully!", "success")
            except Exception as e:
                flash(f"Error: {e}", "danger")

            return redirect(url_for('doctor_availability'))

        # GET — Show existing slots
        slots = DoctorAvailability.query.filter_by(doctor_id=current_user.id)\
                                        .order_by(DoctorAvailability.date.desc()).all()
        return render_template('doctor_availability.html', slots=slots)

    @app.route('/doctor/availability/delete/<int:slot_id>', methods=['POST'])
    @login_required
    def delete_availability(slot_id):
        if current_user.role != 'doctor':
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('login'))

        slot = DoctorAvailability.query.get_or_404(slot_id)
        if slot.doctor_id != current_user.id:
            flash("You can't delete another doctor's slot!", "danger")
            return redirect(url_for('doctor_availability'))

        db.session.delete(slot)
        db.session.commit()
        flash("Availability slot deleted successfully.", "info")
        return redirect(url_for('doctor_availability'))

def auto_update_past_appointments():
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    # FIND all "Booked" appointments whose date/time have already passed
    past_appointments = Appointment.query.filter(
        Appointment.status == "Booked",
        ((Appointment.date < today) |
        ((Appointment.date == today) & (Appointment.time < current_time)))
    ).all()

    for appt in past_appointments:
        appt.status = "Missed"

    if past_appointments:
        db.session.commit()
