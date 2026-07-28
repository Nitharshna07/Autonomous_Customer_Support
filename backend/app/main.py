from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models import User
from app.auth import hash_password
from app.router_auth import router as auth_router
from app.router_chat import router as chat_router
from app.router_kb import router as kb_router
from app.router_admin import router as admin_router

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

def seed_admin():
    db = SessionLocal()
    try:
        admin_email = "admin@supportcopilot.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            # Hash password with bcrypt
            hashed_pwd = hash_password("AdminPassword123!")
            new_admin = User(
                email=admin_email,
                hashed_password=hashed_pwd,
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            print("Successfully seeded admin user.")
    except Exception as e:
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

seed_admin()

app = FastAPI(
    title="Autonomous Customer Support Copilot API",
    description="Full-stack AI Customer Support Copilot with Intent Detection, RAG, and Auto-Escalation",
    version="1.0.0"
)

# Configure CORS for local dev frontend & production hosts
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://autonomous-customer-support-copilot.netlify.app",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(kb_router)
app.include_router(admin_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Autonomous Customer Support Copilot Backend",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
