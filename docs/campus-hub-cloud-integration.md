# Campus Hub Cloud Integration Plan

This document defines how `campus-hub-ha` should connect to
`campus-hub-cloud`.

## Integration Model

The Home Assistant side is responsible for:

- selecting which entities are exposed
- issuing a scoped token for Campus Hub
- returning filtered state payloads over HTTP

The Campus Hub Cloud side should be responsible for:

- storing the Home Assistant bridge URL and scoped token server-side
- proxying requests so the browser never needs the token
- offering a UI to browse entities and bind them to widgets

## Why This Split

Do not put a Home Assistant token directly into widget config in the browser.

That would expose your Home Assistant bridge token to anyone who can inspect
frontend traffic or exported configs.

The right pattern is:

1. Home Assistant exposes `campus_hub_bridge`
2. Campus Hub Cloud stores the bridge credentials privately
3. Campus Hub widgets call Campus Hub Cloud
4. Campus Hub Cloud proxies to Home Assistant

## Proposed Campus Hub Cloud Changes

### 1. New connection model

Add a Home Assistant connection object in the app/backend:

```json
{
  "name": "Home Lab",
  "baseUrl": "http://homeassistant.local:8123/api/campus_hub_bridge",
  "apiToken": "stored-server-side-only",
  "workspaceId": "optional",
  "defaultPollIntervalSeconds": 15
}
```

### 2. New server routes

Add server-side routes such as:

```txt
GET /api/integrations/home-assistant/:connectionId/health
GET /api/integrations/home-assistant/:connectionId/entities
GET /api/integrations/home-assistant/:connectionId/state?entity_id=...
```

Each route should:

- load the stored connection
- attach `Authorization: Bearer <token>`
- fetch from Home Assistant
- return the result to the browser

### 3. Widget update

Extend the existing Home Assistant widget so it supports an HTTP mode:

```json
{
  "mode": "http",
  "connectionId": "home-lab",
  "entityIds": [
    "sensor.bambu_lab_print_progress",
    "camera.front_door"
  ],
  "pollIntervalSeconds": 15
}
```

The current Socket.IO bridge mode can stay for live updates, but the HTTP mode
is simpler and should be the default integration path.

### 4. Admin UI

Add a page or modal in `campus-hub-cloud` to:

- create a Home Assistant connection
- test the bridge health endpoint
- browse exposed entities
- insert entity IDs into widget config

## API Contract

### Health

```txt
GET /api/campus_hub_bridge/health
```

Used by the app to validate credentials and exposure settings.

### Entities

```txt
GET /api/campus_hub_bridge/entities
```

Used by the app to build an entity picker.

### State

```txt
GET /api/campus_hub_bridge/state
GET /api/campus_hub_bridge/state?entity_id=sensor.office_temp&entity_id=camera.front_door
```

Used by widgets and previews to fetch current state.

## Suggested Configuration UX

### In Home Assistant

- install the integration
- choose included domains
- optionally narrow to exact entity IDs
- copy the scoped API token

### In Campus Hub Cloud

- paste the base URL and token once into a connection form
- test the connection
- browse entities from that connection
- select entity IDs for the widget

## Next Build Step

The next implementation step should be in `campus-hub-cloud`:

- add a server-side Home Assistant proxy
- add a connection model/table
- add HTTP mode to the existing Home Assistant widget

