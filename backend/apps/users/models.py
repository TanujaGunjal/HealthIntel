"""Custom User model."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user model for HealthIntel."""
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Profile fields
    full_name = models.CharField(max_length=200, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    SEX_CHOICES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other'), ('prefer_not_to_say', 'Prefer not to say')]
    sex = models.CharField(max_length=20, choices=SEX_CHOICES, blank=True)
    height_cm = models.FloatField(null=True, blank=True, help_text='Height in centimetres (optional)')
    weight_kg = models.FloatField(null=True, blank=True, help_text='Weight in kilograms (optional)')
    known_allergies = models.TextField(blank=True, help_text='Comma-separated list of known allergies')
    existing_conditions = models.TextField(blank=True, help_text='Comma-separated list of existing conditions')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def profile_complete(self):
        """True when minimum profile fields are filled in."""
        return bool(self.full_name and self.age and self.sex)
