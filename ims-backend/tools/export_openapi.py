#!/usr/bin/env python3
"""
OpenAPI specification export tool (FP-A05-01).

Exports the OpenAPI specification from the FastAPI application to openapi.json.

Usage:
    python tools/export_openapi.py           # Export to openapi.json
    python tools/export_openapi.py --validate  # Validate current code matches openapi.json

Rules per FP-A05-01:
- Each endpoint must have summary (Chinese) and tags (domain)
- CI compares: backend OpenAPI vs committed openapi.json
"""

import argparse
import json
import sys
from pathlib import Path


def get_openapi_spec() -> dict:
    """Get OpenAPI spec from the FastAPI app."""
    # Set test environment to include demo routes
    import os
    os.environ.setdefault("IMS_ENV", "test")

    from app.main import app

    return app.openapi()


def export_openapi(output_path: Path) -> None:
    """Export OpenAPI spec to JSON file."""
    spec = get_openapi_spec()

    # Sort keys for consistent output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"OpenAPI specification exported to {output_path}")

    # Print summary
    paths = spec.get("paths", {})
    print(f"Total endpoints: {sum(len(methods) for methods in paths.values())}")

    # List by tag
    tags = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            for tag in details.get("tags", ["untagged"]):
                tags.setdefault(tag, []).append(f"{method.upper()} {path}")

    print("\nEndpoints by domain:")
    for tag, endpoints in sorted(tags.items()):
        print(f"  {tag}: {len(endpoints)} endpoints")


def validate_openapi(spec_path: Path) -> bool:
    """Validate current code matches committed openapi.json."""
    if not spec_path.exists():
        print(f"ERROR: {spec_path} not found. Run 'make openapi-export' first.")
        return False

    # Load committed spec
    with open(spec_path, "r", encoding="utf-8") as f:
        committed_spec = json.load(f)

    # Get current spec
    current_spec = get_openapi_spec()

    # Compare (sort keys for consistent comparison)
    committed_json = json.dumps(committed_spec, sort_keys=True)
    current_json = json.dumps(current_spec, sort_keys=True)

    if committed_json != current_json:
        print("ERROR: OpenAPI spec differs from committed version.")
        print("Run 'make api-gen' to update openapi.json and frontend clients.")

        # Show diff summary
        committed_paths = set(committed_spec.get("paths", {}).keys())
        current_paths = set(current_spec.get("paths", {}).keys())

        added = current_paths - committed_paths
        removed = committed_paths - current_paths

        if added:
            print(f"\nNew endpoints: {added}")
        if removed:
            print(f"\nRemoved endpoints: {removed}")

        return False

    print("OpenAPI specification is up to date.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Export or validate OpenAPI specification")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate current code matches openapi.json (for CI)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi.json"),
        help="Output path for openapi.json"
    )

    args = parser.parse_args()

    if args.validate:
        success = validate_openapi(args.output)
        sys.exit(0 if success else 1)
    else:
        export_openapi(args.output)


if __name__ == "__main__":
    main()
