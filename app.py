import os
import requests
from flask import Flask, render_template, request, jsonify

# Try to load the key from a local file (not committed to GitHub)
try:
    from config_local import GROQ_API
except ImportError:
    GROQ_API = os.getenv("GROQ_API")

if not GROQ_API:
    raise RuntimeError(
        "No API key found. Set it in config_local.py or as env var GROQ_API."
    )

# Adjust folders if your structure is different
app = Flask(
    __name__,
    CORS(app)
)


@app.route("/informationhiding")
def informationhiding():
    """
    Serve the main page.
    Make sure you have templates/Manual-Hiding-Groq.html.
    """
    return render_template("Manual-Hiding-Groq.html")


@app.route("/walkfree", methods=["POST"])
def walkfree():
    return render_template('Manual-Hiding-Groq.html')


if __name__ == "__main__":
    port=int(os.inviron.get('PORT',5000))
    app.run(debug=True, host='0.0.0.0', port=port)
