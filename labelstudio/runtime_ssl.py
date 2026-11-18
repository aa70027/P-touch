"""Keep the Python runtime's certificate policy intact in standalone packages."""
from pathlib import Path
import ssl

POLICY_NAME='codex-rejected-cas.pem'

def policy_required():
    constructor=getattr(ssl.SSLContext.__new__,'__code__',None)
    return bool(constructor and POLICY_NAME in constructor.co_consts)

def required_runtime_files():
    if not policy_required():
        return []
    policy=Path(ssl.__file__).resolve().with_name(POLICY_NAME)
    if not policy.is_file():
        raise ValueError('HTTPS_RUNTIME_FILE_MISSING:'+POLICY_NAME)
    return [policy]

def verified_context():
    # This also diagnoses incomplete repair/extraction before a network attempt.
    required_runtime_files()
    return ssl.create_default_context()
