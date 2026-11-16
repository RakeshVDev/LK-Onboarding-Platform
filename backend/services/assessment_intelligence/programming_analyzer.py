"""Offline Programming, Algorithm & Technical Engineering Analyzer.

Supports:
1. Safe static AST complexity analysis (cyclomatic complexity, max loop/recursion
   nesting depth, estimated Big-O class, forbidden-import/eval security gate).
2. Deterministic sandboxed Python unit test-case execution inside an isolated
   minimal Python subprocess with strict timeout & AST allowlist.
3. Sub-skill clustering for Technical / Programming MCQs so even single-bucket
   assessments yield rich multi-dimensional radar profiles.
"""

import ast
from collections import defaultdict
import json
import re
import subprocess
import sys
from typing import Any

from services.assessment_intelligence.config import (
    format_dimension_label,
    resolve_percentile_band,
)


FORBIDDEN_CALLS = frozenset({
    "eval", "exec", "compile", "open", "__import__", "getattr", "setattr",
    "delattr", "globals", "locals", "vars", "dir", "input", "breakpoint",
    "memoryview", "object",
})

FORBIDDEN_AST_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
)

TECH_TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("data_structures", ("fifo", "lifo", "stack", "queue", "tree", "graph", "heap", "hash", "linked list", "array")),
    ("algorithms", ("binary search", "sort", "time complexity", "o(log", "o(n", "recursion", "dynamic programming", "big-o", "algorithm")),
    ("databases_sql", ("sql", "select", "having", "primary key", "index", "acid", "join", "relational", "database")),
    ("backend_apis", ("http", "api", "fastapi", "status code", "router", "get", "post", "json", "rest")),
    ("language_fundamentals", ("oop", "python", "inheritance", "class", "equality", "java", "css", "javascript", "scope", "output")),
    ("git_devops", ("git", "clone", "commit", "unit test", "testing", "ci/cd", "docker")),
]


def _check_python_ast_safety(tree: ast.AST) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_AST_NODES):
            violations.append(f"Forbidden statement: {type(node).__name__}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                violations.append(f"Forbidden builtin call: {node.func.id}()")
            elif isinstance(node.func, ast.Attribute) and node.func.attr.startswith("__"):
                violations.append(f"Forbidden dunder attribute call: {node.func.attr}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.append(f"Forbidden dunder attribute access: {node.attr}")
    return sorted(set(violations))


def _max_loop_depth(node: ast.AST, current_depth: int = 0) -> int:
    is_loop = isinstance(node, (ast.For, ast.AsyncFor, ast.While))
    next_depth = current_depth + (1 if is_loop else 0)
    max_d = next_depth
    for child in ast.iter_child_nodes(node):
        max_d = max(max_d, _max_loop_depth(child, next_depth))
    return max_d


def _detect_recursion(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            fn_name = node.name
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == fn_name:
                    return True
    return False


def _cyclomatic_complexity(tree: ast.AST) -> int:
    branches = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.IfExp)):
            branches += 1
        elif isinstance(node, ast.BoolOp):
            branches += max(1, len(node.values) - 1)
    return branches


def _estimate_big_o(max_depth: int, has_recursion: bool, code_text: str) -> str:
    lower = code_text.lower()
    if max_depth == 0:
        if has_recursion:
            return "O(2^n) / Recursive" if lower.count("(") > 2 else "O(n) Recursive"
        if ".sort(" in lower or "sorted(" in lower:
            return "O(n log n)"
        return "O(1)"
    if max_depth == 1:
        if "//= 2" in lower or "/= 2" in lower or "mid =" in lower or ">>= 1" in lower:
            return "O(log n)"
        if ".sort(" in lower or "sorted(" in lower:
            return "O(n log n)"
        return "O(n)"
    if max_depth == 2:
        return "O(n^2)"
    return f"O(n^{max_depth})"


def _run_python_sandbox_tests(
    code_text: str,
    entry_point: str,
    cases: list[dict[str, Any]],
    timeout_sec: float = 2.0,
) -> dict[str, Any]:
    """Run candidate Python function against deterministic test cases in an isolated subprocess."""
    if not cases:
        return {"executed": False, "passed": 0, "total": 0, "details": []}

    runner_script = (
        "import json, sys\n"
        "payload = json.loads(sys.stdin.read())\n"
        "code = payload['code']\n"
        "entry = payload['entry_point']\n"
        "cases = payload['cases']\n"
        "safe_builtins = {\n"
        "  'len': len, 'range': range, 'enumerate': enumerate, 'zip': zip,\n"
        "  'map': map, 'filter': filter, 'sum': sum, 'min': min, 'max': max,\n"
        "  'abs': abs, 'sorted': sorted, 'reversed': reversed, 'int': int,\n"
        "  'float': float, 'str': str, 'bool': bool, 'list': list, 'dict': dict,\n"
        "  'set': set, 'tuple': tuple, 'all': all, 'any': any, 'round': round,\n"
        "  'divmod': divmod, 'pow': pow, 'isinstance': isinstance, 'ValueError': ValueError,\n"
        "  'IndexError': IndexError, 'KeyError': KeyError, 'TypeError': TypeError\n"
        "}\n"
        "ns = {'__builtins__': safe_builtins}\n"
        "exec(compile(code, '<candidate_submission>', 'exec'), ns, ns)\n"
        "fn = ns.get(entry)\n"
        "if not callable(fn):\n"
        "  print(json.dumps({'error': f'Function {entry} not found'}))\n"
        "  sys.exit(0)\n"
        "results = []\n"
        "passed = 0\n"
        "for idx, c in enumerate(cases):\n"
        "  try:\n"
        "    args = c.get('args', [])\n"
        "    out = fn(*args) if isinstance(args, list) else fn(args)\n"
        "    ok = (out == c.get('expected'))\n"
        "    if ok: passed += 1\n"
        "    results.append({'case': idx + 1, 'passed': ok, 'actual': repr(out)[:120]})\n"
        "  except Exception as exc:\n"
        "    results.append({'case': idx + 1, 'passed': False, 'error': str(exc)[:120]})\n"
        "print(json.dumps({'executed': True, 'passed': passed, 'total': len(cases), 'details': results}))\n"
    )
    payload_str = json.dumps({"code": code_text, "entry_point": entry_point, "cases": cases})
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", runner_script],
            input=payload_str,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        if proc.returncode != 0:
            err_msg = (proc.stderr or proc.stdout or "Execution error").strip()[:200]
            return {"executed": True, "passed": 0, "total": len(cases), "error": err_msg, "details": []}
        data = json.loads((proc.stdout or "{}").strip() or "{}")
        if data.get("error"):
            return {"executed": True, "passed": 0, "total": len(cases), "error": data["error"], "details": []}
        return data
    except subprocess.TimeoutExpired:
        return {"executed": True, "passed": 0, "total": len(cases), "error": "Time limit exceeded", "details": []}
    except Exception as exc:
        return {"executed": False, "passed": 0, "total": len(cases), "error": str(exc)[:160], "details": []}


def evaluate_code_submission(question: dict[str, Any], code_text: str) -> dict[str, Any]:
    """Evaluate a code submission via safe static AST/complexity heuristics + optional Python tests."""
    code = (code_text or "").strip()
    if not code:
        return {
            "normalized_score": 0.0,
            "language": "python",
            "syntax_valid": False,
            "security_violations": [],
            "cyclomatic_complexity": 0,
            "max_nesting_depth": 0,
            "estimated_big_o": "N/A",
            "test_results": {"executed": False, "passed": 0, "total": 0},
        }

    sk = question.get("scoring_key") or {}
    language = str(sk.get("language") or "python").strip().lower()
    test_cases = sk.get("test_cases") or []
    entry_point = str(sk.get("entry_point") or "solve")
    expected_big_o = str(sk.get("expected_big_o") or "")

    if language == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return {
                "normalized_score": 10.0,
                "language": "python",
                "syntax_valid": False,
                "syntax_error": f"Line {exc.lineno}: {exc.msg}",
                "security_violations": [],
                "cyclomatic_complexity": 0,
                "max_nesting_depth": 0,
                "estimated_big_o": "N/A",
                "test_results": {"executed": False, "passed": 0, "total": len(test_cases)},
            }

        violations = _check_python_ast_safety(tree)
        if violations:
            return {
                "normalized_score": 0.0,
                "language": "python",
                "syntax_valid": True,
                "security_violations": violations,
                "cyclomatic_complexity": 0,
                "max_nesting_depth": 0,
                "estimated_big_o": "Blocked (Unsafe Code)",
                "test_results": {"executed": False, "passed": 0, "total": len(test_cases), "error": "; ".join(violations)},
            }

        complexity = _cyclomatic_complexity(tree)
        max_depth = _max_loop_depth(tree)
        has_rec = _detect_recursion(tree)
        est_big_o = _estimate_big_o(max_depth, has_rec, code)
        fn_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        has_edge_guard = bool(re.search(r"\bif\s+(not\s+|\w+\s+is\s+None|len\()", code))

        test_res = {"executed": False, "passed": 0, "total": len(test_cases)}
        if test_cases:
            test_res = _run_python_sandbox_tests(code, entry_point, test_cases)

        if test_res.get("total", 0) > 0:
            test_score = (test_res["passed"] / test_res["total"]) * 100.0
        else:
            test_score = 75.0 if fn_count > 0 else 55.0

        quality_score = 100.0
        if complexity > 12:
            quality_score -= min(30.0, (complexity - 12) * 3.0)
        if fn_count == 0:
            quality_score -= 15.0
        if has_edge_guard:
            quality_score = min(100.0, quality_score + 5.0)

        complexity_fit = 85.0
        if expected_big_o and expected_big_o.lower() not in est_big_o.lower():
            if max_depth >= 2 and ("log n" in expected_big_o.lower() or "o(n)" == expected_big_o.lower()):
                complexity_fit = 55.0

        composite = round(0.65 * test_score + 0.20 * complexity_fit + 0.15 * quality_score, 2)
        return {
            "normalized_score": composite,
            "language": "python",
            "syntax_valid": True,
            "security_violations": [],
            "cyclomatic_complexity": complexity,
            "max_nesting_depth": max_depth,
            "estimated_big_o": est_big_o,
            "function_count": fn_count,
            "test_case_score": round(test_score, 2),
            "code_quality_score": round(quality_score, 2),
            "complexity_fit_score": round(complexity_fit, 2),
            "test_results": test_res,
        }

    # Generic static heuristics for non-Python code snippets (JS / Java / C# / SQL)
    brace_balance = code.count("{") == code.count("}")
    loop_count = len(re.findall(r"\b(for|while)\b", code))
    if_count = len(re.findall(r"\b(if|else\s+if|switch|case)\b", code))
    est_big_o = "O(n^2)" if loop_count >= 2 else ("O(n)" if loop_count == 1 else "O(1)")
    score = 72.0 if brace_balance and len(code.splitlines()) >= 3 else 45.0
    return {
        "normalized_score": score,
        "language": language,
        "syntax_valid": brace_balance,
        "security_violations": [],
        "cyclomatic_complexity": 1 + loop_count + if_count,
        "max_nesting_depth": min(3, loop_count),
        "estimated_big_o": est_big_o,
        "test_results": {"executed": False, "passed": 0, "total": len(test_cases)},
    }


def _classify_tech_question(question: dict[str, Any]) -> str:
    raw_cat = str(question.get("category") or "").strip().lower()
    if raw_cat and raw_cat not in {"technical_knowledge", "technical", "general"}:
        return raw_cat
    text = f"{question.get('question_text', '')} {question.get('instructions', '')}".lower()
    for dim_key, keywords in TECH_TOPIC_RULES:
        if any(kw in text for kw in keywords):
            return dim_key
    return "language_fundamentals"


def analyze_programming_session(
    questions: list[dict[str, Any]],
    question_results: list[dict[str, Any]],
    category_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """Produce engineering/programming intelligence across MCQs and code submissions."""
    q_by_id = {q["id"]: q for q in questions}
    code_evaluations: list[dict[str, Any]] = []
    sub_buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"score": 0.0, "max_score": 0.0, "count": 0.0})

    for qr in question_results:
        q = q_by_id.get(qr["question_id"], {})
        sub_detail = qr.get("sub_evaluation") or {}
        if qr.get("question_type") in {"code_submission", "algorithm_code", "programming_code"}:
            if not sub_detail and qr.get("answer"):
                sub_detail = evaluate_code_submission(q, str(qr["answer"]))
            if sub_detail:
                code_evaluations.append({"question_id": qr["question_id"], **sub_detail})

        dim_key = _classify_tech_question(q)
        sub_buckets[dim_key]["score"] += max(0.0, float(qr.get("points_awarded", 0.0) or 0.0))
        sub_buckets[dim_key]["max_score"] += max(0.0, float(qr.get("max_score", 1.0) or 1.0))
        sub_buckets[dim_key]["count"] += 1

    dimensions: list[dict[str, Any]] = []
    if code_evaluations and len(category_scores) <= 2:
        total_cases = sum(int((e.get("test_results") or {}).get("total", 0)) for e in code_evaluations)
        passed_cases = sum(int((e.get("test_results") or {}).get("passed", 0)) for e in code_evaluations)
        avg = lambda k, default=0.0: round(sum(float(e.get(k, default)) for e in code_evaluations) / len(code_evaluations), 2)
        test_acc = round((passed_cases / total_cases * 100.0) if total_cases > 0 else avg("test_case_score", 60.0), 2)
        for dim_key, val in [
            ("test_case_correctness", test_acc),
            ("time_complexity", avg("complexity_fit_score", 75.0)),
            ("code_quality", avg("code_quality_score", 75.0)),
            ("problem_solving", avg("normalized_score", 60.0)),
        ]:
            dimensions.append({
                "dimension_key": dim_key,
                "dimension_label": format_dimension_label(dim_key),
                "raw_score": val,
                "max_score": 100.0,
                "normalized_score": val,
                "percentile_band": resolve_percentile_band(val),
                "evidence": {"code_submissions": len(code_evaluations)},
            })
    elif len(category_scores) >= 3:
        for cs in category_scores:
            norm = float(cs.get("weighted_percentage", cs["percentage"]))
            dimensions.append({
                "dimension_key": cs["category"],
                "dimension_label": format_dimension_label(cs["category"]),
                "raw_score": float(cs["score"]),
                "max_score": float(cs["max_score"]),
                "normalized_score": round(norm, 2),
                "percentile_band": resolve_percentile_band(norm),
                "evidence": {"question_count": cs.get("question_count", 0)},
            })
    else:
        for dim_key, vals in sub_buckets.items():
            pct = (vals["score"] / vals["max_score"] * 100.0) if vals["max_score"] > 0 else 0.0
            dimensions.append({
                "dimension_key": dim_key,
                "dimension_label": format_dimension_label(dim_key),
                "raw_score": round(vals["score"], 2),
                "max_score": round(vals["max_score"], 2),
                "normalized_score": round(pct, 2),
                "percentile_band": resolve_percentile_band(pct),
                "evidence": {"question_count": int(vals["count"]), "inferred_from_mcq_text": True},
            })

    total_tests = sum(int((e.get("test_results") or {}).get("total", 0)) for e in code_evaluations)
    passed_tests = sum(int((e.get("test_results") or {}).get("passed", 0)) for e in code_evaluations)

    return {
        "summary": {
            "has_code_submissions": bool(code_evaluations),
            "code_submission_count": len(code_evaluations),
            "total_test_cases": total_tests,
            "passed_test_cases": passed_tests,
            "avg_cyclomatic_complexity": (
                round(sum(e.get("cyclomatic_complexity", 0) for e in code_evaluations) / len(code_evaluations), 2)
                if code_evaluations
                else None
            ),
            "estimated_complexities": [e.get("estimated_big_o") for e in code_evaluations],
            "security_flags": [
                v for e in code_evaluations for v in (e.get("security_violations") or [])
            ],
        },
        "code_evaluations": code_evaluations,
        "dimensions": dimensions,
    }

