from django.db import models
from players.models import Player


class Assessment(models.Model):
    """
    One complete assessment session for a player.
    Contains one or more TestResult entries.
    """
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('synced',    'Synced'),
    ]

    player          = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='assessments')
    scout           = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='assessments')
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    scout_notes     = models.TextField(blank=True)
    overall_score   = models.FloatField(null=True, blank=True)   # computed after all tests
    recommendation  = models.BooleanField(null=True, blank=True) # True = recommend for academy
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Assessment #{self.pk} — {self.player.full_name} ({self.status})"


class TestResult(models.Model):
    """
    Result of a single test within an assessment.
    The metrics JSON field stores all AI-extracted values specific to each test type.
    """
    TEST_CHOICES = [
        ('sprint',   '0-10m Sprint'),
        ('jump',     'Vertical Jump'),
        ('shuttle',  'Shuttle Run'),
        ('cone',     '3-Colour Cone Picking'),
        ('footwork', 'Shadow Footwork'),
    ]

    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('completed',  'Completed'),
        ('failed',     'Failed'),
    ]

    assessment   = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='test_results')
    test_type    = models.CharField(max_length=10, choices=TEST_CHOICES)
    status       = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')

    # Uploaded video file
    video        = models.FileField(upload_to='videos/%Y/%m/%d/', null=True, blank=True)

    # AI output — all metrics stored as flexible JSON
    metrics      = models.JSONField(null=True, blank=True)

    # Top-level score for this test (0–100)
    score        = models.FloatField(null=True, blank=True)

    # Error message if analysis failed
    error        = models.TextField(blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering    = ['created_at']
        unique_together = [['assessment', 'test_type']]  # one result per test per assessment

    def __str__(self):
        return f"{self.get_test_type_display()} — {self.assessment.player.full_name} ({self.status})"
