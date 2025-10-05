from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST

# ✅ Custom User Model with Roles
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('project_manager', 'Project Manager'),
        ('community_builder', 'Community Builder'),
        ('editor', 'Editor'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='community_builder')

    def __str__(self):
        return f"{self.username} ({self.role})"


# ✅ Extended User Profile Model
class UserProfile(models.Model):
    JOB_STATUS_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    linkedin_url = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    job_status = models.CharField(max_length=20, choices=JOB_STATUS_CHOICES, default='full_time')
    joining_date = models.DateField(null=True, blank=True)

    # 🔗 Link to project manager
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'project_manager'},
        related_name='assigned_builders'
    )

    def __str__(self):
        return f"Profile of {self.user.username}"


# 1️⃣ OutreachLead — Raw outreach attempts
class OutreachLead(models.Model):
    STATUS_CHOICES = [
        ('connection_sent', 'Connection Sent'),
    ]

    linkedin_url = models.URLField(unique=True)
    full_name = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='connection_sent')
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.linkedin_url

    def is_older_than_30_days(self):
        return timezone.now() - self.date_added > timedelta(days=30)


# ✅ Chat Screenshot Model (many-to-many with Connection)
class ChatScreenshot(models.Model):
    image = models.ImageField(upload_to='chat_screenshots/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Screenshot {self.id}"


# 2️⃣ Connection — Qualified leads (connected)
class Connection(models.Model):
    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('info_shared', 'Info Shared'),
        ('F1', 'Follow Up 1'),
        ('F2', 'Follow Up 2'),
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('cold_lead', 'Cold Lead'),
    ]

    outreach_lead = models.OneToOneField(OutreachLead, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='connections_added')
    linkedin_email = models.EmailField(blank=True)
    outreach_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='connected')
    date_connected = models.DateTimeField(auto_now_add=True)
    profile_pdf = models.FileField(upload_to='profile_pdfs/', blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    chat_screenshots = models.ManyToManyField(ChatScreenshot, blank=True, related_name='connections')

    # ✅ NEW: Assigned Editor Field
    assigned_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='editor_assigned_connections',
        limit_choices_to={'role': 'editor'}
    )

    def __str__(self):
        return self.full_name


# 📝 Comments on connection activity, with threaded replies
class ConnectionComment(models.Model):
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


# 3️⃣ ColdLead — No response after follow-up
class ColdLead(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE)
    date_cold = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cold: {self.connection.full_name}"


# 4️⃣ Member — Executives who have been featured
class Member(models.Model):
    MEMBERSHIP_CHOICES = [
        ('free', 'Free Member'),
        ('paid', 'Paid Member'),
    ]

    connection = models.OneToOneField(Connection, on_delete=models.CASCADE)
    membership_type = models.CharField(max_length=10, choices=MEMBERSHIP_CHOICES)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    assigned_editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='edited_members')
    community_builder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='connected_members')
    biography_url = models.URLField()
    featured_date = models.DateField()

    def __str__(self):
        return f"{self.connection.full_name} - Member"


# 5️⃣ LinkedInConnection — Uploaded LinkedIn records by builder (Temporary Table)
class LinkedInConnection(models.Model):
    community_builder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    linkedin_url = models.URLField(max_length=500)
    email = models.EmailField(blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, blank=True, null=True)
    connected_on = models.DateField(blank=True, null=True)
    source = models.CharField(max_length=20, default='uploaded')  # fixed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company}"

