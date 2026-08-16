# Threat model

## Intended subjects

Subjects are fresh, non-adversarial coding agents attempting the task in isolated historical fixtures.
They may be incorrect, incomplete, over-broad, or accidentally violate the response protocol. The
instrument is designed to detect those ordinary failure modes and to distinguish the intended semantic
implementation from plausible projection/filter/fallback mistakes.

## Controls

- Every fixture is an independent Git repository without the withheld object.
- The grader requires the prepared fixture commit from the condition-free public manifest and verifies
  exact `HEAD`/tree identity before archive.
- Candidate changes are copied into external temporary sandboxes; the submitted fixture is not mutated.
- Scope is restricted to the two task-authorized paths and the diff remains available for review.
- Hidden semantic tests and the candidate-test runner live outside candidate fixtures and are checksummed
  in schema-v4 grade output.
- The runner creates/binds its loader, suite, result, and execution methods before candidate import.
- A preliminary AST policy rejects ordinary monkeypatch/introspection constructs aimed at `unittest`,
  runner result/suite/loader objects, `__main__`, `sys.modules`, or dynamic `exec`/`eval`.
- Qualification executes positive and negative reference/mutant controls, including live fabricated
  transcript and `unittest.TestResult`/`TestSuite.run` monkeypatch reproductions.

## Explicit non-goals

Candidate tests are arbitrary Python and are executed locally. This is **not a security sandbox**. The
instrument does not defend against a malicious candidate deliberately using arbitrary code execution,
filesystem/process access, obscure reflection, native extensions, resource exhaustion, or other means
to subvert its own grader. The AST checks are conservative defenses against ordinary/obvious tampering,
not a complete language-security policy. The runner is not claimed to be cryptographically tamper-proof.

Operational use therefore still relies on baseline/scope verification, isolated disposable fixtures,
reviewable diffs, bounded subprocess timeouts, and execution under the runner's normal host containment.
Do not run untrusted hostile submissions merely because this experiment has a structured test runner.

