TRIPGENIE — MAHARASHTRA TRAVEL DISCOVERY PROJECT

FULL PROJECT WALKTHROUGH
- Read PROJECT_EXPLANATION.md for the complete architecture, ML scoring workflow, data-storage map, route-animation flow, limitations, test/demo script, and viva preparation notes.

QUICK START (WINDOWS)
1. Extract the ZIP. Open the inner `TripGenie_Project` folder in VS Code.
2. Double-click RUN_TRIPGENIE.bat to install dependencies, rebuild the model when requested, open Chrome, and start Flask. Or use VS Code Terminal: `py -m pip install -r requirements.txt`, `py train_model.py`, `py app.py`.
3. On this PC open `http://127.0.0.1:5000`. Keep the terminal open while the site is running. Stop with Ctrl+C.
4. If Chrome does not open automatically, type the local URL in Chrome yourself.

USE ON MOBILE
- Read MOBILE_ACCESS.txt. The Flask app listens on 0.0.0.0, so another device on the same Wi-Fi can reach it through this PC's private IPv4 address. On phone use `http://<PC-IPv4>:5000`, not 0.0.0.0 and not 127.0.0.1. Allow Python through Windows Firewall on a Private network if prompted. For internet access outside your Wi-Fi, deploy the app securely to a host.

DATA STORAGE
- `smart_travel.db`: local SQLite database, accounts and destination/place/hotel rows. It is created when app.py starts; it is stored beside app.py. If preserving accounts from an older version, back up and copy the older database into this folder before the first run.
- `data/destinations.csv`: destination coordinates, destination details, category, estimated daily budget and interest tags.
- `data/places.csv`: tourist attractions, forts, caves, zoological parks and approximate coordinates. The Maharashtra fort list is curated but not exhaustive.
- `data/hotels.csv`: fictional, clearly-labelled sample hotel options and approximate route points; these are not verified properties or live prices.
- `data/recommendation_training.csv`: synthetic training profiles. These are demo examples, not real traveller data.
- `train_model.py`: rebuilds the prototype model from the CSV. Run `py train_model.py` after changing training data.
- `models/trip_recommender.json`: generated KNN training-example artifact.
- `recommendation_engine.py`: hybrid ranker with explainable factors for interest, budget, duration, training-profile similarity, straight-line proximity, forecast fit and feedback. Scores are relative rankings, not probabilities, validated accuracy, or a guarantee that a trip fits the total budget.
- `recommendation_feedback` in SQLite: stores each logged-in user's `more like this` / `not for me` feedback. Feedback is applied to that user's subsequent recommendations and is filtered by interest when a specific interest is selected.
- `tests/test_recommendation_engine.py`: six functional unit tests. Run `py -m unittest discover -s tests -v`.
- `DATA_QUALITY_AND_RESEARCH_GAPS.md`: implementation gap register and unresolved data/validation risks.
- `docs/TripGenie_Research_Manuscript.docx` and `.pdf`: research-informed technical manuscript draft. Review authorship/affiliation and collect real evaluation evidence before submission; not a peer-reviewed or published paper.

MAPS, WEATHER AND ANIMATION
- Leaflet renders the map in TripGenie. Satellite tiles use Esri; street tiles use OpenStreetMap. Internet is required. Follow each provider's attribution and usage terms.
- Google Maps buttons open consumer Maps URLs for directions/search. Google Maps URLs do not need a Maps Platform API key and work cross-platform; they hand off navigation to Google's app/browser. The website does not embed Google Maps Platform's JavaScript map. Embedded Google Maps JavaScript/Embed API usage has separate setup/billing or key requirements depending on API.
- Weather uses Open-Meteo and requires internet. Forecast may be temporarily unavailable.
- Road route animation calls the public OSRM demo routing service on demand. It's rate-limited/best-effort and not suitable for production. A dashed straight-line fallback is explicitly labelled if road routing fails.

TRAIN/FLIGHT OPTIONS
- Trip results link to the IRCTC train-ticket search page and Google Flights search for the selected origin/destination. These are external-provider links, not in-site transactions; users must enter travel dates/stations and verify fare, availability and terms on the provider's site.

MAHARASHTRA LOCATIONS
- Includes Ajanta and Ellora caves, the Kailasa Temple, Lonar impact crater, Karla Caves, Daulatabad Fort, additional curated hill forts and a starter list of major zoological parks in Pune, Mumbai, Nagpur, Chhatrapati Sambhajinagar, Kolhapur and Pimpri-Chinchwad. Zoo list includes venues shown in Maharashtra government environment statistics; confirm venue status, hours, ticketing and restrictions with the official venue before visiting.
- TripGenie does not claim to list every fort in Maharashtra. Add more verified records by editing data/places.csv and data/destinations.csv.

ACCOUNTS AND DEPLOYMENT
- New passwords are hashed. A local secret-key fallback is for development only; set FLASK_SECRET_KEY before deployment. Flask debug mode is off by default. Do not deploy Flask's debug server as a production service.
- Account menu contains Log out under Account info.


GOOGLE MAPS SETUP (NO API KEY NEEDED FOR LINKS)
- The page's embedded map is Leaflet using satellite/street tile layers. The Google Maps buttons are regular Google Maps URLs for directions and place search; these do not require a Google Maps API key and can open the mobile app/browser: https://developers.google.com/maps/documentation/urls/get-started
- If you specifically want a Google Maps Platform map embedded inside the page, that is different from a link: it needs an active billing setup, the correct Maps API enabled and a restricted key. Do not put a live unrestricted key in this ZIP. Because your previous Google Cloud billing account showed as closed, keep using the no-key Google Maps links until the billing account is active.
- For the route map, keep internet access enabled; Leaflet code and tile layers are loaded online.

USEFUL SOURCE LINKS
- Maharashtra's major zoo list (government environment statistics): https://mahades.maharashtra.gov.in/files/publication/Environment_Statistics_Maharashtra.pdf
- Pune Rajiv Gandhi Zoological Park official site: https://punezoo.in/
- IRCTC train ticketing: https://www.irctc.co.in/nget/train-search
- Google Flights search: https://www.google.com/travel/flights/


LOCATION CATALOGUE UPDATE
- Browse 227 curated destination records in Explore locations and 339 attraction/place records.
- The CSV contains 69 records whose destination category is exactly Fort and 40 Beach records, plus other coastal, heritage, wildlife and nature records. It includes 68+ major Maharashtra forts/fort-treks and 39+ Maharashtra beach/coastal options, plus famous destinations across India. This is a curated educational list, not literally every fort or beach. This is NOT an exhaustive list of every fort in Maharashtra.
- Edit data/destinations.csv and data/places.csv to add/update names and coordinates. Matching places.csv rows must use the exact destination name as the location value.
- Fictional demo hotels have been removed from user-facing results. Use live Google Maps/Booking searches from the destination page to verify real properties, rates and availability.
- Results default to a clear street map and let the user switch to satellite. Route animations go to named attraction pins; when routing is unavailable, the dashed path is clearly labelled as a straight-line preview.
- Selected location pins are refined with a cached, rate-limited OpenStreetMap geocoding request where available; curated coordinates are the fallback. Google Maps navigation links remain available without a Google Maps API key.
- See LOCATION_CATALOGUE_SOURCES.md for source notes and caveats.
