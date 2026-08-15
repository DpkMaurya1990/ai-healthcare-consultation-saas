import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pii_redaction import PIIRedactor, PLACEHOLDER_TOKEN


class PIIRedactorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.redactor = PIIRedactor()

    def test_prepare_for_llm_masks_patient_name_and_redacts_contact_info(self) -> None:
        notes = "Patient Ravi Sharma called from 9876543210 and wrote ravi@example.com"
        prepared = self.redactor.prepare_for_llm(notes, "Ravi Sharma")

        self.assertIn(PLACEHOLDER_TOKEN, prepared)
        self.assertNotIn("Ravi Sharma", prepared)
        self.assertIn("[REDACTED_PHONE]", prepared)
        self.assertIn("[REDACTED_EMAIL]", prepared)

    def test_restore_in_chunks_replaces_placeholder_across_chunks(self) -> None:
        chunks = ["Hello ", "[PAT", "IENT_NAME]!"]
        restored = list(self.redactor.restore_in_chunks(iter(chunks), "Asha"))

        self.assertEqual("".join(restored), "Hello Asha!")

    def test_restore_in_chunks_replaces_variant_placeholder(self) -> None:
        chunks = ["Dear [patient_", "name], thank you."]
        restored = list(self.redactor.restore_in_chunks(iter(chunks), "Asha"))

        self.assertEqual("".join(restored), "Dear Asha, thank you.")

    def test_personalize_signature_replaces_generic_placeholder(self) -> None:
        text = "Thanks,\n[Your Name]"
        personalized = self.redactor.personalize_signature(text, "Dr. Sharma Clinic")

        self.assertIn("Dr. Sharma Clinic", personalized)
        self.assertNotIn("[Your Name]", personalized)

    def test_personalize_signature_appends_professional_signoff_when_missing(self) -> None:
        text = "Hello,\nThanks for your visit."
        personalized = self.redactor.personalize_signature(text, "Dr. Sharma Clinic")

        self.assertIn("Best regards,", personalized)
        self.assertIn("Dr. Sharma Clinic", personalized)

    def test_personalize_salutation_replaces_generic_greeting(self) -> None:
        text = "Hello, thank you for your visit."
        personalized = self.redactor.personalize_salutation(text, "Suraj")

        self.assertTrue(personalized.startswith("Hello Suraj,"))

        text = "Dear Patient, we have your report."
        personalized = self.redactor.personalize_salutation(text, "Suraj")

        self.assertTrue(personalized.startswith("Hello Suraj,"))

    def test_personalize_salutation_uses_hello_when_name_missing(self) -> None:
        text = "Dear , thank you for your visit."
        personalized = self.redactor.personalize_salutation(text, "")

        self.assertTrue(personalized.startswith("Hello,"))

        text = "Hello, thank you for your visit."
        personalized = self.redactor.personalize_salutation(text, "")

        self.assertTrue(personalized.startswith("Hello,"))

    def test_personalize_salutation_replaces_greeting_after_heading(self) -> None:
        text = "### Draft of email to patient\nDear Patient, thank you for your visit."
        personalized = self.redactor.personalize_salutation(text, "")

        self.assertIn("Hello,", personalized)
        self.assertNotIn("Dear Patient,", personalized)

    def test_normalize_email_greeting_forces_hello_style(self) -> None:
        text = "Dear Suraj, thank you for your visit."
        normalized = self.redactor.normalize_email_greeting(text, "Suraj")

        self.assertEqual(normalized, "Hello Suraj, thank you for your visit.")

        text = "Dear, thank you for your visit."
        normalized = self.redactor.normalize_email_greeting(text, "")

        self.assertEqual(normalized, "Hello, thank you for your visit.")

    def test_normalize_email_greeting_inserts_greeting_when_absent(self) -> None:
        text = "### Draft of email to patient\nThanks for your visit."
        normalized = self.redactor.normalize_email_greeting(text, "")

        self.assertIn("### Draft of email to patient", normalized)
        self.assertIn("Hello,", normalized)
        self.assertIn("Thanks for your visit.", normalized)

    def test_prepare_email_payload_creates_subject_and_body(self) -> None:
        text = "### Draft of email to patient\nHello,\nThanks for your visit."
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertEqual(payload["subject"], "Follow-up from your recent visit")
        self.assertIn("Hello Suraj,", payload["body"])
        self.assertIn("Thank you for visiting us today.", payload["body"])

    def test_prepare_email_payload_polishes_body_language(self) -> None:
        text = "### Draft of email to patient\nHello,\nThanks for your visit.\nPlease follow up with us."
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("Thank you for visiting us today.", payload["body"])
        self.assertIn("Please let us know if you have any questions.", payload["body"])

    def test_prepare_email_payload_refines_opening_sentence(self) -> None:
        text = "### Draft of email to patient\nHello,\nThank you for your visit today."
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("Thank you for visiting us today.", payload["body"])

    def test_prepare_email_payload_polishes_closing_paragraph(self) -> None:
        text = "### Draft of email to patient\nHello,\nPlease follow up with us."
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("Please let us know if you have any questions.", payload["body"])

    def test_prepare_email_payload_strips_full_heading_variant(self) -> None:
        text = "### Draft of email to patient in patient-friendly language\nHello Suraj,\nThanks for your visit."
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("Hello Suraj,", payload["body"])
        self.assertNotIn("### Draft of email to patient in patient-friendly language", payload["body"])
        self.assertIn("Thank you for visiting us today.", payload["body"])

    def test_prepare_email_payload_uses_shorter_follow_up_phrase(self) -> None:
        text = "### Draft of email to patient\nHello,\nFeel free to reach out if needed."
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("Please let us know if you have any questions.", payload["body"])

    def test_prepare_email_payload_cleans_repeated_name_and_follow_up_fragment(self) -> None:
        text = (
            "### Draft of email to patient in patient-friendly language\n"
            "Hello Suraj,Suraj,Suraj,Suraj,\n"
            "your blood pressure was 120/80, which is within the normal range. "
            "Please let us know if you have any questions. "
            "We will review you again in a few days if needed. if your fever persists."
        )
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("Hello Suraj,", payload["body"])
        self.assertNotIn("Hello Suraj,Suraj", payload["body"])
        self.assertIn(
            "We will review you again in a few days if your fever persists.",
            payload["body"],
        )

    def test_prepare_email_payload_formats_signature_on_own_lines(self) -> None:
        text = (
            "### Draft of email to patient\n"
            "Hello Suraj,\n"
            "Please let us know if you have any questions. Best regards, Dr. Sharma Clinic"
        )
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("\n\nBest regards,\nDr. Sharma Clinic", payload["body"])

    def test_prepare_email_payload_strips_leaked_subject_from_body(self) -> None:
        text = (
            "Subject: Follow-up from your recent visit, Suraj\n"
            "Hello Suraj,\n"
            "Thanks for your visit."
        )
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertNotIn("Subject:", payload["body"])
        self.assertIn("Hello Suraj,", payload["body"])

    def test_prepare_email_payload_fixes_after_three_days_phrase(self) -> None:
        text = (
            "### Draft of email to patient\n"
            "Hello Suraj,\n"
            "Please let us know if you have any questions. after 3 days if your fever persists."
        )
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn(
            "If your fever persists after 3 days, please schedule a follow-up visit with us.",
            payload["body"],
        )

    def test_prepare_email_payload_capitalizes_opening_and_adds_paragraph_breaks(self) -> None:
        text = (
            "### Draft of email to patient\n"
            "Hello Suraj,\n"
            "your blood pressure was normal. As discussed during your visit, continue rest. Please let us know if you have any questions. If your fever persists, schedule follow-up."
        )
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("\nYour blood pressure was normal.", payload["body"])
        self.assertIn("\n\nAs discussed", payload["body"])
        self.assertIn("\n\nPlease let us know if you have any questions.", payload["body"])

    def test_prepare_email_payload_adds_spacing_after_dash_lines(self) -> None:
        text = (
            "### Draft of email to patient\n"
            "Hello Suraj,\n"
            "- Rest well\n"
            "Please let us know if you have any questions."
        )
        payload = self.redactor.prepare_email_payload(text, "Suraj")

        self.assertIn("- Rest well\n\nPlease let us know if you have any questions.", payload["body"])


if __name__ == "__main__":
    unittest.main()
