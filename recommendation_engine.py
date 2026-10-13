"""Explainable, context-aware TripGenie destination recommender.

The model artifact contains synthetic teaching examples. The runtime combines
KNN-style profile similarity with transparent metadata/context scores. Scores are
relative rankings, not calibrated probabilities or validated accuracy.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import json
import math
import threading
import time

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "trip_recommender.json"
_WEATHER_CACHE = {}
_WEATHER_LOCK = threading.Lock()
_WEATHER_TTL_SECONDS = 15 * 60


def ensure_model():
    if not MODEL_PATH.exists():
        from train_model import train
        train()


def _norm(value):
    return str(value or "").strip().casefold()


def _tags(info):
    raw = info.get("interests", "")
    if isinstance(raw, str):
        values = [part.strip() for part in raw.replace(",", "|").split("|") if part.strip()]
    else:
        values = list(raw or [])
    category = str(info.get("category", "")).strip()
    if category:
        values.append(category)
    return {_norm(value) for value in values}


def _fit_budget(user_ppd, expected):
    expected = max(1.0, float(expected or 2500))
    # This is an approximate daily-budget fit, not a trip quote.
    return max(0.0, 100.0 - abs(math.log(max(1.0, user_ppd) / expected)) * 35.0)


def _fit_days(days, ideal):
    ideal = max(1, int(ideal or 2))
    return max(0.0, 100.0 - abs(int(days) - ideal) * 16.0)


def _interest_matches(preferred, info):
    pref = _norm(preferred)
    if pref in {"", "any", "any interest", "no preference"}:
        return 72.0
    tags = _tags(info)
    aliases = {
        "forts": {"forts", "fort"},
        "zoo & wildlife": {"zoo & wildlife", "wildlife", "nature", "family"},
        "zoos & wildlife": {"zoo & wildlife", "wildlife", "nature", "family"},
        "zoological parks": {"zoo & wildlife", "wildlife", "nature", "family"},
        "engineering marvels": {"engineering marvels", "historical", "culture"},
        "natural wonders": {"natural wonders", "nature", "adventure"},
        "wildlife": {"zoo & wildlife", "wildlife", "nature"},
        "spiritual": {"spiritual", "historical", "culture"},
        "history": {"historical", "culture", "engineering marvels", "forts"},
    }
    # Prefer actual site types over broad base towns when the user asks for a
    # specific kind of place. Towns can still be useful bases, but shouldn't
    # outrank a real fort/beach simply because their metadata includes that tag.
    category = _norm(info.get("category"))
    if pref == "forts":
        if category == "fort" or category.endswith(" fort"):
            return 100.0
        if "forts" in tags:
            return 88.0 if "forts" in category else 78.0
        return 12.0
    if pref == "beach":
        if category == "beach":
            return 100.0
        if "coastal" in category or category == "coastal town":
            return 88.0
        if "beach" in tags:
            return 78.0
        return 12.0
    if pref in {"engineering marvels", "natural wonders", "zoo & wildlife", "zoos & wildlife", "zoological parks"}:
        exact_category = {"engineering marvels": {"engineering marvel", "engineering marvels"},
                          "natural wonders": {"natural wonder", "natural wonders"},
                          "zoo & wildlife": {"wildlife", "zoo & wildlife"},
                          "zoos & wildlife": {"wildlife", "zoo & wildlife"},
                          "zoological parks": {"wildlife", "zoo & wildlife"}}.get(pref, set())
        if category in exact_category:
            return 100.0
        if tags.intersection(aliases.get(pref, {pref})):
            return 88.0
        return 12.0
    accepted = aliases.get(pref, {pref})
    if tags.intersection(accepted):
        return 100.0 if pref in tags else 88.0
    return 12.0


def _haversine_km(a_lat, a_lon, b_lat, b_lon):
    try:
        lat1, lon1, lat2, lon2 = map(math.radians, (float(a_lat), float(a_lon), float(b_lat), float(b_lon)))
        dlat, dlon = lat2-lat1, lon2-lon1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 6371 * 2 * math.asin(min(1, math.sqrt(h)))
    except (TypeError, ValueError):
        return None


def _forecast_window(travel_date):
    try:
        chosen = date.fromisoformat(str(travel_date))
    except (TypeError, ValueError):
        return None
    today = date.today()
    if today <= chosen <= today + timedelta(days=6):
        return chosen
    return None


def _fetch_daily_weather(info, chosen_date):
    """Fetch one daily forecast without a key. Fail closed to neutral scoring.

    Open-Meteo is only queried for selected dates in the next seven days. The
    forecast is advisory; source uptime and forecast precision are not guaranteed.
    """
    try:
        lat = float(info.get("latitude"))
        lon = float(info.get("longitude"))
    except (TypeError, ValueError):
        return None
    cache_key = (round(lat, 3), round(lon, 3), chosen_date.isoformat())
    now = time.time()
    with _WEATHER_LOCK:
        cached = _WEATHER_CACHE.get(cache_key)
        if cached and now - cached[0] < _WEATHER_TTL_SECONDS:
            return cached[1]
    query = urlencode({
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,precipitation_probability_max",
        "timezone": "auto",
        "start_date": chosen_date.isoformat(),
        "end_date": chosen_date.isoformat(),
    })
    try:
        with urlopen("https://api.open-meteo.com/v1/forecast?" + query, timeout=1.8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        daily = payload.get("daily", {})
        codes = daily.get("weather_code", [])
        rain = daily.get("precipitation_probability_max", [])
        if not codes:
            return None
        result = {"weather_code": int(codes[0]), "precip_probability": float(rain[0]) if rain and rain[0] is not None else None}
    except Exception:
        result = None
    with _WEATHER_LOCK:
        _WEATHER_CACHE[cache_key] = (now, result)
    return result


def _is_outdoor(preferred, info):
    outdoor_tags = {"nature", "adventure", "forts", "beach", "natural wonders", "zoo & wildlife", "wildlife"}
    return _norm(preferred) in outdoor_tags or bool(_tags(info).intersection(outdoor_tags))


def _weather_fit(preferred, info, forecast):
    if not forecast:
        return 65.0, "Forecast unavailable for the selected date; weather is not used to rank this option."
    code = int(forecast.get("weather_code", -1))
    rain = forecast.get("precip_probability")
    rain = 0.0 if rain is None else max(0.0, min(100.0, float(rain)))
    severe = code in {65, 66, 67, 82, 95, 96, 99}
    outdoor = _is_outdoor(preferred, info)
    if outdoor:
        if severe or rain >= 80:
            value, note = 20.0, f"Forecast signals a wet/severe-weather day ({rain:.0f}% precipitation chance); review local conditions before outdoor plans."
        elif rain >= 60:
            value, note = 40.0, f"Forecast shows a high precipitation chance ({rain:.0f}%); outdoor plans may need a backup."
        elif rain >= 40:
            value, note = 60.0, f"Some rain is possible ({rain:.0f}%); keep an indoor or flexible alternative."
        elif rain >= 20:
            value, note = 80.0, f"Moderate weather outlook ({rain:.0f}% precipitation chance)."
        else:
            value, note = 95.0, f"Lower precipitation chance ({rain:.0f}%) for this date."
    else:
        if severe or rain >= 80:
            value, note = 55.0, f"Wet/severe-weather signals ({rain:.0f}% precipitation chance); allow extra time and confirm local conditions."
        elif rain >= 60:
            value, note = 68.0, f"Rain is possible ({rain:.0f}%); check conditions before departure."
        else:
            value, note = 88.0, f"Forecast currently shows a {rain:.0f}% precipitation chance."
    return value, note


def _feedback_fit(name, feedback):
    entry = (feedback or {}).get(name)
    if not entry:
        return 50.0, 0
    if isinstance(entry, dict):
        signal_sum = float(entry.get("signal_sum", 0))
        count = max(0, int(entry.get("count", 0)))
    else:
        signal_sum, count = float(entry), 1
    average = signal_sum / count if count else 0.0
    return max(0.0, min(100.0, 50.0 + 25.0 * average)), count


def _diversify(items, top_n):
    """Cap category repetition when possible without dropping good candidates."""
    chosen, deferred, category_counts = [], [], {}
    for item in items:
        category = _norm(item.get("category")) or "uncategorized"
        if category_counts.get(category, 0) >= 3:
            deferred.append(item)
            continue
        chosen.append(item)
        category_counts[category] = category_counts.get(category, 0) + 1
        if len(chosen) >= top_n:
            return chosen
    for item in deferred:
        if len(chosen) >= top_n:
            break
        chosen.append(item)
    return chosen[:top_n]


def recommend_destinations(total_budget, days, travellers, interest, destination_info,
                           top_n=6, origin_name=None, travel_date=None, feedback=None):
    """Rank destinations with explainable multi-factor + optional forecast/feedback signals.

    Training examples remain synthetic, so the model is a functional prototype and
    returned match scores are relative rankings, not probabilities or validated accuracy.
    """
    ensure_model()
    try:
        payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        samples = payload.get("samples", [])
    except (OSError, json.JSONDecodeError):
        samples = []

    days = max(1, int(days)); travellers = max(1, int(travellers))
    budget_per_person_day = max(1.0, float(total_budget) / days / travellers)
    pref = _norm(interest)
    distances = []
    for row in samples:
        try:
            budget_distance = abs(math.log(max(1.0, budget_per_person_day) / max(1.0, float(row["budget_per_person_day"])))) / math.log(60.0)
            day_distance = abs(days - int(row["days"])) / 14.0
            row_interest = _norm(row.get("interest"))
            if pref in {"", "any", "any interest", "no preference"}:
                interest_distance = 0.25
            elif row_interest == pref:
                interest_distance = 0.0
            else:
                # Synonyms and near-equivalent categories should not be treated as fully unrelated.
                related = _interest_matches(interest, {"interests": row_interest, "category": row_interest}) >= 88
                interest_distance = 0.35 if related else 0.75
            distance = math.sqrt(0.48*budget_distance**2 + 0.22*day_distance**2 + 0.30*interest_distance**2)
            distances.append((distance, row.get("destination", "")))
        except (ValueError, TypeError, KeyError):
            continue
    distances.sort(key=lambda item: item[0])
    votes = {}
    for distance, name in distances[:min(35, len(distances))]:
        votes[name] = votes.get(name, 0.0) + 1.0/(distance + 0.08)
    max_vote = max(votes.values(), default=1.0)

    origin = destination_info.get(origin_name) if origin_name else None
    candidates = []
    for name, raw_info in destination_info.items():
        info = dict(raw_info)
        expected_budget = info.get("budget_per_day", 2500)
        budget_fit = _fit_budget(budget_per_person_day, expected_budget)
        days_fit = _fit_days(days, info.get("ideal_days", 2))
        interest_fit = _interest_matches(interest, info)
        # Cold-start destinations are given a modest prior instead of an automatic zero.
        knn_fit = 100.0 * votes.get(name, 0.0) / max_vote if name in votes and max_vote else 38.0
        proximity_fit, distance_km = 55.0, None
        if origin and origin.get("latitude") is not None and origin.get("longitude") is not None:
            distance_km = _haversine_km(origin.get("latitude"), origin.get("longitude"), info.get("latitude"), info.get("longitude"))
            if distance_km is not None:
                proximity_fit = max(0.0, 100.0 - min(100.0, distance_km / 20.0))
        feedback_fit, feedback_count = _feedback_fit(name, feedback)
        # Preliminary ordering before the optional context lookup.
        core_score = .30*interest_fit + .24*budget_fit + .12*days_fit + .14*knn_fit + .10*proximity_fit + .10*feedback_fit
        info.update({
            "budget_fit": round(budget_fit), "days_fit": round(days_fit),
            "interest_fit": round(interest_fit), "training_similarity": round(knn_fit),
            "proximity_fit": round(proximity_fit), "distance_km_from_origin": round(distance_km) if distance_km is not None else None,
            "feedback_fit": round(feedback_fit), "feedback_count": feedback_count,
            "_pre_score": core_score,
        })
        candidates.append(info)
    candidates.sort(key=lambda item: item["_pre_score"], reverse=True)

    chosen_date = _forecast_window(travel_date)
    forecast_by_name = {}
    # Limit calls; lower-ranked destinations remain eligible with a neutral weather factor.
    if chosen_date:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_daily_weather, info, chosen_date): info["name"] for info in candidates[:16]}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    forecast_by_name[name] = future.result()
                except Exception:
                    forecast_by_name[name] = None

    for info in candidates:
        forecast = forecast_by_name.get(info["name"])
        weather_fit, weather_note = _weather_fit(interest, info, forecast)
        # Total weights sum to 1.00; feedback is intentionally small until real feedback accumulates.
        score = (.28*info["interest_fit"] + .23*info["budget_fit"] + .12*info["days_fit"]
                 + .12*info["training_similarity"] + .10*info["proximity_fit"]
                 + .10*weather_fit + .05*info["feedback_fit"])
        info["weather_fit"] = round(weather_fit)
        info["weather_note"] = weather_note
        info["weather_forecast_used"] = bool(forecast)
        info["match_score"] = max(1, min(99, round(score)))
        reasons = []
        if pref not in {"", "any", "any interest", "no preference"} and info["interest_fit"] >= 88:
            reasons.append(f"matches {interest} ({info['interest_fit']}/100)")
        if info["budget_fit"] >= 72:
            reasons.append(f"daily budget fit {info['budget_fit']}/100")
        if info["days_fit"] >= 72:
            reasons.append(f"trip-length fit {info['days_fit']}/100")
        if info.get("distance_km_from_origin") is not None and info["distance_km_from_origin"] <= 250:
            reasons.append(f"about {info['distance_km_from_origin']} km straight-line from {origin_name}")
        if forecast:
            reasons.append(weather_note)
        if info["feedback_count"]:
            reasons.append("adjusted using your earlier feedback")
        info["recommendation_reason"] = "; ".join(reasons[:4]) or "a balanced option to compare across your trip preferences"
        info["recommendation_factors"] = [
            {"label": "Interest match", "score": info["interest_fit"], "weight": "28%"},
            {"label": "Budget fit", "score": info["budget_fit"], "weight": "23%"},
            {"label": "Trip duration", "score": info["days_fit"], "weight": "12%"},
            {"label": "Training-profile similarity", "score": info["training_similarity"], "weight": "12%"},
            {"label": "Proximity", "score": info["proximity_fit"], "weight": "10%"},
            {"label": "Weather fit", "score": info["weather_fit"], "weight": "10%"},
            {"label": "Your feedback", "score": info["feedback_fit"], "weight": "5%"},
        ]
        info.pop("_pre_score", None)
    candidates.sort(key=lambda item: (item["match_score"], item.get("budget_fit", 0)), reverse=True)
    return _diversify(candidates, max(1, int(top_n)))
