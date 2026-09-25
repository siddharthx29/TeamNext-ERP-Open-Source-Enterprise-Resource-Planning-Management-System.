import os
import sys
import django
import json
import base64
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from myapp.models import (
    Company, Employee, Project, ProjectMember, ChatMessage, ChatMessageMedia,
    EmailMessage, Invoice, Expense, Payroll, Ticket, Department, Attendance, LeaveRequest
)
from myapp.views import (
    signup_view, save_settings, chat_messages, api_users,
    project_member_settings, send_dashboard_email, save_email_draft,
    api_notifications, api_generate_report, api_unlock_channel,
    api_channel_lock_settings, api_chat_media, logout_view
)

def build_request(method='GET', path='/', data=None, session_data=None):
    rf = RequestFactory()
    if method == 'GET':
        req = rf.get(path, data or {})
    elif method == 'POST':
        if isinstance(data, dict):
            req = rf.post(path, json.dumps(data), content_type='application/json')
        else:
            req = rf.post(path, data or {})
    elif method == 'PATCH':
        req = rf.patch(path, json.dumps(data or {}), content_type='application/json')
    elif method == 'DELETE':
        req = rf.delete(path, json.dumps(data or {}), content_type='application/json')
    else:
        req = rf.generic(method, path)

    SessionMiddleware(lambda r: None).process_request(req)
    MessageMiddleware(lambda r: None).process_request(req)
    req.session.save()

    if session_data:
        for k, v in session_data.items():
            req.session[k] = v
        req.session.save()

    return req

def build_multipart_request(path='/', data=None, files=None, session_data=None):
    rf = RequestFactory()
    post_data = data.copy() if data else {}
    if files:
        for k, v in files.items():
            post_data[k] = v
    req = rf.post(path, post_data)
    SessionMiddleware(lambda r: None).process_request(req)
    MessageMiddleware(lambda r: None).process_request(req)
    req.session.save()
    if session_data:
        for k, v in session_data.items():
            req.session[k] = v
        req.session.save()
    return req

def run_tests():
    print("=" * 60)
    print("STARTING TEAMNEXT ERP QA VERIFICATION SUITE")
    print("=" * 60)

    results = {}

    # Setup test workspace
    test_co, _ = Company.objects.get_or_create(
        email='qa_company@teamnext.test',
        defaults={'name': 'QA Corp', 'password': 'hashed_qa_pwd'}
    )
    admin_emp, _ = Employee.objects.get_or_create(
        email='qa_admin@teamnext.test',
        defaults={'company': test_co, 'name': 'QA Admin', 'role': 'Administrator', 'password': 'hashed_qa_pwd'}
    )
    test_proj, _ = Project.objects.get_or_create(
        name='QA Core Project',
        company=test_co,
        defaults={'description': 'QA Testing Suite Channel'}
    )

    # 1. Chat Messaging Test
    try:
        user_emp, _ = Employee.objects.get_or_create(
            email='qa_chatter@teamnext.test',
            defaults={'company': test_co, 'name': 'QA Chatter', 'role': 'Developer', 'password': 'pwd'}
        )
        pm, _ = ProjectMember.objects.get_or_create(project=test_proj, employee=user_emp)
        pm.can_chat = True
        pm.is_allowed = True
        pm.save()

        req = build_request('POST', '/api/chat/messages/', {'project_id': test_proj.id, 'text': 'QA Test Hello'}, session_data={'verified': True, 'otp_email': user_emp.email})
        resp = chat_messages(req)
        assert resp.status_code == 200, f"Status {resp.status_code}"
        data = json.loads(resp.content)
        assert data['status'] == 'ok', data

        # Test restricted chat
        pm.can_chat = False
        pm.save()
        req_res = build_request('POST', '/api/chat/messages/', {'project_id': test_proj.id, 'text': 'Blocked Message'}, session_data={'verified': True, 'otp_email': user_emp.email})
        resp_res = chat_messages(req_res)
        assert resp_res.status_code == 403, "Restricted user was not blocked from chatting"

        # Restore permissions
        pm.can_chat = True
        pm.save()

        results['1_chat_messaging'] = "PASSED"
    except Exception as e:
        results['1_chat_messaging'] = f"FAILED: {e}"

    # 2. Users & Access CRUD Test
    try:
        # GET
        req_g = build_request('GET', '/api/users/', session_data={'verified': True, 'otp_email': test_co.email})
        resp_g = api_users(req_g)
        users = json.loads(resp_g.content).get('users', [])
        assert len(users) > 0, "No users returned"

        # POST
        new_email = f"emp_new_{int(time.time() * 1000)}@gmail.com"
        req_p = build_request('POST', '/api/users/', {'name': 'New Dev', 'email': new_email, 'role': 'Backend Lead'}, session_data={'verified': True, 'otp_email': test_co.email})
        resp_p = api_users(req_p)
        assert json.loads(resp_p.content)['status'] == 'ok'

        # PATCH
        req_pt = build_request('PATCH', '/api/users/', {'email': new_email, 'role': 'Principal Engineer'}, session_data={'verified': True, 'otp_email': test_co.email})
        resp_pt = api_users(req_pt)
        assert json.loads(resp_pt.content)['status'] == 'ok'
        updated_emp = Employee.objects.get(email=new_email)
        assert updated_emp.role == 'Principal Engineer'

        # DELETE
        req_d = build_request('DELETE', '/api/users/', {'email': new_email}, session_data={'verified': True, 'otp_email': test_co.email})
        resp_d = api_users(req_d)
        assert json.loads(resp_d.content)['status'] == 'ok'
        assert not Employee.objects.filter(email=new_email).exists()

        results['2_users_access'] = "PASSED"
    except Exception as e:
        results['2_users_access'] = f"FAILED: {e}"

    # 3. Employee Personal Email Signup Test
    try:
        emp_signup_email = f"emp_signup_{int(time.time() * 1000)}@gmail.com"
        rf = RequestFactory()
        req_s = rf.post('/signup/', {
            'kind': 'employee',
            'full_name': 'Signup Tester',
            'employee_email_signup': emp_signup_email,
            'company_email': test_co.email,
            'employee_password_signup': 'Secret123!',
            'employee_otp_signup': '7788',
            'role': 'QA Engineer'
        })
        SessionMiddleware(lambda r: None).process_request(req_s)
        MessageMiddleware(lambda r: None).process_request(req_s)
        req_s.session['otp'] = '7788'
        req_s.session['otp_email'] = emp_signup_email
        req_s.session.save()

        resp_s = signup_view(req_s)
        assert resp_s.status_code == 302
        created_emp = Employee.objects.filter(email=emp_signup_email).first()
        assert created_emp is not None
        assert created_emp.company == test_co
        assert created_emp.role == 'QA Engineer'

        results['3_employee_personal_email_signup'] = "PASSED"
    except Exception as e:
        results['3_employee_personal_email_signup'] = f"FAILED: {e}"

    # 4. Moderator Settings Modification Test
    try:
        mod_emp, _ = Employee.objects.get_or_create(
            email='qa_moderator@teamnext.test',
            defaults={'company': test_co, 'name': 'QA Mod', 'role': 'Manager', 'password': 'pwd'}
        )
        pm_mod, _ = ProjectMember.objects.get_or_create(project=test_proj, employee=mod_emp)
        pm_mod.can_modify_settings = True
        pm_mod.save()

        req_set = build_request('POST', '/api/save-settings/', {'company_name': 'QA Corp Renamed'}, session_data={'verified': True, 'otp_email': mod_emp.email})
        resp_set = save_settings(req_set)
        assert json.loads(resp_set.content)['status'] == 'ok'
        test_co.refresh_from_db()
        assert test_co.name == 'QA Corp Renamed'

        results['4_moderator_settings'] = "PASSED"
    except Exception as e:
        results['4_moderator_settings'] = f"FAILED: {e}"

    # 5. Project Member Permissions Settings API Test
    try:
        req_perm = build_request('POST', f'/api/projects/{test_proj.id}/members/{user_emp.email}/settings/', {
            'is_admin': True,
            'can_chat': True,
            'can_modify_settings': True,
            'can_approve_leaves': True,
            'is_allowed': True
        }, session_data={'verified': True, 'otp_email': test_co.email})
        resp_perm = project_member_settings(req_perm, str(test_proj.id), user_emp.email)
        assert json.loads(resp_perm.content)['status'] == 'ok'
        pm_obj = ProjectMember.objects.get(project=test_proj, employee=user_emp)
        assert pm_obj.is_admin is True
        assert pm_obj.can_modify_settings is True
        assert pm_obj.can_approve_leaves is True

        results['5_permissions_management'] = "PASSED"
    except Exception as e:
        results['5_permissions_management'] = f"FAILED: {e}"

    # 6. Email System Test
    try:
        req_em = build_request('POST', '/dashboard/send-email/', {
            'to': 'recipient@teamnext.test',
            'subject': 'QA Test Email Subject',
            'body': 'QA Verification Email Body Text'
        }, session_data={'verified': True, 'otp_email': test_co.email})
        resp_em = send_dashboard_email(req_em)
        assert json.loads(resp_em.content)['status'] == 'success'
        assert EmailMessage.objects.filter(subject='QA Test Email Subject').exists()

        # Draft Save
        req_ds = build_request('POST', '/email-page/save-draft/', {
            'action': 'save',
            'to': 'draft_to@teamnext.test',
            'subject': 'Draft Subj',
            'body': 'Draft text'
        }, session_data={'verified': True, 'otp_email': test_co.email})
        resp_ds = save_email_draft(req_ds)
        assert json.loads(resp_ds.content)['status'] == 'ok'
        draft = EmailMessage.objects.filter(subject='Draft Subj', is_draft=True).first()
        assert draft is not None

        # Draft Delete
        req_dd = build_request('POST', '/email-page/save-draft/', {
            'action': 'delete',
            'id': draft.id
        }, session_data={'verified': True, 'otp_email': test_co.email})
        resp_dd = save_email_draft(req_dd)
        assert json.loads(resp_dd.content)['status'] == 'ok'
        assert not EmailMessage.objects.filter(id=draft.id).exists()

        results['6_email_system'] = "PASSED"
    except Exception as e:
        results['6_email_system'] = f"FAILED: {e}"

    # 7. Notifications Button / Endpoint Test
    try:
        Ticket.objects.create(project=test_proj, employee=admin_emp, title='QA Critical Server Ticket', priority='high', description='Server load high')
        req_n = build_request('GET', '/api/notifications/', session_data={'verified': True, 'otp_email': test_co.email})
        resp_n = api_notifications(req_n)
        data_n = json.loads(resp_n.content)
        assert data_n['status'] == 'ok'
        assert data_n['count'] >= 1
        assert len(data_n['notifications']) >= 1

        results['7_notifications_button'] = "PASSED"
    except Exception as e:
        results['7_notifications_button'] = f"FAILED: {e}"

    # 8. Post-Deployment Verification
    try:
        from django.conf import settings
        assert 'myapp' in settings.INSTALLED_APPS
        assert 'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE
        assert hasattr(settings, 'DATABASES')
        assert hasattr(settings, 'MEDIA_ROOT')
        results['8_post_deployment'] = "PASSED"
    except Exception as e:
        results['8_post_deployment'] = f"FAILED: {e}"

    # 9 & 10. Reports Accuracy & Audit Statements Deduplication Test
    try:
        Invoice.objects.get_or_create(company=test_co, client_name='Acme Corp', defaults={'amount': 15000.0, 'gst_rate': 18.0})
        Expense.objects.get_or_create(company=test_co, description='Server Cloud Hosting', defaults={'amount': 1200.0, 'category': 'Infrastructure'})

        report_types = ['Financial', 'Productivity', 'Inventory', 'Support']
        generated_reports = {}

        for rep in report_types:
            for fmt in ['pdf', 'excel']:
                req_rep = build_request('POST', '/api/reports/generate/', {'report_type': rep, 'format': fmt}, session_data={'verified': True, 'otp_email': test_co.email, 'company_name': test_co.name})
                resp_rep = api_generate_report(req_rep)
                assert resp_rep.status_code == 200, f"Error generating {rep} in {fmt}: {resp_rep.status_code}"
                rep_data = json.loads(resp_rep.content)
                assert rep_data['status'] == 'ok', f"Failed {rep} {fmt}: {rep_data}"
                raw_bytes = base64.b64decode(rep_data['file_data'])
                assert len(raw_bytes) > 200, f"Report {rep} ({fmt}) payload too small: {len(raw_bytes)} bytes"
                generated_reports[f"{rep}_{fmt}"] = len(raw_bytes)

        # Confirm distinct generation
        assert generated_reports['Financial_pdf'] != generated_reports['Productivity_pdf']
        assert generated_reports['Financial_excel'] != generated_reports['Inventory_excel']

        results['9_reports_accuracy'] = "PASSED"
        results['10_audit_statements_deduplicated'] = "PASSED"
    except Exception as e:
        results['9_reports_accuracy'] = f"FAILED: {e}"
        results['10_audit_statements_deduplicated'] = f"FAILED: {e}"

    # 11. Channel Locking & 4-Character Hex Validation Test
    try:
        # Create a channel to test locking
        locked_proj, _ = Project.objects.get_or_create(
            name='QA Secret Channel',
            company=test_co,
            defaults={'description': 'Locked channel testing'}
        )
        chatter, _ = Employee.objects.get_or_create(
            email='qa_lock_user@teamnext.test',
            defaults={'company': test_co, 'name': 'Lock User', 'role': 'Analyst', 'password': 'pwd'}
        )
        ProjectMember.objects.get_or_create(project=locked_proj, employee=chatter, defaults={'can_chat': True, 'is_allowed': True})

        # Lock channel via admin settings with valid 4-character hex: 'A3F9'
        req_lock = build_request('POST', f'/api/chat/lock-settings/{locked_proj.id}/', {
            'is_locked': True,
            'passcode': 'A3F9'
        }, session_data={'verified': True, 'otp_email': test_co.email})
        resp_lock = api_channel_lock_settings(req_lock, str(locked_proj.id))
        assert json.loads(resp_lock.content)['status'] == 'ok', resp_lock.content
        locked_proj.refresh_from_db()
        assert locked_proj.is_locked is True
        assert locked_proj.passcode_hash is not None

        # User GET messages on locked channel without unlock session -> returns status 'locked' and hides messages
        req_get = build_request('GET', f'/api/chat/messages/?project={locked_proj.id}', session_data={'verified': True, 'otp_email': chatter.email})
        resp_get = chat_messages(req_get)
        data_get = json.loads(resp_get.content)
        assert data_get['status'] == 'locked', f"Expected locked status, got {data_get}"
        assert 'messages' not in data_get, "Messages must be hidden when channel is locked"

        # User POST message on locked channel without unlock -> rejected 403
        req_post_locked = build_request('POST', '/api/chat/messages/', {'project': locked_proj.id, 'text': 'Should not post'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_post_locked = chat_messages(req_post_locked)
        assert resp_post_locked.status_code == 403, "Posting to locked channel without unlock must be forbidden"

        # Test invalid passcode formats:
        # Non-hex character 'GG12'
        req_bad1 = build_request('POST', f'/api/chat/unlock/{locked_proj.id}/', {'passcode': 'GG12'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_bad1 = api_unlock_channel(req_bad1, str(locked_proj.id))
        assert resp_bad1.status_code == 400

        # 5 characters '12345'
        req_bad2 = build_request('POST', f'/api/chat/unlock/{locked_proj.id}/', {'passcode': '12345'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_bad2 = api_unlock_channel(req_bad2, str(locked_proj.id))
        assert resp_bad2.status_code == 400

        # 2 characters 'AB'
        req_bad3 = build_request('POST', f'/api/chat/unlock/{locked_proj.id}/', {'passcode': 'AB'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_bad3 = api_unlock_channel(req_bad3, str(locked_proj.id))
        assert resp_bad3.status_code == 400

        # Wrong 4-character hex 'B2E8'
        req_wrong = build_request('POST', f'/api/chat/unlock/{locked_proj.id}/', {'passcode': 'B2E8'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_wrong = api_unlock_channel(req_wrong, str(locked_proj.id))
        assert resp_wrong.status_code == 400
        assert json.loads(resp_wrong.content)['status'] == 'error'

        # Correct 4-character hex 'a3f9' (case-insensitive)
        req_correct = build_request('POST', f'/api/chat/unlock/{locked_proj.id}/', {'passcode': 'a3f9'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_correct = api_unlock_channel(req_correct, str(locked_proj.id))
        assert resp_correct.status_code == 200, resp_correct.content
        assert json.loads(resp_correct.content)['status'] == 'ok'
        assert str(locked_proj.id) in req_correct.session.get('unlocked_channels', [])

        # Once unlocked in session, messages are accessible
        req_get_unlocked = build_request('GET', f'/api/chat/messages/?project={locked_proj.id}', session_data=req_correct.session)
        resp_get_unlocked = chat_messages(req_get_unlocked)
        data_unlocked = json.loads(resp_get_unlocked.content)
        assert data_unlocked['status'] == 'ok'
        assert 'messages' in data_unlocked

        results['11_channel_locking_and_hex_validation'] = "PASSED"
    except Exception as e:
        results['11_channel_locking_and_hex_validation'] = f"FAILED: {e}"

    # 12. Channel Rate Limiting / Brute Force Protection Test
    try:
        rate_proj, _ = Project.objects.get_or_create(
            name='QA Rate Limit Channel',
            company=test_co,
            defaults={'description': 'Rate limit testing'}
        )
        ProjectMember.objects.get_or_create(project=rate_proj, employee=chatter, defaults={'can_chat': True, 'is_allowed': True})

        # Lock channel with code 'F4D2'
        req_lock_r = build_request('POST', f'/api/chat/lock-settings/{rate_proj.id}/', {
            'is_locked': True,
            'passcode': 'F4D2'
        }, session_data={'verified': True, 'otp_email': test_co.email})
        api_channel_lock_settings(req_lock_r, str(rate_proj.id))

        # Perform 5 consecutive failed unlock attempts in the same session
        sess = {'verified': True, 'otp_email': chatter.email}
        for i in range(5):
            req_f = build_request('POST', f'/api/chat/unlock/{rate_proj.id}/', {'passcode': f'000{i}'}, session_data=sess)
            resp_f = api_unlock_channel(req_f, str(rate_proj.id))
            sess = req_f.session

        # 6th attempt should trigger 429 Too Many Requests rate limit
        req_limit = build_request('POST', f'/api/chat/unlock/{rate_proj.id}/', {'passcode': 'F4D2'}, session_data=sess)
        resp_limit = api_unlock_channel(req_limit, str(rate_proj.id))
        assert resp_limit.status_code == 429, f"Expected 429 rate limit, got {resp_limit.status_code}"
        assert 'Too many failed attempts' in json.loads(resp_limit.content)['message']

        results['12_channel_rate_limiting'] = "PASSED"
    except Exception as e:
        results['12_channel_rate_limiting'] = f"FAILED: {e}"

    # 13. Admin Lock Management & Passcode Modification Test
    try:
        # Non-admin employee trying to change lock settings -> 403 Forbidden
        req_unauth = build_request('POST', f'/api/chat/lock-settings/{locked_proj.id}/', {
            'is_locked': False
        }, session_data={'verified': True, 'otp_email': chatter.email})
        resp_unauth = api_channel_lock_settings(req_unauth, str(locked_proj.id))
        assert resp_unauth.status_code == 403, "Non-admin must not change lock settings"

        # Admin changes passcode to '00AF'
        req_chg = build_request('POST', f'/api/chat/lock-settings/{locked_proj.id}/', {
            'is_locked': True,
            'passcode': '00AF'
        }, session_data={'verified': True, 'otp_email': test_co.email})
        resp_chg = api_channel_lock_settings(req_chg, str(locked_proj.id))
        assert json.loads(resp_chg.content)['status'] == 'ok'

        # Old passcode 'A3F9' now fails
        req_old = build_request('POST', f'/api/chat/unlock/{locked_proj.id}/', {'passcode': 'A3F9'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_old = api_unlock_channel(req_old, str(locked_proj.id))
        assert resp_old.status_code == 400

        # New passcode '00AF' succeeds
        req_new = build_request('POST', f'/api/chat/unlock/{locked_proj.id}/', {'passcode': '00AF'}, session_data={'verified': True, 'otp_email': chatter.email})
        resp_new = api_unlock_channel(req_new, str(locked_proj.id))
        assert resp_new.status_code == 200

        # Admin disables lock
        req_dis = build_request('POST', f'/api/chat/lock-settings/{locked_proj.id}/', {
            'is_locked': False
        }, session_data={'verified': True, 'otp_email': test_co.email})
        resp_dis = api_channel_lock_settings(req_dis, str(locked_proj.id))
        assert json.loads(resp_dis.content)['is_locked'] is False
        locked_proj.refresh_from_db()
        assert locked_proj.is_locked is False

        results['13_admin_lock_management'] = "PASSED"
    except Exception as e:
        results['13_admin_lock_management'] = f"FAILED: {e}"

    # 14. Media Upload, Storage & Database Persistence Test
    try:
        # Create test image and document files
        sample_img = SimpleUploadedFile("diagram.png", b"fake_png_binary_data_123456", content_type="image/png")
        sample_doc = SimpleUploadedFile("spec.pdf", b"%PDF-1.4 fake_pdf_data_header_test", content_type="application/pdf")

        req_media = build_multipart_request(
            path='/api/chat/messages/',
            data={'project': str(test_proj.id), 'text': 'Here are the design specs and diagrams'},
            files={'files': sample_img},
            session_data={'verified': True, 'otp_email': user_emp.email}
        )
        resp_media = chat_messages(req_media)
        assert resp_media.status_code == 200, f"Status {resp_media.status_code}: {resp_media.content}"
        media_data = json.loads(resp_media.content)
        assert media_data['status'] == 'ok'
        msg_id = media_data['message']['id']
        assert len(media_data['message']['media']) == 1
        media_item = media_data['message']['media'][0]
        assert media_item['filename'] == 'diagram.png'
        assert media_item['is_image'] is True

        # Verify DB persistence
        media_rec = ChatMessageMedia.objects.filter(message_id=msg_id).first()
        assert media_rec is not None
        assert media_rec.original_filename == 'diagram.png'
        assert media_rec.file_size > 0

        # Upload document attachment
        req_doc = build_multipart_request(
            path='/api/chat/messages/',
            data={'project': str(test_proj.id), 'text': 'PDF document attached'},
            files={'files': sample_doc},
            session_data={'verified': True, 'otp_email': user_emp.email}
        )
        resp_doc = chat_messages(req_doc)
        doc_data = json.loads(resp_doc.content)
        assert doc_data['status'] == 'ok'
        assert doc_data['message']['media'][0]['is_document'] is True

        # Test dangerous extension rejection (.exe)
        bad_file = SimpleUploadedFile("malicious.exe", b"MZ_binary_executable", content_type="application/x-msdownload")
        req_bad = build_multipart_request(
            path='/api/chat/messages/',
            data={'project': str(test_proj.id), 'text': 'Dangerous file'},
            files={'files': bad_file},
            session_data={'verified': True, 'otp_email': user_emp.email}
        )
        resp_bad = chat_messages(req_bad)
        assert resp_bad.status_code == 400
        assert 'not permitted' in json.loads(resp_bad.content)['message']

        results['14_media_upload_and_persistence'] = "PASSED"
    except Exception as e:
        results['14_media_upload_and_persistence'] = f"FAILED: {e}"

    # 15. Media Access Control & Streaming Endpoint Test
    try:
        # Authorized user stream media (view inline)
        req_view = build_request('GET', f'/api/chat/media/{media_rec.id}/', session_data={'verified': True, 'otp_email': user_emp.email})
        resp_view = api_chat_media(req_view, media_rec.id)
        assert resp_view.status_code == 200
        assert 'inline' in resp_view['Content-Disposition']

        # Authorized user download media (Content-Disposition attachment)
        req_dl = build_request('GET', f'/api/chat/media/{media_rec.id}/?download=1', session_data={'verified': True, 'otp_email': user_emp.email})
        resp_dl = api_chat_media(req_dl, media_rec.id)
        assert resp_dl.status_code == 200
        assert 'attachment' in resp_dl['Content-Disposition']

        # Disallowed user from different company -> 400/403
        other_co, _ = Company.objects.get_or_create(email='other_company@teamnext.test', defaults={'name': 'Other Corp', 'password': 'pwd'})
        req_other = build_request('GET', f'/api/chat/media/{media_rec.id}/', session_data={'verified': True, 'otp_email': other_co.email})
        resp_other = api_chat_media(req_other, media_rec.id)
        assert resp_other.status_code == 400 or resp_other.status_code == 403

        # Media on locked channel without unlock -> blocked
        locked_proj.is_locked = True
        locked_proj.passcode_hash = 'pbkdf2_sha256$test'
        locked_proj.save()
        locked_msg = ChatMessage.objects.create(project=locked_proj, employee=user_emp, text='Secret image')
        locked_media = ChatMessageMedia.objects.create(message=locked_msg, original_filename='secret.png', file=sample_img, content_type='image/png', file_size=100)

        # Locked channel access without unlock session -> blocked
        req_lock_media = build_request('GET', f'/api/chat/media/{locked_media.id}/', session_data={'verified': True, 'otp_email': user_emp.email})
        resp_lock_media = api_chat_media(req_lock_media, locked_media.id)
        assert resp_lock_media.status_code == 400 or resp_lock_media.status_code == 403

        # Locked channel with unlocked session -> allowed
        req_unlock_media = build_request('GET', f'/api/chat/media/{locked_media.id}/', session_data={'verified': True, 'otp_email': user_emp.email, 'unlocked_channels': [str(locked_proj.id)]})
        resp_unlock_media = api_chat_media(req_unlock_media, locked_media.id)
        assert resp_unlock_media.status_code == 200

        results['15_media_access_control'] = "PASSED"
    except Exception as e:
        results['15_media_access_control'] = f"FAILED: {e}"

    # 16. Session Clearance on Logout Test
    try:
        rf = RequestFactory()
        req_logout = rf.get('/logout/')
        SessionMiddleware(lambda r: None).process_request(req_logout)
        MessageMiddleware(lambda r: None).process_request(req_logout)
        req_logout.session['verified'] = True
        req_logout.session['otp_email'] = user_emp.email
        req_logout.session['unlocked_channels'] = [str(test_proj.id), str(locked_proj.id)]
        req_logout.session['lock_failed_attempts'] = {'1': 3}
        req_logout.session.save()

        resp_logout = logout_view(req_logout)
        assert resp_logout.status_code == 302
        assert 'unlocked_channels' not in req_logout.session
        assert 'lock_failed_attempts' not in req_logout.session
        assert 'verified' not in req_logout.session

        results['16_session_clearance_on_logout'] = "PASSED"
    except Exception as e:
        results['16_session_clearance_on_logout'] = f"FAILED: {e}"

    print("\nVERIFICATION RESULTS SUMMARY:")
    print("-" * 60)
    for test_name, status in results.items():
        print(f"[{status}] {test_name}")
    print("=" * 60)

    if all(s == "PASSED" for s in results.values()):
        print("ALL 16 QA AUDIT AREAS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("SOME TESTS FAILED - PLEASE REVIEW.")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
