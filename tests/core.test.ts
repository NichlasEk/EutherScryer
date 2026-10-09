import { test } from "node:test";
import assert from "node:assert/strict";
import {
  Scryer,
  project,
  route,
  clear,
  distance,
  type World,
} from "../src/core.ts";
import { ObservationAccess, mayObserve } from "../src/access.ts";
const now = Date.parse("2026-10-09T19:00:00Z");
function fixture() {
  const positions = new Map([
    ["server", { x: -10, z: 0 }],
    ["vault", { x: 8, z: -10 }],
    ["books", { x: 8, z: 10 }],
  ]);
  const raw = {
    collected_at: new Date(now).toISOString(),
    nodes: [
      {
        id: "server",
        type: "host",
        status: "online",
        detail: "SECRET password=do-not-retain",
      },
      { id: "vault", type: "service", status: "running" },
      { id: "books", type: "service", status: "running" },
    ],
    edges: [
      { from: "server", to: "vault", type: "hosts" },
      { from: "server", to: "books", type: "hosts" },
    ],
    ssh_connections: [{ password: "SECRET" }],
  };
  return { positions, raw, world: project(raw, positions) };
}
function run(s: Scryer, start: number, seconds: number) {
  for (let i = 0; i < seconds * 10; i++) s.tick(0.1, start + i * 100);
}
test("authorization fails closed and revocation cancels state", () => {
  const s = new Scryer();
  assert.throws(() => s.ingest(fixture().world, now), /permission/);
  assert.equal(s.restore("{}", now), false);
  s.authorize(true);
  s.ingest(fixture().world, now);
  s.tick(0.1, now);
  s.authorize(false);
  assert.equal(s.path.length, 0);
  assert.equal(s.world.nodes.length, 0);
  assert.equal(s.state.observations.length, 0);
});
test("projection strips private data and unknown node/edge types", () => {
  const { raw, positions } = fixture();
  raw.nodes.push({ id: "private", type: "vault-content", status: "running" });
  positions.set("private", { x: 50, z: 50 });
  const world = project(raw, positions);
  assert.ok(!JSON.stringify(world).includes("SECRET"));
  assert.ok(!world.nodes.some((n) => n.id === "private"));
  assert.throws(() => project({ ...raw, collected_at: "unknown" }, positions));
});
test("route travels around obstacles and never cuts through their clearance", () => {
  const obstacles = [
    { x: 0, z: 0 },
    { x: 0, z: 8 },
  ];
  const start = { x: -16, z: 0 };
  const path = route(start, { x: 16, z: 0 }, obstacles);
  assert.ok(path.length > 0);
  let last = start;
  for (const p of path) {
    for (let i = 0; i <= 20; i++)
      assert.ok(
        clear(
          {
            x: last.x + ((p.x - last.x) * i) / 20,
            z: last.z + ((p.z - last.z) * i) / 20,
          },
          obstacles,
        ),
      );
    last = p;
  }
  assert.ok(distance(last, { x: 16, z: 0 }) <= 7);
  assert.deepEqual(route({ x: 0, z: 0 }, { x: 16, z: 0 }, obstacles), []);
});
test("vertical slice: travel, observation, grounded ghost, conversation, restore, deduplication", () => {
  const s = new Scryer();
  s.authorize(true);
  s.ingest(fixture().world, now);
  run(s, now, 30);
  assert.ok(s.state.observations.length > 0);
  assert.equal(s.state.ghosts.length, 1);
  const ghost = s.state.ghosts[0];
  assert.equal(ghost.kind, "hypothesis");
  assert.deepEqual(ghost.links, ["server", "books", "vault"]);
  assert.deepEqual(s.state.observations[0].hosted, ["books", "vault"]);
  assert.equal(ghost.evidence[0], s.state.observations[0].id);
  assert.match(s.discuss("What are you looking at?"), /Hypothesis/);
  const restored = new Scryer();
  restored.authorize(true);
  assert.ok(restored.restore(s.serialize(), now + 30_000));
  restored.ingest(fixture().world, now + 30_000);
  assert.deepEqual(restored.state.ghosts, s.state.ghosts);
  run(restored, now + 30_000, 300);
  assert.equal(restored.state.ghosts.length, 1);
  assert.equal(
    new Set(restored.state.observations.map((o) => o.id)).size,
    restored.state.observations.length,
  );
  assert.equal(fixture().world.nodes.length, 3);
});
test("status events select changed service and missing destinations recover", () => {
  const s = new Scryer();
  s.authorize(true);
  const f = fixture();
  s.ingest(f.world, now);
  f.raw.nodes[1].status = "degraded";
  f.raw.collected_at = new Date(now + 1000).toISOString();
  s.ingest(project(f.raw, f.positions), now + 1000);
  s.tick(0.1, now + 1000);
  assert.equal(s.state.destination, "vault");
  assert.equal(s.state.phase, "investigating");
  const next = project(
    { ...f.raw, nodes: [f.raw.nodes[0], f.raw.nodes[2]] },
    f.positions,
  );
  s.ingest(next, now + 2000);
  assert.equal(s.state.destination, null);
  s.tick(0.1, now + 2000);
  assert.notEqual(s.state.destination, "vault");
});
test("pause, disable, stale data and corrupt persistence stop work", () => {
  const s = new Scryer();
  s.authorize(true);
  s.ingest(fixture().world, now);
  s.state.paused = true;
  run(s, now, 30);
  assert.equal(s.state.destination, null);
  s.state.paused = false;
  s.state.disabled = true;
  run(s, now, 30);
  assert.equal(s.state.destination, null);
  s.state.disabled = false;
  run(s, now + 25 * 3600_000, 30);
  assert.equal(s.state.destination, null);
  for (const raw of [
    "{}",
    "nope",
    JSON.stringify({ ...s.state, position: { x: Infinity, z: 0 } }),
    JSON.stringify({ ...s.state, ghosts: [{ kind: "fact" }] }),
  ])
    assert.equal(s.restore(raw, now), false);
});
test("disappearing support archives ghosts; dismissals survive restart", () => {
  const s = new Scryer();
  s.authorize(true);
  const f = fixture();
  s.ingest(f.world, now);
  run(s, now, 30);
  s.state.ghosts[0].status = "dismissed";
  const r = new Scryer();
  r.authorize(true);
  r.restore(s.serialize(), now);
  r.ingest(f.world, now);
  run(r, now, 240);
  assert.equal(r.state.ghosts.length, 1);
  assert.equal(r.state.ghosts[0].status, "dismissed");
  s.state.ghosts[0].status = "active";
  s.ingest(
    { ...f.world, nodes: f.world.nodes.filter((n) => n.id !== "vault") },
    now,
  );
  assert.equal(s.state.ghosts[0].status, "archived");
});
test("read transport has no command capability and cancels on revoked permission", async () => {
  const auth = {
    authenticated: true,
    user: "owner",
    permissions: { canServerMap: true },
  };
  assert.equal(
    mayObserve({ ...auth, permissions: { canServerMap: false } }),
    false,
  );
  const calls: any[] = [];
  const access = new ObservationAccess(auth, async (path, options) => {
    calls.push({ path, options });
    return new Response("{}", { status: 200 });
  });
  await access.map();
  await access.ask("hi", "server");
  assert.deepEqual(
    calls.map((c) => c.path),
    ["/api/admin/euthernet/map", "/api/admin/euthernet/ask"],
  );
  assert.equal(JSON.parse(calls[1].options.body).persona, "scryer");
  assert.equal("run" in access, false);
  const denied = new ObservationAccess(
    auth,
    async () => new Response("", { status: 403 }),
  );
  await assert.rejects(() => denied.map(), /revoked/);
  await assert.rejects(() => denied.map(), /cancelled/);
});
test("queued events and in-flight destination survive restart without inventing an observation", () => {
  const s = new Scryer();
  s.authorize(true);
  const f = fixture();
  s.ingest(f.world, now);
  s.tick(0.1, now);
  assert.equal(s.state.destination, "server");
  f.raw.nodes[1].status = "degraded";
  f.raw.collected_at = new Date(now + 1000).toISOString();
  const next = project(f.raw, f.positions);
  s.ingest(next, now + 1000);
  assert.ok(s.pending.includes("vault"));
  const r = new Scryer();
  r.authorize(true);
  assert.ok(r.restore(s.serialize(), now + 2000));
  r.ingest(next, now + 2000);
  assert.equal(r.state.destination, "server");
  assert.ok(r.path.length);
  assert.ok(r.pending.includes("vault"));
  assert.equal(r.state.observations.length, 0);
});
test("removed supporting edges archive a hypothesis even when all nodes remain", () => {
  const s = new Scryer();
  s.authorize(true);
  const world = fixture().world;
  s.ingest(world, now);
  run(s, now, 30);
  s.ingest({ ...world, edges: [] }, now + 30_000);
  assert.equal(s.state.ghosts[0].status, "archived");
});
test("browser fetch receives its required global receiver", async () => {
  const access = new ObservationAccess(
    { authenticated: true, user: "owner", isAdmin: true },
    async function (this: typeof globalThis) {
      assert.equal(this, globalThis);
      return new Response("{}");
    },
  );
  await access.authorization();
});

test("shared controls require owner permission and never expose infrastructure commands", async () => {
  const reader = new ObservationAccess(
    {
      authenticated: true,
      user: "reader",
      permissions: { canServerMap: true },
    },
    async () => {
      throw Error("must not connect");
    },
  );
  assert.throws(() => reader.control("pause"), /Owner permission/);
  const requests: any[] = [];
  const owner = new ObservationAccess(
    { authenticated: true, user: "owner", isAdmin: true },
    async (path, options) => {
      requests.push({ path, options });
      return new Response("{}");
    },
  );
  await owner.control("pause");
  assert.equal(requests[0].path, "/api/admin/euthernet/scryer/control");
  assert.deepEqual(JSON.parse(requests[0].options.body), { command: "pause" });
});
