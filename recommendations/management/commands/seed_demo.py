"""Create DEMO data for the viva (hard rule 7: everything is labelled DEMO and is illustrative).

    python manage.py seed_demo

Creates three DEMO assessments with illustrative MCQs and one DEMO student per profile in
ml_core/demo.py (the same profiles the notebook uses). Safe to re-run. Never touches internships.
Demo password: ELIGO_DEMO_PASSWORD environment variable, else the default printed below.
"""
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from assessments.models import Assessment, Question
from internships.services import parse_skills_input, skill_vocab
from ml_core.demo import DEMO_PROFILES
from students.models import StudentProfile

DEFAULT_PASSWORD = "Eligo-DEMO-2026!"

#: (question, A, B, C, D, correct). Illustrative questions; answers checked by hand.
BTECH = [
    ("Time complexity of binary search on a sorted array of n items?", "O(n)", "O(log n)", "O(n log n)", "O(1)", "B"),
    ("Which data structure is first-in, first-out?", "Stack", "Queue", "Tree", "Graph", "B"),
    ("What does 7 % 3 evaluate to in Python?", "2", "1", "0", "3", "B"),
    ("Which SQL clause filters groups after aggregation?", "WHERE", "ORDER BY", "HAVING", "LIMIT", "C"),
    ("What is decimal 10 in binary?", "1001", "1010", "1100", "0110", "B"),
    ("Which of these is not an OOP principle?", "Encapsulation", "Inheritance", "Polymorphism", "Compilation", "D"),
    ("A 120 m train at 72 km/h passes a pole in how long?", "5 s", "6 s", "8 s", "10 s", "B"),
    ("If 3x + 5 = 20, what is x?", "3", "4", "5", "6", "C"),
    ("Which protocol encrypts web traffic?", "HTTP", "FTP", "HTTPS", "SMTP", "C"),
    ("What is the average of 10, 20, 30 and 40?", "20", "25", "30", "35", "B"),
]
GRADUATE = [
    ("Next number in the series 2, 4, 8, 16, …?", "24", "30", "32", "36", "C"),
    ("What is 20% of 250?", "25", "40", "50", "60", "C"),
    ("Which word means the same as “rapid”?", "Slow", "Quick", "Calm", "Late", "B"),
    ("A shirt costs ₹800 after a 20% discount. What was the original price?", "₹960", "₹1,000", "₹1,200", "₹900", "B"),
    ("Which of these is a spreadsheet application?", "Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint", "Paint", "B"),
    ("Odd one out: Apple, Mango, Carrot, Banana", "Apple", "Mango", "Carrot", "Banana", "C"),
    ("4 people finish a job in 6 days. How long do 8 people take at the same rate?", "2 days", "3 days", "4 days", "12 days", "B"),
    ("Which word is the opposite of “expand”?", "Enlarge", "Contract", "Extend", "Grow", "B"),
    ("Simple interest on ₹1,000 at 10% a year for 2 years?", "₹100", "₹200", "₹210", "₹220", "B"),
    ("Which is good email etiquette?", "Writing in all caps", "A clear subject line", "No greeting", "Very large attachments", "B"),
]
TIMER = [
    ("What is 5 + 7?", "10", "11", "12", "13", "C"),
    ("Which colour do you get by mixing blue and yellow?", "Green", "Purple", "Orange", "Red", "A"),
    ("How many days are in a leap year?", "364", "365", "366", "367", "C"),
]
ASSESSMENTS = [
    ("DEMO – B.Tech/B.E. aptitude", "B.Tech", 2, BTECH),
    ("DEMO – Any Graduate aptitude", "Any Graduate", 2, GRADUATE),
    ("DEMO – 1-minute timer check", "Any Graduate", 1, TIMER),
]


class Command(BaseCommand):
    help = "Create DEMO-labelled assessments and students for demonstration."

    @transaction.atomic
    def handle(self, *args, **options):
        for name, qualification, minutes, questions in ASSESSMENTS:
            a, _ = Assessment.objects.get_or_create(
                assessment_name=name, defaults={"qualification": qualification, "duration_minutes": minutes})
            if not a.questions.exists():
                Question.objects.bulk_create([
                    Question(assessment=a, question_text=q, option_a=oa, option_b=ob, option_c=oc, option_d=od,
                             correct_option=c, marks=Decimal("1")) for q, oa, ob, oc, od, c in questions])
            if a.status != Assessment.Status.ACTIVE:
                a.status = Assessment.Status.ACTIVE
                a.save(update_fields=["status"])

        password = os.environ.get("ELIGO_DEMO_PASSWORD", DEFAULT_PASSWORD)
        vocab = skill_vocab()
        accounts = []
        for key, p in DEMO_PROFILES.items():
            email = f"demo.{key}@eligo.local"
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email=email, password=password, name=p.label, mobile_number="9000000000")
            skills, _unknown = parse_skills_input(p.skills, vocab)
            StudentProfile.objects.update_or_create(student=user, defaults=dict(
                qualification=p.qualification, specialization=p.specialization, college_name=p.college_name,
                academic_percentage=p.academic_percentage, skills=skills, career_skills=sorted(p.career_skills),
                career_interests=p.interests, preferred_job_role=p.preferred_role,
                preferred_location=p.preferred_location))
            accounts.append((email, p.label))

        self.stdout.write(self.style.SUCCESS("DEMO data ready (illustrative, not real users or training data):"))
        for email, label in accounts:
            self.stdout.write(f"  {email:28}  {label}")
        self.stdout.write(f"  password for all DEMO students: {password}")
        self.stdout.write("  DEMO assessments: " + "; ".join(name for name, *_ in ASSESSMENTS))
