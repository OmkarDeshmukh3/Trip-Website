# TripGenie — Full Project Explanation

## 1. Project overview

TripGenie is a student-built travel discovery and planning website. It helps a traveller explore destinations, compare a destination against a budget and trip length, discover nearby places, see current/short-range weather where available, preview a map route, and continue to external services for directions, accommodation search, train search, or flight comparison.

The project starts with Maharashtra and includes curated options from the rest of India. Main themes include forts, beaches, hill stations, nature, caves and ancient architecture, spiritual places, wildlife, and major Indian destinations.

**Core idea:** TripGenie recommends and organizes a trip; Google Maps, IRCTC, booking websites, weather feeds, and routing services provide separate map/navigation/booking information. TripGenie does not itself sell tickets or confirm hotel rooms.

## 2. Main features

1. **Accounts:** users register and log in. Passwords are stored as hashes. Logging out is available inside the Account info menu.
2. **Destination catalogue:** search and browse 227 curated destination records and 339 place/attraction records.
3. **Trip form:** the user chooses a starting city, interest, total budget, dates, trip length, and traveller count. A specific destination can be selected, or left blank for recommendations.
4. **Recommendation engine:** ranks candidate destinations using budget fit, interest match, days fit, similarity to synthetic training examples, straight-line proximity, weather fit when an eligible forecast exists, and a small user-feedback factor.
5. **Explainable recommendations:** each result gives factor scores and a human-readable reason. “More like this” and “Not for me” feedback is stored for the logged-in user and can influence later results.
6. **Destination details:** selected destination, its catalogue places, trip parameters, and estimated per-person daily budget are shown.
7. **Map and animation:** the webpage uses Leaflet. The user can switch between a CARTO Voyager street map, standard OpenStreetMap streets, and Esri satellite imagery. Markers have names. Selecting a place attempts to refine its coordinate using OpenStreetMap Nominatim, draws an OSRM road-route preview when available, animates a marker, and finishes by zooming into the selected pin. A dashed straight-line fallback is explicitly labelled when a road route cannot be obtained.
8. **Weather:** Open-Meteo provides a current condition and short forecast on a destination page. For recommendation scoring, forecast-based adjustment is only attempted for selected dates within the provider's next-six-day window; the engine falls back neutrally when data is unavailable.
9. **Accommodation discovery:** fictional sample hotels have been removed from user-facing results. The website opens live Google Maps hotel search or Booking.com search results. Users need to verify the real property, dates, room, total cost, rating, and cancellation terms themselves.
10. **Transport:** links open Google Maps directions, IRCTC train search, and Google Flights. These are outbound search links, not in-site or guaranteed bookings.
11. **Itinerary:** builds a basic day-by-day starter plan from available catalogue places. It is an outline, not an optimized navigation schedule.
12. **Mobile access:** responsive templates work in a mobile browser. When the laptop and phone share Wi-Fi, the phone can use the laptop's private IPv4 address and port 5000.

## 3. Technology stack

- **Frontend:** HTML, CSS, JavaScript, Jinja templates, Leaflet.
- **Backend:** Python and Flask.
- **Storage:** SQLite via Python's built-in `sqlite3` library.
- **Recommendation model:** a lightweight KNN-style neighbour lookup from a generated JSON artifact plus a transparent metadata/context ranking formula. The project does not require scikit-learn.
- **Map layers:** CARTO Voyager, OpenStreetMap standard tiles, and Esri World Imagery.
- **Map geocoding:** public OpenStreetMap Nominatim, cached and rate-limited for this small educational demo.
- **Road-route preview:** public OSRM demo endpoint, best-effort only.
- **Weather:** Open-Meteo API, no API key required for the included demo use.
- **Outbound navigation/booking:** Google Maps URLs, IRCTC, Google Flights, and Booking.com search URLs.

## 4. Project folder and purpose of each file

```text
TripGenie_Project/
├── app.py                         Flask routes, account flows, database sync, map geocoding
├── database.py                    SQLite connection and database path
├── requirements.txt               Python package requirements (Flask)
├── RUN_TRIPGENIE.bat              Windows launcher
├── PROJECT_EXPLANATION.md         This full project walkthrough
├── README.txt                     Quick start and operational instructions
├── MOBILE_ACCESS.txt              How to open the app on a phone on the same Wi-Fi
├── GOOGLE_MAPS_SETUP.txt          Difference between a map link and embedded Google Maps
├── LOCATION_CATALOGUE_SOURCES.md  Location-source notes and catalogue limitations
├── DATA_QUALITY_AND_RESEARCH_GAPS.md Research gaps and current limitations
├── data/
│   ├── destinations.csv           Searchable destination names, metadata, coordinates, budget
│   ├── places.csv                 Attractions, forts, beaches, caves, wildlife and coordinates
│   ├── hotels.csv                 Empty by design; no fictional hotel rows are presented as real
│   └── recommendation_training.csv Synthetic labelled profiles for the prototype recommender
├── models/
│   └── trip_recommender.json      Generated training-example artifact
├── recommendation_engine.py       Scoring, weather, distance, explanation, feedback, diversification
├── train_model.py                 Rebuilds the JSON artifact from the training CSV
├── templates/                     HTML templates rendered by Flask
│   ├── base.html                  Shared responsive layout and account menu
│   ├── index.html                 Home page
│   ├── login.html                 Login form
│   ├── register.html              Registration form
│   ├── search.html                Trip input form
│   ├── recommendations.html       Ranked recommendation cards and feedback controls
│   ├── results.html               Destination details, weather, map, hotels, travel links
│   ├── explore.html               Search/filter the complete destination catalogue
│   ├── marvels.html               Engineering and natural wonders section
│   ├── wildlife.html              Zoos and wildlife section
│   └── itinerary.html             Day-wise starter itinerary
├── static/css/style.css            Visual theme and responsive layout
├── tests/test_recommendation_engine.py Unit tests for ranking behavior
└── docs/                           Research manuscript in Markdown, Word, and PDF
```

## 5. Where the data is stored

| Data | Location | What it contains |
|---|---|---|
| Destinations | `data/destinations.csv` | 227 curated destination records, including major forts, beaches and other places across India |
| Attractions/places | `data/places.csv` | 339 named attraction records with category and approximate coordinates |
| ML examples | `data/recommendation_training.csv` | 4,250 synthetic preference/budget/duration examples with destination labels |
| Model artifact | `models/trip_recommender.json` | Generated example rows used for neighbour-style similarity |
| App database | `smart_travel.db` | Created beside `app.py`; stores users, synced catalogue tables and feedback |
| Accommodation | `data/hotels.csv` | Empty in this build. Real property results are opened in external search tools instead of inventing names/prices/ratings |

The database is local to the computer unless the project is deployed. For a new installation, the database is created at startup. If preserving registered accounts from an old version, back up the old `smart_travel.db` and copy it into the new project folder before first run. The CSV catalogue is the source of truth; older catalogue-only rows are removed during sync while user accounts remain.

## 6. How the recommendation engine works

### Step A — Read the user's trip brief

The backend receives origin, selected interest, total budget, days, travellers and date. It estimates a **budget per person per day**:

`budget per person per day = total budget ÷ trip days ÷ number of travellers`

This is used for ranking only; it is not a live quote for transport, hotels, food, or tickets.

### Step B — Compare training examples

`train_model.py` reads synthetic rows from `data/recommendation_training.csv` and writes the samples into `models/trip_recommender.json`. At recommendation time the engine compares budget, duration and interest with labelled examples, retrieves a group of nearest profiles, and calculates destination votes from the examples.

### Step C — Score every destination

The engine calculates interpretable signals for:

- Interest match — does the location match beaches, forts, history, wildlife, spiritual travel, etc.?
- Budget fit — how close is the approximate daily cost to the user's budget per person per day?
- Trip-duration fit — does the entered number of days suit the destination's suggested duration?
- Training-profile similarity — how strongly do nearby synthetic profiles vote for the destination?
- Proximity — how close is the destination to the selected origin in straight-line distance?
- Weather fit — only when the chosen date is inside the forecast window and a forecast is actually returned.
- User feedback — whether this logged-in user has previously liked or disliked the destination.

The code combines these factors into a ranking score and displays the components. Category diversification limits repetitive top results when alternatives exist.

**Important scientific limitation:** the training examples are synthetic. A 92/100 match score is a relative rank from this project's hand-designed scoring formula. It is not a 92% probability, not a claim of 92% accuracy, and not validated evidence that the trip will fit the budget.

## 7. How the map animation works

1. Leaflet draws the selected destination and named place markers using the local catalogue coordinates.
2. When the user selects **Animate here**, the browser calls `/api/geocode` for the selected name plus its destination context.
3. The server tries a cached, rate-limited Nominatim search. If the result is not available or does not match sufficiently, the curated coordinate is used as fallback.
4. The browser requests a road geometry from the OSRM demo route endpoint for shorter, drivable routes.
5. The road shape is drawn. A marker moves along it with JavaScript animation frames.
6. At the end, `map.flyTo()` zooms into the chosen coordinate and opens its pin.
7. For very long journeys, islands, or unavailable road routes, the website shows a dashed straight-line/long-distance preview rather than pretending it is a road route. Google Maps opens for final navigation.

No geocoder can guarantee a door-level coordinate from a name alone. Forts, offshore islands, beaches, hill trails, and large cave sites may have separate access gates, boat departures or trailheads. Google Maps directions and local visitor notices should be checked before travel. The public Nominatim and OSRM demo services are rate-limited and must not be used as production-scale backend services.

## 8. How hotels and transport work

The prior sample hotels were fabricated and could mislead users. This version deliberately removed them from user-facing results. It opens:

- Google Maps search for hotels near the destination;
- Booking.com search results for the destination;
- IRCTC train-ticket search;
- Google Flights search;
- Google Maps route directions.

These links do not reserve, pay for, or guarantee availability. Dates, station/airport, occupancy, fares, taxes, travel restrictions, booking terms and cancellation rules must be confirmed on the external provider's website. To show real in-app hotel cards and live prices later, the project would need a permitted hotel API/provider and a clear data/licensing plan.

## 9. Main web routes

- `/` — home page.
- `/register` and `/login` — account registration and login.
- `/logout` — ends the current session.
- `/search` — collects travel preferences and forwards to results or recommendations.
- `/recommendations` — ranks destinations and displays reasoning/factor scores.
- `/recommendation-feedback` — stores a positive or negative signal for the logged-in user.
- `/results` — selected destination, place pins, weather, route preview, lodging links and travel options.
- `/explore` — search/filter the full location catalogue by type/category.
- `/marvels` — engineering marvels and natural wonders.
- `/wildlife` — zoos and wildlife.
- `/itinerary` — day-wise starter itinerary.
- `/api/geocode` — controlled, cached, best-effort geocoding for catalogue sites only.

## 10. Installation and usage (Windows + VS Code)

1. Extract the ZIP.
2. In VS Code choose **File → Open Folder**, then select the inner `TripGenie_Project` folder—the folder containing `app.py` and `requirements.txt`.
3. Choose **Terminal → New Terminal**.
4. Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

5. Rebuild the model after changing the training CSV:

```powershell
py train_model.py
```

6. Start Flask:

```powershell
py app.py
```

7. Open `http://127.0.0.1:5000` in Chrome. Keep the terminal open; stop the server with Ctrl+C. Alternatively, double-click `RUN_TRIPGENIE.bat`.

### Mobile browser test

Connect the phone and PC to the same Wi-Fi. On the PC, run `ipconfig` in PowerShell and find the active Wi-Fi adapter's IPv4 address. On the phone, visit `http://<PC-IPv4>:5000`. Do not use `127.0.0.1` on the phone: that points back to the phone itself. Allow the Python app through Windows Firewall on a private network if requested. For use outside that Wi-Fi, deploy with HTTPS and a production server.

## 11. How to demonstrate the project

1. Register a new account and log in.
2. Open **Explore locations** and filter by Forts or Beaches; search for a known site such as Raigad Fort, Tarkarli, Ajanta Caves, or Lonar Crater.
3. Open Plan a trip, choose Pune as origin, enter a budget/duration, select Forts or another interest, and set a date.
4. Leave destination blank and generate recommendations. Show the factors that explain why a destination ranked highly.
5. Use “More like this” or “Not for me”, then show how stored feedback affects a subsequent result set.
6. Open a destination result. Show the weather panel, layer control, selected-location pin, Animate here button, distance/time when OSRM returns a route, and Google Maps direction link.
7. Open hotel links, train search or flight comparison to demonstrate that real searches happen at the source provider instead of showing fake offers.
8. Open the same site on a phone using the PC's private IPv4 address.

## 12. Current limitations and future work

- The catalogue is a curated educational list, not an exhaustive inventory of every fort or destination in India. Fort access, permits, opening hours, treks, boat services and restrictions can change; confirm locally.
- Some coordinates are curated approximations. Nominatim refinement is best-effort; final navigation should be checked against Google Maps and local access information.
- Public map tiles, geocoding, OSRM routing and weather services require internet and have usage terms/limits. They are appropriate for an educational demo, not a production traffic guarantee.
- The catalogue image URLs are illustrative and some are reused; a future step is to curate one properly licensed, verified image per location (for example, from Wikimedia Commons with attribution) and audit all photo-to-place matches.
- No verified live hotel inventory or live fares are stored. Booking is external.
- The recommender uses synthetic labelled examples and hand-designed weights. A proper research evaluation needs a licensed/public real dataset or controlled participant study, train/test methodology, ranking metrics (e.g., NDCG@K/Precision@K), user evaluation, and a comparison baseline.
- For deployment, set `FLASK_SECRET_KEY` to a strong environment secret, use a production WSGI server with HTTPS, add CSRF protection and request limits, review password and account recovery handling, and never run Flask debug mode publicly.

## 13. Suggested future research evaluation

A small study could compare a popularity/baseline ranker against TripGenie's hybrid score. Prepare labelled relevance judgements from documented user preferences or a properly licensed dataset; freeze a train/test split; report Precision@5, Recall@5, NDCG@5, coverage and intra-list diversity; evaluate the map/place pin error separately against verified coordinate references; and record average response time/API failure rate. Report sample size and confidence limits, and do not claim improved accuracy until measurements support it.

## 14. Useful official/service references

- Maharashtra Tourism — forts: https://aai-portal.maharashtratourism.gov.in/tourist-intrests/forts/
- Maharashtra Tourism — beaches: https://aai-portal.maharashtratourism.gov.in/tourist-intrests/beaches/
- UNESCO World Heritage Centre: https://whc.unesco.org/
- Google Maps URLs (works without a Maps API key for outbound URLs): https://developers.google.com/maps/documentation/urls/get-started
- OpenStreetMap Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/
- IRCTC: https://www.irctc.co.in/nget/train-search
- Google Flights: https://www.google.com/travel/flights/
- Open-Meteo: https://open-meteo.com/
- Leaflet: https://leafletjs.com/

## 15. Project-report summary and viva preparation

### Problem statement

Travellers often need to compare several websites to discover suitable destinations, estimate a budget, understand what there is to see, check weather, find a route, and locate accommodation or transport booking sites. A single static list of places does not personalize those choices, while fake hotel cards or unsupported live-price claims can mislead the traveller.

### Objectives

- Build an easy, responsive website for destination discovery and trip planning.
- Recommend places using the traveller's budget, interests, duration, origin and available context.
- Explain the recommendation score rather than presenting an unexplained rank.
- Provide a curated Maharashtra-first catalogue with wider Indian destinations.
- Show locations on an interactive map, animate route previews, and provide external verified-navigation links.
- Avoid presenting sample hotels as real offers; redirect the user to live source searches instead.
- Keep data files editable and feedback stored for later personalization.

### Existing-system vs proposed-system comparison

- **Simple travel browsing:** users visit separate travel pages → TripGenie combines a destination catalogue and trip form.
- **Generic lists:** same locations are returned regardless of budget/interest → TripGenie ranks candidates against user preferences and displays factor explanations.
- **Unverified sample hotels:** the UI may show invented names/prices → TripGenie opens hotel-provider search results instead.
- **Map as an image only:** no selectable route → TripGenie displays named pins, layer selection, route shape and animated movement where routing data is available.
- **No feedback:** preferences are not retained → signed-in users can like/dislike suggestions and those signals are stored.

### Text architecture diagram

```text
User (desktop/mobile browser)
        |
        v
Flask routes + Jinja templates (app.py, templates/)
        |                          |
        v                          v
SQLite database              Recommendation engine
(users, catalogue,           (training examples + context
 feedback)                    and scoring factors)
        |                          |
        +------------+-------------+
                     v
       Destination / itinerary results
                     |
           +---------+----------+
           |         |          |
         Leaflet  Weather     Outbound links
         + OSRM   Open-Meteo   Google Maps/IRCTC/
         + OSM                   Flights/Booking
```

### A simple 60-second presentation script

“TripGenie is a responsive travel-discovery and trip-planning prototype built with Python Flask, HTML, CSS, JavaScript and SQLite. A user enters their origin, budget, trip duration, traveller count, date and interests. The recommendation engine compares the preferences with labelled synthetic examples and combines that similarity with interest, budget, duration, proximity, forecast and previous feedback factors. It shows why each location was recommended. The catalogue is stored in CSV files and synchronized into SQLite. The result page shows the destination, nearby named pins, a map route preview, weather when the service is available, accommodation search links, train/flight search links and a day-wise starter itinerary. The map and external booking services are not sold by TripGenie itself. The current project is an educational prototype; real traveller data, live accommodation integration and measured recommendation evaluation remain future work.”

### Likely viva questions

**Q1. Why did you use Flask?**  Flask is a lightweight Python web framework that connects form submissions, the recommendation logic, SQLite, and the HTML templates.

**Q2. Where is the training data?**  In `data/recommendation_training.csv`. The generated neighbour-style example artifact is `models/trip_recommender.json` and is rebuilt with `py train_model.py`.

**Q3. Is the recommender trained on real tourist data?**  No. The profiles are synthetic examples for demonstrating the pipeline. Real user-history data or a properly licensed dataset is needed to validate its quality.

**Q4. What does a score such as 85 mean?**  It is a relative score from the weighted ranking formula. It is not an 85% probability or 85% accuracy.

**Q5. Why does TripGenie use CSV and SQLite?**  CSV makes catalogue and training rows easy to edit, while SQLite stores users, synced catalogue records and user-feedback signals for the local application.

**Q6. Does TripGenie book hotels, trains or flights?**  No. It links to external search providers. The visitor checks real availability, totals and terms and completes any booking on that provider's website.

**Q7. Does the map require a Google API key?**  The embedded map is Leaflet with third-party tile layers; Google Maps buttons are outbound Maps URLs. They do not need a Google Maps Platform key. The tile/geocoding/routing providers have their own terms and limits.

**Q8. Why can a route animation be a straight line?**  The free public routing endpoint can fail, be rate limited, or have no drivable route for long journeys/islands. The UI labels this fallback rather than misrepresenting it as road navigation.

**Q9. How do you make the site available on mobile?**  Responsive pages are served from the computer. On the same Wi-Fi, the phone enters the computer's private IPv4 address and port 5000. Public access requires secure hosting and HTTPS.

**Q10. What is the biggest limitation?**  Catalogue coverage/coordinates and the synthetic recommendation data have not been exhaustively validated. Recommendations and routes are aids for planning, not guarantees.
