from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import appointments, auth, health, invoices, owners, pets, reminders
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(owners.router, prefix="/api/owners", tags=["owners"])
app.include_router(pets.router, prefix="/api/pets", tags=["pets"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["reminders"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
