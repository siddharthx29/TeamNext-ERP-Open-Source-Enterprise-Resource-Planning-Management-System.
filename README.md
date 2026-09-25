<div align="center">

<img src="Teamnext/myapp/static/myapp/images/logo.svg" alt="TeamNext ERP Logo" width="72" height="72"/>

# TeamNext ERP

### Open-Source Enterprise Resource Planning System

**A full-featured, self-hostable ERP built with Python & Django — HR, Finance, Inventory, Projects, Payroll, and more in one place.**

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-Framework-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen?style=flat-square)]()
[![Live Demo](https://img.shields.io/badge/Live%20Demo-teamnexterp.com-4F8EF7?style=flat-square)](https://teamnexterp.com/)

[Live Demo](https://teamnexterp.com/) · [Report a Bug](https://github.com/siddharthx29/Enterprise-Management-System-/issues) · [Request a Feature](https://github.com/siddharthx29/Enterprise-Management-System-/issues)

</div>

---

## What is TeamNext ERP?

**TeamNext ERP** is an open-source, web-based enterprise resource planning system built with **Python and Django**. It gives small and mid-sized organizations a single platform to manage employees, departments, projects, payroll, inventory, leaves, finance, tickets, and internal communication — without paying for expensive SaaS tools.

It ships with a **corporate-grade UI** designed for real business use: clean white panels, structured navigation, responsive layout, and a design system that feels at home in any office environment.

> Built by a developer, for teams who want full control over their data and infrastructure.

---

## Screenshots

> *(Add dashboard and HR screenshots here — store in `docs/images/`)*

| Dashboard | HR Management | Finance |
|-----------|---------------|---------|
| ![Dashboard](docs/images/dashboard.png) | ![HR](docs/images/hr.png) | ![Finance](docs/images/finance.png) |

---

## Features

TeamNext ERP ships with **14 modules** out of the box:

| Module | What it does |
|--------|-------------|
| **Dashboard** | Live KPIs, ticket counts, productivity metrics, org overview |
| **HR Management** | Employee records, roles, departments, onboarding |
| **Attendance** | Track attendance per employee and department |
| **Leave Management** | Submit, approve, and track leave requests |
| **Payroll** | Salary records, payroll runs, payment history |
| **Finance** | Invoices, expenses, bank transactions, vendor payments |
| **Inventory** | Track items, quantities, and stock records |
| **Projects & Departments** | Project creation, team assignment, department structure |
| **Tickets** | Internal support tickets with priority and status tracking |
| **Communication** | Internal chat and messaging between employees |
| **Email Center** | Compose and manage internal email communications |
| **Analytics** | Ticket analytics, priority breakdown, trend charts |
| **Reports** | Exportable reports across modules |
| **Users & Access** | Role-based user management and access control |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x, Django |
| Frontend | HTML5, CSS3 (custom design system), JavaScript |
| Database | SQLite3 (PostgreSQL-ready) |
| ORM | Django ORM |
| Auth | Django Authentication + Session |
| Email | Brevo HTTP API |
| Deployment | Render, Railway (Procfile included) |

---

## Quick Start

### Prerequisites

- Python 3.x
- pip
- Git

### 1. Clone the repository

```bash
git clone https://github.com/siddharthx29/Enterprise-Management-System-.git
cd Enterprise-Management-System-/Teamnext
```

### 2. Set up a virtual environment

```bash
# Linux / macOS
python3 -m venv venv && source venv/bin/activate

# Windows
python -m venv venv && venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Create an admin account

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.
Django Admin is available at `http://127.0.0.1:8000/admin/`.

---

## Project Structure

```text
TeamNext-ERP/
│
├── Teamnext/
│   ├── manage.py
│   ├── db.sqlite3
│   ├── Procfile                    # Render/Railway deployment
│   │
│   ├── myapp/
│   │   ├── models.py               # All data models
│   │   ├── views.py                # Application logic
│   │   ├── urls.py                 # URL routing
│   │   ├── brevo_helper.py         # Email via Brevo API
│   │   │
│   │   ├── Templates/              # Django HTML templates
│   │   │   ├── dashboard.html
│   │   │   ├── hr_page.html
│   │   │   ├── finance_page.html
│   │   │   ├── inventory_page.html
│   │   │   └── ... (14 modules)
│   │   │
│   │   └── static/myapp/
│   │       ├── css/theme.css       # Corporate design system
│   │       ├── css/responsive.css
│   │       └── images/
│   │
│   └── Teamnext/                   # Django project config
│       ├── settings.py
│       └── urls.py
│
└── docs/
    └── images/
```

---

## Architecture

TeamNext ERP follows Django's **Model–View–Template (MVT)** pattern:

```
Browser Request
      │
      ▼
  URL Router (urls.py)
      │
      ▼
  Django Views (views.py)     ←── Session / Auth middleware
      │
      ▼
  Django ORM (models.py)
      │
      ▼
  SQLite3 / PostgreSQL
      │
      ▼
  HTML Templates + CSS
      │
      ▼
Browser Response
```

---

## Deploying to Production

Before going live, update your configuration:

```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
SECRET_KEY = os.environ.get('SECRET_KEY')
```

**Recommended steps:**

- Set all secrets in environment variables (never hardcode)
- Switch to PostgreSQL for concurrent users
- Configure HTTPS (via Render, Railway, or a reverse proxy like nginx)
- Set `STATIC_ROOT` and run `collectstatic`
- Keep dependencies updated

TeamNext ERP includes a **`Procfile`** for zero-config deployment on Render and Railway.

---

## Roadmap

Completed modules are checked. Planned work is tracked openly.

- [x] Employee & department management
- [x] Leave request system
- [x] Payroll management
- [x] Finance: invoices, expenses, bank transactions
- [x] Inventory tracking
- [x] Internal tickets with priority levels
- [x] Internal chat and email center
- [x] Analytics dashboard
- [x] Attendance tracking
- [x] Email delivery via Brevo API
- [x] Corporate UI redesign (light, office-grade design system)
- [ ] PostgreSQL support
- [ ] REST API (DRF)
- [ ] Role-based access control (granular permissions)
- [ ] Docker support
- [ ] Automated tests (pytest-django)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Notifications center
- [ ] Mobile-responsive improvements
- [ ] Dark mode toggle

---

## Contributing

All contributions are welcome — bug fixes, new modules, UI improvements, documentation, or tests.

```bash
# 1. Fork the repo and clone your fork
git clone https://github.com/YOUR-USERNAME/Enterprise-Management-System-.git

# 2. Create a feature branch
git checkout -b feature/my-feature

# 3. Make changes, commit, and push
git add .
git commit -m "feat: describe what you did"
git push origin feature/my-feature

# 4. Open a Pull Request on GitHub
```

Look for issues labeled `good first issue`, `help wanted`, or `enhancement` to find a starting point.

---

## Bug Reports

Found something broken? Open an issue and include:

1. Clear title and description
2. Steps to reproduce
3. Expected vs actual behavior
4. Python / Django version
5. Screenshots or logs where helpful

---

## License

Released under the **MIT License** — free to use, modify, and distribute.
See [LICENSE](LICENSE) for details.

---

## Links

| | |
|---|---|
| 🌐 Live Demo | https://teamnexterp.com/ |
| 💻 GitHub | https://github.com/siddharthx29/Enterprise-Management-System- |
| 🐛 Issues | https://github.com/siddharthx29/Enterprise-Management-System-/issues |

---

<div align="center">

**TeamNext ERP** — open-source enterprise management, built with Django.

⭐ Star the repo if you find it useful — it helps other developers discover the project.

</div>
