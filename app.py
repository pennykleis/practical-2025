import os
import json
import base64
import requests
from flask import Flask, render_template, request, jsonify

# ---- Load Groq API key safely ----
try:
    from config_local import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "No Groq API key found. Set GROQ_API_KEY in config_local.py "
        "or as environment variable GROQ_API_KEY."
    )

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ---- Flask app ----
# Adjust template_folder/static_folder if your structure is different
app = Flask(
    __name__,
    template_folder=".",     # index.html is in the same folder
    static_folder="static"   # if you create a static/ folder for CSS/JS later
)


@app.route("/")
def index():
    """
    Serve the main page (your existing index.html).
    """
    return render_template("index.html")


@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    """
    Called by frontend JS: POST /api/analyze-image
    Body: { "image_base64": "<BASE64 STRING WITHOUT PREFIX>" }

    Returns: JSON object with:
        issueType, estimatedLengthMeters, estimatedBreadthMeters,
        imageTimestamp, confidenceScore, analysisNotes, faceBoxes
    """
    data = request.get_json(silent=True) or {}
    image_base64 = data.get("image_base64")

    if not image_base64:
        return jsonify({"error": "Missing field 'image_base64'"}), 400

    # Rebuild data URL for Groq (the frontend sent only the raw base64 string)
    image_data_url = f"data:image/jpeg;base64,{image_base64}"

    # Same prompts as in your frontend (copied from your JS)
    system_prompt = """
You are a pavement accessibility expert AND privacy assistant.

Return exactly ONE JSON object with the following fields:
- issueType: short description of the main pavement issue (string).
- estimatedLengthMeters: number (0 if unclear).
- estimatedBreadthMeters: number (0 if unclear).
- imageTimestamp: string timestamp if visible in the image, otherwise "null".
- confidenceScore: number from 0.0 to 1.0.
- analysisNotes: brief explanation (string).
- faceBoxes: array of bounding boxes ONLY for human faces.
  Each box is an object { "ymin": number, "xmin": number, "ymax": number, "xmax": number }
  with ALL coordinates NORMALIZED to the range [0,1] relative to image height/width.

IMPORTANT:
- Do NOT include license plates in faceBoxes.
- Do NOT mention GPS, plates, or other privacy-sensitive text, only return faceBoxes for human faces.
""".strip()

    user_prompt = """
Analyze this pavement photo.

1) Describe any accessibility issues (e.g. cracks, obstacles, blocked ramps) and give rough length and breadth in meters.
2) If any timestamp is printed in the image (e.g. camera overlay), extract it as a string.
3) Detect ALL HUMAN FACES and return tight bounding boxes around the faces as "faceBoxes" (normalized 0-1).
""".strip()

    payload = {
        "model": GROQ_VISION_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            },
        ],
    }

    try:
        resp = requests.post(
            GROQ_BASE_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
    except Exception as e:
        return jsonify({"error": f"Error contacting Groq API: {str(e)}"}), 500

    if resp.status_code != 200:
        # Forward some info for debugging (but NEVER the key)
        return jsonify({
            "error": "Groq API error",
            "status_code": resp.status_code,
            "details": resp.text,
        }), 500

    try:
        groq_data = resp.json()
        content = groq_data["choices"][0]["message"]["content"]
        # content is a JSON string; parse it to a dict
        analysis_obj = json.loads(content)
    except Exception as e:
        return jsonify({
            "error": "Failed to parse Groq response",
            "details": str(e),
        }), 500

    # ✅ Return the analysis object directly.
    # Frontend does: `aiAnalysisResult = data;` and uses the fields.
    return jsonify(analysis_obj)


if __name__ == "__main__":
    # For local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
