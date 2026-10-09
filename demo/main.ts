import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { mountScryer } from "../src/integration.ts";
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x060b13);
scene.fog = new THREE.FogExp2(0x060b13, 0.007);
const camera = new THREE.PerspectiveCamera(
  48,
  innerWidth / innerHeight,
  0.1,
  300,
);
camera.position.set(29, 29, 49);
const renderer = new THREE.WebGLRenderer({
  canvas: document.querySelector("canvas")!,
  antialias: true,
});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 2, 8);
controls.update();
scene.add(new THREE.HemisphereLight(0xb6efff, 0x0a1229, 2));
const light = new THREE.DirectionalLight(0xffffff, 3);
light.position.set(20, 30, 10);
scene.add(light);
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(220, 220),
  new THREE.MeshStandardMaterial({ color: 0x080f19, roughness: 0.9 }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.1;
scene.add(floor);
scene.add(new THREE.GridHelper(180, 60, 0x244051, 0x132536));
const root = new THREE.Group();
scene.add(root);
const positions = new Map([
  ["server", new THREE.Vector3(-10, 0, 0)],
  ["euthervault", new THREE.Vector3(8, 0, -12)],
  ["eutherbooks", new THREE.Vector3(8, 0, 0)],
  ["euthernet", new THREE.Vector3(8, 0, 12)],
  ["eutherid", new THREE.Vector3(8, 0, 24)],
]);
const map = {
  collected_at: new Date().toISOString(),
  nodes: [
    { id: "server", type: "host", status: "online" },
    ...["euthervault", "eutherbooks", "euthernet", "eutherid"].map((id) => ({
      id,
      type: "service",
      status: "running",
    })),
  ],
  edges: ["euthervault", "eutherbooks", "euthernet", "eutherid"].map((to) => ({
    from: "server",
    to,
    type: "hosts",
  })),
};
const nodes = new Map();
for (const n of map.nodes) {
  const p = positions.get(n.id)!;
  const group = new THREE.Group();
  group.position.copy(p);
  const mesh = new THREE.Mesh(
    n.type === "host"
      ? new THREE.BoxGeometry(5.8, 5.8, 3.4)
      : new THREE.CylinderGeometry(2.58, 3.4, 4.6, 8),
    new THREE.MeshStandardMaterial({
      color: 0x183341,
      emissive: 0x1b777d,
      emissiveIntensity: 0.28,
      metalness: 0.45,
      roughness: 0.45,
    }),
  );
  mesh.position.y = n.type === "host" ? 2.9 : 2.3;
  group.add(mesh);
  group.userData.nodeId = n.id;
  root.add(group);
  nodes.set(n.id, { ...n, label: n.id, object: group, position: p });
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 100;
  const ctx = canvas.getContext("2d")!;
  ctx.font = "28px monospace";
  ctx.fillStyle = "#bbd7e2";
  ctx.textAlign = "center";
  ctx.fillText(n.id.toUpperCase(), 256, 60);
  const label = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(canvas),
      transparent: true,
    }),
  );
  label.scale.set(12, 2.4, 1);
  label.position.set(p.x, 7, p.z);
  scene.add(label);
}
for (const edge of map.edges) {
  const curve = new THREE.QuadraticBezierCurve3(
    positions.get(edge.from)!.clone().setY(1),
    new THREE.Vector3(-1, 7, positions.get(edge.to)!.z / 2),
    positions.get(edge.to)!.clone().setY(1),
  );
  scene.add(
    new THREE.Mesh(
      new THREE.TubeGeometry(curve, 24, 0.035, 4, false),
      new THREE.MeshBasicMaterial({
        color: 0x386974,
        transparent: true,
        opacity: 0.6,
      }),
    ),
  );
}
// Local mock of the exact allowlisted transport, never forward demo requests.
const auth = {
  authenticated: true,
  user: "simulation",
  permissions: { canServerMap: true },
  csrfToken: "simulated",
};
window.fetch = async (input) =>
  new Response(
    JSON.stringify(
      String(input).endsWith("/status")
        ? auth
        : String(input).endsWith("/map")
          ? map
          : { source: "scryer-inventory" },
    ),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
const scryer = mountScryer(auth, root, nodes, { shared: false });
scryer.attach(map, positions);
const answer = document.querySelector("#answer")!,
  status = document.querySelector("#status")!,
  evidence = document.querySelector("#evidence")!;
function converse() {
  scryer.converse(true);
  answer.textContent = scryer.describe("scryer:inhabitant");
  scryer.converse(false);
}
document.addEventListener("keydown", (e) => {
  if (e.code === "KeyF" && !(e.target instanceof HTMLInputElement)) converse();
});
const ray = new THREE.Raycaster();
renderer.domElement.addEventListener("click", (e) => {
  ray.setFromCamera(
    new THREE.Vector2(
      (e.clientX / innerWidth) * 2 - 1,
      1 - (e.clientY / innerHeight) * 2,
    ),
    camera,
  );
  const hit = ray.intersectObjects(scryer.inhabitant.root.children, true)[0];
  if (hit) converse();
});
document.querySelector("form")!.onsubmit = async (e) => {
  e.preventDefault();
  answer.textContent = await scryer.ask(document.querySelector("input")!.value);
};
document.querySelector("#event")!.addEventListener("click", () => {
  map.nodes[1].status =
    map.nodes[1].status === "running" ? "degraded" : "running";
  map.collected_at = new Date().toISOString();
  scryer.attach(map, positions);
  answer.textContent =
    "Simulated inventory event received. Scryer will inspect the changed service when its current investigation is complete.";
});
const clock = new THREE.Clock();
function frame() {
  requestAnimationFrame(frame);
  scryer.update(Math.min(clock.getDelta(), 0.05), true);
  const state = scryer.inhabitant.engine.state;
  status.textContent = `${state.phase} ${state.destination ? "→ " + state.destination : ""}`;
  evidence.textContent = state.ghosts
    .filter((g) => g.status === "active")
    .map(
      (g) =>
        "HYPOTHESIS\n" + g.description + "\nEvidence: " + g.links.join(", "),
    )
    .join("\n");
  renderer.render(scene, camera);
}
frame();
window.addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
// Inspectable state for the local simulation test only, not a production control API.
Object.assign(window, { scryerDemo: scryer });
