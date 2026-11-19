"""Regression: news links survive later, older, or partial refreshes."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from merge_news_index import merge

class MergeNewsTests(unittest.TestCase):
    def test_a_partial_refresh_cannot_erase_prior_news(self):
        old={"generated_at":"2026-11-19T13:30:00+00:00","articles":[
            {"url":"https://example.com/old","title":"Earlier Hyderabad GCC","seen":"2026-11-19T11:00:00+00:00","desk":"regional-business"},
            {"url":"https://example.com/shared","title":"Verified business result","seen":"2026-11-19T13:25:00+00:00","snippet_te":"తెలుగు సారాంశం"},
        ]}
        late_job={"generated_at":"2026-11-19T13:20:00+00:00","articles":[
            {"url":"https://example.com/shared","title":"Old feed headline","seen":"2026-11-19T13:10:00+00:00"},
            {"url":"https://example.com/new","title":"New business announcement","seen":"2026-11-19T13:18:00+00:00"},
        ]}
        result=merge(old,late_job)
        self.assertEqual(len(result["articles"]),3)
        self.assertEqual(result["generated_at"],old["generated_at"])
        rows={x["url"]:x for x in result["articles"]}
        self.assertEqual(rows["https://example.com/shared"]["title"],"Verified business result")
        self.assertEqual(rows["https://example.com/shared"]["snippet_te"],"తెలుగు సారాంశం")
    def test_latest_refresh_does_not_remove_old_desk(self):
        before={"generated_at":"2026-11-19T13:00:00+00:00","articles":[
            {"url":"https://example.com/ap","title":"AP general","desk":"regional-general","seen":"2026-11-19T12:00:00+00:00"}
        ]}
        new={"generated_at":"2026-11-19T13:30:00+00:00","articles":[
            {"url":"https://example.com/pf","title":"PF update","desk":"personal-finance","seen":"2026-11-19T13:20:00+00:00"}
        ]}
        result=merge(before,new)
        self.assertEqual(len(result["articles"]),2)
        self.assertEqual(result["generated_at"],new["generated_at"])

if __name__=="__main__":unittest.main()
