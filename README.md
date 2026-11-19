# Ninjas ToDo

Ninjas ToDo reminds you about your open Home Assistant shopping-list items when your selected person or device tracker enters a supermarket in Portugal.

## Features

- Select a person or device tracker and a Companion App notification service during setup.
- Select one or more brands: Continente (including Modelo and Bom Dia), Pingo Doce, Auchan, Lidl, Makro, Intermarche, Aldi, Mercadona, and El Corte Inglés.
- Finds matching locations from OpenStreetMap and checks a 120 m radius around each location.
- Reads open items from the built-in `todo.shopping_list` entity.
- Refreshes the location dataset daily and provides buttons to refresh or clear its local cache.
- Creates no Home Assistant zones. Locations are stored by this integration, so zone limits and zone cleanup are not an issue.

## Installation

### HACS

Add `https://github.com/noesisaoliveira/ninjas_todo` as a custom integration repository in HACS, then install **Ninjas ToDo** and restart Home Assistant.

### Manual

Copy `custom_components/ninjas_todo` into the `custom_components` directory of your Home Assistant configuration and restart Home Assistant.

## Configuration

1. In **Settings > Devices & services**, select **Add integration** and search for **Ninjas ToDo**.
2. Choose the person or device tracker whose location is supplied by the Home Assistant Companion App.
3. Choose that phone's `notify.mobile_app_*` service and the supermarket brands to monitor.
4. Confirm that your shopping list is available as `todo.shopping_list`.

The integration uses the selected entity's latitude and longitude attributes. Home Assistant location permissions and mobile background-location settings must allow location updates.

## Controls

The Ninjas ToDo device provides two buttons:

- **Refresh supermarket locations** fetches a current dataset from OpenStreetMap.
- **Clear location cache** removes the downloaded dataset. Reminders resume after the next refresh (or after pressing the refresh button).

The integration enforces a 30-minute notification cooldown and sends a reminder only when the tracked entity newly enters the 120 m radius. It does not create, rename, or delete Home Assistant zones.

## Location data and privacy

Supermarket locations are queried from the Overpass API using OpenStreetMap data. The location dataset is cached locally in Home Assistant and refreshed every 24 hours. OpenStreetMap data is available under the Open Database License; see [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright). The integration sends the selected entity's coordinates only to Home Assistant's local geofence check; coordinates are not sent to Overpass. Overpass requests contain the Portugal-wide supermarket query, not the user's location.

Overpass is a community service and may occasionally rate-limit or be unavailable. When a cached dataset exists, it remains usable if a refresh fails.

## Supported brands

Brand matching uses the OpenStreetMap `brand`, `name`, and `operator` tags. Coverage depends on community mapping and may vary. The Continente option also matches Modelo and Bom Dia; Auchan matches the former Jumbo name; accented spelling variants are normalized.

## Development

The custom integration is in `custom_components/ninjas_todo`. Home Assistant serves its local brand images from `custom_components/ninjas_todo/brand/`; `icon.svg` is the scalable source artwork. HACS does not publish an integration to the default store automatically; the repository must be added as a custom repository, and releases must be published by a maintainer.
