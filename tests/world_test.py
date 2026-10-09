import importlib.util
import json
import pathlib
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "scryer_world", pathlib.Path(__file__).parents[1] / "backend/scryer_world.py"
)
world_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(world_module)
NOW = 1791565200000


def fixture(stamp="2026-10-09T17:00:00Z"):
    return {
        "collected_at": stamp,
        "nodes": [
            {
                "id": "server",
                "type": "host",
                "status": "online",
                "detail": "PRIVATE SECRET",
            },
            {"id": "vault", "type": "service", "status": "running"},
            {"id": "books", "type": "service", "status": "running"},
        ],
        "edges": [
            {"from": "server", "to": "vault", "type": "hosts"},
            {"from": "server", "to": "books", "type": "hosts"},
        ],
    }


class WorldTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.now = NOW
        self.world = world_module.ScryerWorld(
            self.directory.name, fixture, clock=lambda: self.now
        )
        self.world.ingest(fixture())

    def tearDown(self):
        self.directory.cleanup()

    def advance(self, seconds):
        for _ in range(seconds * 4):
            self.now += 250
            self.world.tick(0.25, self.now)

    def test_shared_cycle_movement_ghost_and_bounded_provenance(self):
        self.advance(35)
        s = self.world.snapshot()
        self.assertEqual(len(s["state"]["ghosts"]), 1)
        g = s["state"]["ghosts"][0]
        self.assertEqual(g["kind"], "hypothesis")
        self.assertEqual(g["support"]["hosted"], ["books", "vault"])
        self.assertNotIn("PRIVATE", json.dumps(s))
        self.assertEqual(len(s["world"]["nodes"]), 3)
        self.assertGreater(len(s["state"]["observations"]), 0)

    def test_navigation_stays_clear_of_all_obstacles(self):
        last = dict(self.world.state["position"])
        for _ in range(300):
            self.now += 250
            self.world.tick(0.25, self.now)
            position = self.world.state["position"]
            for i in range(11):
                p = {k: last[k] + (position[k] - last[k]) * i / 10 for k in ("x", "z")}
                self.assertTrue(
                    all(
                        world_module.distance(p, o) >= 4.5
                        for o in self.world.world["obstacles"]
                    )
                )
            last = dict(position)

    def test_only_one_background_writer_can_own_a_state_file(self):
        self.world.start()
        other = world_module.ScryerWorld(
            self.directory.name, fixture, clock=lambda: self.now
        )
        try:
            with self.assertRaises(BlockingIOError):
                other.start()
        finally:
            self.world.close()

    def test_changed_service_is_selected_before_idle_patrol(self):
        raw = fixture("2026-10-09T17:01:00Z")
        raw["nodes"][1]["status"] = "degraded"
        self.world.ingest(raw)
        self.world.tick(0.25, self.now)
        self.assertEqual(self.world.state["destination"], "vault")
        self.assertEqual(self.world.state["phase"], "investigating")

    def test_restart_preserves_pause_location_memory_and_events(self):
        self.advance(35)
        changed = fixture("2026-10-09T17:01:00Z")
        changed["nodes"][1]["status"] = "degraded"
        self.world.ingest(changed)
        self.world.control("pause")
        before = self.world.snapshot()["state"]
        restored = world_module.ScryerWorld(
            self.directory.name, fixture, clock=lambda: self.now
        )
        self.assertEqual(restored.state["position"], before["position"])
        self.assertEqual(restored.state["ghosts"], before["ghosts"])
        self.assertTrue(restored.state["paused"])
        self.assertIn("vault", restored.state["queued"])
        restored.ingest(changed)
        restored.tick(0.25, self.now + 1000)
        self.assertEqual(restored.state["position"], before["position"])
        self.assertEqual(self.world.file.stat().st_mode & 0o777, 0o600)

    def test_disable_and_pause_block_work_and_model(self):
        self.world.control("disable")
        self.advance(35)
        self.assertEqual(self.world.state["observations"], [])
        self.assertFalse(self.world.model_allowed())
        self.world.control("enable")
        self.world.control("pause")
        self.assertFalse(self.world.model_allowed())
        self.world.control("resume")
        self.assertTrue(self.world.model_allowed())

    def test_control_allowlist_and_persistent_dismissal(self):
        for command in ["restart", "deploy", "run", None]:
            with self.assertRaises(ValueError):
                self.world.control(command)
        self.advance(35)
        ghost = self.world.state["ghosts"][0]
        self.world.control("dismiss", ghost["id"])
        restored = world_module.ScryerWorld(
            self.directory.name, fixture, clock=lambda: self.now
        )
        self.assertEqual(restored.state["ghosts"][0]["status"], "dismissed")

    def test_missing_target_and_removed_edges_recover(self):
        self.advance(1)
        self.assertIsNotNone(self.world.state["destination"])
        raw = fixture()
        raw["nodes"] = raw["nodes"][1:]
        self.world.ingest(raw)
        self.assertIsNone(self.world.state["destination"])
        self.world.ingest(fixture())
        self.advance(40)
        raw = fixture()
        raw["edges"] = []
        self.world.ingest(raw)
        for g in self.world.state["ghosts"]:
            self.assertEqual(g["status"], "archived")

    def test_corrupt_memory_fails_closed_and_does_not_reach_model(self):
        self.world.file.write_text("{broken")
        restored = world_module.ScryerWorld(
            self.directory.name, fixture, clock=lambda: self.now
        )
        self.assertTrue(restored.state["paused"])
        self.assertEqual(restored.error, "state-invalid")
        self.assertFalse(restored.model_allowed())
        self.assertTrue(self.world.file.with_suffix(".invalid").exists())

    def test_older_snapshots_and_stale_data_do_not_create_observations(self):
        self.world.ingest(fixture("2026-10-08T17:00:00Z"))
        self.assertEqual(self.world.state["stamp"], "2026-10-09T17:00:00.000Z")
        self.now += 90000000
        self.advance(40)
        self.assertEqual(self.world.state["observations"], [])

    def test_repeated_snapshot_does_not_duplicate_hypotheses(self):
        self.advance(35)
        self.world.ingest(fixture())
        self.advance(300)
        self.assertEqual(len(self.world.state["ghosts"]), 1)
        ids = [o["id"] for o in self.world.state["observations"]]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
