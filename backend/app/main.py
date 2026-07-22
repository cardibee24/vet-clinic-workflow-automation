from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import appointments, assistant, auth, health, invoices, knowledge, owners, pets, triage
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
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant"])
