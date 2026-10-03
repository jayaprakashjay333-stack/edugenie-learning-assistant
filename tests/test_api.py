import os
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from errors import AIServiceError
from main import app


class EduGenieAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_database_path = os.environ.get("EDUGENIE_DB_PATH")
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["EDUGENIE_DB_PATH"] = os.path.join(
            self.temp_dir.name, "test-edugenie.sqlite3"
        )
        self.client = TestClient(app)
        self.register_response = self.client.post(
            "/auth/register",
            json={
                "email": "student@example.com",
                "display_name": "Study Student",
                "password": "a-correct-horse",
            },
        )
        self.assertEqual(self.register_response.status_code, 201)

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()
        if self.previous_database_path is None:
            os.environ.pop("EDUGENIE_DB_PATH", None)
        else:
            os.environ["EDUGENIE_DB_PATH"] = self.previous_database_path

    def test_homepage_and_health_endpoint(self) -> None:
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("EduGenie", page.text)
        self.assertIn("Study Student", page.text)
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_login_page_and_protected_home_redirect(self) -> None:
        self.client.cookies.clear()
        page = self.client.get("/login")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Create account", page.text)
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_registration_creates_session_and_rejects_duplicate_email(self) -> None:
        user = self.register_response.json()["user"]
        self.assertEqual(user["email"], "student@example.com")
        self.assertNotIn("password", user)
        self.assertIn("httponly", self.register_response.headers["set-cookie"].lower())
        connection = sqlite3.connect(os.environ["EDUGENIE_DB_PATH"])
        try:
            password_hash, password_salt = connection.execute(
                "SELECT password_hash, password_salt FROM users WHERE email = ?",
                ("student@example.com",),
            ).fetchone()
        finally:
            connection.close()
        self.assertNotEqual(password_hash, b"a-correct-horse")
        self.assertNotIn(b"a-correct-horse", password_hash)
        self.assertEqual(len(password_salt), 16)

        duplicate = self.client.post(
            "/auth/register",
            json={
                "email": "STUDENT@example.com",
                "display_name": "Another Student",
                "password": "another-password",
            },
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_sign_in_and_sign_out(self) -> None:
        self.client.cookies.clear()
        response = self.client.post(
            "/auth/login",
            json={"email": "STUDENT@example.com", "password": "a-correct-horse"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["display_name"], "Study Student")
        self.assertEqual(self.client.get("/auth/me").status_code, 200)

        logout = self.client.post("/auth/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    def test_sign_in_rejects_incorrect_password(self) -> None:
        self.client.cookies.clear()
        response = self.client.post(
            "/auth/login",
            json={"email": "student@example.com", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Email or password is incorrect.")

    def test_registration_validates_email_and_password(self) -> None:
        response = self.client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "display_name": "Another Student",
                "password": "short",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_ai_endpoints_require_a_session(self) -> None:
        self.client.cookies.clear()
        response = self.client.post(
            "/qa", json={"question": "Which is the largest ocean?"}
        )
        self.assertEqual(response.status_code, 401)

    @patch("main.answer_question", new_callable=AsyncMock)
    def test_question_answer_endpoint(self, answer_question: AsyncMock) -> None:
        answer_question.return_value = "The Pacific is the largest ocean."
        response = self.client.post(
            "/qa", json={"question": "Which is the largest ocean?"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"result": "The Pacific is the largest ocean."}
        )
        answer_question.assert_awaited_once_with("Which is the largest ocean?")

    def test_question_endpoint_validates_input(self) -> None:
        response = self.client.post("/qa", json={"question": "?"})
        self.assertEqual(response.status_code, 422)

    @patch("main.answer_question", new_callable=AsyncMock)
    def test_ai_errors_are_returned_as_actionable_json(
        self, answer_question: AsyncMock
    ) -> None:
        answer_question.side_effect = AIServiceError("Add a Gemini API key.", 503)
        response = self.client.post(
            "/qa", json={"question": "Which is the largest ocean?"}
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Add a Gemini API key."})

    @patch("main.explain_concept", new_callable=AsyncMock)
    def test_explanation_endpoint(self, explain_concept: AsyncMock) -> None:
        explain_concept.return_value = "A short explanation."
        response = self.client.post(
            "/explain", json={"topic": "How photosynthesis works"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "A short explanation."})

    @patch("main.generate_quiz", new_callable=AsyncMock)
    def test_quiz_endpoint(self, generate_quiz: AsyncMock) -> None:
        questions = [
            {
                "question": "Question?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": "A is correct.",
            }
        ] * 3
        generate_quiz.return_value = questions
        response = self.client.post(
            "/quiz", json={"text": "A sufficiently long passage for a quiz."}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"questions": questions})

    @patch("main.summarize_text", new_callable=AsyncMock)
    def test_summary_endpoint(self, summarize_text: AsyncMock) -> None:
        summarize_text.return_value = "A concise summary."
        response = self.client.post(
            "/summarize", json={"text": "A sufficiently long passage to summarize."}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "A concise summary."})

    @patch("main.get_learning_recommendations", new_callable=AsyncMock)
    def test_learning_path_endpoint(
        self, recommendations: AsyncMock
    ) -> None:
        recommendations.return_value = "Start with the fundamentals."
        response = self.client.post(
            "/learn/recommendations",
            json={"topic": "SQL", "level": "Beginner"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"result": "Start with the fundamentals."}
        )
        recommendations.assert_awaited_once_with("SQL", "Beginner")
