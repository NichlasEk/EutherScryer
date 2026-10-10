# EutherScryer

A wandering, read-only inhabitant of the existing EutherVerse. Observe what
exists. Imagine what could exist. Never confuse the two.

This repository contains a working first vertical slice: a geometric Three.js
lantern, obstacle-aware navigation to inventory nodes, status-change reactions,
provenance-backed observations, translucent speculative Ghost Nodes, conversation,
and bounded restartable state. It integrates with EutherOxide's actual
`webview/server-map.ts`, using the existing E/F controls and custodian dialogue.

## Run the simulated world

```sh
npm ci # Node.js 22.6+ for the TypeScript test runner
npm test
npm run check
npm run demo -- --port 5193
```

Open http://127.0.0.1:5193. Scryer starts near the city entrance, visits a host,
pauses to observe it, and proposes testing independent recovery paths when the
inventory shows multiple hosted services. Allow roughly 25 seconds on a normal
renderer. F or clicking Scryer opens a grounded explanation. The event button
changes simulated service status. Pause and Disable work without the model.
Reloading restores the current position, observations, hypotheses and cooldown.
Reduced motion stops decorative oscillation and orbiting, retaining navigation.

`npm run build` writes the standalone simulation to `.local/demo-dist`.
Simulation requests are mocked locally; it never contacts the homelab.

## Integrate into EutherVerse

Read [the architectural findings](docs/ARCHITECTURE.md) first. Work on clean,
explicit staging copies of the existing EutherOxide and EutherNet repositories:

```sh
python3 scripts/integrate.py --oxide /path/to/staged/EutherOxide \
  --net /path/to/staged/EutherNet
```

The script checks known anchors, copies the renderer modules into
`webview/scryer`, reuses existing scene picking and custodian controls, and adds
a bounded Scryer persona to EutherNet's existing `/ask` handler. A shared observer
runs inside the existing EutherNet process. GET `/scryer` exposes filtered state;
POST `/scryer/control` requires the host's administrator permission. No new
daemon or unrestricted model tools. Mirror health uses one restricted SSH
identity that can only export checker metadata.
The normal Librarian path remains available. The script does not deploy,
restart services, or modify any other checkout.

Build the existing host with its normal toolchain after applying. Scryer's map
bundle can be checked independently of unrelated host frontend code:

```sh
npx tsc --noEmit --strict --skipLibCheck --moduleResolution bundler \
  --module esnext --target es2022 --allowImportingTsExtensions \
  /path/to/staged/EutherOxide/webview/server-map.ts
```

## Evidence and limits

See [validation](docs/VALIDATION.md) for what was actually exercised.

* Observations are facts about the **cached inventory**, not fresh health checks.
  Only bounded node identifiers, types, normalized status and typed relationships
  enter Scryer's state. Logs, credentials, paths, vault contents and port/SSH
  details are discarded. Unknown measurements stay unknown.
* A hypothesis explicitly records evidence, linked nodes, assumptions,
  uncertainty, benefit, risks and a suggested test. It has no deployment path.
  Dismissed ideas stay dismissed; disappearing supporting nodes/edges archive
  active ideas. Ghosts are in a separate render group and never enter topology.
* Deterministic exploration makes no model calls. Conversation can request at
  most one model interpretation per minute, persisted before sending. Backend
  concurrency is one, timeout 30 seconds, context 4096 and output 384 tokens.
  Free-text model output is marked unverified and cannot mutate state or run
  commands. Browser cancellation stops waiting; the server request remains
  bounded by its own timeout. Disabled AI falls back to grounded local dialogue.
* The owner can globally pause or disable the inhabitant and dismiss ideas.
  Server exploration continues with browsers closed. Stale inventory (>24 hours)
  stops new work.
  Authorization is checked before boot, periodically and before dialogue.
* Production memory is shared and persisted atomically in EutherNet's state
  directory (`scryer-state.json`, mode 0600), protected by a single-writer lock.
  Limits: 64 observations, 24 hypotheses, 32 queued events and 2000 visited IDs.
  Corrupt state pauses the observer; restarts preserve controls and progress.
  Only the standalone simulation uses browser-local memory.
* Optional spoken reports reuse EutherVox TTS; see [Vox reports](docs/REPORTS.md).
  No agent-to-agent messaging is enabled. No bounded documentation
  interface was found to safely reuse. A local Qwen backend is supported via
  existing EutherNet configuration; model availability is an independent gate.

The checkout is currently the disk root chosen by the owner. Its allowlist
`.gitignore` intentionally excludes all unrelated project directories, models,
staging copies, generated builds and local runtime data.

For an already integrated checkout, use `scripts/enable_shared.py --oxide PATH --net PATH`.
See [deployment evidence and rollback](docs/DEPLOYMENT.md).

[Evidence, investigations and mirror health](docs/IDEAS_AND_MIRROR.md) describes
the Find Scryer control, three hypothesis types and persisted owner reports.
