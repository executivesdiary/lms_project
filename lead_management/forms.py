from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, OutreachLead, Connection, UserProfile

# ✅ Super Admin or Manager: Create new users (Editor / Community Builder)
class UserRegistrationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('editor', 'Editor'),
        ('community_builder', 'Community Builder'),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Role")
    linkedin_url = forms.URLField(required=False)
    location = forms.CharField(required=False)
    job_status = forms.ChoiceField(choices=UserProfile.JOB_STATUS_CHOICES)
    joining_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    class Meta:
        model = CustomUser
        fields = ['username', 'email']

# ✅ User creation and update (Django Admin use)
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']


# ✅ Outreach Lead Form
class OutreachLeadForm(forms.ModelForm):
    class Meta:
        model = OutreachLead
        fields = ['linkedin_url', 'full_name', 'location']
        widgets = {
            'linkedin_url': forms.URLInput(attrs={'placeholder': 'Paste LinkedIn profile URL here'}),
            'full_name': forms.TextInput(attrs={'placeholder': 'Enter full name'}),
            'location': forms.TextInput(attrs={'placeholder': 'City, Country'}),
        }


# ✅ Add Connection Form
class AddConnectionForm(forms.ModelForm):
    class Meta:
        model = Connection
        fields = [
            'full_name',
            'location',
            'linkedin_email',
            'outreach_email',
            'profile_pdf',
            'profile_picture',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'location': forms.TextInput(attrs={'placeholder': 'City, Country'}),
            'linkedin_email': forms.EmailInput(attrs={'placeholder': 'LinkedIn Email'}),
            'outreach_email': forms.EmailInput(attrs={'placeholder': 'Outreach Email (optional)'}),
        }


# ✅ Connection Status Update Form
class ConnectionStatusForm(forms.ModelForm):
    class Meta:
        model = Connection
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'})
        }


# ✅ Edit Connection (no file upload field here now)
class ConnectionEditForm(forms.ModelForm):
    class Meta:
        model = Connection
        fields = [
            'full_name',
            'location',
            'linkedin_email',
            'outreach_email',
            'status',
            'profile_picture',
            'profile_pdf',
        ]
