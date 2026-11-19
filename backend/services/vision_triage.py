import os
from typing import Literal
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured in .env. Please add a valid Gemini API key.")
    return genai.Client(api_key=api_key)


class TriageResult(BaseModel):
    is_valid_civic_issue: bool = Field(
        description="True ONLY if the photograph depicts a genuine outdoor urban infrastructure, sanitation, water, or electrical hazard."
    )
    department_code: Literal["ROADS", "WASTE", "WATER", "EMERGENCY"] = Field(
        description="Responsible municipal department code."
    )
    issue_subcategory: str = Field(
        description="Concise issue label, e.g., Deep Pothole, Garbage Overflow, Water Main Burst, Exposed Live Wire."
    )
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="CRITICAL for life-safety hazards (fallen electrical wires, open manholes, severe flooding); HIGH for major traffic/water disruption; MEDIUM/LOW otherwise."
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence between 0 and 1.")
    reasoning: str = Field(description="One-sentence visual inspection summary.")


def analyze_grievance_image(image_bytes: bytes, mime_type: str, user_note: str) -> TriageResult:
    gemini = get_gemini_client()
    prompt = (
        "You are an automated municipal 311 multimodal triage inspector. "
        "Inspect the uploaded citizen photograph alongside their description. "
        "1. Reject selfies, indoor scenes, memes, or blurry/unrelated photos by setting is_valid_civic_issue=false. "
        "2. Map valid issues to ROADS, WASTE, WATER, or EMERGENCY. "
        "3. Escalate exposed electrical wires, open manholes, collapsed roads, or severe flooding as CRITICAL.\n"
        f"Citizen Description: {user_note}"
    )

    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TriageResult,
            temperature=0.1,
        ),
    )
    return TriageResult.model_validate_json(response.text)
