# Deployment — 2026-10-09

Server: 192.168.32.186. Existing checkouts remain authoritative:

* EutherOxide: `e10015b` on `agent/euthernet-admin-boundary` (initial integration
  `922ad82`). Includes native rendering and administrator control authorization.
* EutherNet: `e9e91c2` on `agent/eutherid-stepup` (initial persona `5cfbe43`).
  Includes shared background state, bounded memory and read-only conversation.

Build using the existing frontend/WASM pipeline and `scripts/build-release.sh`.
Services are `systemctl --user ... euthernet.service` and the system service
`sudo systemctl ... eutherhost.service`. The former binds loopback port 8791;
the latter provides the authenticated page and API proxy.

Release evidence, build logs and rollback files are under
`/home/nichlas/releases/eutherscryer-20261009/` on the server. The initial complete
frontend and executable are in `rollback/dist` and `rollback/euther-oxide`;
`rollback/euthernet_http.py` is the original handler. Initial Git heads are in
`rollback/oxide-head` and `rollback/net-head`. Do not reset unrelated history.

To disable Scryer, use its administrator-only Disable control in EutherVerse.
It persists independently of the model and browser. To roll back integration,
stop the affected services, restore the original handler, executable and dist
from that rollback directory into their respective checkouts, and restart the
same services. Retain the fixed Scryer state file for inspection or later
restoration. Reconcile source commits separately before a subsequent build.

Production state is `EutherNet/state/scryer-state.json`, permissions 0600.
A server-side acceptance probe verified pause, clean EutherNet restart, exact
position/observations/ghosts restoration, and resume. The live Qwen persona
returned an interpretation with source `scryer-model`.

The screenshot supplied by the owner shows Scryer and its native dialogue.
Automated full interaction testing uses the real renderer with simulated
authorization and filtered cached topology; this is distinct from an automated
logged-in production browser test. No reusable production Firefox session was
available to the test runner. No authentication boundary was bypassed.

Optional TTS and structured Librarian requests remain unimplemented. Current
hypothesis generation is a deterministic shared-host recovery question; model
interpretations are explicitly unverified and never execution instructions.
