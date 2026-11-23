"""Check the shipped read-only prompt templates for basic safety and usability."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'scenarios'
FILES = {
    'ga4-landing-analysis.md': ('<GA4_PROPERTY_ID>', '<LANDING_PATHS>', '<EVENT_NAME>', 'run_report'),
    'google-ads-campaign-performance.md': ('<GOOGLE_ADS_CUSTOMER_ID>', 'search_search', '3 complete', '7 complete'),
    'combined-ads-ga4.md': ('<GOOGLE_ADS_CUSTOMER_ID>', '<GA4_PROPERTY_ID>', 'search_search', 'run_report'),
}


class ScenarioTests(unittest.TestCase):
    def test_prompts_have_placeholders_read_only_and_limits(self):
        for name, terms in FILES.items():
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding='utf-8')
                self.assertIn('## Prompt', text)
                self.assertIn('READ ONLY', text)
                self.assertIn('timezone', text.lower())
                self.assertIn('no baseline', text.lower())
                self.assertIn('Do not', text)
                for term in terms:
                    self.assertIn(term, text)

    def test_index_links_to_all_templates(self):
        index = (ROOT / 'README.md').read_text(encoding='utf-8')
        for name in FILES:
            self.assertIn(f']({name})', index)


if __name__ == '__main__':
    unittest.main()
