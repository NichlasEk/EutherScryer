# Architecture investigated 2026-10-09

Source of truth inspected over SSH: EutherOxide server commit
3ba1c25f0cd7bf59a32f87e4789e938b88639f49; EutherNet
3f7d5fa4c267656a80d261dd521ddba0f873387e.

* EutherVerse lives in EutherOxide/webview/server-map.ts, not a standalone
  EutherVerse repository. Three.js 0.184, PointerLockControls, Y-up world,
  deterministic type lanes (host x=-10, service x=8). SceneNode and nodeId
  picking drive E inspect / F enter and mobile inspection. Rooms rebuild
  cityRoot and sceneNodes. Existing movement has no collision solver.
* GET /api/admin/euthernet/map returns a cached inventory projection with
  nodes, typed directed edges, collected_at and service reports. hosts edges
  are host -> service; dependency edges are service -> dependency. Collection
  is a separate explicit POST /refresh; Scryer must never call it.
* Library qwen-desk shares custodianForm and POST /api/admin/euthernet/ask.
  This endpoint calls EutherNet answer_question, local fallback + configured
  local model /api/generate. Some desk copy still says planned. The code path
  exists; an actual model reply has not yet been verified in this session.
* The host authenticates ServerMap permission on both page and proxy. Mutations
  /run and /preflight need admin; /run additionally needs EutherID step-up.
  Scryer receives none of those capabilities. Existing ask injects broad
  inventory context, so Scryer needs a narrowly filtered persona branch there.
* EutherNet uses Python ThreadingHTTPServer, filesystem snapshots and systemd
  euthernet.service + refresh timer. EutherOxide has filesystem user state and
  a supervised host service. Reuse these, not a new daemon for this slice.
* No existing autonomous agent memory API or structured Librarian request API
  was found. First slice uses versioned, bounded per-user browser storage,
  validated only after authorization. It is browser-local, not shared global
  state. Autonomous work pauses when world is hidden/closed. Cross-browser
  shared persistence and always-on supervision remain later phases.

## Implementation plan

1. Pure deterministic state machine: project safe inventory, status-diff events,
   obstacle-aware routes, dwell/investigate, provenance-backed hypotheses.
2. Three.js geometric body and independent translucent hypothesis group; reuse
   picking and custodian form. Pause/disable controls independent of the model.
3. Bounded state restore, denied access cancellation, observation deduplication.
4. Narrow optional Scryer persona on existing ask endpoint with cooldown and
   no tools; free-text model output is explicitly unverified, never executed.
5. Simulated integration harness and regression tests, apply integration to an
   ignored copy of the actual server checkout and typecheck/build it.

No production deployment or service restart is necessary for local validation.
No private vault data, log bodies, paths, credentials, units, SSH or port data
are copied into Scryer's observations. Node identifiers are topology metadata;
status is reported inventory evidence, never a fresh health measurement.

## Shared production observer (implemented after the initial investigation)

The initial browser-local slice above has been superseded in production.
EutherNet now owns a bounded deterministic ScryerWorld thread, using its existing
state root and cached map. It polls inventory every 60 seconds and moves at
4 world units/second with obstacle avoidance matching native lane coordinates.
Routine observation makes no model calls. Its state is atomic, fsynced, bounded
and single-writer locked; SIGTERM enters clean shutdown. Invalid persisted state
pauses instead of silently starting another investigation.

The existing authenticated EutherOxide proxy exposes GET /scryer to ServerMap
users and POST /scryer/control only to administrators. Controls only affect the
observer. Browsers interpolate authoritative positions and preserve existing
E/F interaction, room transitions and the Librarian. Two browsers share one
world, memory and pause state. The model remains a bounded optional interpreter
on /ask and cannot perform operations or create real infrastructure.

## Evidence and owner investigations

The observer adds shared-dependency and recurring-status templates using the
same bounded filtered inventory. No model call is needed. Owner reports are
separate fields attached to immutable hypothesis evidence, persisted through the
existing administrator-only Scryer control route. Native focus and the Ideas
dialog reuse the existing scene nodes and camera; no alternate world is built.

The existing desktop backup check is reused through a restricted SSH metadata
export. A dedicated key is constrained by source address and a forced command,
with forwarding disabled. EutherNet reads that fixed export with a timeout and
cache; Scryer itself only sees normal filtered topology. See IDEAS_AND_MIRROR.md
for the freshness boundaries and removal instructions.
