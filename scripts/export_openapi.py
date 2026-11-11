#!/usr/bin/env python3
"""
Export OpenAPI schema from FastAPI application
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api" / "src"))

from app.main import app


def export_openapi():
    """Export OpenAPI schema to contracts/openapi.json"""
    schema = app.openapi()

    # Ensure contracts directory exists
    contracts_dir = Path(__file__).parent.parent / "contracts"
    contracts_dir.mkdir(exist_ok=True)

    # Write schema
    output_path = contracts_dir / "openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"✓ OpenAPI schema exported to {output_path}")
    print(f"  Title: {schema['info']['title']}")
    print(f"  Version: {schema['info']['version']}")
    print(f"  Paths: {len(schema.get('paths', {}))}")


if __name__ == "__main__":
    export_openapi()
