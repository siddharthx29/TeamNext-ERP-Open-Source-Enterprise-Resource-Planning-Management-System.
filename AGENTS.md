# AGENTS.md

## Project overview
- This repository contains a Django ERP application; the actual app code lives in `Teamnext/`.
- Run Django commands from that directory: `cd Teamnext && python manage.py ...`
- Main app code is in `Teamnext/myapp/` with the core business logic in `models.py`, `views.py`, and `urls.py`.
- Templates and frontend assets live under `Teamnext/myapp/Templates/` and `Teamnext/myapp/static/myapp/`.
- Site configuration is in `Teamnext/project/settings.py`.

## Auth and permissions model
- This project does not rely on Django's default `auth.User` permission framework for regular app access.
- Authentication is custom and session-based: `Company` and `Employee` records store their own password hashes, and login flows set session values such as `verified`, `otp_email`, and `company_name` in `Teamnext/myapp/views.py`.
- Access checks commonly use company scoping and membership logic such as `company=co`, `employee__company=co`, and custom flags like `ProjectMember.is_admin`, `can_approve_leaves`, and `is_allowed`.
- When changing permissions, preserve the custom company/employee separation and do not assume `request.user` or Django `Permission` objects are available.
- Prefer existing patterns in `views.py` for authorization rather than introducing a separate auth system.

## Working conventions
- Follow the existing MVT pattern: models in `myapp/models.py`, logic in `myapp/views.py`, templates in `myapp/Templates`.
- Keep tenant isolation in mind: filters should generally include `company=co` or `project__company=co` when returning records.
- Reuse helper patterns such as `get_user_employee()`, `get_user_company_and_employee()`, and `create_notification_for_users()` instead of duplicating logic.
- The app uses OTP-based verification for signup and password reset; keep session state consistent when changing login flows.
- Avoid cross-tenant data leaks and keep permission-related code explicit and reviewable.

## Validation
- Health check: `cd Teamnext && python manage.py check`
- Database changes: `cd Teamnext && python manage.py makemigrations && python manage.py migrate`
- Regression checks: `cd Teamnext && python manage.py test`

## Useful files
- `Teamnext/project/settings.py` — environment, security, and Django config
- `Teamnext/myapp/models.py` — custom company/employee/project schema
- `Teamnext/myapp/views.py` — login, session logic, permissions, and dashboard behavior
- `Teamnext/myapp/urls.py` — router surface for the ERP app
