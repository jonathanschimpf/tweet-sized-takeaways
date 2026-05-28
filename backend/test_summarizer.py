import unittest

from backend.summarizer import _normalize_fetch_url


class FetchUrlNormalizationTests(unittest.TestCase):
    def test_bare_url_defaults_to_https(self):
        self.assertEqual(
            _normalize_fetch_url("bbc.com/news"),
            "https://bbc.com/news",
        )

    def test_existing_scheme_is_preserved(self):
        self.assertEqual(
            _normalize_fetch_url("http://bbc.com/news"),
            "http://bbc.com/news",
        )


if __name__ == "__main__":
    unittest.main()
