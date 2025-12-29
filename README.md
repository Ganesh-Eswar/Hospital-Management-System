# Hospital Management System (HMS)

A role-based **Hospital Management System** web application built using **Flask**, **SQLite**, and **Bootstrap**.  
The application enables Admins, Doctors, and Patients to manage appointments, medical records, and hospital operations efficiently.

---

## 📌 Project Overview

Hospitals often rely on manual or fragmented systems to manage patients, doctors, and appointments, leading to inefficiencies and data inconsistencies.  
This project aims to digitize and streamline hospital operations by providing a centralized web-based platform with clearly defined user roles.

The application supports:
- Doctor and patient management
- Appointment scheduling
- Treatment and medical history tracking
- Secure role-based access

---

## 🛠 Tech Stack (Mandatory)

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, Bootstrap, Jinja2
- **Database:** SQLite (programmatically created)
- **Authentication:** Flask-Login (or similar Flask extensions)

> ⚠️ Note:  
> - The database is created programmatically  
> - Manual database creation is NOT used  
> - The application runs completely on a local machine  

---

## 👥 User Roles & Functionalities

### 🔑 Admin (Hospital Staff)
- Pre-existing superuser (no registration)
- Dashboard with total doctors, patients, and appointments
- Add, update, or delete doctor profiles
- View and manage all appointments
- Search doctors by name/specialization
- Search patients by name, ID, or contact information
- Edit or blacklist doctors and patients

---

### 🩺 Doctor
- Login to view assigned appointments
- View upcoming appointments (day/week)
- Mark appointments as Completed or Cancelled
- Define availability for the next 7 days
- Add diagnosis, prescriptions, and treatment notes
- View complete medical history of assigned patients

---

### 🧑‍⚕️ Patient
- Self-registration and login
- View available departments/specializations
- Search doctors by specialization and availability
- Book, reschedule, or cancel appointments
- View appointment status and history
- View diagnosis and prescriptions from past visits
- Update personal profile

---

## Core Components:

- **User Management** (Admin, Doctor, Patient)
- **Appointment Management**
- **Doctor Availability**
- **Treatment & Medical Records**
- **Search & Filtering**
- **Role-Based Authentication**

---

## 📊 Database Design (Core Tables)

- `users` (authentication & role management)
- `doctor_availability`
- `departments`
- `appointments`
- `treatments`

All tables are created automatically when the application runs.

---

## 🔒 Business Rules & Constraints

- A doctor cannot have multiple appointments at the same date and time
- Appointment status lifecycle:
  - Booked → Completed / Cancelled (Sometimes - Missed (Admin can only handle))
- Patients can only view their own data
- Doctors can only view assigned patients
- Admin has full access

---

## Project Demonstration Link:
- https://drive.google.com/file/d/1VsucoOrq686KzvmzB4YqMiHILneSHBy_/view

---

## How to run:

1. create and activate virtualenv:
   python3 -m venv venv
   source venv/bin/activate   # on Windows use: venv\Scripts\activate

2. install:
   pip install -r requirements.txt

3. run:
   python run.py

Visit http://127.0.0.1:5000 in your browser.
Seeded admin credentials: admin@hospital.local / Admin@123
