#!/usr/bin/env python3
"""Install native focus/review UI and the fixed metadata-only mirror reader."""

import argparse
import pathlib
import shutil

p = argparse.ArgumentParser()
p.add_argument("--oxide", type=pathlib.Path, required=True)
p.add_argument("--net", type=pathlib.Path, required=True)
a = p.parse_args()
root = pathlib.Path(__file__).resolve().parents[1]
p = a.net / "scripts/euthernet_http.py"
s = (
    p.read_text()
    .replace(
        'self.scryer_runtime.control(payload.get("command"), payload.get("ghost_id"))',
        'self.scryer_runtime.control(payload.get("command"), payload.get("ghost_id"), payload.get("data"))',
    )
    .replace("range(1, 2049)", "range(1, 4097)")
)
p.write_text(s)
p = a.net / "scripts/euthernet_cli.py"
s = p.read_text()
if "from mirror_health import read_remote" not in s:
    s = s.replace(
        "import argparse\n",
        "import argparse\nfrom mirror_health import read_remote as mirror_health, describe as describe_mirror_health\n",
    )
    s = s.replace(
        "    eutherhost_backup = backup_health(snapshot)",
        "    mirror = mirror_health()\n    eutherhost_backup = backup_health(snapshot)",
    )
    old = """                "status": "configured",
                "detail": "Configured encrypted mirror on .88; local checksum checks exist, but their results are not collected by this map.","""
    new = """                "status": mirror["status"],
                "detail": describe_mirror_health(mirror),"""
    if old not in s:
        old = old.replace(
            "Configured encrypted mirror on .88; local checksum checks exist, but their results are not collected by this map.",
            "local checksum timer and desktop failure alert",
        )
    if old not in s:
        raise SystemExit("Mirror integration anchor changed")
    s = s.replace(old, new)
s = s.replace(
    "from mirror_health import read_remote as mirror_health\n",
    "from mirror_health import read_remote as mirror_health, describe as describe_mirror_health\n",
).replace(
    '"Mirror check: " + json.dumps(mirror, ensure_ascii=False, sort_keys=True)',
    "describe_mirror_health(mirror)",
)
p.write_text(s)
shutil.copy2(root / "backend/mirror_health.py", a.net / "scripts/mirror_health.py")
p = a.oxide / "webview/server-map.ts"
s = p.read_text()
if "function focusScryerEvidence" not in s:
    s = s.replace(
        "scryerAuth, cityRoot, sceneNodes, { onMap:",
        "scryerAuth, cityRoot, sceneNodes, { onFocus: focusScryerEvidence, onMap:",
    )
    s = s.replace(
        "serverMap?.collected_at !== map.collected_at",
        "(serverMap?.collected_at !== map.collected_at || JSON.stringify(serverMap?.nodes) !== JSON.stringify(map.nodes))",
    )
    anchor = "async function bootstrap(): Promise<void> {"
    fn = """function focusScryerEvidence(id: string): void {
  if (roomMode !== "city") leaveRoom();
  const node = sceneNodes.get(id);
  if (!node) return;
  controls.unlock();
  const target = node.position.clone();
  target.y = id.startsWith("scryer:") ? 3.5 : 2;
  // An explicit user camera move; no continuous tracking or decorative motion.
  // Choose an unobstructed offset around the target, never inside its body.
  for (let step = 0; step < 16; step++) {
    const angle = step * Math.PI / 8;
    const candidate = target.clone().add(new THREE.Vector3(Math.sin(angle) * 9, 4, Math.cos(angle) * 9));
    if ([...sceneNodes.values()].some(n => n.id !== id && Math.hypot(n.position.x - candidate.x, n.position.z - candidate.z) < 4.5)) continue;
    camera.position.copy(candidate);
    camera.lookAt(target);
    showNode(node);
    return;
  }
  camera.position.copy(target.clone().add(new THREE.Vector3(0, 12, 9)));
  camera.lookAt(target);
  showNode(node);
}

"""
    s = s.replace(anchor, fn + anchor)
    anchor = "      detailPanel.append(dismiss);"
    s = s.replace(
        anchor,
        anchor
        + """\n      const idea = document.createElement("button"); idea.textContent = "Evidence & investigation";
      idea.onclick = () => scryer?.openIdea(node.id);
      detailPanel.append(idea);""",
    )
s = s.replace("  controls.unlock();\n  const target = node.position.clone();", "  controls.unlock();\n  viewMode = \"walk\";\n  navigationEnabled = false;\n  keys.clear();\n  velocity.set(0, 0, 0);\n  modeButton.textContent = \"Map\";\n  crosshair.style.display = \"\";\n  pointer.set(0, 0);\n  const target = node.position.clone();")
p.write_text(s)
print("Focus, hypothesis review and metadata-only mirror integration prepared.")
