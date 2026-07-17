import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
from fastapi import APIRouter

api_router = APIRouter()

# Add CORS middleware (allows frontend to call backend)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clerk authentication setup
clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)

class Visit(BaseModel):
    patient_name: str
    date_of_visit: str
    notes: str

system_prompt = """
You are provided with notes written by a doctor from a patient's visit.
Your job is to summarize the visit for the doctor and provide an email.
Reply with exactly three sections with the headings:
### Summary of visit for the doctor's records
### Next steps for the doctor
### Draft of email to patient in patient-friendly language

If the notes mention specific measurements or standard clinical details (such as
blood pressure, temperature, weight, height, age, pulse, or other vitals), include
those same values in the "Draft of email to patient" section as well, phrased in
plain, patient-friendly language with brief context (for example: "your blood
pressure was 120/80, which is within the normal range" rather than just "BP 120/80").
Do not omit vitals from the patient email only because they appear in the doctor's
summary. Only mention a measurement in the "Next steps" section if it is directly
relevant to what the patient or doctor needs to monitor or act on going forward.
"""

def user_prompt_for(visit: Visit) -> str:
    return f"""Create the summary, next steps and draft email for:
Patient Name: {visit.patient_name}
Date of Visit: {visit.date_of_visit}
Notes:
{visit.notes}"""

# NEW CODE:
@api_router.post("/consultation")
def consultation_summary(
    visit: Visit,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    user_id = creds.decoded["sub"]

    ai_provider = os.getenv("AI_PROVIDER", "openai")  # "openai" or "groq"

    if ai_provider == "groq":
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    else:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_name = "gpt-5-nano"

    user_prompt = user_prompt_for(visit)
    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    stream = client.chat.completions.create(
        model=model_name,
        messages=prompt,
        stream=True,
    )
    
    def event_stream():
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                lines = text.split("\n")
                for line in lines[:-1]:
                    yield f"data: {line}\n\n"
                    yield "data:  \n"
                yield f"data: {lines[-1]}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/health")
def health_check():
    """Health check endpoint for AWS App Runner"""
    return {"status": "healthy"}


# ✅ ALWAYS include router (outside condition)
app.include_router(api_router, prefix="/api/v1")

static_path = Path("static")

# Serve static files (Next.js export) - MUST BE LAST!
if static_path.exists():
    app.mount("/_next", StaticFiles(directory=static_path / "_next"), name="next")
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/")
    async def serve_root():
        return FileResponse(static_path / "index.html")
    
    # 👇 ADD THIS — catch-all for all other frontend pages (product, pricing, etc.)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Try exact matching .html file first (e.g. /product -> product.html)
        html_file = static_path / f"{full_path}.html"
        if html_file.exists():
            return FileResponse(html_file)

        # Fallback: maybe it's a folder-style export (e.g. /product/index.html)
        folder_index = static_path / full_path / "index.html"
        if folder_index.exists():
            return FileResponse(folder_index)

        # Nothing matched — genuine 404
        return JSONResponse(status_code=404, content={"detail": "Page not found"})