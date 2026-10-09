#!/usr/bin/env python3
"""Bundle a test-only instrumented copy without editing the staged host source."""

import argparse
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--oxide", type=pathlib.Path, required=True)
a = p.parse_args()
webview = a.oxide.resolve() / "webview"
source = (webview / "server-map.ts").read_text()
if "mountScryer" not in source:
    raise SystemExit("Apply integrate.py to the staging checkout first.")
source += """
Object.assign(window, { scryerHostTest: {
  get agent() { return scryer; },
  get nodes() { return [...sceneNodes.keys()]; },
  get room() { return roomMode; },
  get positions() { return Object.fromEntries([...sceneNodes].map(([id,node])=>[id,{x:node.position.x,z:node.position.z}])); },
  aim(id: string) {
    const node = sceneNodes.get(id)!;
    const aim = node.object.getWorldPosition(new THREE.Vector3());
    if (!id.startsWith("scryer:")) aim.y += 2.5;
    camera.position.copy(aim).add(new THREE.Vector3(7, 1, 0));
    camera.lookAt(aim);
    pointer.set(0, 0);
  }
}});
"""
output = root / ".local/integrated"
output.mkdir(parents=True, exist_ok=True)
subprocess.run(
    [
        str(root / "node_modules/.bin/esbuild"),
        "--bundle",
        "--loader=ts",
        "--format=esm",
        f"--outfile={output}/server-map.js",
    ],
    input=source,
    text=True,
    cwd=webview,
    check=True,
)
(output / "index.html").write_text(
    '<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><script type="module" src="/server-map.js"></script></html>'
)
print("Test-only bundle prepared in .local/integrated; serve on localhost:5194.")
