from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pymongo import ASCENDING, DESCENDING
from pymongo.collection import ReturnDocument
from pymongo.database import Database


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MongoRepository:
    def __init__(self, db: Database):
        self.db = db
        self.patients = db["patients"]
        self.snapshots = db["medication_snapshots"]
        self.conflicts = db["medication_conflicts"]

    def ensure_indexes(self) -> None:
        self.patients.create_index([("clinic_id", ASCENDING)])
        self.snapshots.create_index([("patient_id", ASCENDING), ("source", ASCENDING), ("version", DESCENDING)])
        self.snapshots.create_index([("patient_id", ASCENDING), ("captured_at", DESCENDING)])
        self.conflicts.create_index([("clinic_id", ASCENDING), ("resolved", ASCENDING), ("last_seen_at", DESCENDING)])
        self.conflicts.create_index([("patient_id", ASCENDING), ("conflict_key", ASCENDING)], unique=True)

    def create_patient(self, payload: dict[str, Any]) -> dict[str, Any]:
        doc = {"_id": str(uuid4()), "created_at": utc_now(), **payload}
        self.patients.insert_one(doc)
        return doc

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        return self.patients.find_one({"_id": patient_id})

    def get_latest_snapshot(self, patient_id: str, source: str) -> dict[str, Any] | None:
        return self.snapshots.find_one(
            {"patient_id": patient_id, "source": source},
            sort=[("version", DESCENDING)],
        )

    def get_latest_snapshots_for_patient(self, patient_id: str) -> dict[str, dict[str, Any]]:
        pipeline = [
            {"$match": {"patient_id": patient_id}},
            {"$sort": {"source": 1, "version": -1}},
            {
                "$group": {
                    "_id": "$source",
                    "doc": {"$first": "$$ROOT"},
                }
            },
        ]
        rows = self.snapshots.aggregate(pipeline)
        return {row["_id"]: row["doc"] for row in rows}

    def create_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        doc = {"_id": str(uuid4()), "created_at": utc_now(), **payload}
        self.snapshots.insert_one(doc)
        return doc

    def upsert_conflict(self, conflict_doc: dict[str, Any]) -> dict[str, Any]:
        existing = self.conflicts.find_one(
            {
                "patient_id": conflict_doc["patient_id"],
                "conflict_key": conflict_doc["conflict_key"],
            }
        )
        if existing:
            update_data = {
                "summary": conflict_doc["summary"],
                "details": conflict_doc["details"],
                "involved_drugs": conflict_doc["involved_drugs"],
                "involved_sources": conflict_doc["involved_sources"],
                "resolved": False,
                "resolution_reason": None,
                "chosen_source": None,
                "resolved_at": None,
                "last_seen_at": utc_now(),
            }
            self.conflicts.update_one({"_id": existing["_id"]}, {"$set": update_data})
            existing.update(update_data)
            return existing

        doc = {
            "_id": str(uuid4()),
            "created_at": utc_now(),
            "last_seen_at": utc_now(),
            "resolved": False,
            "resolution_reason": None,
            "chosen_source": None,
            "resolved_at": None,
            **conflict_doc,
        }
        self.conflicts.insert_one(doc)
        return doc

    def auto_resolve_conflicts_not_in_keys(self, patient_id: str, active_keys: set[str]) -> None:
        query = {"patient_id": patient_id, "resolved": False}
        if active_keys:
            query["conflict_key"] = {"$nin": list(active_keys)}
        updates = {
            "$set": {
                "resolved": True,
                "resolution_reason": "auto_resolved_no_longer_detected",
                "chosen_source": None,
                "resolved_at": utc_now(),
                "last_seen_at": utc_now(),
            }
        }
        self.conflicts.update_many(query, updates)

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_reason: str,
        chosen_source: str | None,
        resolver: str | None,
    ) -> dict[str, Any] | None:
        updates = {
            "resolved": True,
            "resolution_reason": resolution_reason,
            "chosen_source": chosen_source,
            "resolved_at": utc_now(),
            "resolved_by": resolver,
            "last_seen_at": utc_now(),
        }
        result = self.conflicts.find_one_and_update(
            {"_id": conflict_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        return result

    def get_unresolved_patients_by_clinic(self, clinic_id: str) -> list[dict[str, Any]]:
        pipeline = [
            {"$match": {"clinic_id": clinic_id, "resolved": False}},
            {
                "$group": {
                    "_id": "$patient_id",
                    "conflicts": {"$push": "$$ROOT"},
                    "conflict_count": {"$sum": 1},
                }
            },
            {
                "$lookup": {
                    "from": "patients",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "patient",
                }
            },
            {"$unwind": "$patient"},
            {
                "$project": {
                    "_id": 0,
                    "patient_id": "$patient._id",
                    "patient_name": {
                        "$concat": ["$patient.first_name", " ", "$patient.last_name"]
                    },
                    "clinic_id": "$patient.clinic_id",
                    "conflict_count": 1,
                    "conflicts": {
                        "$map": {
                            "input": "$conflicts",
                            "as": "c",
                            "in": {
                                "id": "$$c._id",
                                "type": "$$c.conflict_type",
                                "summary": "$$c.summary",
                                "involved_drugs": "$$c.involved_drugs",
                                "last_seen_at": "$$c.last_seen_at",
                            },
                        }
                    },
                }
            },
            {"$sort": {"conflict_count": -1, "patient_name": 1}},
        ]
        return list(self.conflicts.aggregate(pipeline))

    def get_30d_conflict_summary(self, min_conflicts: int = 2) -> list[dict[str, Any]]:
        since = utc_now() - timedelta(days=30)
        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": {"clinic_id": "$clinic_id", "patient_id": "$patient_id"},
                    "conflict_count": {"$sum": 1},
                }
            },
            {"$match": {"conflict_count": {"$gte": min_conflicts}}},
            {
                "$group": {
                    "_id": "$_id.clinic_id",
                    "patients_with_conflicts": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "clinic_id": "$_id",
                    "patients_with_conflicts": 1,
                }
            },
            {"$sort": {"clinic_id": 1}},
        ]
        return list(self.conflicts.aggregate(pipeline))

    def get_patient_history(self, patient_id: str) -> list[dict[str, Any]]:
        cursor = self.snapshots.find({"patient_id": patient_id}).sort(
            [("captured_at", DESCENDING), ("version", DESCENDING)]
        )
        return list(cursor)


class InMemoryRepository:
    def __init__(self):
        self.patients: dict[str, dict[str, Any]] = {}
        self.snapshots: list[dict[str, Any]] = []
        self.conflicts: dict[str, dict[str, Any]] = {}

    def ensure_indexes(self) -> None:
        return None

    def create_patient(self, payload: dict[str, Any]) -> dict[str, Any]:
        doc = {"_id": str(uuid4()), "created_at": utc_now(), **payload}
        self.patients[doc["_id"]] = deepcopy(doc)
        return deepcopy(doc)

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        patient = self.patients.get(patient_id)
        return deepcopy(patient) if patient else None

    def get_latest_snapshot(self, patient_id: str, source: str) -> dict[str, Any] | None:
        candidates = [
            s for s in self.snapshots if s["patient_id"] == patient_id and s["source"] == source
        ]
        if not candidates:
            return None
        row = sorted(candidates, key=lambda x: x["version"], reverse=True)[0]
        return deepcopy(row)

    def get_latest_snapshots_for_patient(self, patient_id: str) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for snapshot in self.snapshots:
            if snapshot["patient_id"] == patient_id:
                grouped[snapshot["source"]].append(snapshot)
        return {
            source: deepcopy(sorted(values, key=lambda x: x["version"], reverse=True)[0])
            for source, values in grouped.items()
        }

    def create_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        doc = {"_id": str(uuid4()), "created_at": utc_now(), **payload}
        self.snapshots.append(deepcopy(doc))
        return deepcopy(doc)

    def upsert_conflict(self, conflict_doc: dict[str, Any]) -> dict[str, Any]:
        lookup = (conflict_doc["patient_id"], conflict_doc["conflict_key"])
        existing = next(
            (c for c in self.conflicts.values() if (c["patient_id"], c["conflict_key"]) == lookup),
            None,
        )
        now = utc_now()
        if existing:
            existing.update(
                {
                    "summary": conflict_doc["summary"],
                    "details": conflict_doc["details"],
                    "involved_drugs": conflict_doc["involved_drugs"],
                    "involved_sources": conflict_doc["involved_sources"],
                    "resolved": False,
                    "resolution_reason": None,
                    "chosen_source": None,
                    "resolved_at": None,
                    "last_seen_at": now,
                }
            )
            return deepcopy(existing)

        doc = {
            "_id": str(uuid4()),
            "created_at": now,
            "last_seen_at": now,
            "resolved": False,
            "resolution_reason": None,
            "chosen_source": None,
            "resolved_at": None,
            **conflict_doc,
        }
        self.conflicts[doc["_id"]] = doc
        return deepcopy(doc)

    def auto_resolve_conflicts_not_in_keys(self, patient_id: str, active_keys: set[str]) -> None:
        for conflict in self.conflicts.values():
            if conflict["patient_id"] != patient_id or conflict["resolved"]:
                continue
            if conflict["conflict_key"] in active_keys:
                continue
            conflict.update(
                {
                    "resolved": True,
                    "resolution_reason": "auto_resolved_no_longer_detected",
                    "chosen_source": None,
                    "resolved_at": utc_now(),
                    "last_seen_at": utc_now(),
                }
            )

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_reason: str,
        chosen_source: str | None,
        resolver: str | None,
    ) -> dict[str, Any] | None:
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return None
        conflict.update(
            {
                "resolved": True,
                "resolution_reason": resolution_reason,
                "chosen_source": chosen_source,
                "resolved_at": utc_now(),
                "resolved_by": resolver,
                "last_seen_at": utc_now(),
            }
        )
        return deepcopy(conflict)

    def get_unresolved_patients_by_clinic(self, clinic_id: str) -> list[dict[str, Any]]:
        conflicts_by_patient: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for conflict in self.conflicts.values():
            if conflict["clinic_id"] == clinic_id and not conflict["resolved"]:
                conflicts_by_patient[conflict["patient_id"]].append(deepcopy(conflict))

        result: list[dict[str, Any]] = []
        for patient_id, conflicts in conflicts_by_patient.items():
            patient = self.patients.get(patient_id)
            if not patient:
                continue
            result.append(
                {
                    "patient_id": patient_id,
                    "patient_name": f"{patient['first_name']} {patient['last_name']}",
                    "clinic_id": clinic_id,
                    "conflict_count": len(conflicts),
                    "conflicts": [
                        {
                            "id": c["_id"],
                            "type": c["conflict_type"],
                            "summary": c["summary"],
                            "involved_drugs": c["involved_drugs"],
                            "last_seen_at": c["last_seen_at"],
                        }
                        for c in conflicts
                    ],
                }
            )
        result.sort(key=lambda x: (-x["conflict_count"], x["patient_name"]))
        return result

    def get_30d_conflict_summary(self, min_conflicts: int = 2) -> list[dict[str, Any]]:
        since = utc_now() - timedelta(days=30)
        per_patient: dict[tuple[str, str], int] = defaultdict(int)
        for conflict in self.conflicts.values():
            if conflict["created_at"] >= since:
                per_patient[(conflict["clinic_id"], conflict["patient_id"])] += 1

        per_clinic: dict[str, int] = defaultdict(int)
        for (clinic_id, _patient_id), count in per_patient.items():
            if count >= min_conflicts:
                per_clinic[clinic_id] += 1

        return [
            {"clinic_id": clinic_id, "patients_with_conflicts": count}
            for clinic_id, count in sorted(per_clinic.items(), key=lambda x: x[0])
        ]

    def get_patient_history(self, patient_id: str) -> list[dict[str, Any]]:
        history = [s for s in self.snapshots if s["patient_id"] == patient_id]
        history.sort(key=lambda x: (x["captured_at"], x["version"]), reverse=True)
        return deepcopy(history)
