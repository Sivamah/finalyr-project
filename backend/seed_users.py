import sys
sys.path.append('backend')
from app.db.database import SessionLocal
from app.db.models import User
from app.core.security import get_password_hash

db = SessionLocal()

for role, email in [("Customer", "customer@aiorch.com"), ("Driver", "driver@aiorch.com")]:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            email=email,
            full_name=f"Test {role}",
            password_hash=get_password_hash("password123"),
            role=role,
        )
        db.add(u)
        db.commit()
        print(f"Created {role} with {email}:password123")
    else:
        print(f"{role} exists")
db.close()
