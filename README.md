# Ninjas ToDo

Ninjas ToDo reminds you about your open Home Assistant shopping-list items when your selected person or device tracker enters a supermarket in Portugal.

## Features

- Select a person or device tracker and a Companion App notification service during setup.
- Select one or more brands: Continente (including Modelo and Bom Dia), Pingo Doce, Auchan, Lidl, Makro, Intermarche, Aldi, Mercadona, and El Corte Inglés.
- Finds matching locations from OpenStreetMap and checks a configurable radius around each location (120 m by default).
- Reads open items from the built-in `todo.shopping_list` entity.
- Refreshes the location dataset daily and provides buttons to refresh or clear its local cache.
- Provides a **Query 1Km Now** sensor with the nearby supermarket count and matching locations as attributes.
- Creates no Home Assistant zones. Locations are stored by this integration, so zone limits and zone cleanup are not an issue.

## Installation

### Required: built-in Shopping list integration

Ninjas ToDo reads open items from Home Assistant's built-in Shopping list integration. Set it up before configuring Ninjas ToDo:

1. In Home Assistant, go to **Settings > Devices & services**.
2. Select **Add integration**.
3. Search for and select **Shopping list**.
4. Follow the setup flow. Confirm that `todo.shopping_list` exists in **Developer Tools > States**.

See the [Home Assistant Shopping list documentation](https://www.home-assistant.io/integrations/shopping_list/) for details.

### HACS

Add `https://github.com/noesisaoliveira/ninjas_todo` as a custom integration repository in HACS, then install **Ninjas ToDo** and restart Home Assistant.

### Manual

Copy `custom_components/ninjas_todo` into the `custom_components` directory of your Home Assistant configuration and restart Home Assistant.

## Configuration

1. In **Settings > Devices & services**, select **Add integration** and search for **Ninjas ToDo**.
2. Choose the person or device tracker whose location is supplied by the Home Assistant Companion App.
3. Choose that phone's `notify.mobile_app_*` service, supermarket brands, and detection radius in meters (120 m by default).
4. Confirm that your shopping list is available as `todo.shopping_list`.

The integration uses the selected entity's latitude and longitude attributes. Home Assistant location permissions and mobile background-location settings must allow location updates.

## Controls

The Ninjas ToDo device provides three buttons:

- **Refresh supermarket locations** fetches a current dataset from OpenStreetMap.
- **Clear location cache** removes the downloaded dataset. Reminders resume after the next refresh (or after pressing the refresh button).
- **Test phone notification** sends a sample notification through the selected Companion App service without requiring a supermarket entry or shopping-list items.

The **Query 1Km Now** sensor reports how many selected supermarkets are within 1 km of the configured tracker. Its `locations` attribute lists each match with its name, brand, distance, and coordinates. It updates when the tracker moves and when the cached supermarket dataset changes. In **Developer Tools → States**, inspect `sensor.ninjas_todo_query_1km_now` to see the result.

The integration queues a reminder when the tracked entity enters the configured radius, including when it is already inside at startup. It rechecks on tracker and shopping-list changes and once per minute. If the list is empty, a service fails, or the 30-minute notification cooldown is active, the reminder stays pending while the tracker remains inside. A successful send completes the reminder for that visit; leaving the radius cancels any pending reminder. Missing GPS updates do not count as leaving. The periodic check uses the latest coordinates already in Home Assistant; it cannot force the phone to supply fresh GPS updates.

The cooldown helps prevent repeated notifications when GPS jitter moves the tracker across the radius edge. On iPhone, notifications are marked **time-sensitive**; allow Time Sensitive Notifications for Home Assistant in iOS notification settings if you want them to get through Focus modes. The integration does not create, rename, or delete Home Assistant zones.

### Troubleshooting missed reminders

1. Press **Test phone notification** to check the selected notification service.
2. Inspect the configured tracker in **Developer Tools > States** and confirm its latitude and longitude update while you travel. For a person entity, check that its location matches the phone's GPS tracker.
3. Inspect the **Query 1Km Now** sensor's `locations` attribute. The store must be in the downloaded dataset and within the configured detection radius, not just within 1 km. OpenStreetMap coordinates and GPS accuracy can affect detection; increase the radius if necessary.
4. Confirm that `todo.shopping_list` has open items. Enable debug logging for Ninjas ToDo from its integration menu and inspect Home Assistant logs for shopping-list errors, notification-service errors, or an active cooldown.

## Location data and privacy

Supermarket locations are queried from the Overpass API using OpenStreetMap data. The location dataset is cached locally in Home Assistant and refreshed every 24 hours. OpenStreetMap data is available under the Open Database License; see [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright). The integration sends the selected entity's coordinates only to Home Assistant's local geofence check; coordinates are not sent to Overpass. Overpass requests contain the Portugal-wide supermarket query, not the user's location.

Overpass is a community service and may occasionally rate-limit or be unavailable. When a cached dataset exists, it remains usable if a refresh fails.

## Supported brands

Brand matching uses the OpenStreetMap `brand`, `name`, and `operator` tags. Coverage depends on community mapping and may vary. The Continente option also matches Modelo and Bom Dia; Auchan matches the former Jumbo name; accented spelling variants are normalized.

## Development

Run `python -m unittest discover -s tests -v` for the notification regression tests. These execute the notification methods and setup callbacks with mocked Home Assistant dependencies; they do not verify a running Home Assistant instance or phone delivery.

The custom integration is in `custom_components/ninjas_todo`. Home Assistant serves its local brand images from `custom_components/ninjas_todo/brand/`; `icon.svg` is the scalable source artwork. HACS does not publish an integration to the default store automatically; the repository must be added as a custom repository, and releases must be published by a maintainer.
