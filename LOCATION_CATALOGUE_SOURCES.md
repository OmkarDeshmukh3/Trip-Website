# Expanded TripGenie location catalogue — provenance and limits

This release expands the editable CSV-based catalogue to cover 227 destination records and 339 attraction/place records. It adds a curated set of 68+ major Maharashtra forts/fort-treks, 39 Maharashtra coastal/beach entries, additional Maharashtra nature/pilgrimage/wildlife places, and popular destinations across India.

## Reference sources used for selection and general context
- Maharashtra Department of Tourism, forts: https://aai-portal.maharashtratourism.gov.in/tourist-intrests/forts/
- Maharashtra Department of Tourism, beaches: https://aai-portal.maharashtratourism.gov.in/tourist-intrests/beaches/
- Maharashtra Tourism official site and destinations: https://maharashtratourism.gov.in/
- Raigad District Administration, forts in Raigad district: https://raigad.gov.in/en/tourist-place/forts-in-raigad/
- UNESCO World Heritage Centre for Ajanta, Ellora and other listed heritage properties: https://whc.unesco.org/
- Google Maps URLs documentation for no-key external directions: https://developers.google.com/maps/documentation/urls/get-started
- OpenStreetMap Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/

## Important data-quality note
This is a curated educational catalogue, not an exhaustive official record of every fort, beach, temple, wildlife area or destination in India. The state has many hundreds of forts, including private, restricted, remote, partly ruined and locally named sites, and a single reliable official open master list is not available here. The list therefore says “major forts” rather than claiming literally all forts. Some coordinates are approximate starting/landmark pins. When a user opens a result, TripGenie makes a best-effort, cached geocoding request for the selected location and falls back to the curated point if no suitable result is found. Open Google Maps for final navigation, permissions, entry points and current access conditions.

## Accommodation accuracy
Synthetic hotel names, coordinates, prices and ratings have been removed from the user-facing results and CSV. TripGenie now directs visitors to live Google Maps and Booking.com search results. Those links are neither endorsements nor confirmed availability; users should verify the real property's details, total price and cancellation terms.

## Routing and maps
- Carto Voyager is the default street basemap; OpenStreetMap standard streets and Esri World Imagery are alternative layers. All must retain provider attribution and comply with usage policies.
- Route previews use the public OSRM demo service on a best-effort basis. It is rate-limited and not intended for production navigation. If road routing is unavailable or a route is too long, the interface displays a dashed straight-line preview and does not label it as a road route.
- Maps URLs open Google Maps without a Maps API key; this does not embed a Google map inside TripGenie.

## How to expand the catalogue
Edit `data/destinations.csv` and add one destination row with name, region/state, description, category, approximate coordinates, budget estimate, ideal duration, interest tags and image URL. Add one or more `data/places.csv` rows with the destination's exact `location` name and named attraction coordinates. Keep names consistent across both files. On the next app start, the CSV data synchronizes into `smart_travel.db`. Use verified sources for new coordinates and access information.
