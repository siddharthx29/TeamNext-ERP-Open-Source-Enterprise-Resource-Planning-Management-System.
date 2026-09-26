from django.urls import path

from . import views

urlpatterns = [

    path("", views.login_view, name="login"),

    path("send-otp/", views.send_otp, name="send_otp"),

    path("otp/", views.otp_view, name="otp"),

    path("verify/", views.verify_otp, name="verify_otp"),

    path("resend/", views.resend_otp, name="resend_otp"),

    path("dashboard/", views.dashboard, name="dashboard"),

    path("login/password/", views.password_login, name="password_login"),

    path("signup/", views.signup_view, name="signup"),

    path("forgot-password/", views.forgot_password, name="forgot_password"),

    path("set-password/", views.set_password, name="set_password"),

    path("dashboard/send-email/", views.send_dashboard_email, name="dashboard_send_email"),

    path("dashboard/create-ticket/", views.create_ticket, name="dashboard_create_ticket"),

    path("tickets-page/", views.tickets_page, name="tickets_page"),
    path("api/tickets/update-status/", views.api_update_ticket_status, name="api_update_ticket_status"),
    path("api/tickets/assign/", views.api_assign_ticket, name="api_assign_ticket"),
    path("api/tickets/delete/", views.api_delete_ticket, name="api_delete_ticket"),


    path("email-page/", views.email_page, name="email_page"),

    path("email-page/save-draft/", views.save_email_draft, name="save_email_draft"),

    path("api/email/fetch/", views.api_fetch_emails, name="api_fetch_emails"),

    path("api/email/receive/", views.receive_email, name="api_email_receive"),

    path("projects-page/", views.projects_page, name="projects_page"),

    path("chat-page/", views.chat_page, name="chat_page"),

    path("analytics-page/", views.analytics_page, name="analytics_page"),

    path("users-page/", views.users_page, name="users_page"),

    path("profile-page/", views.profile_page, name="profile_page"),
    path("api/profile/update/", views.api_update_profile, name="api_update_profile"),

    path("settings-page/", views.settings_page, name="settings_page"),

    path("help-centre-page/", views.help_centre_page, name="help_centre_page"),
    path("api/help-centre/contact/", views.api_contact_help_centre, name="api_contact_help_centre"),

    path("social-page/", views.social_page, name="social_page"),

    path("api/social/add/", views.api_add_social_item, name="api_add_social"),
    path("api/social/delete/", views.api_delete_social_item, name="api_delete_social"),


    path("leaves-page/", views.leaves_page, name="leaves_page"),

    path("api/leaves/apply/", views.api_apply_leave, name="api_apply_leave"),

    path("api/leaves/action/", views.api_leave_action, name="api_leave_action"),

    path("logout/", views.logout_view, name="logout"),

    path("api/add-developer/", views.add_developer, name="api_add_developer"),

    path("api/verify-developer/", views.verify_developer, name="api_verify_developer"),

    path("api/developers/", views.developers_list, name="api_developers"),

    path("api/analytics/", views.analytics_api, name="api_analytics"),

    path("api/save-settings/", views.save_settings, name="api_save_settings"),

    path("api/send-otp-json/", views.api_send_otp_json, name="api_send_otp_json"),

    path("api/chat/messages/", views.chat_messages, name="api_chat_messages"),
    path("api/chat/unlock/<str:project_id>/", views.api_unlock_channel, name="api_unlock_channel"),
    path("api/chat/lock-settings/<str:project_id>/", views.api_channel_lock_settings, name="api_channel_lock_settings"),
    path("api/chat/media/<int:media_id>/", views.api_chat_media, name="api_chat_media"),

    path("api/projects/<str:project_id>/members/", views.project_members, name="api_project_members"),

    path("api/projects/<str:project_id>/members/<str:member_email>/settings/", views.project_member_settings, name="api_project_member_settings"),

    path("api/projects/", views.api_projects, name="api_projects"),

    path("api/projects/add/", views.api_add_project, name="api_add_project"),

    path("api/users/", views.api_users, name="api_users"),
    path("api/departments/", views.api_departments, name="api_departments"),

    path("finance-page/", views.finance_page, name="finance_page"),
    path("api/finance/invoice/", views.api_create_invoice, name="api_create_invoice"),
    path("api/finance/expense/", views.api_log_expense, name="api_log_expense"),
    path("api/finance/salary/", views.api_add_salary, name="api_add_salary"),
    path("api/finance/bill/", views.api_add_bill, name="api_add_bill"),
    path("api/finance/reconcile/", views.api_bank_reconciliation, name="api_bank_reconcile"),
    path("api/finance/export/", views.api_export_finance, name="api_export_finance"),
    path("api/finance/data/", views.api_finance_data, name="api_finance_data"),
    path("hr-page/", views.hr_page, name="hr_page"),
    path("api/hr/employees/", views.api_hr_employees, name="api_hr_employees"),
    path("api/hr/add-employee/", views.api_hr_add_employee, name="api_hr_add_employee"),
    path("api/hr/mark-attendance/", views.api_hr_mark_attendance, name="api_hr_mark_attendance"),
    path("api/hr/attendance-tracker/", views.api_hr_attendance_tracker, name="api_hr_attendance_tracker"),
    path("api/hr/attendance-records/", views.api_hr_attendance_records, name="api_hr_attendance_records"),
    path("api/hr/project-staffing/", views.api_hr_project_staffing, name="api_hr_project_staffing"),
    path("api/hr/appoint-project/", views.api_hr_appoint_project, name="api_hr_appoint_project"),
    path("api/hr/remove-project-member/", views.api_hr_remove_project_member, name="api_hr_remove_project_member"),
    path("inventory-page/", views.inventory_page, name="inventory_page"),
    path("api/inventory/add-asset/", views.api_add_asset, name="api_add_asset"),
    path("api/inventory/delete-asset/", views.api_delete_asset, name="api_delete_asset"),
    path("api/inventory/data/", views.api_inventory_data, name="api_inventory_data"),
    path("api/reports/generate/", views.api_generate_report, name="api_generate_report"),
    path("reports-page/", views.reports_page, name="reports_page"),
    path("api/notifications/", views.api_notifications, name="api_notifications"),
    path("api/notifications/mark-read/", views.api_mark_notifications_read, name="api_mark_notifications_read"),
    path("api/dashboard-data/", views.api_dashboard_data, name="api_dashboard_data"),
    path("api/dashboard-data/seed/", views.seed_dashboard_data, name="api_seed_data"),

    # Feedback Module
    path("feedback-page/", views.feedback_page, name="feedback_page"),
    path("api/feedback/submit/", views.api_submit_feedback, name="api_submit_feedback"),
    path("api/feedback/list/", views.api_feedback_list, name="api_feedback_list"),
    path("api/feedback/respond/", views.api_respond_feedback, name="api_respond_feedback"),
    path("api/feedback/delete/", views.api_delete_feedback, name="api_delete_feedback"),

    # Project Management Module
    path("project-management-page/", views.project_management_page, name="project_management_page"),
    path("api/project-management/tasks/", views.api_project_tasks, name="api_project_tasks"),
    path("api/project-management/create-task/", views.api_create_project_task, name="api_create_project_task"),
    path("api/project-management/update-task/", views.api_update_project_task, name="api_update_project_task"),
    path("api/project-management/delete-task/", views.api_delete_project_task, name="api_delete_project_task"),

    path("go/", views.quick_redirect, name="go_default"),

    path("go/<str:target>/", views.quick_redirect, name="go_target"),

    path("reset-db/", views.reset_db_view, name="reset_db"),

    # Database Persistence, Backup & Disaster Recovery Administration
    path("admin-recovery/", views.admin_recovery_page, name="admin_recovery_page"),
    path("api/health/db/", views.api_db_health, name="api_db_health"),
    path("api/admin/backup/create/", views.api_admin_trigger_backup, name="api_admin_trigger_backup"),
    path("api/admin/backup/verify/", views.api_admin_verify_backups, name="api_admin_verify_backups"),
    path("api/admin/backup/restore-database/", views.api_admin_restore_database, name="api_admin_restore_database"),
    path("api/admin/backup/download/<str:filename>/", views.api_admin_download_backup, name="api_admin_download_backup"),
    path("api/admin/recovery/restore/", views.api_admin_restore_soft_deleted, name="api_admin_restore_soft_deleted"),
    path("api/admin/export/", views.api_admin_export_data, name="api_admin_export_data"),
]

