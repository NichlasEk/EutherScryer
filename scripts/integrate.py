#!/usr/bin/env python3
"""Apply reviewed Scryer integration to an explicit staging checkout, never SSH."""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--oxide", type=pathlib.Path, required=True)
p.add_argument("--net", type=pathlib.Path)
a = p.parse_args()
path = a.oxide / "webview/server-map.ts"
s = path.read_text()
if "mountScryer" in s:
    raise SystemExit("Already integrated; use a fresh source snapshot to rebuild.")


def replace(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit(f"Integration anchor changed: {old[:80]}")
    s = s.replace(old, new)


replace(
    "type MapNode = {",
    'import { mountScryer } from "./scryer/integration.ts";\nlet scryer: ReturnType<typeof mountScryer> | null = null;\nlet scryerAuth: any;\nlet scryerDialog = false;\n\ntype MapNode = {',
)
replace(
    "  initScene();\n  bindInput();",
    "  initScene();\n  scryer = mountScryer(scryerAuth, cityRoot, sceneNodes);\n  bindInput();",
)
replace(
    '  csrfToken = auth.csrfToken || "";',
    '  scryerAuth = auth;\n  csrfToken = auth.csrfToken || "";',
)
replace(
    "  showOverview(map);\n}",
    "  scryer?.attach(map, positions);\n  showOverview(map);\n}",
)
replace(
    "  updateMovement(delta);",
    '  scryer?.update(delta, roomMode === "city");\n  updateMovement(delta);',
)
replace(
    "function showNode(node: SceneNode): void {",
    """function showNode(node: SceneNode): void {
  if (scryer?.owns(node.id)) {
    detailPanel.textContent = scryer.describe(node.id);
    detailPanel.style.whiteSpace = "pre-line";
    document.querySelector("#ev-target")!.textContent = node.label;
    if (node.type === "scryer-ghost") {
      const dismiss = document.createElement("button"); dismiss.textContent = "Dismiss hypothesis";
      dismiss.disabled = !scryer.canControl();
      dismiss.onclick = async () => {
        try { await scryer?.dismiss(node.id); detailPanel.textContent = "Hypothesis dismissed; no infrastructure changed."; }
        catch { detailPanel.textContent = "Dismissal could not be confirmed."; }
      };
      detailPanel.append(dismiss);
    }
    return;
  }
  detailPanel.style.whiteSpace = "";""",
)
replace(
    "  const target = focusedNode || selectedNode;",
    """  const target = focusedNode || selectedNode;
  if (target && scryer?.owns(target.id)) {
    scryerDialog = true; scryer.converse(true); setCustodianVisible(true);
    if (controls.isLocked) controls.unlock();
    custodianTitle.textContent = "EutherScryer · What if…";
    custodianContext.textContent = "Read-only observer · hypotheses are not infrastructure";
    custodianAnswer.textContent = scryer.describe(target.id);
    custodianQuestion.focus({ preventScroll: true });
    return;
  }""",
)
replace(
    "function nodeCanEnter(node: SceneNode): boolean {",
    "function nodeCanEnter(node: SceneNode): boolean {\n  if (scryer?.owns(node.id)) return true;",
)
replace(
    "function restartCommandForNode(node: SceneNode): string | null {",
    "function restartCommandForNode(node: SceneNode): string | null {\n  if (scryer?.owns(node.id)) return null;",
)
replace(
    "function closeCustodianDialog(): void {",
    "function closeCustodianDialog(): void {\n  if (scryerDialog) scryer?.converse(false);\n  scryerDialog = false;",
)
replace(
    "async function askCustodian(): Promise<void> {",
    """async function askCustodian(): Promise<void> {
  if (scryerDialog && scryer) {
    const question = custodianQuestion.value.trim() || "What are you looking at?";
    custodianAnswer.textContent = "Considering the available observations…";
    const answer = await scryer.ask(question);
    if (scryerDialog && answer) custodianAnswer.textContent = answer;
    return;
  }""",
)
# Validate all source anchors and configuration before touching either checkout.
config = a.oxide / "tsconfig.json"
cfg = json.loads(config.read_text())
cfg["compilerOptions"]["allowImportingTsExtensions"] = True
net_path = a.net / "scripts/euthernet_http.py" if a.net else None
http = None
if net_path:
    http = net_path.read_text()
    anchor = '        self.write_json(HTTPStatus.OK, {"ok": True, **answer_question(self.config, question)})'
    if http.count(anchor) != 1 or "scryer_answer" in http:
        raise SystemExit("EutherNet ask anchor changed or already integrated")
    http = http.replace(
        anchor,
        """        if payload.get("persona") == "scryer":
            from scryer import answer as scryer_answer
            self.write_json(HTTPStatus.OK, scryer_answer(self.config, payload, eutherverse_map(self.config)))
            return
""" + anchor,
    )

replace(
    "function cityObjectiveFor(node: SceneNode): string {",
    """function cityObjectiveFor(node: SceneNode): string {
  if (scryer?.owns(node.id)) return "A wandering observer. Press E for observations or F to discuss what might be. Ghost Nodes are hypotheses.";""",
)
replace(
    "function updateEnterButton(node: SceneNode | null): void {",
    """function updateEnterButton(node: SceneNode | null): void {
  if (node && scryer?.owns(node.id)) {
    enterNodeButton.disabled = false;
    enterNodeButton.textContent = node.type === "scryer-ghost" ? "Discuss Hypothesis" : "Talk to Scryer";
    const top = document.querySelector<HTMLButtonElement>("#ev-enter");
    if (top && viewMode === "map" && isTouchMapDevice()) top.textContent = "Talk";
    return;
  }""",
)
path.write_text(s)
shutil.copytree(ROOT / "src", a.oxide / "webview/scryer", dirs_exist_ok=True)
config.write_text(json.dumps(cfg, indent=2) + "\n")
if net_path and http:
    net_path.write_text(http)
    shutil.copy2(ROOT / "backend/scryer.py", a.net / "scripts/scryer.py")
if a.net:
    subprocess.run([sys.executable, str(ROOT / "scripts/enable_shared.py"), "--oxide", str(a.oxide), "--net", str(a.net)], check=True)
print("Integrated into explicit checkout. No services restarted.")
