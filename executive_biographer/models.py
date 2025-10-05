from django.db import models
from django.conf import settings
from lead_management.models import Connection


class BiographyDraft(models.Model):
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='biography_drafts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    title = models.CharField(max_length=200, default="Untitled Draft")
    prompt = models.TextField()
    generated_text = models.TextField()
    
    version = models.IntegerField(default=1)  # incremented per connection
    is_published = models.BooleanField(default=False)  # only one per connection
    is_finetune_ready = models.BooleanField(default=False)  # for tagging the best final versions

    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"v{self.version} - {self.title} ({self.connection.full_name})"


class FineTuningSample(models.Model):
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE)
    input_data_json = models.JSONField()  # stores sections, style, parsed resume, etc.
    final_output = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Training Sample for {self.connection.full_name}"
