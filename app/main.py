import os
from flask import Flask
from dotenv import load_dotenv

# Load local .env if present (no-op in Codespaces where secrets are injected)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = Flask(__name__)

@app.route("/")
def home():
    openai_key = os.getenv("OPENAI_API_KEY", "<unset>")
    jwt_secret = os.getenv("JWT_SECRET", "<unset>")
    # DO NOT print secrets in real apps; this is just a health hint
    return (
        "Hello from Codespaces / Local! "
        f"OPENAI_API_KEY set: {openai_key != '<unset>'}, "
        f"JWT_SECRET set: {jwt_secret != '<unset>'}"
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)

