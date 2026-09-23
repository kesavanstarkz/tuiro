from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import sys

# Support the documented `python scripts/seed.py` command as well as
# `python -m scripts.seed`. Python otherwise sets sys.path to scripts/.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import ClassGroup, ClassStudent, ClassTeacher, Organization, OrganizationMember, Parent, Role, ScheduleEntry, Student, StudentFee, Subscription, SubscriptionPlan, Teacher, User


def seed() -> None:
    db = SessionLocal()
    try:
        organization = db.scalar(select(Organization).where(Organization.name == "Tuiro Development Centre"))
        if organization:
            # Earlier development seeds used a .local address. EmailStr rejects
            # that reserved domain at the API boundary, making login impossible.
            owner = db.scalar(select(User).where(User.email == "owner@tuiro.local"))
            if owner:
                owner.email = "owner@tuiro.example.com"
                db.commit()
                print("Updated development owner email: owner@tuiro.example.com / tuiro-development")
            else:
                print("Development seed already exists: owner@tuiro.example.com / tuiro-development")
            return
        organization = Organization(name="Tuiro Development Centre", country_code="IN", currency_code="INR", timezone="Asia/Kolkata")
        owner = User(email="owner@tuiro.example.com", password_hash=hash_password("tuiro-development"), display_name="Tuiro Owner")
        db.add_all([organization, owner]); db.flush()
        db.add(OrganizationMember(organization_id=organization.id, user_id=owner.id, role=Role.OWNER.value))
        plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.name == "FREE"))
        if plan is None:
            plan = SubscriptionPlan(name="FREE", student_limit=20, features="{}")
            db.add(plan); db.flush()
        db.add(Subscription(organization_id=organization.id, plan_id=plan.id, status="TRIAL"))
        parent = Parent(organization_id=organization.id, name="Development Guardian", phone="+10000000000", relationship="Parent")
        teacher = Teacher(organization_id=organization.id, employee_number="DEV-001", specialization="General Studies")
        class_group = ClassGroup(organization_id=organization.id, name="Foundation Group", subject="General Studies", description="Development seed class", fee_amount=Decimal("1500"))
        db.add_all([parent, teacher, class_group]); db.flush()
        students = [Student(organization_id=organization.id, student_number=f"DEV-{index:03d}", first_name=f"Student {index}", last_name="Demo", grade="Level 1") for index in range(1, 6)]
        db.add_all(students); db.flush()
        for student in students:
            db.add(ClassStudent(organization_id=organization.id, class_id=class_group.id, student_id=student.id))
        db.add(ClassTeacher(organization_id=organization.id, class_id=class_group.id, teacher_id=teacher.id, is_primary=True))
        db.add(ScheduleEntry(organization_id=organization.id, class_id=class_group.id, teacher_id=teacher.id, day_of_week=date.today().weekday(), start_time="16:00", end_time="17:00", room="Development Room"))
        for student in students:
            db.add(StudentFee(organization_id=organization.id, student_id=student.id, billing_period=date.today().strftime("%Y-%m"), amount=Decimal("1500"), amount_due=Decimal("1500"), due_date=date.today() + timedelta(days=7), status="DUE"))
        db.commit()
        print("Seeded development organization: owner@tuiro.example.com / tuiro-development")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
