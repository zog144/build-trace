"""Hardening of verification-history through public build-record constructors."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from zog.build_trace import BuildTrace

try:
    from zog.build_record import (
        Store, canonical, generation_observation_snapshot, make_record, record_id,
        verification_check_from_execution, verification_execution,
    )
except ImportError:
    Store = None


def sha(char):
    return "sha256:" + char * 64


def producer_id(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def descriptor(timeout=120):
    return {
        "isolation": {
            "mount_namespace": True,
            "user_namespace": False,
            "root_read_only": True,
        },
        "user": {
            "uid": 0,
            "gid": 0,
            "supplementary_groups": [],
        },
        "root": {
            "mode": "prepared-rootfs",
            "writable_state": "explicit-only",
        },
        "network": {"mode": "host"},
        "timeout": {"seconds": timeout},
        "runtime": {
            "executor": "systemd",
            "kill_sequence": ["SIGINT", "SIGTERM"],
        },
    }


def environment_digest(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


@unittest.skipUnless(Store is not None, "requires build-record")
class CanonicalVerificationHistoryHardening(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.record_store = self.directory / "records"
        self.store = Store(self.record_store)
        self.project_root = self.directory / "offline-project"
        self.generation_name = "generation-1"
        self.generation_id = json.dumps(
            ["host", "project", self.generation_name], separators=(",", ":"))
        self.root_inventory_digest = sha("4")
        self.check_id = "image-build/installed-trust/command/0"
        self.definition1 = sha("1")
        self.definition2 = sha("6")

        self.base_records = self._generation_closure()
        self.generation_record = self.base_records[-1]
        self.generation_record_id = record_id(self.generation_record)

        self.legacy_observation = self._observation_v1()
        self.explicit_observation = self._observation_v2(
            "explicit-1", self.definition1, descriptor(), sha("5"))
        self.explicit_observation2 = self._observation_v2(
            "explicit-2", self.definition2, descriptor(timeout=240), sha("7"))

        self.legacy_execution = verification_execution(self.legacy_observation)
        self.explicit_execution = verification_execution(self.explicit_observation)
        self.explicit_execution2 = verification_execution(self.explicit_observation2)
        self.check1 = verification_check_from_execution(self.legacy_observation)
        self.check2 = verification_check_from_execution(self.explicit_observation2)
        self.coverage = make_record("observation-coverage", {
            "producer": {
                "name": "image-build",
                "contract": "image-build-integration-observations-v1",
            },
            "subject": {
                "kind": "generation-candidate",
                "generation_id": self.generation_id,
                "root_inventory_digest": self.root_inventory_digest,
            },
            "family": "verification-commands",
            "collector": {"implementation_digest": sha("8")},
            "scope": {"selection": "named installed command checks"},
            "outcome": "complete",
            "observation_count": 3,
            "details": {},
        })

        for record in (
            *self.base_records,
            self.legacy_execution,
            self.explicit_execution,
            self.explicit_execution2,
            self.check1,
            self.check2,
            self.coverage,
        ):
            self.store.put(record)

        self.legacy_snapshot = generation_observation_snapshot(
            self.generation_record_id,
            self.generation_id,
            self.root_inventory_digest,
            verification_checks=[record_id(self.check1)],
            verification_executions=[record_id(self.legacy_execution)],
            coverage=[record_id(self.coverage)],
        )
        self.mixed_snapshot = generation_observation_snapshot(
            self.generation_record_id,
            self.generation_id,
            self.root_inventory_digest,
            verification_checks=[record_id(self.check1), record_id(self.check2)],
            verification_executions=[
                record_id(self.legacy_execution),
                record_id(self.explicit_execution),
                record_id(self.explicit_execution2),
            ],
            coverage=[record_id(self.coverage)],
        )
        self.legacy_snapshot_id = self.store.put(self.legacy_snapshot)
        self.mixed_snapshot_id = self.store.put(self.mixed_snapshot)

        self.trace = BuildTrace(
            self.project_root,
            host_id="host",
            record_store=self.record_store,
            record_project_id="project",
        )
        self.assertFalse((self.project_root / "state/image-build").exists())

    def _artifact(self, name, char):
        return {"name": name, "digest": sha(char), "size": 1}

    def _generation_closure(self):
        base_inputs = make_record("build-inputs", {
            "package": "base",
            "step": "build",
            "purpose": "assembly",
            "sources": [],
            "recipe": self._artifact("base-recipe", "9"),
            "patches": [],
            "target": "x86_64-linux",
            "options": {},
            "environment": {},
            "materials": [self._artifact("base-material", "a")],
            "dependencies": [],
        })
        base_start = make_record("attempt-start", {
            "attempt_id": json.dumps(
                ["host", "project", "base-build", "base"],
                separators=(",", ":")),
            "inputs": record_id(base_inputs),
            "prepared_at": "2026-10-09T18:00:00Z",
            "retry_of": None,
        })
        base_output = make_record("package-output", {
            "package": "base",
            "attempt": record_id(base_start),
            "artifacts": [self._artifact("base", "b")],
        })
        base_result = make_record("attempt-result", {
            "attempt": record_id(base_start),
            "outcome": "succeeded",
            "finished_at": "2026-10-09T18:01:00Z",
            "jobs": [],
            "traces": [],
            "outputs": [record_id(base_output)],
            "summary": "base package fixture",
        })

        rootfs_artifact = self._artifact("rootfs", "c")
        manifest_artifact = self._artifact("manifest", "d")
        assembly_inputs = make_record("build-inputs", {
            "package": "@rootfs",
            "step": "assemble",
            "purpose": "assembly",
            "sources": [],
            "recipe": self._artifact("assembly-recipe", "e"),
            "patches": [],
            "target": "x86_64-linux",
            "options": {},
            "environment": {},
            "materials": [self._artifact("assembly-material", "f")],
            "dependencies": [{
                "output": record_id(base_output),
                "result": record_id(base_result),
            }],
        })
        assembly_start = make_record("attempt-start", {
            "attempt_id": json.dumps(
                ["host", "project", "assembly", "@rootfs-assembly"],
                separators=(",", ":")),
            "inputs": record_id(assembly_inputs),
            "prepared_at": "2026-10-09T19:00:00Z",
            "retry_of": None,
        })
        assembly_output = make_record("package-output", {
            "package": "@rootfs",
            "attempt": record_id(assembly_start),
            "artifacts": [rootfs_artifact, manifest_artifact],
        })
        assembly_result = make_record("attempt-result", {
            "attempt": record_id(assembly_start),
            "outcome": "succeeded",
            "finished_at": "2026-10-09T19:01:00Z",
            "jobs": [],
            "traces": [],
            "outputs": [record_id(assembly_output)],
            "summary": "canonical rootfs assembly fixture",
        })
        generation = make_record("generation", {
            "generation_id": self.generation_id,
            "assembly_result": record_id(assembly_result),
            "packages": [{
                "output": record_id(base_output),
                "result": record_id(base_result),
            }],
            "artifact": rootfs_artifact,
            "content_manifest": manifest_artifact,
            "verification": [],
        })
        return [
            base_inputs, base_start, base_output, base_result,
            assembly_inputs, assembly_start, assembly_output, assembly_result,
            generation,
        ]

    def _base_observation(self, schema, attempt, definition, invocation):
        value = {
            "schema": schema,
            "check_id": self.check_id,
            "definition_digest": definition,
            "subject": {
                "kind": "generation-candidate",
                "generation_id": self.generation_id,
                "root_inventory_digest": self.root_inventory_digest,
            },
            "attempt_id": json.dumps(
                ["host", "project", attempt], separators=(",", ":")),
            "sequence": 0,
            "outcome": "PASS",
            "execution": {"invocation_id": invocation, "exit_code": 0},
            "evidence": [{
                "kind": "build-trace",
                "host_id": "host",
                "build_id": "attempt:" + attempt,
            }],
            "granularity": "command",
            "timing": {
                "started_at": None,
                "finished_at": None,
                "observed_at": "2026-10-09T20:00:00+00:00",
            },
            "producer": {"name": "image-build", "contract": schema},
        }
        return value

    def _observation_v1(self):
        value = self._base_observation(
            "image-build-verification-observation-v1",
            "legacy-1", self.definition1, "legacy-invocation")
        value["environment_digest"] = sha("2")
        value["id"] = producer_id(value)
        return value

    def _observation_v2(self, attempt, definition, env, policy):
        value = self._base_observation(
            "image-build-verification-observation-v2",
            attempt, definition, attempt + "-invocation")
        value["execution_environment"] = {
            "contract": "image-build-verification-environment-v1",
            "digest": environment_digest(env),
            "descriptor": env,
        }
        value["producer_policy_digest"] = policy
        value["id"] = producer_id(value)
        return value

    def history(self, snapshots, **kwargs):
        return self.trace.verification_history(
            snapshots, self.check_id, **kwargs)

    def expected_execution(self, record):
        data = record["data"]
        if "execution_environment" in data:
            environment = {
                "availability": "available",
                "contract": data["execution_environment"]["contract"],
                "digest": data["execution_environment"]["digest"],
                "descriptor": data["execution_environment"]["descriptor"],
            }
        else:
            environment = {
                "availability": "legacy-opaque",
                "digest": data["environment_digest"],
            }
        return {
            "id": record_id(record),
            "record": record_id(record),
            "availability": "available",
            "authority": "build-record",
            "canonical_kind": "verification-execution",
            "persistence": "stored",
            "gaps": [],
            "producer": data["producer"],
            "producer_observation": data["producer_observation"],
            "check_id": data["check_id"],
            "definition_digest": data["definition_digest"],
            "subject": data["subject"],
            "attempt_id": data["attempt_id"],
            "build_id": "attempt:" + json.loads(data["attempt_id"])[2],
            "sequence": data["sequence"],
            "outcome": data["outcome"],
            "execution": data["execution"],
            "environment": environment,
            "environment_digest": data.get("environment_digest"),
            "producer_policy_digest": data.get("producer_policy_digest"),
            "evidence": data["evidence"],
            "granularity": data["granularity"],
            "timing": data["timing"],
        }

    def test_public_build_record_constructors_feed_mixed_history(self):
        value = self.history(
            [self.legacy_snapshot_id, self.mixed_snapshot_id])
        self.assertEqual(
            [point["snapshot"] for point in value["points"]],
            [self.legacy_snapshot_id, self.mixed_snapshot_id])
        self.assertEqual(
            [point["execution_count"] for point in value["points"]], [1, 3])
        self.assertEqual(value["points"][1]["definition_count"], 2)
        rows = {
            row["record"]: row for row in value["points"][1]["executions"]
        }
        self.assertEqual(
            rows[record_id(self.legacy_execution)],
            self.expected_execution(self.legacy_execution))
        self.assertEqual(
            rows[record_id(self.explicit_execution)],
            self.expected_execution(self.explicit_execution))
        self.assertEqual(
            rows[record_id(self.explicit_execution2)],
            self.expected_execution(self.explicit_execution2))
        self.assertTrue(all(
            point["reference_closure_complete"] for point in value["points"]))
        self.assertTrue(all(
            point["declared_gap_free"] for point in value["points"]))
        self.assertEqual(
            [point["coverage"][0]["outcome"] for point in value["points"]],
            ["complete", "complete"])

    def test_verification_history_public_output_contract_is_exact(self):
        value = self.history([self.mixed_snapshot_id])
        self.assertEqual(set(value), {
            "schema_version", "kind", "check_id", "definition_digest",
            "snapshot_count", "order", "chronology", "points", "has_more",
            "next_cursor", "authority", "interpretation",
        })
        self.assertEqual(value["schema_version"], 1)
        self.assertEqual(value["kind"], "verification-history")
        self.assertEqual(value["check_id"], self.check_id)
        self.assertIsNone(value["definition_digest"])
        self.assertEqual(value["snapshot_count"], 1)
        self.assertEqual(value["order"], "caller-supplied")
        self.assertEqual(value["chronology"], "not-inferred")
        self.assertFalse(value["has_more"])
        self.assertIsNone(value["next_cursor"])
        self.assertEqual(value["authority"], "build-record")

        point = value["points"][0]
        self.assertEqual(set(point), {
            "id", "position", "snapshot", "generation", "generation_record",
            "generation_id", "root_inventory_digest", "record_set_digest",
            "definitions", "definition_count", "executions", "execution_count",
            "coverage", "coverage_availability",
            "reference_closure_complete", "missing_record_count",
            "declared_gap_free", "declared_gap_count",
            "declared_gap_reason_count", "declared_gap_summary", "inspection",
        })
        self.assertEqual(point["position"], 1)
        self.assertEqual(point["snapshot"], self.mixed_snapshot_id)
        self.assertEqual(point["generation"], self.generation_name)
        self.assertEqual(point["generation_record"], self.generation_record_id)
        self.assertEqual(point["generation_id"], self.generation_id)
        self.assertEqual(
            point["root_inventory_digest"], self.root_inventory_digest)
        self.assertEqual(
            point["record_set_digest"],
            self.mixed_snapshot["data"]["record_set_digest"])
        self.assertEqual(point["definition_count"], 2)
        self.assertEqual(point["execution_count"], 3)
        self.assertEqual(point["coverage_availability"], "recorded")
        self.assertTrue(point["reference_closure_complete"])
        self.assertEqual(point["missing_record_count"], 0)
        self.assertTrue(point["declared_gap_free"])
        self.assertEqual(point["declared_gap_count"], 0)
        self.assertEqual(point["declared_gap_reason_count"], 0)
        self.assertEqual(point["declared_gap_summary"], [])

        rows = {row["record"]: row for row in point["executions"]}
        self.assertEqual(
            rows[record_id(self.legacy_execution)],
            self.expected_execution(self.legacy_execution))
        self.assertEqual(
            rows[record_id(self.explicit_execution)],
            self.expected_execution(self.explicit_execution))

    def test_canonical_history_cursor_is_deterministic(self):
        snapshots = [self.legacy_snapshot_id, self.mixed_snapshot_id]
        first = self.history(snapshots, limit=1)
        repeat = self.history(snapshots, limit=1)
        self.assertTrue(first["has_more"])
        self.assertEqual(first["next_cursor"], repeat["next_cursor"])
        self.assertEqual(first["points"], repeat["points"])
        second = self.history(
            snapshots, limit=1, cursor=first["next_cursor"])
        self.assertFalse(second["has_more"])
        self.assertEqual(second["points"][0]["position"], 2)
        self.assertEqual(
            second["points"][0]["snapshot"], self.mixed_snapshot_id)


if __name__ == "__main__":
    unittest.main()
