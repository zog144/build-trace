"""Minimal independent consumer for the early integrate-observe read-only contract.

This module intentionally imports only the public zog.build_trace package surface.  It does
not know build-record schemas, image-build producer layouts, or build-trace internals.
"""
from zog.build_trace import BuildTrace


def inspect_sequence(
    trace: BuildTrace,
    snapshots,
    *,
    check_id,
    soname,
    package,
):
    """Return a neutral factual digest for one caller-selected snapshot sequence."""
    snapshots = list(snapshots)
    if not snapshots:
        raise ValueError("at least one snapshot is required")

    first = trace.observation_snapshot(snapshots[0])
    last = trace.observation_snapshot(snapshots[-1])
    comparison = trace.compare_observation_snapshots(snapshots[0], snapshots[-1])
    verification = trace.verification_history(snapshots, check_id)
    reverse_interfaces = trace.relationship_traversal(
        snapshots, "reverse", "soname", soname)
    package_relationships = trace.relationship_traversal(
        snapshots, "forward", "package", package)

    return {
        "contract": "build-trace-independent-consumer-v1",
        "snapshot_count": len(snapshots),
        "caller_order": list(snapshots),
        "first": {
            "snapshot": first["snapshot"],
            "generation_record": first["generation_record"],
            "reference_closure_complete": first["reference_closure_complete"],
            "missing_record_count": first["missing_record_count"],
            "declared_gap_free": first["declared_gap_free"],
            "declared_gap_count": first["declared_gap_count"],
            "declared_gap_summary": first["declared_gap_summary"],
            "coverage": first["coverage"],
        },
        "last": {
            "snapshot": last["snapshot"],
            "generation_record": last["generation_record"],
            "reference_closure_complete": last["reference_closure_complete"],
            "missing_record_count": last["missing_record_count"],
            "declared_gap_free": last["declared_gap_free"],
            "declared_gap_count": last["declared_gap_count"],
            "declared_gap_summary": last["declared_gap_summary"],
            "coverage": last["coverage"],
        },
        "comparison": {
            "same_generation_record": comparison["same_generation_record"],
            "same_root_inventory": comparison["same_root_inventory"],
            "same_record_set": comparison["same_record_set"],
            "collections": comparison["collections"],
            "verification_check_changes": comparison["verification_check_changes"],
            "coverage_changes": comparison["coverage_changes"],
            "before_reference_closure_complete": comparison["before_reference_closure_complete"],
            "after_reference_closure_complete": comparison["after_reference_closure_complete"],
            "before_missing_record_count": comparison["before_missing_record_count"],
            "after_missing_record_count": comparison["after_missing_record_count"],
            "before_declared_gap_free": comparison["before_declared_gap_free"],
            "after_declared_gap_free": comparison["after_declared_gap_free"],
            "before_declared_gap_count": comparison["before_declared_gap_count"],
            "after_declared_gap_count": comparison["after_declared_gap_count"],
            "before_declared_gap_summary": comparison["before_declared_gap_summary"],
            "after_declared_gap_summary": comparison["after_declared_gap_summary"],
            "before_coverage": comparison["before_coverage"],
            "after_coverage": comparison["after_coverage"],
        },
        "verification": {
            "check_id": verification["check_id"],
            "order": verification["order"],
            "chronology": verification["chronology"],
            "points": verification["points"],
        },
        "reverse_interfaces": {
            "direction": reverse_interfaces["direction"],
            "selector": reverse_interfaces["selector"],
            "match_semantics": reverse_interfaces["match_semantics"],
            "order": reverse_interfaces["order"],
            "chronology": reverse_interfaces["chronology"],
            "points": reverse_interfaces["points"],
        },
        "package_relationships": {
            "direction": package_relationships["direction"],
            "selector": package_relationships["selector"],
            "match_semantics": package_relationships["match_semantics"],
            "order": package_relationships["order"],
            "chronology": package_relationships["chronology"],
            "points": package_relationships["points"],
        },
        "interpretation": {
            "baseline_selected": False,
            "chronology_inferred": False,
            "representative_execution_selected": False,
            "environment_compatibility_evaluated": False,
            "provider_resolution_performed": False,
            "regression_classified": False,
            "blast_radius_computed": False,
        },
    }
