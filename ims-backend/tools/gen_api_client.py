#!/usr/bin/env python3
"""
Frontend TypeScript API client generator (FP-A05-01).

Generates TypeScript type definitions and request functions from openapi.json.

Usage:
    python tools/gen_api_client.py

Output:
    ims-web/src/api/generated/<domain>.ts

Rules per FP-A05-01:
- Frontend business code must not contain /admin-api strings (static check)
- Only generated/ and request base can contain /admin-api
"""

import json
import re
from datetime import datetime
from pathlib import Path

# Map OpenAPI types to TypeScript types
TYPE_MAP = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "array": "any[]",
    "object": "Record<string, any>",
}


def openapi_type_to_ts(schema: dict, ref_resolver: dict) -> str:
    """Convert OpenAPI schema to TypeScript type."""
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return ref_name

    schema_type = schema.get("type", "any")

    if schema_type == "array":
        items = schema.get("items", {})
        item_type = openapi_type_to_ts(items, ref_resolver)
        return f"{item_type}[]"

    if schema_type == "object":
        additional = schema.get("additionalProperties")
        if additional:
            value_type = openapi_type_to_ts(additional, ref_resolver)
            return f"Record<string, {value_type}>"
        return "Record<string, any>"

    # Handle allOf, anyOf, oneOf
    if "allOf" in schema:
        types = [openapi_type_to_ts(s, ref_resolver) for s in schema["allOf"]]
        return " & ".join(types)

    if "anyOf" in schema or "oneOf" in schema:
        items = schema.get("anyOf") or schema.get("oneOf")
        types = [openapi_type_to_ts(s, ref_resolver) for s in items]
        return " | ".join(types)

    return TYPE_MAP.get(schema_type, "any")


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def generate_interface(name: str, schema: dict, ref_resolver: dict) -> str:
    """Generate TypeScript interface from OpenAPI schema."""
    lines = [f"export interface {name} {{"]

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for prop_name, prop_schema in properties.items():
        ts_name = snake_to_camel(prop_name)
        ts_type = openapi_type_to_ts(prop_schema, ref_resolver)
        optional = "" if prop_name in required else "?"
        description = prop_schema.get("description", "")

        if description:
            lines.append(f"  /** {description} */")
        lines.append(f"  {ts_name}{optional}: {ts_type};")

    lines.append("}")
    return "\n".join(lines)


def generate_api_function(
    path: str,
    method: str,
    operation: dict,
    ref_resolver: dict,
) -> str:
    """Generate TypeScript API function."""
    operation_id = operation.get("operationId", "")
    summary = operation.get("summary", "")

    # Generate clean function name from path
    # /admin-api/ims/auth/login -> login
    # /admin-api/ims/system/dept/tree -> getDeptTree
    # /admin-api/ims/system/user/page -> getUserPage
    path_parts = path.replace("/admin-api/ims/", "").strip("/").split("/")

    # Remove domain prefix (auth, system, demo)
    if len(path_parts) > 1:
        path_parts = path_parts[1:]

    # Build function name based on method
    method_prefixes = {
        "get": "get",
        "post": "",  # POST usually implies create/action
        "put": "update",
        "delete": "delete",
        "patch": "patch",
    }

    prefix = method_prefixes.get(method.lower(), method.lower())

    # Handle common patterns
    if len(path_parts) == 1:
        name = path_parts[0]
        if method == "post" and name == "login":
            func_name = "login"
        elif method == "post" and name == "logout":
            func_name = "logout"
        elif method == "post" and name == "refresh-token":
            func_name = "refreshToken"
        else:
            func_name = prefix + name.replace("-", " ").title().replace(" ", "")
    else:
        # Multi-part path: dept/tree -> getDeptTree, user/page -> getUserPage
        path_name = "".join(
            p.replace("-", " ").title().replace(" ", "")
            for p in path_parts
            if not p.startswith("{")
        )
        func_name = prefix + path_name

    # Ensure first char is lowercase
    if func_name:
        func_name = func_name[0].lower() + func_name[1:]

    # Collect parameters
    params = operation.get("parameters", [])
    path_params = [p for p in params if p.get("in") == "path"]
    query_params = [p for p in params if p.get("in") == "query"]

    # Get request body
    request_body = operation.get("requestBody", {})
    body_schema = None
    if request_body:
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        body_schema = json_content.get("schema", {})

    # Get response type
    responses = operation.get("responses", {})
    success_response = responses.get("200", {})
    response_content = success_response.get("content", {})
    response_json = response_content.get("application/json", {})
    response_schema = response_json.get("schema", {})
    response_type = openapi_type_to_ts(response_schema, ref_resolver) if response_schema else "any"

    # Build function signature
    func_params = []

    # Path parameters
    for p in path_params:
        p_name = snake_to_camel(p["name"])
        p_type = openapi_type_to_ts(p.get("schema", {}), ref_resolver)
        func_params.append(f"{p_name}: {p_type}")

    # Query parameters as object
    if query_params:
        query_type_parts = []
        for p in query_params:
            p_name = snake_to_camel(p["name"])
            p_type = openapi_type_to_ts(p.get("schema", {}), ref_resolver)
            optional = "" if p.get("required") else "?"
            query_type_parts.append(f"{p_name}{optional}: {p_type}")
        query_type = "{ " + "; ".join(query_type_parts) + " }"
        func_params.append(f"params: {query_type}")

    # Request body
    if body_schema:
        body_type = openapi_type_to_ts(body_schema, ref_resolver)
        func_params.append(f"data: {body_type}")

    params_str = ", ".join(func_params)

    # Build function body
    lines = []
    if summary:
        lines.append("/**")
        lines.append(f" * {summary}")
        lines.append(" */")

    lines.append(f"export async function {func_name}({params_str}): Promise<{response_type}> {{")

    # Build URL
    url_path = path
    for p in path_params:
        p_name = snake_to_camel(p["name"])
        url_path = url_path.replace("{" + p["name"] + "}", f"${{{p_name}}}")

    if path_params:
        lines.append(f"  const url = `{url_path}`;")
    else:
        lines.append(f"  const url = '{url_path}';")

    # Build request options
    options = [f"method: '{method.upper()}'"]
    if query_params:
        options.append("params")
    if body_schema:
        options.append("data")

    options_str = ", ".join(options)
    lines.append(f"  return request(url, {{ {options_str} }});")
    lines.append("}")

    return "\n".join(lines)


def generate_domain_file(
    domain: str,
    paths: dict[str, dict],
    schemas: dict,
    ref_resolver: dict,
) -> str:
    """Generate TypeScript file for a domain."""
    lines = [
        "/**",
        f" * {domain} API - Auto-generated from OpenAPI",
        f" * Generated at: {datetime.now().isoformat()}",
        " * DO NOT EDIT MANUALLY",
        " */",
        "",
        "import { request } from '../request';",
        "",
    ]

    # Collect used schemas
    used_schemas = set()

    # Generate API functions
    functions = []
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                func = generate_api_function(path, method, operation, ref_resolver)
                functions.append(func)

                # Track used schemas
                for param in operation.get("parameters", []):
                    schema = param.get("schema", {})
                    if "$ref" in schema:
                        used_schemas.add(schema["$ref"].split("/")[-1])

    # Generate interfaces for used schemas
    interfaces = []
    for schema_name in sorted(used_schemas):
        if schema_name in schemas:
            interface = generate_interface(schema_name, schemas[schema_name], ref_resolver)
            interfaces.append(interface)

    if interfaces:
        lines.append("// Types")
        lines.extend(interfaces)
        lines.append("")

    lines.append("// API Functions")
    lines.extend(functions)

    return "\n\n".join(lines)


def main():
    # Load OpenAPI spec
    spec_path = Path("openapi.json")
    if not spec_path.exists():
        print("ERROR: openapi.json not found. Run 'make openapi-export' first.")
        return

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})
    ref_resolver = schemas

    # Map Chinese tags to domain names
    TAG_TO_DOMAIN = {
        "认证": "auth",
        "系统管理": "system",
        "演示": "demo",
        "健康检查": "health",
    }

    # Group paths by tag (domain)
    domains: dict[str, dict] = {}
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            tags = operation.get("tags", ["common"])
            for tag in tags:
                # Map Chinese tag to domain name
                domain = TAG_TO_DOMAIN.get(tag)
                if not domain:
                    # Normalize non-Chinese tag name
                    domain = re.sub(r"[^a-zA-Z0-9]", "_", tag).lower()
                    if not domain or domain == "_":
                        domain = "common"
                if domain not in domains:
                    domains[domain] = {}
                if path not in domains[domain]:
                    domains[domain][path] = {}
                domains[domain][path][method] = operation

    # Output directory
    output_dir = Path("../ims-web/src/api/generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate files
    for domain, domain_paths in domains.items():
        content = generate_domain_file(domain, domain_paths, schemas, ref_resolver)
        output_path = output_dir / f"{domain}.ts"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Generated {output_path}")

    # Generate index file
    index_lines = [
        "/**",
        " * API Index - Auto-generated",
        " * DO NOT EDIT MANUALLY",
        " */",
        "",
    ]
    for domain in sorted(domains.keys()):
        index_lines.append(f"export * from './{domain}';")

    index_path = output_dir / "index.ts"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    print(f"\nGenerated {len(domains)} domain files")
    print(f"Index file: {index_path}")


if __name__ == "__main__":
    main()
