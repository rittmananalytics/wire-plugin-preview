#!/usr/bin/env python3
"""Deterministic, AI-free linter for Wire's per-domain conventions.

Reads a wire/conventions/<domain>.yml file (see
wire/schemas/convention-schema.md) and checks target files against whichever
rules in it are mechanically checkable — filename patterns, forbidden/
required text patterns, style thresholds, and a handful of domain-specific
structural checks (dbt cast-macro suffixes, LookML refinement placement,
Cube required fields). Rules without a recognised check hook are
documentation for the agent, not enforced here.

This exists so the naming/style half of a review doesn't cost an AI call or
depend on an agent's semantic read of a 1000-line prose spec — it runs the
same way every time, for free. Judgment calls (grain choice, join direction,
whether a pre-aggregation is warranted) are explicitly out of scope; see the
matching skill file for those.

Usage:
  python3 wire/scripts/lint_conventions.py --domain dbt \\
      --convention wire/conventions/dbt.yml --path models/ [--format json]

Exit code: 1 if any error-severity finding fires, 0 otherwise. Warnings never
fail the run.
"""
import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

DOMAIN_EXTENSIONS = {
    "dbt": (".sql", ".yml", ".yaml"),
    "lookml": (".lkml",),
    "cube": (".yml", ".yaml"),
}


class Finding:
    def __init__(self, rule_id, severity, file, message, line=None):
        self.rule_id = rule_id
        self.severity = severity
        self.file = file
        self.message = message
        self.line = line

    def to_dict(self):
        d = {"rule": self.rule_id, "severity": self.severity, "file": self.file, "message": self.message}
        if self.line is not None:
            d["line"] = self.line
        return d


def load_convention(path):
    with open(path) as fh:
        doc = yaml.safe_load(fh)
    for required in ("schema_version", "domain", "description"):
        if required not in doc:
            raise ValueError(f"{path}: convention file missing required field '{required}'")
    return doc


def get_rule(conv, section, rule_id):
    for rule in conv.get(section, []) or []:
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return rule
    return None


def iter_target_files(path, extensions):
    if os.path.isfile(path):
        yield path
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in sorted(files):
            if fname.endswith(extensions):
                yield os.path.join(root, fname)


def _severity(rule, default="warning"):
    return rule.get("severity", default)


# ----------------------------------------------------------------------
# Generic checks — driven entirely by the YAML, no domain-specific code
# ----------------------------------------------------------------------

def check_file_naming(conv, filepath, layer=None):
    """Matches file_naming rules against the file's inferred layer (a plain
    path-segment check, done once by the caller — see infer_dbt_layer /
    infer_lookml_layer) rather than the rule's `path_glob`. `path_glob` is
    kept in the YAML as human-readable documentation of where a rule
    applies, but isn't matched literally: fnmatch has no brace-expansion
    (`{staging,aggregate}`) and treats `**` the same as a single `*`, so a
    file sitting directly under staging/ with no entity-group subfolder (or
    any .lkml file at all, since every lookml glob uses brace syntax) would
    silently skip its check under a literal glob match."""
    findings = []
    basename = os.path.basename(filepath)
    for rule in conv.get("file_naming", []) or []:
        pattern = rule.get("pattern")
        if not pattern:
            continue
        rule_layer = rule.get("layer")
        if rule_layer is not None:
            allowed = rule_layer if isinstance(rule_layer, list) else [rule_layer]
            if layer not in allowed:
                continue
        if not re.search(pattern, basename):
            findings.append(Finding(
                rule["id"], _severity(rule, "error"), filepath,
                f"{rule.get('description', rule['id'])} — got '{basename}'",
            ))
    return findings


def check_file_content_rules(conv, filepath, text, layer=None):
    """Runs every rule (in any section) with scope: file_content. A rule may
    carry forbidden_pattern (flag every matching line) and/or required_pattern
    (flag if absent from the whole file). An optional `layer` field (string
    or list) restricts the rule to files inferred to be in that layer."""
    findings = []
    lines = text.splitlines()
    for section_name, rules in conv.items():
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("scope") != "file_content":
                continue
            rule_layer = rule.get("layer")
            if rule_layer is not None:
                allowed = rule_layer if isinstance(rule_layer, list) else [rule_layer]
                if layer not in allowed:
                    continue
            severity = _severity(rule)
            rid = rule["id"]
            desc = rule.get("description", rid)
            if "forbidden_pattern" in rule:
                pat = re.compile(rule["forbidden_pattern"], re.IGNORECASE)
                for i, line in enumerate(lines, start=1):
                    if pat.search(line):
                        findings.append(Finding(rid, severity, filepath, desc, line=i))
            if "required_pattern" in rule:
                pat = re.compile(rule["required_pattern"], re.IGNORECASE | re.MULTILINE)
                if not pat.search(text):
                    findings.append(Finding(rid, severity, filepath, f"{desc} — not found in file"))
    return findings


def check_style_thresholds(conv, filepath, text):
    """Handles style rules keyed by a threshold value (max_line_length via
    `value`, tab-forbidding via `forbid_tabs`) rather than a regex pattern."""
    findings = []
    lines = text.splitlines()
    for rule in conv.get("style", []) or []:
        rid = rule.get("id", "")
        severity = _severity(rule)
        desc = rule.get("description", rid)
        if "value" in rule and "length" in rid:
            limit = rule["value"]
            for i, line in enumerate(lines, start=1):
                if len(line) > limit:
                    findings.append(Finding(rid, severity, filepath, f"{desc} — line is {len(line)} chars", line=i))
        if rule.get("forbid_tabs"):
            for i, line in enumerate(lines, start=1):
                if "\t" in line:
                    findings.append(Finding(rid, severity, filepath, f"{desc} — tab character found", line=i))
    return findings


def extract_brace_block(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
    return text[open_idx:]


# ----------------------------------------------------------------------
# dbt
# ----------------------------------------------------------------------

def infer_dbt_layer(filepath):
    parts = filepath.replace(os.sep, "/").split("/")
    for layer in ("staging", "integration", "warehouse"):
        if layer in parts:
            return layer
    return None


ALIAS_RE = re.compile(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*$", re.IGNORECASE)
CAST_MACRO_ALIAS_RES = {
    "boolean_prefix": re.compile(r"type_boolean\(\)\s*\)\s*as\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "timestamp_suffix": re.compile(r"type_timestamp\(\)\s*\)\s*as\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "date_suffix": re.compile(r"type_date\(\)\s*\)\s*as\s+([A-Za-z_][A-Za-z0-9_]*)"),
}
RESERVED_ALIAS_WORDS = {"select", "from", "final", "where", "group", "order"}


def check_dbt_sql(conv, filepath, text):
    findings = []
    lines = text.splitlines()

    snake_rule = get_rule(conv, "naming", "snake_case")
    if snake_rule:
        pat = re.compile(snake_rule["pattern"])
        for i, line in enumerate(lines, start=1):
            m = ALIAS_RE.search(line.strip())
            if not m:
                continue
            alias = m.group(1)
            if alias.lower() in RESERVED_ALIAS_WORDS:
                continue
            if not pat.match(alias):
                findings.append(Finding(
                    snake_rule["id"], _severity(snake_rule), filepath,
                    f"{snake_rule.get('description')} — '{alias}'", line=i,
                ))

    for rule_id, cast_re in CAST_MACRO_ALIAS_RES.items():
        rule = get_rule(conv, "naming", rule_id)
        if not rule:
            continue
        pat = re.compile(rule["pattern"])
        for i, line in enumerate(lines, start=1):
            m = cast_re.search(line)
            if m and not pat.search(m.group(1)):
                findings.append(Finding(
                    rule["id"], _severity(rule), filepath,
                    f"{rule.get('description')} — '{m.group(1)}'", line=i,
                ))

    surrogate_rule = get_rule(conv, "naming", "surrogate_key_suffix")
    if surrogate_rule:
        pat = re.compile(surrogate_rule["pattern"])
        for i, line in enumerate(lines):
            if "generate_surrogate_key(" not in line:
                continue
            for j in range(i, min(i + 3, len(lines))):
                m = re.search(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)", lines[j])
                if m:
                    alias = m.group(1)
                    if not pat.search(alias):
                        findings.append(Finding(
                            surrogate_rule["id"], _severity(surrogate_rule, "error"), filepath,
                            f"{surrogate_rule.get('description')} — got '{alias}'", line=j + 1,
                        ))
                    break

    return findings


def check_dbt_layer_rules(conv, filepath, text):
    findings = []
    layer = infer_dbt_layer(filepath)
    if not layer:
        return findings
    layer_rule = (conv.get("layer_rules") or {}).get(layer)
    if not layer_rule:
        return findings
    may = layer_rule.get("may_select_from", [])
    if "source" not in may and re.search(r"\{\{\s*source\(", text):
        findings.append(Finding(
            f"layer_rules.{layer}", "error", filepath,
            f"{layer} models must not select from source() — only staging models do",
        ))
    return findings


def check_dbt_schema_yml(conv, filepath, text):
    findings = []
    try:
        doc = yaml.safe_load(text)
    except Exception:
        return findings
    if not isinstance(doc, dict):
        return findings

    pk_rule = get_rule(conv, "testing", "primary_key_tests_required")
    doc_rule = get_rule(conv, "documentation", "warehouse_columns_documented")
    is_warehouse = "warehouse" in filepath.replace(os.sep, "/").split("/")

    for model in doc.get("models") or []:
        if not isinstance(model, dict):
            continue
        for col in model.get("columns") or []:
            if not isinstance(col, dict):
                continue
            name = col.get("name", "")
            if pk_rule and name.endswith("_pk"):
                tests = col.get("tests") or col.get("data_tests") or []
                test_names = set()
                for t in tests:
                    if isinstance(t, str):
                        test_names.add(t)
                    elif isinstance(t, dict):
                        test_names.update(t.keys())
                missing = [t for t in pk_rule.get("required_tests", []) if t not in test_names]
                if missing:
                    findings.append(Finding(
                        pk_rule["id"], _severity(pk_rule, "error"), filepath,
                        f"primary key column '{name}' in model '{model.get('name')}' missing test(s): {missing}",
                    ))
            if doc_rule and is_warehouse and not (col.get("description") or "").strip():
                findings.append(Finding(
                    doc_rule["id"], _severity(doc_rule), filepath,
                    f"column '{name}' in warehouse model '{model.get('name')}' has no description",
                ))
    return findings


def check_dbt_file(conv, filepath, text):
    layer = infer_dbt_layer(filepath)
    if filepath.endswith((".yml", ".yaml")):
        return check_file_naming(conv, filepath, layer=layer) + check_dbt_schema_yml(conv, filepath, text)
    findings = []
    findings += check_file_naming(conv, filepath, layer=layer)
    findings += check_file_content_rules(conv, filepath, text, layer=layer)
    findings += check_style_thresholds(conv, filepath, text)
    findings += check_dbt_sql(conv, filepath, text)
    findings += check_dbt_layer_rules(conv, filepath, text)
    return findings


# ----------------------------------------------------------------------
# LookML
# ----------------------------------------------------------------------

def infer_lookml_layer(filepath):
    parts = filepath.replace(os.sep, "/").split("/")
    for layer in ("base", "staging", "aggregate", "int", "model"):
        if layer in parts:
            return layer
    return None


def check_lookml(conv, filepath, text):
    findings = []
    layer = infer_lookml_layer(filepath)
    findings += check_file_naming(conv, filepath, layer=layer)
    findings += check_file_content_rules(conv, filepath, text, layer=layer)
    findings += check_style_thresholds(conv, filepath, text)

    braces_rule = get_rule(conv, "style", "balanced_braces")
    if braces_rule:
        opens, closes = text.count("{"), text.count("}")
        if opens != closes:
            findings.append(Finding(
                braces_rule["id"], _severity(braces_rule, "error"), filepath,
                f"unbalanced braces: {opens} '{{' vs {closes} '}}'",
            ))

    view_rule = get_rule(conv, "naming", "warehouse_view_name")
    if view_rule and layer == "base":
        pat = re.compile(view_rule["pattern"])
        for m in re.finditer(r"view:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{", text):
            name = m.group(1)
            if not pat.match(name):
                findings.append(Finding(
                    view_rule["id"], _severity(view_rule, "error"), filepath,
                    f"{view_rule.get('description')} — got '{name}'",
                ))

    explore_rule = get_rule(conv, "required_fields", "explore_requires_label_and_description")
    if explore_rule:
        for m in re.finditer(r"explore:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{", text):
            block = extract_brace_block(text, m.end() - 1)
            for key in explore_rule.get("required_keys", []):
                if not re.search(rf"\b{key}\s*:", block):
                    findings.append(Finding(
                        explore_rule["id"], _severity(explore_rule, "error"), filepath,
                        f"explore '{m.group(1)}' missing required field '{key}'",
                    ))

    return findings


# ----------------------------------------------------------------------
# Cube
# ----------------------------------------------------------------------

def check_cube(conv, filepath, text):
    findings = []
    findings += check_file_naming(conv, filepath)
    findings += check_file_content_rules(conv, filepath, text)
    findings += check_style_thresholds(conv, filepath, text)

    try:
        doc = yaml.safe_load(text)
    except Exception as e:
        return findings + [Finding("yaml_parse_error", "error", filepath, f"could not parse YAML: {e}")]
    if not isinstance(doc, dict):
        return findings

    snake_rule = get_rule(conv, "naming", "snake_case_throughout")
    view_suffix_rule = get_rule(conv, "naming", "view_suffix")
    bool_prefix_rule = get_rule(conv, "naming", "boolean_dimension_prefix")
    cube_fields_rule = get_rule(conv, "required_fields", "cube_requires_core_fields")
    cube_pk_rule = get_rule(conv, "required_fields", "cube_requires_primary_key")
    dim_fields_rule = get_rule(conv, "required_fields", "dimension_requires_core_fields")
    measure_fields_rule = get_rule(conv, "required_fields", "measure_requires_core_fields")

    def check_snake_case(name, what):
        if snake_rule and name and not re.match(snake_rule["pattern"], name):
            findings.append(Finding(
                snake_rule["id"], _severity(snake_rule, "error"), filepath,
                f"{what} '{name}' is not snake_case",
            ))

    for cube in doc.get("cubes") or []:
        if not isinstance(cube, dict):
            continue
        name = cube.get("name", "<unnamed>")
        if cube_fields_rule:
            missing = [k for k in cube_fields_rule["required_keys"] if k not in cube]
            if missing:
                findings.append(Finding(
                    cube_fields_rule["id"], _severity(cube_fields_rule, "error"), filepath,
                    f"cube '{name}' missing required field(s): {missing}",
                ))
        check_snake_case(name if name != "<unnamed>" else None, "cube name")

        dims = cube.get("dimensions") or []
        if cube_pk_rule and not any(isinstance(d, dict) and d.get("primary_key") for d in dims):
            findings.append(Finding(
                cube_pk_rule["id"], _severity(cube_pk_rule, "error"), filepath,
                f"cube '{name}' has no dimension with primary_key: true",
            ))
        for dim in dims:
            if not isinstance(dim, dict):
                continue
            dname = dim.get("name", "<unnamed>")
            if dim_fields_rule:
                missing = [k for k in dim_fields_rule["required_keys"] if k not in dim]
                if missing:
                    findings.append(Finding(
                        dim_fields_rule["id"], _severity(dim_fields_rule, "error"), filepath,
                        f"dimension '{dname}' on cube '{name}' missing required field(s): {missing}",
                    ))
            check_snake_case(dname if dname != "<unnamed>" else None, f"dimension name (cube '{name}')")
            if bool_prefix_rule and dim.get("type") == "boolean" and dname != "<unnamed>" \
                    and not re.match(bool_prefix_rule["pattern"], dname):
                findings.append(Finding(
                    bool_prefix_rule["id"], _severity(bool_prefix_rule), filepath,
                    f"boolean dimension '{dname}' on cube '{name}' should read as a yes/no question",
                ))

        for meas in cube.get("measures") or []:
            if not isinstance(meas, dict):
                continue
            mname = meas.get("name", "<unnamed>")
            if measure_fields_rule:
                missing = [k for k in measure_fields_rule["required_keys"] if k not in meas]
                if missing:
                    findings.append(Finding(
                        measure_fields_rule["id"], _severity(measure_fields_rule, "error"), filepath,
                        f"measure '{mname}' on cube '{name}' missing required field(s): {missing}",
                    ))
            check_snake_case(mname if mname != "<unnamed>" else None, f"measure name (cube '{name}')")

    for view in doc.get("views") or []:
        if not isinstance(view, dict):
            continue
        vname = view.get("name", "<unnamed>")
        if view_suffix_rule and vname != "<unnamed>" and not re.search(view_suffix_rule["pattern"], vname):
            findings.append(Finding(
                view_suffix_rule["id"], _severity(view_suffix_rule, "error"), filepath,
                f"view name '{vname}' should end with _view",
            ))

    return findings


DISPATCH = {"dbt": check_dbt_file, "lookml": check_lookml, "cube": check_cube}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", required=True, choices=sorted(DOMAIN_EXTENSIONS))
    ap.add_argument("--convention", required=True, help="path to the domain's convention YAML")
    ap.add_argument("--path", required=True, help="file or directory to lint")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    try:
        conv = load_convention(args.convention)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    if conv.get("domain") != args.domain:
        print(f"ERROR: convention file domain '{conv.get('domain')}' does not match --domain {args.domain}", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(args.path):
        print(f"ERROR: --path '{args.path}' does not exist", file=sys.stderr)
        sys.exit(2)

    check_fn = DISPATCH[args.domain]
    extensions = DOMAIN_EXTENSIONS[args.domain]

    all_findings = []
    files_checked = 0
    for f in iter_target_files(args.path, extensions):
        files_checked += 1
        try:
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            all_findings.append(Finding("read_error", "error", f, str(e)))
            continue
        all_findings.extend(check_fn(conv, f, text))

    errors = [f for f in all_findings if f.severity == "error"]
    warnings = [f for f in all_findings if f.severity == "warning"]

    if args.format == "json":
        print(json.dumps({
            "domain": args.domain,
            "files_checked": files_checked,
            "errors": len(errors),
            "warnings": len(warnings),
            "findings": [f.to_dict() for f in all_findings],
        }, indent=2))
    else:
        for f in sorted(all_findings, key=lambda x: (x.file, x.line or 0)):
            loc = f"{f.file}:{f.line}" if f.line else f.file
            print(f"  {f.severity.upper():7} [{f.rule_id}] {loc} — {f.message}")
        print()
        print(f"{files_checked} file(s) checked — {len(errors)} error(s), {len(warnings)} warning(s)")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
