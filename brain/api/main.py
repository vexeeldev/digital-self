from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import experiences, memory, reasoning, decisions, outcomes, corrections

app = FastAPI(
    title="Digital Self API",
    description="Digital Self Cognitive Architecture API Layer",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiences.router)
app.include_router(memory.router)
app.include_router(reasoning.router)
app.include_router(decisions.router)
app.include_router(outcomes.router)
app.include_router(corrections.router)
