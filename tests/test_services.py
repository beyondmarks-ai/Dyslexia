import unittest

from services.model_service import FEATURES, feature_importance, load_artifacts, predict
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


if __name__ == "__main__":
    unittest.main()
