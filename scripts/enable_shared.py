#!/usr/bin/env python3
"""Upgrade an already integrated explicit checkout to shared EutherNet state."""

import argparse
import pathlib
import shutil

root = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--oxide", type=pathlib.Path, required=True)
p.add_argument("--net", type=pathlib.Path, required=True)
a = p.parse_args()
http_path = a.net / "scripts/euthernet_http.py"
rust_path = a.oxide / "src/main.rs"
map_path = a.oxide / "webview/server-map.ts"
http = http_path.read_text()
rust = rust_path.read_text()
worldmap = map_path.read_text()


def change(text, old, new):
    if text.count(old) != 1:
        raise SystemExit("Integration anchor changed: " + old[:90])
    return text.replace(old, new)


if "scryer_runtime" not in http:
    http = change(
        http,
        "    config: dict[str, Any]\n",
        "    config: dict[str, Any]\n    scryer_runtime: Any = None\n",
    )
    http = change(
        http,
        "    def do_GET(self) -> None:\n        path = urlparse(self.path).path",
        """    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/euthernet/scryer":
            self.write_json(HTTPStatus.OK, self.scryer_runtime.snapshot())
            return""",
    )
    http = change(
        http,
        "    def do_POST(self) -> None:\n        path = urlparse(self.path).path",
        """    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/euthernet/scryer/control":
            try:
                if int(self.headers.get("Content-Length", "0")) not in range(1, 2049):
                    raise ValueError("bounded request required")
                payload = self.read_json()
                if not isinstance(payload, dict):
                    raise ValueError("object required")
                result = self.scryer_runtime.control(payload.get("command"), payload.get("ghost_id"))
                self.write_json(HTTPStatus.OK, result)
            except (ValueError, TypeError):
                self.write_error(HTTPStatus.BAD_REQUEST, "invalid Scryer control")
            except OSError:
                self.write_error(HTTPStatus.SERVICE_UNAVAILABLE, "Scryer state could not be persisted")
            return""",
    )
    http = change(
        http,
        "            self.write_json(HTTPStatus.OK, scryer_answer(self.config, payload, eutherverse_map(self.config)))",
        """            if self.scryer_runtime:
                if not self.scryer_runtime.model_allowed():
                    self.write_json(HTTPStatus.OK, {"ok": True, "source": "scryer-inventory", "answer": "Scryer is paused or disabled."})
                    return
                payload["node"] = self.scryer_runtime.conversation()
            self.write_json(HTTPStatus.OK, scryer_answer(self.config, payload, eutherverse_map(self.config)))""",
    )
    http = change(
        http,
        "    EutherNetHTTP.config = config\n",
        """    from scryer_world import ScryerWorld
    EutherNetHTTP.scryer_runtime = ScryerWorld(
        config["server"].get("state_root", "state"), lambda: eutherverse_map(config)
    )
    EutherNetHTTP.config = config
""",
    )
    http = change(
        http,
        "    server = ThreadingHTTPServer((host, port), EutherNetHTTP)\n",
        "    server = ThreadingHTTPServer((host, port), EutherNetHTTP)\n    EutherNetHTTP.scryer_runtime.start()\n",
    )
    http = change(
        http,
        "        server.server_close()",
        "        EutherNetHTTP.scryer_runtime.close()\n        server.server_close()",
    )
if '"/scryer/control"' not in rust:
    rust = change(
        rust,
        '        "/run" | "/preflight"',
        '        "/run" | "/preflight" | "/scryer/control"',
    )
    rust = change(
        rust,
        '        "/commands",\n        "/run",\n        "/ask",',
        '        "/commands",\n        "/run",\n        "/ask",\n        "/scryer",\n        "/scryer/control",',
    )
    anchor = "    fn euthernet_run_requires_host_admin_but_read_routes_do_not() {"
    rust = change(
        rust,
        anchor,
        anchor
        + """
        assert!(euthernet_request_requires_host_admin("POST", "/api/admin/euthernet/scryer/control"));
        assert!(euthernet_request_requires_host_admin("POST", "/api/admin/euthernet/scryer/control?source=map"));
        assert!(!euthernet_request_requires_host_admin("GET", "/api/admin/euthernet/scryer"));
        assert!(!euthernet_request_requires_eutherid("POST", "/api/admin/euthernet/scryer/control"));
        assert_eq!(euthernet_admin_upstream_path("/api/admin/euthernet/scryer").unwrap(), "/api/euthernet/scryer");""",
    )
if "onMap: (map)" not in worldmap:
    worldmap = change(
        worldmap,
        "  scryer = mountScryer(scryerAuth, cityRoot, sceneNodes);",
        """  scryer = mountScryer(scryerAuth, cityRoot, sceneNodes, { onMap: (map) => {
    if (roomMode === "city" && serverMap?.collected_at !== map.collected_at) {
      serverMap = map as ServerMap;
      buildCity(serverMap);
    }
  } });""",
    )
if (
    '      dismiss.onclick = () => { scryer?.dismiss(node.id); detailPanel.textContent = "Hypothesis dismissed; no infrastructure changed."; };'
    in worldmap
):
    worldmap = change(
        worldmap,
        '      dismiss.onclick = () => { scryer?.dismiss(node.id); detailPanel.textContent = "Hypothesis dismissed; no infrastructure changed."; };',
        '      dismiss.disabled = !scryer.canControl();\n      dismiss.onclick = async () => {\n        try { await scryer?.dismiss(node.id); detailPanel.textContent = "Hypothesis dismissed; no infrastructure changed."; }\n        catch { detailPanel.textContent = "Dismissal could not be confirmed."; }\n      };',
    )
if "def stop_scryer_service" not in http:
    http = change(
        http,
        "    EutherNetHTTP.scryer_runtime.start()\n",
        """    EutherNetHTTP.scryer_runtime.start()
    import signal
    def stop_scryer_service(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop_scryer_service)
""",
    )
# No mutation until every known anchor has been validated.
http_path.write_text(http)
rust_path.write_text(rust)
map_path.write_text(worldmap)
shutil.copytree(root / "src", a.oxide / "webview/scryer", dirs_exist_ok=True)
for filename in ("scryer.py", "scryer_world.py", "scryer_reports.py", "scryer_vox_bridge.py"):
    shutil.copy2(root / "backend" / filename, a.net / "scripts" / filename)
print("Shared state integration prepared; no services restarted.")

import subprocess
import sys
subprocess.run([sys.executable, str(root / 'scripts/extend_integration.py'), '--oxide', str(a.oxide), '--net', str(a.net)], check=True)
