
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["lmstudio", "groq"], default=None,
                         help="override LLM_PROVIDER from .env for this run")
    args = parser.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    from app import config
    from app.services import llm_client

    print(f"Provider : {config.LLM_PROVIDER}")
    info = llm_client.current_provider_info()
    print(f"Endpoint : {info['endpoint']}")
    print(f"Model    : {info['model']}")
    print("Sending test prompt...")

    result = llm_client.test_connection()
    if result["ok"]:
        print(f"OK - reply: {result['reply']}")
    else:
        print(f"FAILED: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
