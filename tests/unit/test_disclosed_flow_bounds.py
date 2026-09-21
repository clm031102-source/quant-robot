import itertools
import unittest
from fractions import Fraction
from quant_robot.research.disclosed_flow_bounds import breadth_bounds


class DisclosedFlowBoundsTests(unittest.TestCase):
    def test_original_missingness_example_is_unknown_not_zero(self):
        result = breadth_bounds([{'value_cents': 60, 'positive_days': 1, 'unknown_days': 1},
            {'value_cents': 40, 'positive_days': 1, 'unknown_days': 0}], total_value_cents=100, sessions=2)
        self.assertEqual(result['lower'], '1/2')
        self.assertEqual(result['upper'], '4/5')
        self.assertIsNone(result['identified_state'])

    def test_sharp_bounds_enclose_all_binary_completions(self):
        for weights in ((1, 1), (2, 7), (1, 1000000)):
            for counts in itertools.product(range(3), repeat=4):
                p1, u1, p2, u2 = counts
                if p1+u1>2 or p2+u2>2: continue
                rows = [dict(value_cents=w, positive_days=p, unknown_days=u)
                        for w, p, u in zip(weights, (p1, p2), (u1, u2))]
                b = breadth_bounds(rows, total_value_cents=sum(weights), sessions=2)
                values = [Fraction(weights[0]*(p1+a)+weights[1]*(p2+c), sum(weights)*2)
                          for a in range(u1+1) for c in range(u2+1)]
                self.assertEqual(Fraction(b['lower']), min(values))
                self.assertEqual(Fraction(b['upper']), max(values))
                if b['identified_state'] is not None:
                    self.assertTrue(all(int(v>Fraction(1,2)) == b['identified_state'] for v in values))

    def test_strict_threshold_and_one_cent_precision(self):
        for positive, expected in ((1, 0), (2, 1)):
            self.assertEqual(breadth_bounds([dict(value_cents=10**18, positive_days=positive, unknown_days=0)],
                total_value_cents=10**18, sessions=2)['identified_state'], expected)
        r = breadth_bounds([dict(value_cents=10**18, positive_days=1, unknown_days=0),
            dict(value_cents=1, positive_days=2, unknown_days=0)], total_value_cents=10**18+1, sessions=2)
        self.assertEqual(r['identified_state'], 1)

    def test_no_renormalization_or_invalid_counts(self):
        with self.assertRaises(ValueError):
            breadth_bounds([dict(value_cents=60, positive_days=1, unknown_days=0)], total_value_cents=100, sessions=2)
        for bad in (-1, True, 1.5, 3):
            with self.assertRaises(ValueError):
                breadth_bounds([dict(value_cents=100, positive_days=bad, unknown_days=0)], total_value_cents=100, sessions=2)


if __name__ == '__main__': unittest.main()
