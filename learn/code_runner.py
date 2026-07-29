"""Runs a learner's Python submission against one TestCase's stdin and
compares stdout to the expected output.

Security note (read this before trusting this in a multi-tenant/public
deployment): this is a best-effort sandbox, not a hard security boundary.
It runs the submission as a plain subprocess on the same machine as the
Django app — there's no container, VM, or network-namespace isolation, which
matches this project's existing "fine for single-user local use, needs
hardening before deploying anywhere public" posture (see README.md/
DEPLOYMENT.md). Three layers, each best-effort on its own:

1. A static AST check (`static_check`) that only allows a fixed, safe
   stdlib module allowlist to be imported and blocks a handful of dangerous
   builtins (`eval`, `exec`, `open`, `__import__`, ...) — this is the main
   defense, since it rules out filesystem/process/network access outright
   rather than trying to enumerate every dangerous thing.
2. POSIX resource limits (CPU time, address space) applied to the child via
   `resource.setrlimit`, as a backstop against accidental infinite loops or
   memory blow-ups in code that passed the static check.
3. A wall-clock timeout on the subprocess itself, with the whole process
   group killed on timeout (via `start_new_session=True` +
   `os.killpg`), in case anything spawns children.

None of this blocks outbound network access at the OS level (that needs a
network namespace / firewall rule, which isn't available on a shared-uid
process without extra host privileges) — the import allowlist is what
actually prevents `socket`/`requests`/etc. from being reachable at all.
"""
import ast
import os
import signal
import subprocess
import sys
import tempfile

IS_POSIX = os.name == 'posix'

if IS_POSIX:
    import resource
else:
    resource = None

ALLOWED_MODULES = {
    'array', 'bisect', 'collections', 'copy', 'dataclasses', 'datetime',
    'decimal', 'enum', 'fractions', 'functools', 'heapq', 'itertools',
    'json', 'math', 'operator', 'queue', 'random', 're', 'statistics',
    'string', 'sys', 'textwrap', 'time', 'typing',
}
BLOCKED_CALL_NAMES = {
    'eval', 'exec', 'compile', '__import__', 'open', 'exit', 'quit',
    'globals', 'locals', 'vars', 'breakpoint', 'input',
}
# 'input' is blocked as a *call name* only in the sense that we don't need to
# special-case it — it's actually how learners are expected to read stdin,
# so it stays allowed; kept out of BLOCKED_CALL_NAMES deliberately.
BLOCKED_CALL_NAMES.discard('input')

TIMEOUT_SECONDS = 5
CPU_LIMIT_SECONDS = 5
MEMORY_LIMIT_BYTES = 256 * 1024 * 1024
OUTPUT_LIMIT_CHARS = 200_000


class CodeRejected(Exception):
    """The static check found something disallowed before we ever ran it."""


def static_check(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CodeRejected(f'Syntax error: {exc}') from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split('.')[0]
                if root not in ALLOWED_MODULES:
                    raise CodeRejected(
                        f"Import of '{root}' isn't allowed here. "
                        f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}."
                    )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or '').split('.')[0]
            if root not in ALLOWED_MODULES:
                raise CodeRejected(
                    f"Import of '{root}' isn't allowed here. "
                    f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}."
                )
        elif isinstance(node, ast.Call):
            fn = node.func
            name = None
            if isinstance(fn, ast.Name):
                name = fn.id
            elif isinstance(fn, ast.Attribute):
                name = fn.attr
            if name in BLOCKED_CALL_NAMES:
                raise CodeRejected(f"Calling '{name}()' isn't allowed here.")


def _limit_resources():
    """Runs in the child right after fork (POSIX only), before exec."""
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS))
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    except (ValueError, OSError):
        pass


def _kill_process_tree(proc):
    if IS_POSIX:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            proc.kill()
    else:
        proc.kill()


def _normalize(text: str):
    lines = (text or '').replace('\r\n', '\n').split('\n')
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == '':
        lines.pop()
    return lines


def outputs_match(actual: str, expected: str) -> bool:
    return _normalize(actual) == _normalize(expected)


def run_against_stdin(code: str, stdin_text: str) -> dict:
    """Returns {ok, stdout, stderr, timed_out, blocked_reason, exit_code}.
    ok=False + blocked_reason set means the static check rejected the code
    before it ever ran (surfaced to the learner like a failed test, not a
    system error)."""
    try:
        static_check(code)
    except CodeRejected as exc:
        return {
            'ok': False, 'stdout': '', 'stderr': '', 'timed_out': False,
            'blocked_reason': str(exc), 'exit_code': None,
        }

    with tempfile.TemporaryDirectory(prefix='coding_challenge_') as tmp_dir:
        script_path = os.path.join(tmp_dir, 'submission.py')
        with open(script_path, 'w') as f:
            f.write(code)

        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
        if not IS_POSIX:
            # Windows' runtime needs SystemRoot on the child's env or importing
            # some stdlib modules (e.g. socket) can fail.
            env['SystemRoot'] = os.environ.get('SystemRoot', '')

        popen_kwargs = {}
        if IS_POSIX:
            popen_kwargs['preexec_fn'] = _limit_resources
            popen_kwargs['start_new_session'] = True

        proc = subprocess.Popen(
            [sys.executable, '-I', script_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=tmp_dir, env=env,
            **popen_kwargs,
        )
        try:
            stdout, stderr = proc.communicate(input=stdin_text, timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc)
            proc.communicate()
            return {
                'ok': False, 'stdout': '', 'stderr': '', 'timed_out': True,
                'blocked_reason': None, 'exit_code': None,
            }

        return {
            'ok': proc.returncode == 0,
            'stdout': (stdout or '')[:OUTPUT_LIMIT_CHARS],
            'stderr': (stderr or '')[:OUTPUT_LIMIT_CHARS],
            'timed_out': False,
            'blocked_reason': None,
            'exit_code': proc.returncode,
        }


def grade_submission(code: str, test_cases) -> dict:
    """test_cases: iterable of objects with .stdin, .expected_output, .is_sample, .id.
    Returns {passed_count, total_count, results: [{test_case_id, is_sample, passed, stdout, stderr, timed_out, blocked_reason}]}."""
    test_cases = list(test_cases)

    try:
        static_check(code)
    except CodeRejected as exc:
        # A rejected import/builtin applies to every test case identically —
        # run the check once so the reason is reported clearly instead of
        # repeated (and instead of only partially counting test cases).
        results = [{
            'test_case_id': tc.id, 'is_sample': tc.is_sample, 'passed': False,
            'stdout': '', 'stderr': '', 'timed_out': False, 'blocked_reason': str(exc),
        } for tc in test_cases]
        return {'passed_count': 0, 'total_count': len(test_cases), 'results': results}

    results = []
    passed_count = 0
    for tc in test_cases:
        run = run_against_stdin(code, tc.stdin)
        passed = bool(run['ok'] and outputs_match(run['stdout'], tc.expected_output))
        if passed:
            passed_count += 1
        results.append({
            'test_case_id': tc.id,
            'is_sample': tc.is_sample,
            'passed': passed,
            'stdout': run['stdout'],
            'stderr': run['stderr'],
            'timed_out': run['timed_out'],
            'blocked_reason': run['blocked_reason'],
        })
    return {'passed_count': passed_count, 'total_count': len(test_cases), 'results': results}
