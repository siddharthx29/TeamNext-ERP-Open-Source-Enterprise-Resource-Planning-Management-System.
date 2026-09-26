from django.db import models
from django.utils import timezone
import time


# ============================================================
# Soft Delete Architecture & Durable Storage Framework
# ============================================================

class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that enforces soft deletion and prevents permanent record loss."""

    def delete(self, deleted_by=None):
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=deleted_by or ''
        )

    def hard_delete(self):
        return super().delete()

    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Manager that defaults to active (non-deleted) records for regular ERP queries."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_set(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)


class SoftDeleteModel(models.Model):
    """
    Abstract base model providing soft-delete capabilities, deletion metadata,
    and undo/recovery support for critical ERP entities.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.CharField(max_length=255, null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, deleted_by=None):
        """Soft delete the instance and preserve the record in the database."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if deleted_by:
            self.deleted_by = deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently purge the instance from the database."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a previously soft-deleted instance."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


# ============================================================
# Audit Logging & Recovery Metadata Models
# ============================================================

class AuditLog(models.Model):
    """
    Comprehensive audit trail tracking who created, modified, soft-deleted,
    restored, exported, or backed up ERP records.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Soft Deleted'),
        ('HARD_DELETE', 'Permanently Deleted'),
        ('RESTORE', 'Restored'),
        ('LOGIN', 'User Logged In'),
        ('EXPORT', 'Data Exported'),
        ('BACKUP', 'Database Backup Created'),
        ('RECOVERY', 'Database Restored'),
    ]

    company = models.ForeignKey('Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    actor_email = models.CharField(max_length=255, db_index=True)
    actor_name = models.CharField(max_length=255, blank=True, null=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True, null=True)
    entity_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f"[{self.action}] {self.entity_type} {self.entity_id} by {self.actor_email} at {self.created_at}"


def log_audit(company=None, actor_email='', actor_name='', action='CREATE', entity_type='', entity_id='', entity_name='', description='', changes=None, ip_address=''):
    """Safe audit trail recorder helper that guarantees business flow continuity."""
    try:
        return AuditLog.objects.create(
            company=company,
            actor_email=actor_email or 'system',
            actor_name=actor_name or '',
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else '',
            entity_name=entity_name or '',
            description=description or '',
            changes=changes or {},
            ip_address=ip_address or ''
        )
    except Exception:
        return None


class DatabaseBackupRecord(models.Model):
    """
    Immutable ledger of all automated and manual database backups, integrity hashes,
    verification statuses, and test-restoration outcomes.
    """
    BACKUP_TYPES = [
        ('daily', 'Daily Scheduled Backup'),
        ('weekly', 'Weekly Long-term Backup'),
        ('monthly', 'Monthly Archival Backup'),
        ('pre_deployment', 'Pre-Deployment Safety Snapshot'),
        ('manual', 'Manual Administrator Backup'),
    ]
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('verified', 'Verified & Intact'),
        ('corrupted', 'Integrity Check Failed'),
    ]

    filename = models.CharField(max_length=255, unique=True)
    filepath = models.CharField(max_length=500)
    backup_type = models.CharField(max_length=30, choices=BACKUP_TYPES, default='daily')
    engine = models.CharField(max_length=50)
    size_bytes = models.BigIntegerField(default=0)
    sha256_hash = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='in_progress')
    record_count = models.IntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, null=True)
    restoration_tested = models.BooleanField(default=False)
    restoration_tested_at = models.DateTimeField(null=True, blank=True)
    storage_destination = models.CharField(max_length=255, default='local')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.status}) - {self.size_bytes} bytes"


# ============================================================
# Core Business & ERP Entities
# ============================================================

class Company(SoftDeleteModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    employees_count = models.CharField(max_length=50, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Department(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Employee(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=100, blank=True, null=True)
    department_old = models.CharField(max_length=100, blank=True, null=True)
    dept = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Project(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='projects')
    departments = models.ManyToManyField(Department, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_locked = models.BooleanField(default=False)
    passcode_hash = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProjectMember(SoftDeleteModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='project_memberships')
    can_chat = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    can_modify_settings = models.BooleanField(default=False)
    can_approve_leaves = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)

    class Meta:
        unique_together = ('project', 'employee')


class Ticket(SoftDeleteModel):
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tickets')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatMessage(SoftDeleteModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='messages')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='chat_messages')
    text = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)


class ChatMessageMedia(SoftDeleteModel):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='media_attachments')
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='chat_media/%Y/%m/', blank=True, null=True)
    content_type = models.CharField(max_length=100)
    file_size = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} ({self.content_type})"

    @property
    def formatted_size(self):
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"


class EmailMessage(SoftDeleteModel):
    sender_email = models.EmailField()
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_draft = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class LeaveRequest(SoftDeleteModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    reason = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)


class SocialItem(SoftDeleteModel):
    ITEM_TYPES = [
        ('birthday', 'Birthday'),
        ('topic', 'Hot Topic'),
        ('dare', 'Daily Dare'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='social_items')
    type = models.CharField(max_length=10, choices=ITEM_TYPES)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    meta_info = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Invoice(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoices')
    client_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('paid', 'Paid'), ('cancelled', 'Cancelled')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.gst_amount = (self.amount * self.gst_rate) / 100
        self.total_amount = self.amount + self.gst_amount
        super().save(*args, **kwargs)


class Expense(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)


class Payroll(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payrolls')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_entries')
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    month_year = models.CharField(max_length=20)

    def save(self, *args, **kwargs):
        self.net_salary = self.base_salary + self.bonus - self.deductions
        super().save(*args, **kwargs)


class VendorPayment(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='vendor_payments')
    vendor_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='completed')
    date = models.DateField(default=timezone.now)


class BankTransaction(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bank_transactions')
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=[('credit', 'Credit'), ('debit', 'Debit')])
    is_reconciled = models.BooleanField(default=False)


class InventoryItem(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='inventory_items')
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    sales_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Attendance(SoftDeleteModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[('present', 'Present'), ('absent', 'Absent'), ('late', 'Late')], default='present')
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'date')


class Notification(SoftDeleteModel):
    user = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, default='GENERAL', db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, null=True)
    related_object_id = models.CharField(max_length=100, blank=True, null=True)
    unread = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'unread']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} for {self.user.email}"


class Feedback(SoftDeleteModel):
    FEEDBACK_TYPES = [
        ('daily', 'Daily Feedback of the Day'),
        ('issue', 'Issue / Workplace Blocker'),
        ('suggestion', 'Improvement Suggestion'),
        ('grievance', 'Private Concern / Grievance'),
        ('praise', 'Kudos / Appreciation'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open / Submitted'),
        ('under_review', 'Under Review'),
        ('addressed', 'Addressed / Resolved'),
        ('closed', 'Closed'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='feedbacks')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks_submitted')
    feedback_type = models.CharField(max_length=30, choices=FEEDBACK_TYPES, default='daily')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_private = models.BooleanField(default=True)
    is_anonymous = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_response = models.TextField(blank=True, null=True)
    responded_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback_responses')
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        author = "Anonymous" if self.is_anonymous else (self.employee.name if self.employee else "Unknown")
        return f"[{self.feedback_type.upper()}] {self.title} by {author}"


class ProjectTask(SoftDeleteModel):
    PRIORITY_CHOICES = [
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('in_review', 'In Review'),
        ('completed', 'Completed'),
        ('blocked', 'Blocked'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='project_tasks')
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_project_tasks')
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_project_tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    logged_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    tags = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.project.name} - {self.status})"
