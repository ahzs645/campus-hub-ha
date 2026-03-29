# Campus Hub HA

Home Assistant custom integration for exposing selected Home Assistant entities
to Campus Hub in a scoped, app-friendly JSON format.

This repo is the Home Assistant side of the integration. It does not replace
existing HA integrations like Bambu Lab, Weather, MQTT, ESPHome, or template
sensors. Instead, it sits on top of Home Assistant and exposes a filtered view
of entity data that Campus Hub can consume safely.

## Goals

- expose entity metadata and current state to Campus Hub
- avoid giving Campus Hub a full Home Assistant long-lived access token
- keep entity selection and exposure rules configurable inside Home Assistant
- provide a stable HTTP contract that Campus Hub Cloud can proxy server-side

## Current Scope

The initial scaffold provides:

- a config flow
- options for selecting which domains and entities are exposed
- a scoped API token
- read-only HTTP endpoints for health, entity discovery, and state reads

It does not yet provide:

- live streaming updates
- Home Assistant service calls
- a Campus Hub Cloud UI for managing Home Assistant connections

## Repository Layout

```txt
custom_components/campus_hub_bridge/
  __init__.py
  api.py
  config_flow.py
  const.py
  manifest.json
  translations/en.json
docs/
  campus-hub-cloud-integration.md
```

## Installation

1. Copy `custom_components/campus_hub_bridge` into your Home Assistant
   configuration directory under `custom_components/`.
2. Restart Home Assistant.
3. Go to `Settings -> Devices & Services -> Add Integration`.
4. Search for `Campus Hub Bridge`.
5. Copy the generated API token from the setup form and keep it for Campus Hub.

## Configuration

During setup and in options you can configure:

- `API token`: the scoped token Campus Hub will use
- `Campus Hub URL`: optional reference to the dashboard/app base URL
- `Included domains`: comma-separated domain allowlist, for example
  `sensor, binary_sensor, camera, media_player`
- `Entity allowlist`: optional comma-separated exact entity IDs to include
- `Expose attributes`: whether full entity attributes are returned

## API Endpoints

All endpoints use:

```txt
Authorization: Bearer <api_token>
```

### Health

```txt
GET /api/campus_hub_bridge/health
```

### Entity Discovery

```txt
GET /api/campus_hub_bridge/entities
```

Returns the currently exposed entity catalog.

### Current State

```txt
GET /api/campus_hub_bridge/state
GET /api/campus_hub_bridge/state?entity_id=sensor.office_temp&entity_id=camera.front_door
GET /api/campus_hub_bridge/state?entity_ids=sensor.office_temp,camera.front_door
```

Returns current state payloads for the requested entities, limited to the
configured allowlist.

## Campus Hub Cloud

The app-side plan lives in
[docs/campus-hub-cloud-integration.md](/Users/ahmadjalil/github/campus-hub-ha/docs/campus-hub-cloud-integration.md).

