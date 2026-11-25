"""Eligo user: email login, Admin/Student role, Active/Inactive status (spec §10 "Users")."""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models

mobile_validator = RegexValidator(r"^[6-9]\d{9}$", "Enter a valid 10-digit Indian mobile number.")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("user_type", User.UserType.STUDENT)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(user_type=User.UserType.ADMIN, is_staff=True, is_superuser=True)
        return self._create(email, password, **extra)


class User(AbstractUser):
    class UserType(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    username = None
    first_name = None
    last_name = None
    name = models.CharField(max_length=150)
    email = models.EmailField("email", unique=True)
    mobile_number = models.CharField(max_length=10, blank=True, default="", validators=[mobile_validator])
    user_type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.STUDENT, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    registered_date = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    class Meta:
        ordering = ["-registered_date"]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"

    def save(self, *args, **kwargs):
        self.email = (self.email or "").lower()
        self.is_active = self.status == self.Status.ACTIVE
        super().save(*args, **kwargs)

    @property
    def is_admin_user(self) -> bool:
        return self.user_type == self.UserType.ADMIN

    @property
    def is_student(self) -> bool:
        return self.user_type == self.UserType.STUDENT
