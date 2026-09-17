import unittest

from services.model_service import FEATURES, feature_importance, load_artifacts, predict, screening_likelihood
from services.question_service import validate_question_set
from services.test_service import score_answers, score_recalled_words, speed_score


class ServiceTests(unittest.TestCase):
    def test_existing_artifacts_and_prediction(self):
        model, scaler = load_artifacts()
        self.assertEqual(model.n_features_in_, 6)
        self.assertEqual(list(scaler.feature_names_in_), list(FEATURES))
        result = predict(dict.fromkeys(FEATURES, 0.5))
        self.assertIn(result["label"], (0, 1, 2))
        self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0)
        self.assertEqual(set(feature_importance()), set(FEATURES))

    def test_invalid_features_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            predict(dict.fromkeys(FEATURES, 1.1))
        with self.assertRaisesRegex(ValueError, "missing"):
            predict({"Memory": 0.5})

    def test_scoring(self):
        self.assertEqual(score_answers([" A ", "B!"], ["a", "b"])["accuracy"], 1)
        self.assertAlmostEqual(score_recalled_words("red blue", ["Red", "Blue", "Green"]), 2 / 3)
        self.assertEqual(speed_score(3), 1)
        self.assertEqual(speed_score(30), 0)

    def test_screening_likelihood_weights_model_classes(self):
        score = screening_likelihood({"High": 0.6, "Moderate": 0.3, "Low": 0.1})
        self.assertAlmostEqual(score, 0.75)

    def test_generated_questions_are_strictly_validated(self):
        vocabulary = [
            {"question": f"The bird ___ over tree {i}.", "options": ["flies", "sleeps", "reads"], "correct_answer": "flies"}
            for i in range(10)
        ]
        reading = [
            {"passage": f"Mina planted seed {i} and watered it every day. A green shoot appeared soon.", "question": "What appeared?", "options": ["A shoot", "A boat", "A stone"], "correct_answer": "A shoot"}
            for i in range(4)
        ]
        payload = {
            "vocabulary": vocabulary,
            "reading": reading,
            "dictation_sentence": "The quiet train moved slowly beside the wide river.",
            "read_aloud_sentence": "A small bird rested safely beneath the old tree.",
        }
        validated = validate_question_set(payload)
        self.assertEqual(len(validated["vocabulary"]), 10)
        self.assertEqual(
            validate_question_set(validated)["reading"],
            validated["reading"],
        )
        with self.assertRaisesRegex(ValueError, "explicit blank"):
            invalid = dict(payload)
            invalid["vocabulary"] = [dict(item) for item in vocabulary]
            invalid["vocabulary"][0]["question"] = "The bird flies."
            validate_question_set(invalid)


if __name__ == "__main__":
    unittest.main()
