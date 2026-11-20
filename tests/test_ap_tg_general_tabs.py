"""Regression checks: AP/TG are broad general news tabs, not business-only."""
import unittest
from pathlib import Path

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

class GeneralRegionTabsTests(unittest.TestCase):
    def test_ap_tg_all_use_general_news_branch(self):
        self.assertIn("['telugu-states','andhra-pradesh','telangana'].includes(selectedDesk)", HTML)
        self.assertIn("'regional-general','regional-business'", HTML)
        self.assertIn("selectedDesk==='andhra-pradesh'&&item.region!=='andhra-pradesh'", HTML)
        self.assertIn("selectedDesk==='telangana'&&!['telangana','hyderabad'].includes(item.region)", HTML)
    def test_ui_has_general_news_not_business_news_labels(self):
        self.assertIn("'andhra-pradesh':'Andhra Pradesh General News'", HTML)
        self.assertIn("'telangana':'Telangana General News'", HTML)
    def test_main_business_desk_remains_separate(self):
        self.assertIn("'hyderabad':'Hyderabad Business News'", HTML)
        self.assertIn("'telugu-companies':'Listed Companies'", HTML)

if __name__=="__main__": unittest.main()
