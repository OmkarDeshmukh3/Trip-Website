import unittest
from datetime import date, timedelta
from unittest.mock import patch

import recommendation_engine as engine


DESTINATIONS = {
    "Pune": {"name": "Pune", "location": "Maharashtra", "category": "Culture", "interests": "Historical|Culture|Food|Nature", "latitude": 18.5204, "longitude": 73.8567, "budget_per_day": 2600, "ideal_days": 2},
    "Ajanta Caves": {"name": "Ajanta Caves", "location": "Maharashtra", "category": "Engineering Marvel", "interests": "Engineering Marvels|Historical|Culture|Spiritual", "latitude": 20.5531, "longitude": 75.7002, "budget_per_day": 1800, "ideal_days": 1},
    "Lonavala": {"name": "Lonavala", "location": "Maharashtra", "category": "Nature", "interests": "Nature|Adventure|Food", "latitude": 18.7546, "longitude": 73.4062, "budget_per_day": 2200, "ideal_days": 2},
    "Raigad Fort": {"name": "Raigad Fort", "location": "Maharashtra", "category": "Forts & Heritage", "interests": "Forts|Historical|Adventure|Culture", "latitude": 18.2332, "longitude": 73.4402, "budget_per_day": 2000, "ideal_days": 1},
    "Lonar Crater": {"name": "Lonar Crater", "location": "Maharashtra", "category": "Natural Wonder", "interests": "Natural Wonders|Nature|Adventure|Engineering Marvels", "latitude": 19.9764, "longitude": 76.5093, "budget_per_day": 2100, "ideal_days": 2},
}


class RecommendationEngineTests(unittest.TestCase):
    def setUp(self):
        engine._WEATHER_CACHE.clear()

    def test_exposes_explanation_factors_for_each_recommendation(self):
        results = engine.recommend_destinations(10000, 2, 2, "Engineering Marvels", DESTINATIONS,
                                                 top_n=4, origin_name="Pune", travel_date=(date.today()+timedelta(days=10)).isoformat())
        self.assertTrue(results)
        for item in results:
            self.assertGreaterEqual(item["match_score"], 1)
            self.assertLessEqual(item["match_score"], 99)
            self.assertEqual(len(item["recommendation_factors"]), 7)
            self.assertIn("recommendation_reason", item)
            self.assertIn("weather_note", item)

    def test_interest_fit_places_matching_destination_above_unrelated_place(self):
        results = engine.recommend_destinations(10000, 2, 2, "Engineering Marvels", DESTINATIONS,
                                                 top_n=5, origin_name="Pune", travel_date=(date.today()+timedelta(days=10)).isoformat())
        by_name = {row["name"]: row for row in results}
        self.assertGreater(by_name["Ajanta Caves"]["interest_fit"], by_name["Lonavala"]["interest_fit"])

    def test_user_feedback_is_reflected_in_explainable_factor(self):
        no_feedback = engine.recommend_destinations(10000, 2, 2, "Any interest", DESTINATIONS,
                                                      top_n=5, origin_name="Pune", travel_date=(date.today()+timedelta(days=10)).isoformat())
        with_feedback = engine.recommend_destinations(10000, 2, 2, "Any interest", DESTINATIONS,
            top_n=5, origin_name="Pune", travel_date=(date.today()+timedelta(days=10)).isoformat(),
            feedback={"Ajanta Caves": {"signal_sum": 3, "count": 3}})
        liked = {row["name"]: row for row in with_feedback}["Ajanta Caves"]
        baseline = {row["name"]: row for row in no_feedback}["Ajanta Caves"]
        self.assertEqual(liked["feedback_fit"], 75)
        self.assertGreater(liked["match_score"], baseline["match_score"])

    @patch("recommendation_engine._fetch_daily_weather")
    def test_forecast_changes_weather_factor_for_outdoor_trip(self, fetch_weather):
        fetch_weather.side_effect = lambda info, chosen_date: {
            "weather_code": 61,
            "precip_probability": 90 if info["name"] == "Lonavala" else 10,
        }
        target = (date.today() + timedelta(days=1)).isoformat()
        results = engine.recommend_destinations(10000, 2, 2, "Nature", DESTINATIONS, top_n=5,
                                                 origin_name="Pune", travel_date=target)
        by_name = {row["name"]: row for row in results}
        self.assertTrue(by_name["Lonavala"]["weather_forecast_used"])
        self.assertLess(by_name["Lonavala"]["weather_fit"], by_name["Lonar Crater"]["weather_fit"])

    def test_weather_is_not_fabricated_when_date_is_outside_forecast_window(self):
        with patch("recommendation_engine._fetch_daily_weather") as fetch_weather:
            results = engine.recommend_destinations(10000, 2, 2, "Nature", DESTINATIONS, top_n=3,
                origin_name="Pune", travel_date=(date.today()+timedelta(days=20)).isoformat())
        fetch_weather.assert_not_called()
        self.assertTrue(all(not row["weather_forecast_used"] for row in results))

    def test_diversifier_limits_same_category_when_alternatives_exist(self):
        results = engine.recommend_destinations(30000, 3, 2, "Any interest", DESTINATIONS,
            top_n=5, origin_name="Pune", travel_date=(date.today()+timedelta(days=20)).isoformat())
        from collections import Counter
        counts = Counter(row["category"] for row in results)
        self.assertTrue(all(count <= 3 for count in counts.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
