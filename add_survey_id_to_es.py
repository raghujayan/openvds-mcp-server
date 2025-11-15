#!/usr/bin/env python3
"""
Add survey_id field to all existing Elasticsearch documents (in-place update)

This is much faster than re-crawling all 2,858 VDS files.
"""

import requests
import json
from typing import Dict, List

ES_URL = "http://localhost:9200"
INDEX_NAME = "vds-metadata"


def get_all_documents() -> List[Dict]:
    """Fetch all documents from ES"""
    url = f"{ES_URL}/{INDEX_NAME}/_search"
    params = {"size": 10000}  # Max docs to fetch

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    hits = data["hits"]["hits"]

    print(f"Fetched {len(hits)} documents from Elasticsearch")
    return hits


def extract_survey_id(file_path: str) -> str:
    """Extract survey_id from file_path (basename without .vds extension)"""
    basename = file_path.split("/")[-1]
    survey_id = basename.replace(".vds", "")
    return survey_id


def update_document(doc_id: str, survey_id: str) -> None:
    """Update a single document to add survey_id field"""
    url = f"{ES_URL}/{INDEX_NAME}/_update/{doc_id}"
    payload = {
        "doc": {
            "survey_id": survey_id
        }
    }

    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()


def main():
    print("=" * 80)
    print("ADDING survey_id TO ALL ELASTICSEARCH DOCUMENTS")
    print("=" * 80)

    # Fetch all documents
    documents = get_all_documents()

    if not documents:
        print("No documents found in Elasticsearch!")
        return

    # Count documents missing survey_id
    missing_count = 0
    for doc in documents:
        if "survey_id" not in doc["_source"]:
            missing_count += 1

    print(f"\nDocuments missing survey_id: {missing_count} / {len(documents)}")

    if missing_count == 0:
        print("All documents already have survey_id field!")
        return

    # Update all documents
    print(f"\nUpdating {missing_count} documents...")

    updated = 0
    errors = 0

    for i, doc in enumerate(documents, 1):
        doc_id = doc["_id"]
        source = doc["_source"]

        # Skip if survey_id already exists
        if "survey_id" in source:
            continue

        # Extract survey_id from file_path
        file_path = source.get("file_path", "")
        if not file_path:
            print(f"  WARNING: Document {doc_id} has no file_path, skipping")
            errors += 1
            continue

        survey_id = extract_survey_id(file_path)

        try:
            update_document(doc_id, survey_id)
            updated += 1

            if updated % 100 == 0:
                print(f"  Progress: {updated}/{missing_count} documents updated...")

        except Exception as e:
            print(f"  ERROR updating document {doc_id}: {e}")
            errors += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total documents: {len(documents)}")
    print(f"Updated: {updated}")
    print(f"Errors: {errors}")
    print(f"Already had survey_id: {len(documents) - missing_count}")

    if errors == 0:
        print("\n✅ All documents successfully updated!")
    else:
        print(f"\n⚠️  Completed with {errors} errors")


if __name__ == "__main__":
    main()
