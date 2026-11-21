"""Regression checks: AP/TG are broad general news tabs, not business-only."""
import unittest
from pathlib import Path

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

class GeneralRegionTabsTests(unittest.TestCase):
    def test_ap_tg_all_use_general_news_branch(self):
        self.assertIn("['telugu-states','andhra-pradesh','telangana'].includes(selectedDesk)", HTML)
        branch=HTML.split("else if(['telugu-states','andhra-pradesh','telangana'].includes(selectedDesk))",1)[1].split("else if(selectedDesk==='india-general')",1)[0]
        # Regional tabs must accept every captured regional headline, including
        # business, sports, crime and health; no desk/sector filtering here.
        self.assertIn("['andhra-pradesh','telangana','hyderabad','ap-tg'].includes(area)", branch)
        self.assertIn("selectedDesk==='andhra-pradesh'&&!['andhra-pradesh','ap-tg'].includes(area)", branch)
        self.assertIn("selectedDesk==='telangana'&&!['telangana','hyderabad','ap-tg'].includes(area)", branch)
        self.assertNotIn("item.desk", branch)
        self.assertNotIn("item.sector", branch)
    def test_ui_has_general_news_not_business_news_labels(self):
        self.assertIn("'andhra-pradesh':'Andhra Pradesh General News'", HTML)
        self.assertIn("'telangana':'Telangana General News'", HTML)
    def test_main_business_desk_remains_separate(self):
        self.assertIn("'hyderabad':'Hyderabad Business News'", HTML)
        self.assertIn("'telugu-companies':'Listed Companies'", HTML)

if __name__=="__main__": unittest.main()
