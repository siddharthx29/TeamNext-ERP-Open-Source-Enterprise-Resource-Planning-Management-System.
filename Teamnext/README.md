<div align="center">

<img src="myapp/static/myapp/images/logo.svg" alt="TeamNext ERP Logo" width="72" height="72"/>

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

## Quick Start

### 1. Set up a virtual environment

```bash
# Linux / macOS
python3 -m venv venv && source venv/bin/activate

# Windows
python -m venv venv && venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply migrations

```bash
python manage.py migrate
```

### 4. Create an admin account

```bash
python manage.py createsuperuser
```

### 5. Run the development server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.
Django Admin is available at `http://127.0.0.1:8000/admin/`.
