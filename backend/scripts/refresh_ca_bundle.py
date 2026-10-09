"""Build a project CA bundle from certifi and the OS's existing trusted CAs."""
import argparse
import json
import re
import ssl
from pathlib import Path

import certifi

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configure-env", action="store_true",
                        help="Set REQUESTS_CA_BUNDLE in this project's .env")
    args = parser.parse_args()
    destination = PROJECT_ROOT / "logs" / "requests-ca-bundle.pem"
    destination.parent.mkdir(parents=True, exist_ok=True)
    certificates = set(ssl.create_default_context().get_ca_certs(binary_form=True))
    if not certificates:
        raise RuntimeError("No OS-trusted CA certificates are available")
    pem = Path(certifi.where()).read_text(encoding="ascii")
    pem += "\n# Additional certificate authorities already trusted by this OS\n"
    pem += "".join(ssl.DER_cert_to_PEM_cert(der) for der in sorted(certificates))
    # Validate the completed bundle before configuring the application to use it.
    ssl.create_default_context(cafile=None, cadata=pem)
    destination.write_text(pem, encoding="ascii")
    if args.configure_env:
        env_path = PROJECT_ROOT / ".env"
        original = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        setting = f"REQUESTS_CA_BUNDLE='{destination.as_posix()}'"
        if re.search(r"^REQUESTS_CA_BUNDLE\s*=.*$", original, re.MULTILINE):
            updated = re.sub(r"^REQUESTS_CA_BUNDLE\s*=.*$", lambda _: setting, original, flags=re.MULTILINE)
        else:
            updated = original.rstrip() + "\n\n# Use the OS-trusted CA bundle for HTTPS (verification remains enabled)\n" + setting + "\n"
        env_path.write_text(updated, encoding="utf-8")
    print(json.dumps({"ca_bundle": str(destination), "os_ca_count": len(certificates),
                      "configured_env": args.configure_env}))


if __name__ == "__main__":
    main()
