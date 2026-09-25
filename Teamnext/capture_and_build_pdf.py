import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import time
import json
import base64
import asyncio
import subprocess
import urllib.request
from datetime import datetime, date, timedelta
from decimal import Decimal

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django
django.setup()

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.hashers import make_password
from myapp.models import (
    Company, Department, Employee, Project, ProjectMember, Ticket,
    ChatMessage, ChatMessageMedia, EmailMessage, LeaveRequest,
    SocialItem, Invoice, Expense, Payroll, VendorPayment,
    BankTransaction, InventoryItem, Attendance
)

def seed_rich_demo_data():
    print("[*] Seeding rich demo data for visual screenshots...")
    
    # 1. Company
    co, _ = Company.objects.get_or_create(
        email='admin@teamnext.com',
        defaults={
            'name': 'TeamNext Global Technologies',
            'password': make_password('Admin@12345'),
            'address': 'One World Trade Center, Suite 4800, New York, NY 10007',
            'phone': '+1 (800) 555-0199',
            'website': 'https://teamnext.io',
            'employees_count': '50-100',
            'industry': 'Enterprise Software & Cloud Solutions'
        }
    )
    co.name = 'TeamNext Global Technologies'
    co.save()

    # 2. Departments
    dept_names = [
        ('Engineering & DevOps', 'Core system architecture, web development, and cloud infra'),
        ('Product & UI/UX', 'Product roadmap, user experience research, and design systems'),
        ('Human Resources', 'Talent acquisition, employee wellness, and organizational culture'),
        ('Finance & Accounting', 'Corporate treasury, payroll management, and financial reporting'),
        ('Marketing & Sales', 'Client growth, digital outreach, and brand expansion')
    ]
    depts = {}
    for name, desc in dept_names:
        d, _ = Department.objects.get_or_create(company=co, name=name, defaults={'description': desc})
        depts[name] = d

    # 3. Employees
    emp_data = [
        ('Arjun Mehta', 'arjun.mehta@teamnext.com', 'Chief Technology Officer', 'Engineering & DevOps', '+91 98765 43401'),
        ('Ananya Iyer', 'ananya.iyer@teamnext.com', 'Lead Product Designer', 'Product & UI/UX', '+91 98765 43402'),
        ('Rohan Kapoor', 'rohan.kapoor@teamnext.com', 'Senior Cloud Architect', 'Engineering & DevOps', '+91 98765 43403'),
        ('Priya Nair', 'priya.nair@teamnext.com', 'Head of Human Resources', 'Human Resources', '+91 98765 43404'),
        ('Vikram Shah', 'vikram.shah@teamnext.com', 'Senior Financial Controller', 'Finance & Accounting', '+91 98765 43405'),
        ('Kavya Reddy', 'kavya.reddy@teamnext.com', 'Product Operations Manager', 'Product & UI/UX', '+91 98765 43406'),
        ('Aditya Verma', 'aditya.verma@teamnext.com', 'Full Stack Developer', 'Engineering & DevOps', '+91 98765 43407'),
        ('nsb566@gmail.com', 'nsb566@gmail.com', 'Executive Administrator', 'Engineering & DevOps', '+1 (555) 012-3400')
    ]
    employees = {}
    for name, email, role, dept_k, phone in emp_data:
        emp, _ = Employee.objects.get_or_create(
            email=email,
            defaults={
                'company': co,
                'name': name,
                'password': make_password('Emp@12345'),
                'role': role,
                'dept': depts[dept_k],
                'phone': phone
            }
        )
        emp.company = co
        emp.role = role
        emp.dept = depts[dept_k]
        emp.save()
        employees[email] = emp

    # 4. Projects
    proj_data = [
        ('Project Phoenix: Cloud Migration', 'Zero-downtime database and microservices migration to multi-region cloud cluster.', False),
        ('TeamNext Mobile ERP App (iOS & Android)', 'Next-generation Flutter mobile application with offline synchronization.', False),
        ('Enterprise Security & SOC2 Compliance', 'Automated penetration testing, identity federation, and role-based access control.', True),
        ('Global Q3 Marketing & Expansion', 'Omnichannel product marketing campaigns and European client acquisition.', False)
    ]
    projects = {}
    for name, desc, locked in proj_data:
        p, _ = Project.objects.get_or_create(
            company=co,
            name=name,
            defaults={'description': desc, 'is_locked': locked}
        )
        p.departments.set(depts.values())
        p.save()
        projects[name] = p
        
        # Add members
        for emp in employees.values():
            ProjectMember.objects.get_or_create(
                project=p,
                employee=emp,
                defaults={'can_chat': True, 'is_admin': True, 'can_modify_settings': True}
            )

    # 5. Tickets
    tickets_data = [
        ('Optimize BigQuery & Postgres query latency', 'Phoenix: Cloud Migration', 'arjun.mehta@teamnext.com', 'high', 'Query response times under high concurrency need p99 latency sub-50ms.'),
        ('Finalize Figma UI Tokens & Dark Mode Theme', 'TeamNext Mobile ERP App (iOS & Android)', 'ananya.iyer@teamnext.com', 'medium', 'Ensure all WCAG AAA color contrast ratios are met across all components.'),
        ('Configure Automated Daily Cloud Backups', 'Enterprise Security & SOC2 Compliance', 'rohan.kapoor@teamnext.com', 'high', 'Implement immutable S3/GCS bucket retention locks with automated snapshot verification.'),
        ('Prepare FY2026 Q3 Financial Variance Report', 'Global Q3 Marketing & Expansion', 'vikram.shah@teamnext.com', 'medium', 'Reconcile Q2 actuals against projected forecast for the board meeting.'),
        ('Deploy Webhook Listeners for Stripe Billing', 'Project Phoenix: Cloud Migration', 'aditya.verma@teamnext.com', 'low', 'Ensure idempotent event handling for recurring subscription renewals.')
    ]
    for title, p_name, emp_email, prio, desc in tickets_data:
        proj = projects.get(p_name) or list(projects.values())[0]
        emp = employees.get(emp_email)
        Ticket.objects.get_or_create(
            project=proj,
            title=title,
            defaults={'employee': emp, 'priority': prio, 'description': desc}
        )

    # 6. Chat Messages
    chat_proj = list(projects.values())[0]
    chat_lines = [
        ('arjun.mehta@teamnext.com', 'Good morning team! Cloud migration staging pipeline passed all regression tests with zero errors.'),
        ('ananya.iyer@teamnext.com', 'Awesome news! The new UI design components for the mobile dashboard are ready for review.'),
        ('rohan.kapoor@teamnext.com', 'Database replicas are synchronized. We will perform the cutover during the scheduled maintenance window.'),
        ('kavya.reddy@teamnext.com', 'All stakeholder approvals have been logged in the audit trail.')
    ]
    for email, msg in chat_lines:
        emp = employees.get(email)
        if emp and not ChatMessage.objects.filter(project=chat_proj, text=msg).exists():
            ChatMessage.objects.create(project=chat_proj, employee=emp, text=msg)

    # 7. Invoices & Expenses
    invoices_data = [
        ('Apex Global Enterprises', Decimal('45000.00'), 'paid'),
        ('Starlight Logistics Inc', Decimal('28500.00'), 'paid'),
        ('Vanguard Financial Group', Decimal('62000.00'), 'pending'),
        ('Horizon Retail Systems', Decimal('19500.00'), 'pending')
    ]
    for client, amt, status in invoices_data:
        Invoice.objects.get_or_create(
            company=co,
            client_name=client,
            defaults={'amount': amt, 'status': status, 'gst_rate': Decimal('18.00')}
        )

    expenses_data = [
        ('AWS Cloud Infrastructure & Compute', 'Cloud Hosting', Decimal('8450.00')),
        ('GitHub Enterprise & Copilot Licenses', 'Software SaaS', Decimal('2400.00')),
        ('Corporate Office Lease & Utilities', 'Facilities', Decimal('12500.00')),
        ('Q3 Team Building & Catering Event', 'Employee Welfare', Decimal('3100.00')),
        ('SOC2 Type II Annual Audit Retainer', 'Legal & Compliance', Decimal('15000.00'))
    ]
    for desc, cat, amt in expenses_data:
        Expense.objects.get_or_create(
            company=co,
            description=desc,
            defaults={'category': cat, 'amount': amt}
        )

    # 8. Payroll
    for emp in employees.values():
        Payroll.objects.get_or_create(
            company=co,
            employee=emp,
            month_year='August 2026',
            defaults={
                'base_salary': Decimal('95000.00') / 12,
                'bonus': Decimal('850.00'),
                'deductions': Decimal('420.00')
            }
        )

    # 9. Inventory Items
    inv_data = [
        ('Apple MacBook Pro 16" M3 Max', 'HW-MBP-01', 'Hardware', 24, Decimal('3499.00'), 18),
        ('Dell UltraSharp 32" 4K HDR Monitor', 'HW-DEL-02', 'Peripherals', 45, Decimal('899.00'), 30),
        ('Herman Miller Aeron Ergonomic Chair', 'FUR-HM-03', 'Office Furniture', 35, Decimal('1395.00'), 25),
        ('Cisco Meraki MX85 Security Appliance', 'NET-CS-04', 'Networking', 8, Decimal('2150.00'), 6),
        ('Jabra Evolve2 85 Wireless Headset', 'ACC-JB-05', 'Audio & Video', 50, Decimal('379.00'), 40)
    ]
    for name, sku, cat, qty, price, sales in inv_data:
        InventoryItem.objects.get_or_create(
            company=co,
            sku=sku,
            defaults={'name': name, 'category': cat, 'quantity': qty, 'price': price, 'sales_count': sales}
        )

    # 10. Leaves & Attendance
    today = date.today()
    for i, emp in enumerate(employees.values()):
        Attendance.objects.get_or_create(
            employee=emp,
            date=today,
            defaults={
                'status': 'present' if i % 4 != 0 else 'late',
                'check_in': datetime.strptime('09:00', '%H:%M').time(),
                'check_out': datetime.strptime('18:00', '%H:%M').time()
            }
        )

    leaves_data = [
        ('arjun.mehta@teamnext.com', 'Attending Global Cloud Architecture Summit in Bengaluru', today + timedelta(days=5), today + timedelta(days=8), 'approved'),
        ('ananya.iyer@teamnext.com', 'Annual family vacation leave', today + timedelta(days=12), today + timedelta(days=16), 'pending'),
        ('aditya.verma@teamnext.com', 'Medical recovery & personal checkup', today - timedelta(days=2), today - timedelta(days=1), 'approved')
    ]
    for email, reason, s_date, e_date, status in leaves_data:
        emp = employees.get(email)
        if emp:
            LeaveRequest.objects.get_or_create(
                employee=emp,
                start_date=s_date,
                defaults={'reason': reason, 'end_date': e_date, 'status': status}
            )

    # 11. Social Items
    social_data = [
        ('birthday', 'Happy Birthday Ananya Iyer!', 'Wishing our Lead Product Designer an incredible year ahead with great achievements and creativity! 🎉🎂'),
        ('topic', 'AI in Enterprise Resource Planning: Future Trends', 'Join our open AMA channel this Thursday to explore our upcoming GenAI copilot integrations.'),
        ('dare', 'Green Workspace Challenge', 'Reduce paper usage and log 10,000 steps this Friday to win company wellness badges!')
    ]
    for typ, title, content in social_data:
        SocialItem.objects.get_or_create(
            company=co,
            title=title,
            defaults={'type': typ, 'content': content, 'meta_info': 'General Announcement'}
        )

    # 12. Corporate Emails
    emails_data = [
        ('admin@teamnext.com', 'all-hands@teamnext.com', 'Monthly Town Hall & Product Roadmap Q3', 'Join us on Zoom this Friday for quarterly performance highlights and new feature demos.', False, True),
        ('vikram.shah@teamnext.com', 'admin@teamnext.com', 'Q2 Fiscal Audit Completion Notice', 'The independent auditor has submitted the clean unqualified audit report for FY26 Q2.', False, True),
        ('arjun.mehta@teamnext.com', 'devops@teamnext.com', 'Draft: Microservices Architecture Blueprint', 'Attached is the draft diagram for our Kubernetes container autoscaling policy.', True, False)
    ]
    for s_email, r_email, subj, body, is_d, is_s in emails_data:
        EmailMessage.objects.get_or_create(
            sender_email=s_email,
            recipient_email=r_email,
            subject=subj,
            defaults={'body': body, 'is_draft': is_d, 'is_sent': is_s}
        )

    print("[✓] Demo data seeded successfully.")

def create_admin_session():
    s = SessionStore()
    s['verified'] = True
    s['otp_email'] = 'admin@teamnext.com'
    s['company_name'] = 'TeamNext Global Technologies'
    s.save()
    print(f"[✓] Created persistent admin session: {s.session_key}")
    return s.session_key

async def capture_all_screenshots(session_key, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # Define all pages to capture
    pages = [
        # Onboarding & Auth Flow
        {
            'name': '01_login_portal',
            'title': 'Enterprise Login Portal & MFA Authentication',
            'url': 'http://127.0.0.1:8000/',
            'auth': False,
            'category': 'Onboarding & Authentication',
            'description': 'Dual-mode login portal supporting fast OTP email verification and secure hashed enterprise password authentication with company directory selection.'
        },
        {
            'name': '02_signup_onboarding',
            'title': 'Company & Workspace Registration Onboarding',
            'url': 'http://127.0.0.1:8000/signup/',
            'auth': False,
            'category': 'Onboarding & Authentication',
            'description': 'Comprehensive corporate onboarding wizard capturing company entity details, industry sector, team size, administrative credentials, and verification.'
        },
        {
            'name': '03_otp_verification',
            'title': 'Multi-Factor OTP Security Screen',
            'url': 'http://127.0.0.1:8000/otp/',
            'auth': False,
            'category': 'Onboarding & Authentication',
            'description': 'Cryptographically verified 4-digit numeric OTP authentication screen with automated countdown timer, brute-force rate limiter, and email resend handler.'
        },
        {
            'name': '04_forgot_password',
            'title': 'Self-Service Password Recovery Portal',
            'url': 'http://127.0.0.1:8000/forgot-password/',
            'auth': False,
            'category': 'Onboarding & Authentication',
            'description': 'Automated identity verification and password reset dispatch interface for employees and administrators with secure token dispatch.'
        },
        {
            'name': '05_set_password',
            'title': 'Credential Creation & Password Setup',
            'url': 'http://127.0.0.1:8000/set-password/',
            'auth': False,
            'category': 'Onboarding & Authentication',
            'description': 'Secure credential establishment portal enforcing enterprise password complexity standards and PBKDF2 cryptographic hashing.'
        },
        # Executive & Core ERP Features
        {
            'name': '06_executive_dashboard',
            'title': 'Executive Command Center & KPI Dashboard',
            'url': 'http://127.0.0.1:8000/dashboard/',
            'auth': True,
            'category': 'Executive & Core Operations',
            'description': 'Real-time overview of active projects, critical support tickets, quick-action email dispatchers, developer workforce metrics, and team status feeds.'
        },
        {
            'name': '07_hr_workforce_management',
            'title': 'HR & Workforce Management System',
            'url': 'http://127.0.0.1:8000/hr-page/',
            'auth': True,
            'category': 'Human Resources & Workforce',
            'description': 'Full-lifecycle employee directory, department structuring, daily biometric attendance tracking, check-in timestamps, and employee onboarding.'
        },
        {
            'name': '08_finance_accounting_invoicing',
            'title': 'Finance, GST Invoicing & Payroll Management',
            'url': 'http://127.0.0.1:8000/finance-page/',
            'auth': True,
            'category': 'Financial Management',
            'description': 'Enterprise financial ledger featuring GST-compliant invoice generation, expense categorization, automated payroll calculation, vendor bills, and bank reconciliation.'
        },
        {
            'name': '09_project_management_workspaces',
            'title': 'Project Management & Department Workspaces',
            'url': 'http://127.0.0.1:8000/projects-page/',
            'auth': True,
            'category': 'Project & Workflow Management',
            'description': 'Multi-department project spaces, task boards, passcode-locked channels, team member role assignment, and milestone delivery trackers.'
        },
        {
            'name': '10_team_chat_collaboration',
            'title': 'Real-Time Team Collaboration & Chat Channels',
            'url': 'http://127.0.0.1:8000/chat-page/',
            'auth': True,
            'category': 'Communication & Collaboration',
            'description': 'High-performance team messaging hub with project-based chat rooms, file and media attachments, granular channel access locks, and member permission controls.'
        },
        {
            'name': '11_business_intelligence_analytics',
            'title': 'BI Analytics & Performance Intelligence',
            'url': 'http://127.0.0.1:8000/analytics-page/',
            'auth': True,
            'category': 'Business Intelligence',
            'description': 'Dynamic data visualization dashboard displaying revenue trends, departmental expense breakdowns, employee growth curves, and operational KPIs.'
        },
        {
            'name': '12_corporate_email_inbox',
            'title': 'Corporate Email & Communication Hub',
            'url': 'http://127.0.0.1:8000/email-page/',
            'auth': True,
            'category': 'Communication & Collaboration',
            'description': 'Centralized enterprise email client with multi-folder navigation (Inbox, Sent, Drafts), rich-text compose modal, and Brevo SMTP email synchronization.'
        },
        {
            'name': '13_helpdesk_support_tickets',
            'title': 'Helpdesk & Support Ticketing System',
            'url': 'http://127.0.0.1:8000/tickets-page/',
            'auth': True,
            'category': 'Support & Operations',
            'description': 'Customer and internal support ticketing workflow with urgency prioritization (High, Medium, Low), assignee delegation, and status resolution tracking.'
        },
        {
            'name': '14_leave_absence_management',
            'title': 'Employee Leave & Absence Tracking',
            'url': 'http://127.0.0.1:8000/leaves-page/',
            'auth': True,
            'category': 'Human Resources & Workforce',
            'description': 'Digital leave requisition and management platform with calendar date range pickers, status approval workflows, and leave quota tracking.'
        },
        {
            'name': '15_inventory_asset_management',
            'title': 'Asset Inventory & Stock Control',
            'url': 'http://127.0.0.1:8000/inventory-page/',
            'auth': True,
            'category': 'Financial Management',
            'description': 'Hardware, software license, and office asset tracker featuring SKU cataloging, unit pricing, real-time quantity monitoring, and valuation summaries.'
        },
        {
            'name': '16_reports_document_generation',
            'title': 'Executive Reports & Document Generator',
            'url': 'http://127.0.0.1:8000/reports-page/',
            'auth': True,
            'category': 'Business Intelligence',
            'description': 'Comprehensive reporting engine generating exportable executive summaries across Financial statements, HR headcount, Project velocity, and Operations.'
        },
        {
            'name': '17_user_directory_roles',
            'title': 'User Management & Role Administration',
            'url': 'http://127.0.0.1:8000/users-page/',
            'auth': True,
            'category': 'System Administration',
            'description': 'Company-wide staff directory, role-based permission management, new developer/employee invitation workflows, and direct profile administration.'
        },
        {
            'name': '18_company_social_feed',
            'title': 'Internal Social Feed & Announcements',
            'url': 'http://127.0.0.1:8000/social-page/',
            'auth': True,
            'category': 'Communication & Collaboration',
            'description': 'Employee engagement network highlighting colleague birthdays, trending workplace topics, company-wide announcements, and interactive team challenges.'
        },
        {
            'name': '19_user_profile_security',
            'title': 'Personal User Profile & Security Settings',
            'url': 'http://127.0.0.1:8000/profile-page/',
            'auth': True,
            'category': 'System Administration',
            'description': 'User profile management interface for updating avatar, contact phone numbers, biographical info, department roles, and password credentials.'
        },
        {
            'name': '20_system_workspace_settings',
            'title': 'Workspace & Organization Settings',
            'url': 'http://127.0.0.1:8000/settings-page/',
            'auth': True,
            'category': 'System Administration',
            'description': 'Global workspace configuration for custom company branding, email notification triggers, theme settings, API integrations, and security policies.'
        }
    ]

    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    user_data = os.path.abspath('temp_chrome_user_data_pdf')
    cmd = [
        chrome_path,
        '--headless=new',
        '--remote-debugging-port=9222',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1600,1050',
        f'--user-data-dir={user_data}'
    ]
    
    print("[*] Launching headless Chrome for screenshot capture...")
    chrome_proc = subprocess.Popen(cmd)
    await asyncio.sleep(2.5)

    captured_items = []
    try:
        import websockets
        req = urllib.request.Request('http://127.0.0.1:9222/json/new', method='PUT')
        with urllib.request.urlopen(req) as resp:
            tab = json.loads(resp.read().decode())
        ws_url = tab['webSocketDebuggerUrl']

        async with websockets.connect(ws_url, max_size=50*1024*1024) as ws:
            msg_id = 1
            
            async def send_cmd(method, params=None):
                nonlocal msg_id
                current_id = msg_id
                msg_id += 1
                payload = {'id': current_id, 'method': method}
                if params:
                    payload['params'] = params
                await ws.send(json.dumps(payload))
                while True:
                    raw = await ws.recv()
                    res = json.loads(raw)
                    if res.get('id') == current_id:
                        return res.get('result', {})

            await send_cmd('Page.enable')
            await send_cmd('Network.enable')
            await send_cmd('Emulation.setDeviceMetricsOverride', {
                'width': 1600,
                'height': 1000,
                'deviceScaleFactor': 1.5,
                'mobile': False
            })

            # Set session cookie for 127.0.0.1
            await send_cmd('Network.setCookie', {
                'name': 'sessionid',
                'value': session_key,
                'domain': '127.0.0.1',
                'path': '/'
            })

            for p_info in pages:
                print(f"[*] Navigating to: {p_info['title']} ({p_info['url']})")
                
                # If page is non-auth and needs clean look, we can clear or keep cookie
                if not p_info['auth']:
                    # We can open in clean state or standard
                    pass
                
                await send_cmd('Page.navigate', {'url': p_info['url']})
                await asyncio.sleep(1.8) # Wait for animations and data charts to load
                
                # Capture screenshot
                shot_res = await send_cmd('Page.captureScreenshot', {
                    'format': 'png',
                    'captureBeyondViewport': False
                })
                
                if 'data' in shot_res:
                    img_data = base64.b64decode(shot_res['data'])
                    img_filename = f"{p_info['name']}.png"
                    img_path = os.path.join(output_dir, img_filename)
                    with open(img_path, 'wb') as f:
                        f.write(img_data)
                    print(f"  [✓] Saved screenshot: {img_filename} ({len(img_data)//1024} KB)")
                    p_info['image_path'] = img_path
                    p_info['image_filename'] = img_filename
                    captured_items.append(p_info)
                else:
                    print(f"  [!] Failed capturing screenshot for {p_info['name']}")

    finally:
        chrome_proc.terminate()
        print("[✓] Headless Chrome terminated.")

    return captured_items

def build_pdf_catalog(captured_items, pdf_output_path):
    print(f"[*] Compiling executive PDF guide to: {pdf_output_path}...")
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfgen import canvas
    from PIL import Image as PILImage

    # Numbered Canvas for professional header & footer
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super().showPage()
            super().save()

        def draw_page_decorations(self, page_count):
            if self._pageNumber == 1:
                return # Skip cover page

            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))

            # Running Header
            self.drawString(54, 755, "TeamNext ERP — Enterprise Management Platform UI & Feature Catalog")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(54, 748, 558, 748)

            # Running Footer
            self.line(54, 45, 558, 45)
            self.drawString(54, 32, "Confidential — Internal & Client System Documentation")
            self.drawRightString(558, 32, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    doc = SimpleDocTemplate(
        pdf_output_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Brand Typography Styles
    c_primary = colors.HexColor("#0f172a") # Dark Slate Navy
    c_accent = colors.HexColor("#2563eb")  # Royal Blue
    c_subtext = colors.HexColor("#475569") # Muted Slate
    c_card_bg = colors.HexColor("#f8fafc") # Clean Ice White

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=c_primary,
        alignment=0
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=c_subtext,
        alignment=0
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'FeatureH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_accent,
        spaceAfter=4
    )

    meta_style = ParagraphStyle(
        'MetaP',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#3b82f6")
    )

    body_style = ParagraphStyle(
        'BodyP',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b")
    )

    tag_style = ParagraphStyle(
        'TagP',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f766e")
    )

    story = []

    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 40))
    story.append(Paragraph("TEAMNEXT ERP SYSTEM", ParagraphStyle('SubHeader', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=c_accent)))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Comprehensive UI, Menu & Feature Screenshot Guide", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph("A full visual audit and architectural walkthrough of the open-source Enterprise Resource Planning suite, covering authentication, onboarding, human resources, finance, project management, and analytics.", subtitle_style))
    story.append(Spacer(1, 24))
    
    # Metadata Badge Box
    meta_table_data = [
        [
            Paragraph("<b>Platform:</b> TeamNext ERP v2.4", body_style),
            Paragraph("<b>Generated:</b> " + datetime.now().strftime("%B %d, %Y"), body_style)
        ],
        [
            Paragraph("<b>Framework:</b> Python / Django 5.2 / SQLite", body_style),
            Paragraph("<b>Captured Screens:</b> " + str(len(captured_items)) + " Modules", body_style)
        ],
        [
            Paragraph("<b>Interface Scale:</b> 1600 × 1000 High-Res", body_style),
            Paragraph("<b>Security:</b> PBKDF2 / Multi-Factor OTP", body_style)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 30))

    # Architecture Overview Summary
    story.append(Paragraph("Platform Architecture & Functional Blueprint", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=4, spaceAfter=12))
    
    summary_text = (
        "TeamNext ERP is an enterprise resource planning and organizational collaboration management system designed "
        "to consolidate core business operations into an integrated interface. "
        "This document contains high-definition visual screenshots across all onboarding portals, operational menus, "
        "and business feature modules. Each section provides route endpoints, UI design highlights, and workflow specifications."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 15))

    # Visual Table of Contents
    toc_data = [
        [Paragraph("<b>Category / Domain</b>", body_style), Paragraph("<b>Screens & Features Included</b>", body_style)]
    ]
    
    categories = {}
    for item in captured_items:
        cat = item['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item['title'])

    for cat, titles in categories.items():
        toc_data.append([
            Paragraph(f"<b>{cat}</b>", tag_style),
            Paragraph(", ".join([t.split(" - ")[0] for t in titles]), body_style)
        ])

    toc_table = Table(toc_data, colWidths=[170, 350])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ==================== FEATURE SCREEN PAGES ====================
    for idx, item in enumerate(captured_items, 1):
        # Header banner
        badge = f"MODULE {idx:02d} OF {len(captured_items):02d}  •  {item['category'].upper()}"
        story.append(Paragraph(badge, tag_style))
        story.append(Spacer(1, 3))
        story.append(Paragraph(item['title'], h1_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=2, spaceAfter=8))

        # Metadata bar
        meta_row = [
            [
                Paragraph(f"<b>Route URL:</b> <font color='#2563eb'>{item['url']}</font>", body_style),
                Paragraph(f"<b>Authentication:</b> {'Required (Session Verified)' if item['auth'] else 'Public / Onboarding'}", body_style)
            ]
        ]
        meta_t = Table(meta_row, colWidths=[280, 240])
        meta_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(meta_t)
        story.append(Spacer(1, 8))

        # Description
        story.append(Paragraph(f"<b>Functional Overview:</b> {item['description']}", body_style))
        story.append(Spacer(1, 10))

        # Embedded High-Resolution Screenshot Image
        if os.path.exists(item['image_path']):
            # Target width: 520pt, Target height: ~325pt
            img = RLImage(item['image_path'], width=520, height=325)
            
            # Wrap image in framed table
            img_table = Table([[img]], colWidths=[520])
            img_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#94a3b8")),
                ('PADDING', (0, 0), (-1, -1), 0),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(img_table)
        
        story.append(Spacer(1, 10))
        
        # Action Highlights Box
        highlights_data = [
            [
                Paragraph("<b>Key Menu Actions & Capabilities:</b>", tag_style),
                Paragraph("<b>Business & Security Value:</b>", tag_style)
            ],
            [
                Paragraph("• Live interactive data filtering & CRUD actions<br/>• Real-time modal dialogues and form input validation<br/>• Breadcrumb navigation and fast module switching", body_style),
                Paragraph("• Role-based permission controls & audit logs<br/>• Export capabilities (PDF / Excel / CSV formats)<br/>• Responsive UI styled with modern CSS & glassmorphism", body_style)
            ]
        ]
        hi_table = Table(highlights_data, colWidths=[260, 260])
        hi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(hi_table)

        if idx < len(captured_items):
            story.append(PageBreak())

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[✓] Successfully generated PDF Catalog: {pdf_output_path}")

async def main():
    seed_rich_demo_data()
    session_key = create_admin_session()
    
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    screenshots_dir = os.path.join(base_dir, 'screenshots')
    pdf_path = os.path.join(base_dir, 'TeamNext_ERP_UI_Feature_Catalog.pdf')
    
    # Also copy to artifacts dir
    artifacts_dir = r"C:\Users\HP\.gemini\antigravity-ide\brain\08eb6a61-212e-44e8-b9d9-768c49a18e48"
    os.makedirs(artifacts_dir, exist_ok=True)
    artifacts_pdf_path = os.path.join(artifacts_dir, 'TeamNext_ERP_UI_Feature_Catalog.pdf')
    
    # Start Django server
    print("[*] Starting Django development server...", flush=True)
    django_proc = subprocess.Popen(
        [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for Django server to respond
    server_ready = False
    for attempt in range(20):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/', timeout=2) as resp:
                if resp.status in (200, 302):
                    print("[OK] Django development server is up and running on http://127.0.0.1:8000", flush=True)
                    server_ready = True
                    break
        except Exception:
            await asyncio.sleep(0.5)
            
    if not server_ready:
        print("[!] Warning: server did not respond on root, proceeding anyway...", flush=True)
            
    try:
        captured_items = await capture_all_screenshots(session_key, screenshots_dir)
        print(f"[✓] Captured {len(captured_items)} high-definition UI screenshots.")
        
        # Build PDF in workspace
        build_pdf_catalog(captured_items, pdf_path)
        
        # Build PDF in artifacts directory
        build_pdf_catalog(captured_items, artifacts_pdf_path)
        
        # Also copy screenshots to artifacts directory for markdown previews
        art_screenshots_dir = os.path.join(artifacts_dir, 'screenshots')
        os.makedirs(art_screenshots_dir, exist_ok=True)
        import shutil
        for item in captured_items:
            dest = os.path.join(art_screenshots_dir, item['image_filename'])
            shutil.copyfile(item['image_path'], dest)
        print(f"[✓] Copied screenshots and PDF to artifact directory: {artifacts_dir}")
        
    finally:
        django_proc.terminate()
        print("[✓] Django server stopped.")

if __name__ == '__main__':
    asyncio.run(main())
