"""Campaign workload checks with synthetic graphs and script constants."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from campaign_routes import review_route


class CampaignRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'common/national_focus/test.txt'
        self.file.parent.mkdir(parents=True)
        self.file.write_text('''@late_cost = 7
focus_tree = {
 focus = { id = GER_A cost = 5 mutually_exclusive = { focus = GER_B } }
 focus = { id = GER_B cost = 3 mutually_exclusive = { focus = GER_A } }
 focus = { id = GER_end cost = @late_cost prerequisite = { focus = hro_ger_reform } }
}
shared_focus = { id = hro_ger_reform cost = 2
 prerequisite = { focus = GER_A focus = GER_B }
 available = { OR = { date > 1938.1.1 always = yes } }
}
''', encoding='utf-8')

    def test_reports_actual_full_plan_not_a_claimed_minimum(self):
        result = review_route(self.root, ['GER_end'])
        self.assertEqual([item['id'] for item in result['plan']], ['GER_A', 'hro_ger_reform', 'GER_end'])
        self.assertEqual(result['workdays'], {'native': 84, 'authored': 14, 'total': 98})
        self.assertIn('not a minimum', result['plan_selection'])
        self.assertFalse(result['availability_and_calendar_verified'])

    def test_forbidden_alternative_changes_the_compatible_plan(self):
        result = review_route(self.root, ['GER_end'], forbidden=['GER_A'])
        self.assertEqual(result['workdays']['total'], 84)
        self.assertEqual(result['plan'][0]['id'], 'GER_B')

    def test_multiple_goals_are_jointly_required_not_either_or(self):
        result = review_route(self.root, ['GER_end', 'GER_B'])
        self.assertEqual(result['plan'][0]['id'], 'GER_B')
        self.assertEqual(result['workdays']['total'], 84)
        with self.assertRaisesRegex(ValueError, 'no mutually compatible'):
            review_route(self.root, ['GER_A', 'GER_B'])

    def test_raw_date_checks_are_reported_without_claiming_unconditional_gates(self):
        result = review_route(self.root, ['GER_end'])
        self.assertEqual(result['own_date_checks'][0]['checks'], [{'operator': '>', 'date': '1938.1.1'}])
        self.assertIn('OR rules', result['date_check_note'])

    def test_unresolved_or_recursive_cost_is_rejected(self):
        text = self.file.read_text(encoding='utf-8')
        self.file.write_text(text.replace('@late_cost = 7', '@late_cost = @missing'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unresolved cost constant'):
            review_route(self.root, ['GER_end'])
        self.file.write_text(text.replace('@late_cost = 7', '@late_cost = @late_cost'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Cost constant cycle'):
            review_route(self.root, ['GER_end'])

    def test_deadline_is_an_explicit_workload_comparison(self):
        result = review_route(self.root, ['GER_end'], start_date='1936.1.1', deadline='1937.1.1')
        self.assertEqual(result['calendar_workload_budget']['calendar_days'], 366)
        self.assertEqual(result['calendar_workload_budget']['nominal_spare_days'], 268)
        self.assertFalse(result['calendar_workload_budget']['accounts_for_waits_or_availability'])

    def test_missing_prerequisite_cannot_be_treated_as_a_free_root(self):
        text = self.file.read_text(encoding='utf-8')
        self.file.write_text(text.replace('focus = GER_A focus = GER_B', 'focus = GER_missing'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unknown prerequisite'):
            review_route(self.root, ['GER_end'])


if __name__ == '__main__':
    unittest.main()
