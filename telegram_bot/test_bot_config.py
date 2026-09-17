import pathlib
import unittest


class BotConfigTests(unittest.TestCase):
    def test_no_hardcoded_bot_token(self):
        bot_source = pathlib.Path(__file__).with_name("bot.py").read_text(encoding="utf-8")
        self.assertNotIn("8857756377:AAGyG35MMYTVfoLnHh6J0PxiM5NMa13UUA0", bot_source)


if __name__ == "__main__":
    unittest.main()
