"""Put the DEMO accounts back into a clean, ready-to-demo state (D-028).

    python manage.py reset_demo

Deletes the assessment attempts (with their answers), recommendations and job-role predictions of
the DEMO students only, restores each DEMO account (name, password, active) and re-runs seed_demo
(profiles, DEMO assessments). A DEMO student is one of the seeded accounts, demo.<key>@eligo.local,
the same rule seed_demo uses. Nothing else is read or changed: other students, admins, internships
and non-DEMO assessments are never touched. Hard rule 12 (never delete attempts) protects real
students' records; DEMO accounts are illustrative and resetting them is this command's job.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from assessments.models import Attempt
from ml_core.demo import DEMO_PROFILES
from recommendations.management.commands.seed_demo import demo_email, demo_password
from recommendations.models import InternshipRecommendation, JobRolePrediction


class Command(BaseCommand):
    help = "Reset the DEMO students to a clean state. Never touches non-DEMO data."

    @transaction.atomic
    def handle(self, *args, **options):
        emails = {demo_email(key): profile.label for key, profile in DEMO_PROFILES.items()}
        demo_users = User.objects.filter(email__in=emails, user_type=User.UserType.STUDENT)

        # Order matters: recommendations point at attempts (PROTECT); answers go with their attempt (CASCADE).
        n_recs, _ = InternshipRecommendation.objects.filter(student__in=demo_users).delete()
        n_preds, _ = JobRolePrediction.objects.filter(student__in=demo_users).delete()
        n_attempts = Attempt.objects.filter(student__in=demo_users).count()
        Attempt.objects.filter(student__in=demo_users).delete()

        password = demo_password()
        for user in demo_users:
            user.name = emails[user.email]
            user.status = User.Status.ACTIVE
            user.set_password(password)
            user.save()

        call_command("seed_demo", stdout=self.stdout)
        def plural(n, word):
            return f"{n} {word}{'' if n == 1 else 's'}"

        self.stdout.write(self.style.SUCCESS(
            f"Reset {plural(demo_users.count(), 'DEMO student')}: removed {plural(n_attempts, 'attempt')}, "
            f"{plural(n_recs, 'recommendation row')} and {plural(n_preds, 'prediction')}. "
            f"Non-DEMO data was not touched."))
