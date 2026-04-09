"""
Pest Shield — optional vision API (OpenRouter-compatible).
POST /analyze-pest with an image; returns pest name, analysis, suggestions.

Run:
  pip install -r requirements_api.txt
  uvicorn main:app --reload --host 0.0.0.0 --port 8000

.env:
  OPENROUTER_API_KEY=sk-or-...
  # optional: PEST_VISION_MODEL=openai/gpt-4o-mini
"""

from __future__ import annotations

import base64
import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

MODEL = os.getenv("PEST_VISION_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


def _get_client() -> OpenAI:
    key = os.getenv("OPENROUTER_API_KEY") or os.getenv("CHRISKEY")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Set OPENROUTER_API_KEY (or CHRISKEY) in .env.",
        )
    return OpenAI(base_url=OPENROUTER_BASE, api_key=key)


app = FastAPI(title="Pest Shield API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_origins=["*"],
)


class PestAnalysisResponse(BaseModel):
    pest: str = Field(..., description="Likely pest or category")
    analysis: str = Field(..., description="What is visible")
    suggestions: str = Field(..., description="IPM-style actions")


def _encode_image(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def _analyze_pest_image(image_base64: str) -> str:
    system = """You are an agricultural extension assistant for smallholder farmers in Ghana and similar climates.
The user sends a photo that may show an insect, mite, slug, snail, larva, or pest damage on crops.

Respond in exactly three sections separated by the line ---SECTION---
Section 1 (one short line): most likely pest.
IMPORTANT: If there is no clear evidence of a pest (or image is non-crop / random object / too blurry), output exactly:
Not a pest / unclear image
Section 2 (2–5 sentences): visible signs; note uncertainty.
Section 3: practical suggestions — cultural/mechanical first; involve extension when needed; avoid specific pesticide brands unless essential.

Crops and pests only — not human medical advice."""

    user_text = (
        "Identify the pest or damage. Our app labels often include: ants, bees, beetle, "
        "catterpillar, earthworms, earwig, grasshopper, moth, slug, snail, wasp, weevil — "
        "pick the best match from the image even if not in this list."
    )

    cli = _get_client()
    rsp = cli.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            },
        ],
        temperature=0.2,
        max_tokens=900,
    )
    return rsp.choices[0].message.content or ""


def _split_sections(raw: str) -> tuple[str, str, str]:
    parts = re.split(r"\s*---SECTION---\s*", raw.strip(), maxsplit=2)
    if len(parts) >= 3:
        return parts[0].strip(), parts[1].strip(), parts[2].strip()
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        return paragraphs[0], paragraphs[1], paragraphs[2]
    if len(paragraphs) == 2:
        return paragraphs[0], paragraphs[1], "Consult your agriculture extension agent for confirmation."
    if len(paragraphs) == 1:
        return "Analysis", paragraphs[0], "Verify in the field with extension support."
    return "Uncertain", raw.strip() or "No content", "Retake a closer, well-lit photo."


def _normalize_non_pest_response(
    pest: str, analysis: str, suggestions: str
) -> tuple[str, str, str]:
    text = f"{pest} {analysis}".lower()
    non_pest_markers = [
        "not a pest",
        "unclear",
        "no visible pest",
        "no pest",
        "cannot identify",
        "insufficient detail",
        "blurry",
        "out of focus",
        "non-crop",
    ]
    if any(marker in text for marker in non_pest_markers):
        return (
            "Not a pest / unclear image",
            analysis,
            "Retake the photo closer to the insect or damaged leaf in good daylight. "
            "If symptoms persist, consult a local extension officer for confirmation.",
        )
    return pest, analysis, suggestions


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL}


@app.post("/analyze-pest", response_model=PestAnalysisResponse)
async def analyze_pest(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Expected an image file.")

    image_data = await file.read()
    if len(image_data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 15 MB).")

    try:
        full = _analyze_pest_image(_encode_image(image_data))
        pest, analysis, suggestions = _split_sections(full)
        pest, analysis, suggestions = _normalize_non_pest_response(
            pest, analysis, suggestions
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vision model error: {e!s}") from e

    return JSONResponse(content={"pest": pest, "analysis": analysis, "suggestions": suggestions})
