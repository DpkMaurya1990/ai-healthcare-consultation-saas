import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLERK_JWKS_URL", "https://example.com/.well-known/jwks.json")

from pydantic import ValidationError

from main import Visit


class VisitValidationTests(unittest.TestCase):
    def test_visit_rejects_oversized_notes(self) -> None:
        with self.assertRaises(ValidationError):
            Visit(
                patient_name="Asha",
                sender_name="Dr. Sharma Clinic",
                date_of_visit="2026-07-26",
                notes="x" * 10001,
            )


if __name__ == "__main__":
    unittest.main()
