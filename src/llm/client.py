"""
client.py — IBM watsonx.ai Granite model wrapper.

Single public function: generate(prompt: str) -> str

If WATSONX_API_KEY is not configured, returns a stub string instead of
crashing — the app remains fully functional, just without real LLM output.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

_STUB = (
    "[watsonx.ai not configured — set WATSONX_API_KEY, WATSONX_PROJECT_ID, "
    "and WATSONX_URL in src/.env to enable AI-generated output]"
)


def _is_configured() -> bool:
    # Read at call time so .env changes take effect without restart
    key = os.getenv("WATSONX_API_KEY", "")
    pid = os.getenv("WATSONX_PROJECT_ID", "")
    return bool(
        key and key != "your_api_key_here"
        and pid and pid != "your_project_id_here"
    )


def generate(prompt: str, max_new_tokens: int = 512) -> str:
    """
    Send *prompt* to the Granite model and return the generated text.
    Returns a stub string if watsonx.ai credentials are not set.
    """
    if not _is_configured():
        return _STUB

    # Read all credentials at call time
    api_key    = os.getenv("WATSONX_API_KEY", "")
    project_id = os.getenv("WATSONX_PROJECT_ID", "")
    url        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    model_id   = os.getenv("WATSONX_MODEL_ID", "ibm/granite-13b-instruct-v2")

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

        credentials = Credentials(url=url, api_key=api_key)
        model = ModelInference(
            model_id=model_id,
            credentials=credentials,
            project_id=project_id,
            params={
                Params.MAX_NEW_TOKENS: max_new_tokens,
                Params.TEMPERATURE: 0.7,
                Params.REPETITION_PENALTY: 1.1,
            },
        )
        response = model.generate_text(prompt=prompt)
        return response.strip() if isinstance(response, str) else str(response)

    except Exception as exc:
        print(f"[llm] watsonx.ai error: {exc}", file=sys.stderr)
        return f"[LLM error: {exc}]"


# ---------------------------------------------------------------------------
# CLI self-test:  python -m llm.client --test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run connectivity test")
    args = parser.parse_args()

    if not args.test:
        parser.print_help()
        sys.exit(0)

    print("watsonx.ai connectivity test")
    print(f"  URL    : {os.getenv('WATSONX_URL', '(not set)')}")
    print(f"  Project: {os.getenv('WATSONX_PROJECT_ID', '(not set)')}")
    print(f"  Model  : {os.getenv('WATSONX_MODEL_ID', 'ibm/granite-13b-instruct-v2')}")

    if not _is_configured():
        print("\n⚠  WATSONX_API_KEY not set — will return stub responses.")
        print("   Edit src/.env and set WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL")
        sys.exit(0)

    print("\nSending test prompt...")
    result = generate("In one sentence, what is pharmacovigilance?")
    print(f"Response: {result}")
    if not result.startswith("["):
        print("\n✅ watsonx.ai LLM OK")
    else:
        print("\n⚠  Received error/stub response — check credentials")
