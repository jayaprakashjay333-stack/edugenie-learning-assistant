import unittest

from errors import AIServiceError
from quiz_module import parse_quiz_response


def valid_quiz() -> dict[str, list[dict[str, object]]]:
    return {
        "questions": [
            {
                "question": f"Question {number}?",
                "options": ["Correct", "Wrong 1", "Wrong 2", "Wrong 3"],
                "correct_answer": "Correct",
                "explanation": "The source supports this answer.",
            }
            for number in range(1, 4)
        ]
    }


class QuizParsingTests(unittest.TestCase):
    def test_parses_json_wrapped_in_markdown_fence(self) -> None:
        response = f"```json\n{valid_quiz()!r}\n```".replace("'", '"')
        parsed = parse_quiz_response(response)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(len(parsed[0]["options"]), 4)

    def test_rejects_wrong_number_of_questions(self) -> None:
        quiz = valid_quiz()
        quiz["questions"].pop()
        with self.assertRaises(AIServiceError):
            parse_quiz_response(str(quiz).replace("'", '"'))

    def test_rejects_correct_answer_not_in_options(self) -> None:
        quiz = valid_quiz()
        quiz["questions"][0]["correct_answer"] = "Not an option"
        with self.assertRaises(AIServiceError):
            parse_quiz_response(str(quiz).replace("'", '"'))

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaises(AIServiceError):
            parse_quiz_response("not json")
