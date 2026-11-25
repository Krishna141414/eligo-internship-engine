"""Create an Eligo admin account.

Interactive:      python manage.py create_admin
Non-interactive:  python manage.py create_admin --email a@b.c --name "Admin" --no-input
                  (password from --password or the ELIGO_ADMIN_PASSWORD environment variable)
"""
import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Create an Eligo admin account (email login)."

    def add_arguments(self, parser):
        parser.add_argument("--email")
        parser.add_argument("--name")
        parser.add_argument("--password")
        parser.add_argument("--no-input", action="store_false", dest="interactive")

    def handle(self, *args, email=None, name=None, password=None, interactive=True, **options):
        if interactive:
            email = email or input("Admin email: ").strip()
            name = name or input("Admin name: ").strip()
            while not password:
                first = getpass.getpass("Password: ")
                if first != getpass.getpass("Password (again): "):
                    self.stderr.write("Passwords don't match. Try again.")
                    continue
                password = first
        password = password or os.environ.get("ELIGO_ADMIN_PASSWORD")
        if not (email and name and password):
            raise CommandError("Email, name and password are required.")
        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise CommandError(f"A user with email {email} already exists.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        User.objects.create_superuser(email=email, password=password, name=name)
        self.stdout.write(self.style.SUCCESS(f"Admin account created: {email}"))
