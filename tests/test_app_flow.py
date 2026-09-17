import unittest

from streamlit.testing.v1 import AppTest

MEMORY_WORDS = [
    ["Apple", "Lettuce", "House", "River", "Dog", "Book", "Cooking"],
    ["Dog", "Cat", "Rabbit", "Horse", "Sheep", "Cow", "Goat"],
    ["Table", "Chair", "Sofa", "Bed", "Desk", "Lamp", "Shelf"],
    ["River", "Lake", "Ocean", "Pond", "Stream", "Beach", "Waterfall"],
    ["Red", "Blue", "Green", "Yellow", "Pink", "Black", "White"],
    ["Car", "Bus", "Train", "Plane", "Boat", "Bike", "Truck"],
    ["Rain", "Snow", "Sun", "Cloud", "Wind", "Storm", "Thunder"],
    ["Pen", "Pencil", "Eraser", "Paper", "Book", "Notebook", "Ruler"],
    ["Tree", "Flower", "Grass", "Leaf", "Seed", "Branch", "Bush"],
    ["Shirt", "Pants", "Socks", "Jacket", "Hat", "Gloves", "Scarf"],
]
class AppFlowTest(unittest.TestCase):
    def test_complete_flow_without_azure(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        app.button[0].click().run(timeout=20)
        app.checkbox[0].check().run(timeout=20)
        app.button[0].click().run(timeout=20)

        questions = app.session_state["vocab_questions"]
        for widget, question in zip(app.radio, questions):
            widget.set_value(question["correct_answer"])
        app.button[0].click().run(timeout=20)

        app.button[0].click().run(timeout=20)
        for widget, sequence in zip(app.text_input[:3], app.session_state["memory_sequences"]):
            widget.input(sequence)
        audio_ids = app.session_state["memory_audio_ids"]
        for widget, audio_id in zip(app.text_input[3:], audio_ids):
            widget.input(" ".join(MEMORY_WORDS[audio_id]))
        app.button[0].click().run(timeout=20)

        for i, question in enumerate(app.session_state["reading_questions"]):
            answer = question.get("correct_answer", question.get("answer"))
            app.radio(key=f"reading_{i}").set_value(answer)
        app.number_input[0].set_value(3)
        app.multiselect[0].set_value(["b", "p", "q", "d"])
        app.radio[4].set_value("○ ○ ■")
        for i, (_, _, expected) in enumerate(app.session_state["phoneme_items"]):
            app.radio(key=f"phoneme_{i}").set_value(expected)
        app.multiselect[1].set_value(["Take", "Lake"])
        app.radio[10].set_value("Second")
        app.text_input[0].input("The quick brown fox jumps over the lazy dog.")
        for i in range(5):
            app.radio(key=f"survey_{i}").set_value("No")
        app.button[0].click().run(timeout=20)

        self.assertIn("Azure Speech is not configured", app.info[0].value)
        app.button[0].click().run(timeout=20)
        self.assertFalse(list(app.exception))
        self.assertTrue(any("screening indication" in title.value for title in app.title))
        self.assertIn(app.session_state["prediction"]["label"], (0, 1, 2))
        self.assertIsNotNone(app.session_state["prediction"]["likelihood"])


if __name__ == "__main__":
    unittest.main()
