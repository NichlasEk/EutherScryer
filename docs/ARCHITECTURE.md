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
