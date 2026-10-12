from django.db import models


class Player(models.Model):
    """
    A player (participant) registered by a scout in the field.
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    EXPERIENCE_CHOICES = [
        ('none',   'None'),
        ('street', 'Street play'),
        ('school', 'School team'),
        ('club',   'Club level'),
    ]

    DOMINANT_FOOT_CHOICES = [
        ('right', 'Right'),
        ('left',  'Left'),
        ('both',  'Both'),
    ]

    # Identity
    full_name        = models.CharField(max_length=150)
    age              = models.PositiveSmallIntegerField()
    gender           = models.CharField(max_length=1, choices=GENDER_CHOICES)
    dominant_foot    = models.CharField(max_length=5, choices=DOMINANT_FOOT_CHOICES, default='right')

    # Physical stats
    height_cm        = models.FloatField(null=True, blank=True)
    weight_kg        = models.FloatField(null=True, blank=True)

    # Location
    village          = models.CharField(max_length=150)
    district         = models.CharField(max_length=100)
    state            = models.CharField(max_length=100, default='Andhra Pradesh')

    # Background
    experience_level = models.CharField(max_length=10, choices=EXPERIENCE_CHOICES, default='none')

    # Scout who registered this player
    registered_by    = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, related_name='players'
    )

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.age}y) — {self.village}"
