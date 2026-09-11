"""Generate the VAPID keypair that identifies this server to Apple and Google.

VAPID is the whole identity story for Web Push. There is no App Store account, no Apple
developer program and no Firebase project: you generate a P-256 keypair yourself, the
public half goes to the browser when a device subscribes, and the private half signs a
JWT on every send. The push service checks the signature against the key the device was
subscribed with, and that is the entire trust chain.

Run this ONCE for the project. Rotating the keypair invalidates every existing
subscription, silently, so a rotation means every phone has to toggle reminders off and
on again.

    python scripts/vapid_keys.py

It prints the two lines to add to .env and the one to add to the GitHub repo secrets. It
writes nothing itself, on purpose: a private key that a script drops on disk is a private
key that gets committed by accident one day.
"""
from __future__ import annotations

import base64
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64(raw: bytes) -> str:
    """base64url with no padding, which is the only encoding Web Push accepts."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate() -> tuple[str, str]:
    """Return (public, private) as base64url strings.

    The public key is the uncompressed P-256 point, 65 bytes starting with 0x04, which is
    the form `pushManager.subscribe` expects in applicationServerKey. The private key is
    the 32 byte scalar, which is what pywebpush wants.
    """
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    private = key.private_numbers().private_value.to_bytes(32, "big")
    return b64(public), b64(private)


def main() -> int:
    public, private = generate()

    # Checked rather than assumed: a 65 byte point starting 0x04 is the only thing
    # Safari accepts, and a wrong length fails at subscribe() time on the phone with an
    # error nobody can read.
    raw = base64.urlsafe_b64decode(public + "=" * (-len(public) % 4))
    assert len(raw) == 65 and raw[0] == 0x04, "public key is not an uncompressed P-256 point"

    print("Add to .env (never commit it):\n")
    print("VAPID_PUBLIC_KEY=%s" % public)
    print("VAPID_PRIVATE_KEY=%s" % private)
    print("VAPID_SUBJECT=mailto:gdmotley1@gmail.com")
    print("\nAdd to .env as well, so the client bundle can see the PUBLIC half:\n")
    print("VITE_VAPID_PUBLIC_KEY=%s" % public)
    print("\nThe public key is not a secret: it ships in the browser bundle by design,")
    print("exactly like the anon key. Only VAPID_PRIVATE_KEY must stay out of the repo.")
    print("\nFor the sender running in GitHub Actions or Supabase, set the same three")
    print("VAPID_* values as secrets there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
