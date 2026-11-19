import os, sys, unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from snippets import enrich,valid

class TeluguSnippetTests(unittest.TestCase):
    def test_telugu_validation(self):
        self.assertTrue(valid("మ్యూచువల్ ఫండ్లలో పెట్టుబడి గురించి సమాచారం."))
        self.assertFalse(valid("Read the original story."))
        self.assertFalse(valid(""))
    def test_no_key_does_not_invent_content(self):
        stories=[{"title":"Interest rates may change","url":"https://example.org/a"}]
        with patch.dict(os.environ,{"OPENAI_API_KEY":""}):
            status=enrich(stories)
        self.assertFalse(status["configured"])
        self.assertEqual(status["pending"],1)
        self.assertNotIn("snippet_te",stories[0])
    def test_existing_snippet_not_rewritten(self):
        stories=[{"title":"Savings account update","title_te":"పొదుపు ఖాతా సమాచారం","snippet_te":"పొదుపు ఖాతాకు సంబంధించిన సమాచారం వచ్చింది. పూర్తి వివరాలు మూల కథనంలో ఉన్నాయి."}]
        with patch.dict(os.environ,{"OPENAI_API_KEY":""}):
            status=enrich(stories)
        self.assertEqual(status["pending"],0)

if __name__=="__main__":
    unittest.main()
