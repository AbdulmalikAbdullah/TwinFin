"""Twin   Flask API.

Every endpoint is wrapped so that a failure anywhere (Groq down, embeddings missing, a
malformed request) returns a friendly JSON payload the UI can render as a message. The
demo must never show a stack trace or a blank screen.
"""

from __future__ import annotations

import logging
import traceback

from flask import Flask, jsonify, request
from flask_cors import CORS

import i18n
import llm
import rag
import router
from config import GROQ_MODEL
from i18n import t
from simulation import baseline_timeline, health_breakdown
from twin_profile import load_profile

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s"
)
log = logging.getLogger("twin")

app = Flask(__name__)
CORS(app)

# The Financial Twin is parsed once at startup. If this fails the app is unusable, so we
# fail loudly here rather than mysteriously on the first request.
PROFILE = load_profile()
log.info(
    "Financial Twin loaded: %s, %s | savings %s SAR | surplus %s SAR/month",
    PROFILE.name,
    PROFILE.city,
    f"{PROFILE.savings:,.0f}",
    f"{PROFILE.monthly_surplus:,.0f}",
)


def req_lang() -> str:
    """The language for this request: ?lang=ar, a JSON `lang` field, or Accept-Language.

    Anything unrecognised falls back to English rather than erroring   a bad language code
    should never cost the user their answer.
    """
    candidate = request.args.get("lang")
    if not candidate and request.is_json:
        body = request.get_json(silent=True) or {}
        candidate = body.get("lang")
    if not candidate:
        candidate = (request.headers.get("Accept-Language") or "")[:2]
    return i18n.normalize(candidate)


def fail(message: str, status: int = 500, **extra):
    """The only error shape this API emits. The UI renders `error` as a friendly notice."""
    payload = {"error": message, "intent": None, "answer": None,
               "scenarios": [], "timeline": [], "alert": None, "sources": [], **extra}
    return jsonify(payload), status


@app.errorhandler(Exception)
def handle_unexpected(exc: Exception):
    """Last line of defence: nothing escapes as HTML or a stack trace."""
    log.error("Unhandled error: %s\n%s", exc, traceback.format_exc())
    # Even the language lookup is defended: a broken request must still get a message.
    try:
        lang = req_lang()
    except Exception:  # noqa: BLE001
        lang = "en"
    return fail(t("err.generic", lang), 500)


@app.get("/api/health")
def health():
    """Startup diagnostics. Handy for checking the demo box before you walk on stage."""
    _, embed_backend = rag.get_embeddings()
    ingested = rag.is_ingested()
    return jsonify(
        {
            "status": "ok",
            "profile": PROFILE.name,
            "llm": {
                "configured": llm.is_configured(),
                "model": GROQ_MODEL if llm.is_configured() else None,
                # Without a Groq key the app still works: rule-based routing and the
                # template writer take over. Numbers are unaffected either way.
                "mode": "groq" if llm.is_configured() else "deterministic-fallback",
            },
            "rag": {"embeddings": embed_backend, "ingested": ingested},
            "languages": list(i18n.LANGS),
        }
    )


@app.get("/api/profile")
def get_profile():
    """The Financial Twin plus the health score and its four components."""
    lang = req_lang()
    try:
        return jsonify(
            {
                "profile": PROFILE.to_dict(lang),
                "health": health_breakdown(PROFILE, lang),
                "lang": lang,
                "dir": "rtl" if i18n.is_rtl(lang) else "ltr",
            }
        )
    except Exception as exc:  # noqa: BLE001
        log.error("profile failed: %s", exc, exc_info=True)
        return fail(t("err.profile", lang))


@app.get("/api/timeline")
def get_timeline():
    """The baseline 12-month projection for the dashboard chart."""
    lang = req_lang()
    try:
        rows = baseline_timeline(PROFILE, lang=lang)
        return jsonify(
            {
                "timeline": [
                    {
                        "month": r.month,
                        "income": r.income,
                        "expenses": r.expenses,
                        "purchase": r.purchase,
                        "savings": r.savings,
                        "warnings": r.warnings,
                        "events": r.events,
                    }
                    for r in rows
                ],
                "emergency_fund_target": PROFILE.emergency_fund_target,
                "lang": lang,
            }
        )
    except Exception as exc:  # noqa: BLE001
        log.error("timeline failed: %s", exc, exc_info=True)
        return fail(t("err.timeline", lang))


@app.post("/api/chat")
def chat():
    """Classify -> simulate -> retrieve -> answer."""
    try:
        body = request.get_json(silent=True) or {}
    except Exception:  # noqa: BLE001
        body = {}

    lang = req_lang()
    message = str(body.get("message", "")).strip()
    history = body.get("history") or []
    if not isinstance(history, list):
        history = []

    if not message:
        return fail(t("err.empty", lang), 400)
    if len(message) > 2000:
        return fail(t("err.too_long", lang), 400)

    try:
        response = router.handle(PROFILE, message, history, lang)
        response["lang"] = lang
        return jsonify(response)
    except Exception as exc:  # noqa: BLE001
        log.error("chat failed: %s", exc, exc_info=True)
        # Even total failure gets a useful, honest reply rather than a broken UI.
        return fail(t("err.chat", lang))


if __name__ == "__main__":
    if not rag.is_ingested():
        log.warning("")
        log.warning("  The knowledge base has not been ingested yet.")
        log.warning("  Run:  python backend/ingest.py")
        log.warning("  Answers will still work, but they won't cite sources.")
        log.warning("")
    if not llm.is_configured():
        log.warning("")
        log.warning("  No GROQ_API_KEY found   running in deterministic fallback mode.")
        log.warning("  Every number is still correct; the prose is templated, not written.")
        log.warning("  Add your key to .env to enable the language model.")
        log.warning("")

    # app.run(host="127.0.0.1", port=5000, debug=False)
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
