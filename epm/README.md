# Examination Management Portal (EPM)
Flask + SQLAlchemy + SQLite. Run on Windows (PowerShell):

    py -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    py app.py

Open http://127.0.0.1:5000. The database (`instance/examination_portal.db`) and the admin are created automatically.
Default admin: `admin@epm.local` / `Admin@123` (override with env vars ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY).
Before deployment: set SECRET_KEY, change the admin password, run with a production server and debug off.

## Demo flow
1. Admin: Courses -> add course. Examinations -> create one (type, slot-creation and booking dates). Open it -> add rubric criteria -> set status "Slot Creation Open".
2. Register an examiner (Register page); Admin -> Examiners -> Approve.
3. Examiner: My slots -> create a slot. Admin sets exam status "Booking Open".
4. Register a student; Find exams -> Book. Dashboard -> Cancel (before deadline).
5. Examiner: Evaluate -> save draft / submit (submitted evaluations are locked).
6. Admin: exam page -> Publish results. Student: Results.

Tests: `python -m pytest -q`

## Updated functionality
- Admin student directory with search by name, email, or ID.
- Examiner profile fields (contact number and department), with backward-compatible SQLite column upgrades.
- Server-side slot date-range and booking-window validation.
- Weighted rubric score normalized to a 100-point scale.
- Pending evaluation count scoped to active bookings.
- Login, registration, logout, and existing management actions recorded in the audit log.
- Admin student directory and examiner profile navigation links.

Run tests with `python -m pytest -v`. The project uses SQLite and Flask; no manual database setup is required.
