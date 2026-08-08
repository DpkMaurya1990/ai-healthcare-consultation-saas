import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as consultation_main


class ConsultationSSEIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        consultation_main.app.dependency_overrides.clear()

    def tearDown(self) -> None:
        consultation_main.app.dependency_overrides.clear()

    def test_consultation_endpoint_streams_personalized_email(self) -> None:
        class DummyCreds:
            def __init__(self) -> None:
                self.decoded = {"sub": "test-user"}

        def override_clerk() -> DummyCreds:
            return DummyCreds()

        consultation_main.app.dependency_overrides[consultation_main.clerk_guard] = override_clerk

        class FakeChunk:
            def __init__(self, content: str) -> None:
                self.choices = [type("Choice", (), {"delta": type("Delta", (), {"content": content})()})()]

        class FakeCompletions:
            def create(self, model: str, messages: list[dict], stream: bool):
                return iter([
                    FakeChunk("### Draft of email to patient\n"),
                    FakeChunk("Dear [PATIENT_NAME],\n"),
                    FakeChunk("Thanks,\n"),
                    FakeChunk("[Your Name]\n"),
                ])

        class FakeChat:
            def __init__(self) -> None:
                self.completions = FakeCompletions()

        class FakeOpenAI:
            def __init__(self, *args, **kwargs) -> None:
                self.chat = FakeChat()

        with patch.object(consultation_main, "OpenAI", FakeOpenAI):
            with consultation_main.app.test_client() as client:
                response = client.post(
                    "/api/v1/consultation",
                    json={
                        "patient_name": "",
                        "sender_name": "Dr. Sharma Clinic",
                        "date_of_visit": "2026-07-26",
                        "notes": "Patient reported mild fever and fatigue.",
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"].startswith("text/event-stream"), True)

        body = response.text
        self.assertIn("Hello,", body)
        self.assertIn("Dr. Sharma Clinic", body)
        self.assertNotIn("Dear ,", body)


if __name__ == "__main__":
    unittest.main()
