"""Put the demo database back into a clean, ready-to-demo state (D-028).

    python manage.py reset_demo

1. DEMO students (the seeded accounts, demo.<key>@eligo.local, the same rule seed_demo uses): their
   assessment attempts (with answers), recommendations and job-role predictions are deleted, and each
   account is restored (name, password, active).
2. Test accounts are removed completely, with their history. A test account is a STUDENT that carries
   a test marker: an email on a domain reserved for testing (RFC 2606: example.com/.net/.org, *.test,
   *.example, *.invalid, localhost), or a "DEMO" name that isn't one of the seeded DEMO accounts (E2E
   runs, rehearsals). Admins are never removed.
3. seed_demo runs again (profiles, DEMO assessments).

Everyone else is never read or changed: real students, admins, internships and non-DEMO assessments.
Hard rule 12 (never delete attempts) protects real students' records; DEMO and test accounts are
illustrative and resetting them is this command's job.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from accounts.models import User
from assessments.models import Attempt
from ml_core.demo import DEMO_PROFILES
from recommendations.management.commands.seed_demo import demo_email, demo_password
from recommendations.models import InternshipRecommendation, JobRolePrediction

#: RFC 2606 / RFC 6761 names that can never belong to a real person's mailbox.
TEST_DOMAINS = ("example.com", "example.net", "example.org")
TEST_TLDS = (".test", ".example", ".invalid", ".localhost")


def find_test_accounts(seeded_emails):
    """Students carrying a test marker (see the module docstring). Never admins, never seeded DEMO accounts."""
    marker = Q(name__startswith="DEMO") | Q(email__iendswith="@localhost")
    for domain in TEST_DOMAINS:
        marker |= Q(email__iendswith=f"@{domain}")
    for tld in TEST_TLDS:
        marker |= Q(email__iendswith=tld)
    return User.objects.filter(marker, user_type=User.UserType.STUDENT).exclude(email__in=seeded_emails)


def _wipe_history(users):
    """Delete the users' recommendations, predictions and attempts. Order matters: recommendations point at
    attempts (PROTECT); answers go with their attempt (CASCADE). Returns (attempts, recommendation rows,
    predictions)."""
    n_recs, _ = InternshipRecommendation.objects.filter(student__in=users).delete()
    n_preds, _ = JobRolePrediction.objects.filter(student__in=users).delete()
    attempts = Attempt.objects.filter(student__in=users)
    n_attempts = attempts.count()
    attempts.delete()
    return n_attempts, n_recs, n_preds


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


class Command(BaseCommand):
    help = "Reset the DEMO students and remove test accounts. Never touches real students or admins."

    @transaction.atomic
    def handle(self, *args, **options):
        labels = {demo_email(key): profile.label for key, profile in DEMO_PROFILES.items()}
        demo_users = User.objects.filter(email__in=labels, user_type=User.UserType.STUDENT)
        n_attempts, n_recs, n_preds = _wipe_history(demo_users)

        to_remove = list(find_test_accounts(labels))
        removed = [f"{u.name} <{u.email}>" for u in to_remove]
        _wipe_history(to_remove)
        User.objects.filter(pk__in=[u.pk for u in to_remove]).delete()     # profile goes with it (CASCADE)

        password = demo_password()
        for user in demo_users:
            user.name = labels[user.email]
            user.status = User.Status.ACTIVE
            user.set_password(password)
            user.save()

        call_command("seed_demo", stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(
            f"Reset {_plural(demo_users.count(), 'DEMO student')}: removed {_plural(n_attempts, 'attempt')}, "
            f"{_plural(n_recs, 'recommendation row')} and {_plural(n_preds, 'prediction')}."))
        if removed:
            self.stdout.write(self.style.SUCCESS(f"Removed {_plural(len(removed), 'test account')}: " + "; ".join(removed)))
        self.stdout.write("Real students and admins were not touched.")
