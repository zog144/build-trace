"""Repository-only tests for canonical observation snapshot queries."""
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from zog.build_trace import BuildTrace, TraceError
from zog.build_trace.cli import main


def rid(token):
    value = (token * 64)[:64]
    return "sha256:" + value


def canonical_digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class FakeLib:
    @staticmethod
    def record_id(record):
        return record["_id"]

    @staticmethod
    def snapshot_record_set_digest(generation, observations):
        return rid("f")


class FakeReader:
    graphs = {}

    def __init__(self, trace):
        self.trace = trace
        self.lib = FakeLib

    def graph(self, root):
        return self.graphs[root]

    def finish(self):
        return {"owner": {"source_bytes": 0}, "records": {"source_bytes": 0}}


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "state/image-build").mkdir(parents=True)
        self.trace = BuildTrace(
            self.root,
            host_id="host",
            record_store=self.root / "records",
            record_project_id="project",
        )
        self.generation = "g" * 64
        self.generation_id = json.dumps(
            ["host", "project", self.generation], separators=(",", ":"))
        self.root_inventory = rid("e")

        self.check = self.record("verification-check", {
            "producer": {"name": "image-build", "contract": "image-build-integration-observations-v1"},
            "check_id": "image-build/trust/command/0",
            "definition_digest": rid("1"),
            "granularity": "command",
        }, "1")
        self.execution1 = self.execution("verify-1", "invocation-1", "PASS", "2")
        self.execution2 = self.execution("verify-2", "invocation-2", "FAIL", "3")
        self.check2 = self.record("verification-check", {
            "producer": {"name": "image-build", "contract": "image-build-integration-observations-v1"},
            "check_id": "image-build/trust/command/0",
            "definition_digest": rid("a1"),
            "granularity": "command",
        }, "a2")
        self.execution3 = self.execution(
            "verify-3", "invocation-3", "PASS", "a3", definition=rid("a1"))
        descriptor1 = {
            "isolation": {"read_only_root": True, "mount_namespace": True},
            "user": {"uid": 1000, "gid": 1000},
            "root": {"immutable": True},
            "network": {"access": "none"},
            "timeout": {"seconds": 300},
            "runtime": {"controller_mode": "box-control-transient-v1"},
        }
        descriptor2 = {
            "isolation": {"read_only_root": True, "mount_namespace": True},
            "user": {"uid": 1000, "gid": 1000},
            "root": {"immutable": True},
            "network": {"access": "none"},
            "timeout": {"seconds": 600},
            "runtime": {"controller_mode": "box-control-transient-v1"},
        }
        self.explicit_environment1 = {
            "contract": "image-build-verification-environment-v1",
            "digest": canonical_digest(descriptor1),
            "descriptor": descriptor1,
        }
        self.explicit_environment2 = {
            "contract": "image-build-verification-environment-v1",
            "digest": canonical_digest(descriptor2),
            "descriptor": descriptor2,
        }
        self.execution4 = self.execution(
            "verify-4", "invocation-4", "PASS", "a6",
            environment=self.explicit_environment1,
            producer_policy_digest=rid("a7"))
        self.execution5 = self.execution(
            "verify-5", "invocation-5", "ERROR", "a8", definition=rid("a1"),
            environment=self.explicit_environment2,
            producer_policy_digest=rid("a9"))
        self.relationship = self.record("relationship-observation", {
            "producer": {"name": "image-build", "contract": "image-build-integration-observations-v1"},
            "producer_observation": rid("4"),
            "subject": {
                "kind": "artifact",
                "path": "/usr/bin/demo",
                "digest": rid("5"),
                "packages": ["demo"],
            },
            "relation": "needs-library",
            "target": {"kind": "soname", "value": "libdemo.so.1"},
            "evidence": {
                "kind": "elf-metadata",
                "tool": {"name": "readelf", "sha256": "6" * 64},
            },
        }, "4")
        self.relationship2 = self.record("relationship-observation", {
            "producer": {"name": "image-build", "contract": "image-build-integration-observations-v1"},
            "producer_observation": rid("b1"),
            "subject": {
                "kind": "artifact",
                "path": "/usr/lib/libdemo.so.1",
                "digest": rid("b2"),
                "packages": ["provider"],
            },
            "relation": "provides-soname",
            "target": {"kind": "soname", "value": "libdemo.so.1"},
            "evidence": {
                "kind": "elf-metadata",
                "tool": {"name": "readelf", "sha256": "b" * 64},
            },
        }, "b3")

        self.repository = self.record("source-repository", {
            "location": "https://example.invalid/demo.git",
            "normalization": "exact-literal-v1",
        }, "7")
        self.reference = self.record("source-reference", {
            "repository": self.repository["_id"],
            "kind": "tag",
            "value": "v1.0",
        }, "8")
        self.archive = self.record("source-archive", {
            "digest": rid("9"),
            "size": 123,
        }, "a")
        self.association = self.record("source-archive-association", {
            "archive": self.archive["_id"],
            "reference": self.reference["_id"],
            "relationship": "declared-not-independently-reproduced",
            "producer": {"name": "image-build", "contract": "image-build-integration-observations-v1"},
        }, "b")
        self.source = self.record("source-provenance", {
            "producer": {"name": "image-build", "contract": "image-build-integration-observations-v1"},
            "producer_observation": rid("c"),
            "package": "demo",
            "project": "demo-project",
            "output": rid("d"),
            "build_inputs": rid("a"),
            "source_selection": rid("b"),
            "archive": self.archive["_id"],
            "associations": [self.association["_id"]],
        }, "c")
        self.coverage_complete = self.coverage(
            "elf-interfaces", "complete", 0, "d")
        self.coverage_partial = self.coverage(
            "elf-interfaces", "partial", 1, "e")
        self.coverage_unavailable = self.coverage(
            "verification-commands", "unavailable", 0, "f")

        self.generation_record = self.record("generation", {
            "generation_id": self.generation_id,
            "assembly_result": rid("0"),
            "packages": [],
            "artifact": {"name": "rootfs", "digest": rid("1"), "size": 1},
            "content_manifest": {"name": "manifest", "digest": rid("2"), "size": 1},
            "verification": [],
        }, "0")

        self.s1 = self.snapshot(
            "ab",
            checks=[self.check["_id"]],
            executions=[self.execution1["_id"]],
            relationships=[self.relationship["_id"]],
            coverage=[self.coverage_complete["_id"], self.coverage_unavailable["_id"]],
        )
        self.s2 = self.snapshot(
            "cd",
            checks=[self.check["_id"]],
            executions=[self.execution1["_id"], self.execution2["_id"]],
            relationships=[self.relationship["_id"]],
            coverage=[self.coverage_partial["_id"], self.coverage_unavailable["_id"]],
        )
        self.s3 = self.snapshot(
            "ef",
            checks=[self.check["_id"], self.check2["_id"]],
            executions=[self.execution1["_id"], self.execution2["_id"], self.execution3["_id"]],
            relationships=[self.relationship["_id"], self.relationship2["_id"]],
            coverage=[self.coverage_partial["_id"], self.coverage_unavailable["_id"]],
        )
        self.s4 = self.snapshot(
            "fa",
            checks=[self.check["_id"], self.check2["_id"]],
            executions=[self.execution1["_id"], self.execution4["_id"], self.execution5["_id"]],
            relationships=[self.relationship["_id"], self.relationship2["_id"]],
            coverage=[self.coverage_partial["_id"], self.coverage_unavailable["_id"]],
        )
        self.install_graph(self.s1)
        self.install_graph(self.s2)
        self.install_graph(self.s3)
        self.install_graph(self.s4)

    def record(self, kind, data, token, gaps=None):
        return {
            "_id": rid(token),
            "schema_version": 1,
            "kind": kind,
            "data": data,
            "gaps": gaps or [],
        }

    def execution(self, attempt, invocation, outcome, token, definition=None,
                  environment=None, producer_policy_digest=None):
        data = {
            "producer": {"name": "image-build", "contract": "image-build-verification-observation-v1"},
            "producer_observation": rid(token),
            "check_id": "image-build/trust/command/0",
            "definition_digest": definition or rid("1"),
            "subject": {
                "kind": "generation-candidate",
                "generation_id": self.generation_id,
                "root_inventory_digest": self.root_inventory,
            },
            "attempt_id": json.dumps(["host", "project", attempt], separators=(",", ":")),
            "sequence": 0,
            "outcome": outcome,
            "execution": {"invocation_id": invocation, "exit_code": 0 if outcome == "PASS" else 1},
            "evidence": [{
                "kind": "build-trace",
                "host_id": "host",
                "build_id": "attempt:" + attempt,
            }],
            "granularity": "command",
            "timing": {"started_at": None, "finished_at": None, "observed_at": None},
        }
        if environment is None:
            data["environment_digest"] = rid("7")
        else:
            data["execution_environment"] = environment
            data["producer_policy_digest"] = producer_policy_digest
        return self.record("verification-execution", data, token)

    def coverage(self, family, outcome, count, token):
        return self.record("observation-coverage", {
            "producer": {"name": "image-build", "contract": "image-build-integration-observations-v1"},
            "subject": {
                "kind": "generation-candidate",
                "generation_id": self.generation_id,
                "root_inventory_digest": self.root_inventory,
            },
            "family": family,
            "collector": {"implementation_digest": rid("8")},
            "scope": {"selection": "fixture"},
            "outcome": outcome,
            "observation_count": count,
            "details": {},
        }, token)

    def snapshot(self, token, *, checks, executions, relationships, coverage):
        return self.record("generation-observation-snapshot", {
            "generation": self.generation_record["_id"],
            "generation_id": self.generation_id,
            "root_inventory_digest": self.root_inventory,
            "observations": {
                "verification_checks": checks,
                "verification_executions": executions,
                "relationships": relationships,
                "source_provenance": [self.source["_id"]],
                "coverage": coverage,
            },
            "record_set_digest": rid(token),
        }, token)

    def install_graph(self, snapshot):
        direct = set(sum(snapshot["data"]["observations"].values(), []))
        records = {snapshot["_id"]: snapshot, self.generation_record["_id"]: self.generation_record}
        for item in (
            self.check, self.check2, self.execution1, self.execution2, self.execution3,
            self.execution4, self.execution5, self.relationship, self.relationship2, self.source,
            self.coverage_complete, self.coverage_partial, self.coverage_unavailable,
        ):
            if item["_id"] in direct:
                records[item["_id"]] = item
        records.update({
            self.repository["_id"]: self.repository,
            self.reference["_id"]: self.reference,
            self.archive["_id"]: self.archive,
            self.association["_id"]: self.association,
        })
        FakeReader.graphs[snapshot["_id"]] = (
            {"schema_version": 1, "roots": [snapshot["_id"]], "records": records},
            {"complete": True, "missing_records": [], "gaps": [], "snapshots": []},
        )

    def query(self, method, *args, **kwargs):
        with patch("zog.build_trace.snapshot_observations.Reader", FakeReader):
            return getattr(self.trace, method)(*args, **kwargs)

    def test_manifest_separates_reference_closure_declared_gaps_and_coverage(self):
        value = self.query("observation_snapshot", self.s1["_id"])
        self.assertTrue(value["reference_closure_complete"])
        self.assertTrue(value["declared_gap_free"])
        self.assertEqual(value["missing_record_count"], 0)
        self.assertEqual(value["declared_gap_count"], 0)
        coverage = {row["family"]: row for row in value["coverage"]}
        self.assertEqual(coverage["elf-interfaces"]["outcome"], "complete")
        self.assertEqual(coverage["elf-interfaces"]["observation_count"], 0)
        self.assertEqual(coverage["verification-commands"]["outcome"], "unavailable")
        self.assertEqual(value["collections"]["verification-executions"]["declared_count"], 1)

    def test_collections_expand_canonical_source_and_execution(self):
        source = self.query(
            "observation_snapshot", self.s1["_id"],
            collection="source-provenance", package="demo")
        row = source["items"]["items"][0]
        self.assertEqual(row["archive"]["digest"], rid("9"))
        self.assertEqual(row["associations"][0]["reference_kind"], "tag")
        self.assertEqual(
            row["associations"][0]["relationship"],
            "declared-not-independently-reproduced")

        executions = self.query(
            "observation_snapshot", self.s1["_id"],
            collection="verification-executions")
        self.assertEqual(executions["items"]["items"][0]["build_id"], "attempt:verify-1")
        self.assertEqual(executions["items"]["items"][0]["persistence"], "stored")

    def test_coverage_and_relationship_filters_are_bounded(self):
        coverage = self.query(
            "observation_snapshot", self.s1["_id"], collection="coverage",
            family="elf-interfaces", outcome="complete")
        self.assertEqual(len(coverage["items"]["items"]), 1)

        relationship = self.query(
            "observation_snapshot", self.s1["_id"], collection="relationships",
            relation="needs-library", package="demo")
        self.assertEqual(len(relationship["items"]["items"]), 1)
        with self.assertRaises(TraceError):
            self.query(
                "observation_snapshot", self.s1["_id"],
                collection="coverage", relation="needs-library")

    def test_same_generation_s2_reports_added_execution_and_coverage_change(self):
        value = self.query(
            "compare_observation_snapshots", self.s1["_id"], self.s2["_id"])
        self.assertTrue(value["same_generation_record"])
        self.assertTrue(value["same_generation_id"])
        self.assertTrue(value["same_root_inventory"])
        self.assertFalse(value["same_record_set"])
        self.assertEqual(
            value["collections"]["verification-executions"]["added_count"], 1)
        change = next(row for row in value["coverage_changes"]
                      if row["family"] == "elf-interfaces")
        self.assertEqual((change["before_outcome"], change["after_outcome"]),
                         ("complete", "partial"))

        details = self.query(
            "compare_observation_snapshots", self.s1["_id"], self.s2["_id"],
            collection="verification-executions")
        self.assertEqual(details["changes"]["items"][0]["change"], "added")
        self.assertEqual(
            details["changes"]["items"][0]["observation"]["outcome"], "FAIL")

    def test_allowed_build_scope_applies_to_snapshot_execution_evidence(self):
        restricted = BuildTrace(
            self.root,
            host_id="host",
            record_store=self.root / "records",
            record_project_id="project",
            allowed_build_ids=["attempt:verify-1"],
        )
        with patch("zog.build_trace.snapshot_observations.Reader", FakeReader):
            with self.assertRaises(TraceError) as caught:
                restricted.observation_snapshot(self.s2["_id"])
        self.assertEqual(caught.exception.code, "not-found")

    def test_verification_history_preserves_caller_order_all_executions_and_definitions(self):
        value = self.query(
            "verification_history",
            [self.s3["_id"], self.s1["_id"]],
            self.check["data"]["check_id"],
        )
        self.assertEqual(value["order"], "caller-supplied")
        self.assertEqual(value["chronology"], "not-inferred")
        self.assertEqual(
            [point["snapshot"] for point in value["points"]],
            [self.s3["_id"], self.s1["_id"]],
        )
        self.assertEqual(value["points"][0]["definition_count"], 2)
        self.assertEqual(value["points"][0]["execution_count"], 3)
        self.assertEqual(
            {row["outcome"] for row in value["points"][0]["executions"]},
            {"PASS", "FAIL"},
        )
        self.assertEqual(
            value["points"][0]["coverage"][0]["family"],
            "verification-commands",
        )
        self.assertEqual(value["points"][0]["coverage"][0]["outcome"], "unavailable")

        filtered = self.query(
            "verification_history",
            [self.s1["_id"], self.s3["_id"]],
            self.check["data"]["check_id"],
            definition_digest=self.check2["data"]["definition_digest"],
        )
        self.assertEqual(filtered["points"][0]["execution_count"], 0)
        self.assertEqual(filtered["points"][1]["execution_count"], 1)
        self.assertEqual(filtered["points"][1]["definitions"][0]["record"], self.check2["_id"])

    def test_verification_history_cursor_binds_exact_caller_sequence(self):
        first = self.query(
            "verification_history",
            [self.s1["_id"], self.s2["_id"], self.s3["_id"]],
            self.check["data"]["check_id"],
            limit=1,
        )
        self.assertTrue(first["has_more"])
        second = self.query(
            "verification_history",
            [self.s1["_id"], self.s2["_id"], self.s3["_id"]],
            self.check["data"]["check_id"],
            cursor=first["next_cursor"],
            limit=1,
        )
        self.assertEqual(second["points"][0]["position"], 2)
        with self.assertRaises(TraceError) as caught:
            self.query(
                "verification_history",
                [self.s3["_id"], self.s2["_id"], self.s1["_id"]],
                self.check["data"]["check_id"],
                cursor=first["next_cursor"],
                limit=1,
            )
        self.assertEqual(caught.exception.code, "invalid-cursor")

    def test_verification_history_projects_legacy_environment_as_opaque(self):
        value = self.query(
            "verification_history", [self.s1["_id"]],
            self.check["data"]["check_id"])
        row = value["points"][0]["executions"][0]
        self.assertEqual(
            row["environment"],
            {"availability": "legacy-opaque", "digest": rid("7")})
        self.assertEqual(row["environment_digest"], rid("7"))
        self.assertIsNone(row["producer_policy_digest"])
        self.assertEqual(row["record"], self.execution1["_id"])

    def test_verification_history_projects_explicit_environment_literally(self):
        value = self.query(
            "verification_history", [self.s4["_id"]],
            self.check["data"]["check_id"])
        rows = {row["record"]: row for row in value["points"][0]["executions"]}
        explicit = rows[self.execution4["_id"]]
        self.assertEqual(explicit["environment"], {
            "availability": "available",
            "contract": self.explicit_environment1["contract"],
            "digest": self.explicit_environment1["digest"],
            "descriptor": self.explicit_environment1["descriptor"],
        })
        self.assertEqual(explicit["producer_policy_digest"], rid("a7"))
        self.assertIsNone(explicit["environment_digest"])
        self.assertEqual(explicit["record"], self.execution4["_id"])

    def test_mixed_environment_history_preserves_caller_order_and_execution_identity(self):
        value = self.query(
            "verification_history", [self.s4["_id"], self.s1["_id"]],
            self.check["data"]["check_id"])
        self.assertEqual(
            [point["snapshot"] for point in value["points"]],
            [self.s4["_id"], self.s1["_id"]])
        first = {row["record"]: row for row in value["points"][0]["executions"]}
        self.assertEqual(first[self.execution1["_id"]]["environment"]["availability"],
                         "legacy-opaque")
        self.assertEqual(first[self.execution4["_id"]]["environment"]["availability"],
                         "available")
        second = value["points"][1]["executions"]
        self.assertEqual([row["record"] for row in second], [self.execution1["_id"]])
        self.assertEqual(second[0]["environment"]["availability"], "legacy-opaque")

    def test_multiple_definitions_and_executions_keep_each_environment_fact(self):
        value = self.query(
            "verification_history", [self.s4["_id"]],
            self.check["data"]["check_id"])
        point = value["points"][0]
        self.assertEqual(point["definition_count"], 2)
        self.assertEqual(point["execution_count"], 3)
        rows = {row["record"]: row for row in point["executions"]}
        self.assertEqual(rows[self.execution4["_id"]]["environment"]["digest"], self.explicit_environment1["digest"])
        self.assertEqual(rows[self.execution5["_id"]]["environment"]["digest"], self.explicit_environment2["digest"])
        self.assertEqual(rows[self.execution4["_id"]]["producer_policy_digest"], rid("a7"))
        self.assertEqual(rows[self.execution5["_id"]]["producer_policy_digest"], rid("a9"))
        self.assertEqual(rows[self.execution5["_id"]]["outcome"], "ERROR")

    def test_missing_execution_is_absent_not_synthetic_skip(self):
        value = self.query(
            "verification_history", [self.s1["_id"]],
            self.check["data"]["check_id"],
            definition_digest=self.check2["data"]["definition_digest"])
        point = value["points"][0]
        self.assertEqual(point["execution_count"], 0)
        self.assertEqual(point["executions"], [])
        self.assertNotIn("SKIP", json.dumps(point))

    def test_environment_projection_does_not_change_completeness_or_coverage(self):
        legacy = self.query(
            "verification_history", [self.s1["_id"]],
            self.check["data"]["check_id"])["points"][0]
        explicit = self.query(
            "verification_history", [self.s4["_id"]],
            self.check["data"]["check_id"])["points"][0]
        for key in (
            "reference_closure_complete", "missing_record_count",
            "declared_gap_free", "declared_gap_count",
            "declared_gap_reason_count", "declared_gap_summary",
            "coverage_availability",
        ):
            self.assertEqual(explicit[key], legacy[key])
        self.assertEqual(explicit["coverage"], legacy["coverage"])

    def test_environment_projection_contains_no_compatibility_or_regression_result(self):
        value = self.query(
            "verification_history", [self.s1["_id"], self.s4["_id"]],
            self.check["data"]["check_id"])
        for point in value["points"]:
            for row in point["executions"]:
                self.assertFalse({"compatible", "comparable", "regression"} & set(row))

    def test_build_record_canonical_boundary_rejects_malformed_explicit_environment(self):
        try:
            from zog.build_record import RecordError, validate
        except ImportError:
            self.skipTest("requires build-record")
        record = {
            "schema_version": 1,
            "kind": "verification-execution",
            "data": dict(self.execution4["data"]),
            "gaps": [],
        }
        validate(record)
        malformed = json.loads(json.dumps(record))
        malformed["data"]["execution_environment"]["digest"] = "not-a-digest"
        with self.assertRaises(RecordError):
            validate(malformed)

    def test_relationship_traversal_is_literal_and_coverage_aware(self):
        reverse = self.query(
            "relationship_traversal",
            [self.s1["_id"], self.s3["_id"]],
            "reverse", "soname", "libdemo.so.1",
        )
        self.assertEqual(reverse["match_semantics"], "literal-canonical-fields-only")
        self.assertEqual(reverse["points"][0]["relationship_count"], 1)
        self.assertEqual(reverse["points"][1]["relationship_count"], 2)
        self.assertEqual(
            {row["relation"] for row in reverse["points"][1]["relationships"]},
            {"needs-library", "provides-soname"},
        )
        coverage1 = next(row for row in reverse["points"][0]["coverage"]
                         if row["family"] == "elf-interfaces")
        coverage3 = next(row for row in reverse["points"][1]["coverage"]
                         if row["family"] == "elf-interfaces")
        self.assertEqual(coverage1["outcome"], "complete")
        self.assertEqual(coverage3["outcome"], "partial")

        forward = self.query(
            "relationship_traversal",
            [self.s1["_id"], self.s3["_id"]],
            "forward", "package", "provider",
            relation="provides-soname",
        )
        self.assertEqual(forward["points"][0]["relationship_count"], 0)
        self.assertEqual(forward["points"][1]["relationship_count"], 1)
        self.assertEqual(
            forward["points"][1]["relationships"][0]["subject"]["path"],
            "/usr/lib/libdemo.so.1",
        )

    def test_relationship_traversal_rejects_direction_selector_mismatch(self):
        with self.assertRaises(TraceError) as caught:
            self.query(
                "relationship_traversal",
                [self.s1["_id"]],
                "forward", "soname", "libdemo.so.1",
            )
        self.assertEqual(caught.exception.code, "invalid-query")

    def test_history_and_traversal_cli_dispatch(self):
        common = [
            "--project-root", str(self.root),
            "--host-id", "host",
            "--record-store", str(self.root / "records"),
            "--record-project-id", "project",
        ]
        out = io.StringIO()
        with patch("zog.build_trace.snapshot_observations.Reader", FakeReader), redirect_stdout(out):
            code = main(common + [
                "verification-history",
                self.check["data"]["check_id"],
                self.s1["_id"], self.s3["_id"],
            ])
        self.assertEqual(code, 0)
        history = json.loads(out.getvalue())
        self.assertEqual(history["kind"], "verification-history")
        self.assertEqual([point["position"] for point in history["points"]], [1, 2])

        out = io.StringIO()
        with patch("zog.build_trace.snapshot_observations.Reader", FakeReader), redirect_stdout(out):
            code = main(common + [
                "relationship-traversal", "reverse", "soname", "libdemo.so.1",
                self.s1["_id"], self.s3["_id"],
                "--relation", "provides-soname",
            ])
        self.assertEqual(code, 0)
        traversal = json.loads(out.getvalue())
        self.assertEqual(traversal["kind"], "relationship-traversal")
        self.assertEqual(traversal["points"][0]["relationship_count"], 0)
        self.assertEqual(traversal["points"][1]["relationship_count"], 1)

    def test_invalid_snapshot_record_identity_is_query_error(self):
        with self.assertRaises(TraceError) as caught:
            self.query("observation_snapshot", "not-a-record")
        self.assertEqual(caught.exception.code, "invalid-query")


if __name__ == "__main__":
    unittest.main()
