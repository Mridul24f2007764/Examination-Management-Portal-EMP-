# Examination Management Portal (EPM)

A web-based Examination Management Portal built using Python, Flask, SQLite, and HTML/CSS/JavaScript for managing examination-related activities through a centralized platform. The application provides a structured interface for administrators and students, with authentication and role-based access to relevant features.

The system is designed to simplify examination administration, organize academic information, and provide an accessible platform for examination-related operations.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [Key Features](#key-features)
- [Default Admin Account](#default-admin-account)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Security Considerations](#security-considerations)
- [Future Enhancements](#future-enhancements)
- [Notes](#notes)

## Tech Stack

- **Backend:** Python and Flask for application logic and server-side functionality
- **Database:** SQLite for persistent data storage
- **Frontend:** HTML, CSS, and JavaScript
- **Templating:** Flask templates for rendering dynamic web pages
- **Authentication:** Login functionality for authorized access
- **Testing:** Pytest for automated application testing
- **Version Control:** Git and GitHub

## Project Structure

```text
Examination-Management-Portal/
│
├── epm/
│   ├── app.py                      # Main Flask application
│   ├── models.py                   # Database models
│   ├── requirements.txt            # Python dependencies
│   ├── COMPLIANCE_REPORT.txt       # Project compliance report
│   │
│   ├── static/                     # Static assets
│   │   ├── css/                    # Stylesheets
│   │   ├── js/                     # JavaScript files
│   │   └── images/                 # Image assets
│   │
│   ├── templates/                  # HTML templates
│   │
│   └── tests/                      # Automated test cases
│
├── .gitignore                      # Git ignored files
└── README.md                       # Project documentation
```

## Core Concepts

**Centralized Examination Management**

The application provides a centralized platform for handling examination-related activities, reducing dependence on manual administrative processes.

**User Authentication**

The system provides a login mechanism to restrict access to authorized users and protect examination-related information.

**Administrator Access**

The administrator has access to administrative functionality and can manage examination-related operations through the application.

**Database Management**

SQLite is used to store application data and support persistent information management.

**Automated Testing**

Pytest is used to execute automated test cases and verify application functionality.

## Key Features

### Administrator

- Access the administrative dashboard.
- Manage examination-related information.
- Access administrative functionality through authenticated login.
- Manage relevant application records.

### Student

- Access the student interface.
- Log in using authorized credentials.
- View examination-related information.
- Access available student functionalities.

### Application Features

- Centralized examination management.
- User authentication.
- Database integration.
- Structured web-based interface.
- Automated testing support.
- Organized project architecture.

## Default Admin Account

The application automatically creates the default administrator account when the database is initialized, provided an administrator account does not already exist.

| **Field** | **Value** |
|---|---|
| Email | `admin@epm.local` |
| Password | `Admin@123` |
| Role | Administrator |

**Login URL:** `http://127.0.0.1:5000/login`

The default credentials can be overridden using the `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables.

For a real deployment, change the default administrator password after the first login.

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip (Python package manager)
- Git

### Installation

**1. Clone the Repository**

```bash
git clone https://github.com/Mridul24f2007764/Examination-Management-Portal-EMP-.git
```

**2. Navigate to the Project Directory**

```bash
cd Examination-Management-Portal-EMP-
```

**3. Create a Virtual Environment**

```bash
python -m venv venv
```

**4. Activate the Virtual Environment**

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

**5. Install Dependencies**

```bash
pip install -r epm/requirements.txt
```

**6. Run the Application**

```bash
cd epm
python app.py
```

The application will be available at:

```text
http://127.0.0.1:5000/
```

Open the URL in your browser to access the Examination Management Portal.

## Running Tests

The project includes automated tests using Pytest.

To execute the test suite, navigate to the project root directory and run:

```bash
python -m pytest -v
```

The command executes the available test cases and displays their results in the terminal.

## Security Considerations

- Keep administrator credentials confidential.
- Change default passwords before production deployment.
- Do not upload passwords, API keys, or secret configuration files to GitHub.
- Use strong passwords for administrative accounts.
- Keep application dependencies updated.
- Configure appropriate security settings before deployment.
- Restrict access to administrative functionality.

## Future Enhancements

- Advanced examination scheduling and management.
- Automated examination notifications.
- Enhanced student performance analytics.
- Downloadable examination reports.
- Improved role-based access control.
- Advanced reporting and dashboard visualizations.
- Cloud deployment and scalability improvements.

## Notes

- The application requires its Python dependencies to be installed before execution.
- Run the application from the `epm` directory using `python app.py`.
- The default administrator account is created during database initialization if it does not already exist.
- The project includes a test suite that can be executed using Pytest.
- Keep the virtual environment and local database files out of version control where appropriate.

## Project Information

**Project Name:** Examination Management Portal (EPM)

**Project Type:** Full-Stack Web Application

**Backend Framework:** Flask

**Database:** SQLite

**Repository:** [Examination Management Portal – GitHub](https://github.com/Mridul24f2007764/Examination-Management-Portal-EMP-)

## Author

**Mridul Sharma**

## License

This project is developed for academic and educational purposes. An appropriate open-source license should be added before public redistribution.
