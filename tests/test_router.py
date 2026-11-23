"""Tests for the routing rules, including the escalation policy (should_escalate).

Run:  python -m unittest tests.test_router -v
"""

import unittest

import config
from router import route_team, should_escalate


def result(severity="high", category="network", confidence=0.9):
    return {"severity": severity, "category": category,
            "summary": "test summary", "confidence": confidence}


class TestRouteTeam(unittest.TestCase):
    def test_every_category_has_a_team(self):
        for category in config.CATEGORIES:
            self.assertEqual(route_team(category), config.TEAM_ROUTING[category])


class TestShouldEscalate(unittest.TestCase):
    def assertEscalates(self, res, valid):
        escalate, reason = should_escalate(res, valid)
        self.assertTrue(escalate)
        self.assertIsInstance(reason, str)
        self.assertTrue(reason.strip(), "escalations need a non-empty reason")

    def assertNotEscalates(self, res, valid=True):
        escalate, reason = should_escalate(res, valid)
        self.assertFalse(escalate)
        self.assertEqual(reason, "")

    # Rule 1: invalid output
    def test_invalid_output_escalates(self):
        self.assertEscalates(None, valid=False)

    # Rule 2: critical severity
    def test_critical_escalates_even_when_confident(self):
        self.assertEscalates(result(severity="critical", confidence=0.99), valid=True)

    # Rule 3: low confidence
    def test_low_confidence_escalates(self):
        self.assertEscalates(result(severity="low", confidence=0.4), valid=True)

    def test_threshold_boundary_is_not_uncertain(self):
        self.assertNotEscalates(result(confidence=config.CONFIDENCE_THRESHOLD))

    def test_just_below_threshold_escalates(self):
        self.assertEscalates(result(confidence=config.CONFIDENCE_THRESHOLD - 0.01), valid=True)

    # Rule 4: everything else is auto-routed
    def test_confident_non_critical_is_routed(self):
        for severity in ["low", "medium", "high"]:
            with self.subTest(severity=severity):
                self.assertNotEscalates(result(severity=severity, confidence=0.9))


if __name__ == "__main__":
    unittest.main()
