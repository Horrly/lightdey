from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid01, b64urlencode


class Command(BaseCommand):
    help = "Generate a VAPID key pair for web push notifications."

    def handle(self, *args, **options):
        vapid = Vapid01()
        vapid.generate_keys()
        private = b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, "big"))
        public = b64urlencode(
            vapid.public_key.public_bytes(
                serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
            )
        )
        self.stdout.write("Add these as environment variables (keep the private key secret):\n")
        self.stdout.write(f"VAPID_PUBLIC_KEY={public}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private}")
