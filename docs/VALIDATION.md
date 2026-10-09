# Validation — 2026-10-09

## Passed

* Eleven TypeScript regression tests: authorization and revocation; projection
  stripping sensitive/unrecognized fields; collision-free routes; complete
  travel/inspect/hypothesis/conversation/restore cycle; event selection and
  missing destination recovery; pause/disable/staleness/corrupt memory;
  hypothesis dismissal/archive; exact read-only transport capability surface;
  queued/in-flight restore; removed edge support; Firefox fetch receiver.
* Four Python backend tests: allowlisted context; no request when AI disabled;
  token/context bounds and durable reservation/cooldown; malformed requests.
* Strict TypeScript check of Scryer and demo; production Vite demo build.
* Native EutherVerse server-map.ts + Scryer strict typecheck and esbuild bundle.
* Full EutherOxide frontend strict typecheck and Vite build using its own locked
  dependencies. The unchanged EutherCivet WASM rebuild and Rust host executable
  were not part of this frontend validation.
* Firefox desktop + mobile simulation: real rendered travel and ghost creation,
  conversation, reload persistence, simulated event, pause/disable, reduced-motion
  setting and no horizontal mobile overflow; zero JavaScript page errors.

## Integration evidence

The server checkout was clean before inspection. Source commits are recorded in
ARCHITECTURE.md. All implementation/build work uses a local ignored snapshot.
A read-only GET of the server's existing cached EutherNet map yielded 96 nodes
and 112 edges, timestamp 2026-10-09T17:13:11+00:00. Only identifiers, types,
statuses and edge endpoints/types were retained in the ignored local fixture.
No inventory refresh, service restart, deployment or live mutation was issued.

Firefox native-renderer integration passed against that filtered fixture:
approach Scryer, E inspect, F converse using the existing custodian overlay,
enter the EutherBooks room (Qwen desk present), leave and restore the inhabitant,
then revoke permission and verify fail-closed behavior. No JavaScript page
errors. The sole POST was the mocked conversation endpoint, never refresh/run.
A browser-specific fetch receiver bug was discovered here, fixed, and covered
by a regression test.

The configured local model was reachable and qwen3-coder:30b was installed.
A bounded read-only Scryer interpretation using the existing configuration
succeeded with source `scryer-model` after raising the initial 15-second timeout
to 30 seconds (client 35 seconds). It distinguished reported services/status
from unknown recovery independence. The probe ran from stdin with temporary
cooldown storage; no production code or configuration was changed. This verifies
the model adapter, not a deployed authenticated end-to-end conversation.

## Reproduce browser checks

Use a Python environment with Playwright and its Firefox browser installed.
`tests/browser_smoke.py` expects the demo on port 5193. `tests/host_smoke.py`
expects an instrumented local native renderer on port 5194 and a private,
filtered topology fixture in `.local/integrated/topology.json`. These tests
never authenticate to production and are separate from `npm test`.
Create the native harness with:

```sh
python3 scripts/prepare_host_smoke.py --oxide .local/eutheroxide
python3 -m http.server 5194 --bind 127.0.0.1 --directory .local/integrated
```

Set `FIREFOX_EXECUTABLE` if using an existing Firefox Playwright installation;
otherwise the tests use Playwright's installed Firefox. Screenshots and generated
artifacts remain under ignored `.local/`.

## Remaining delivery gates

Production deployment, authenticated live browser acceptance, shared server
persistence and an always-on observation service are not certified by local
simulation. Optional voice and structured Librarian documentation requests are
not implemented. These are explicit scope limits of this first vertical slice.
