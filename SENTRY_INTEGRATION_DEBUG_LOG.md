# Sentry Integration Debugging Log - 2025-05-15

## Problem Description

Attempts to verify Sentry integration by causing an error in `main.py` (e.g., `1/0`) did not result in any errors appearing in the Sentry.io dashboard. 
Local execution of `main.py` (via `.\main.py` in PowerShell on Windows 11 Pro within Cursor IDE) showed problematic behavior: an external console window would flashเปิด and disappear Tregsinstantly, with no output visible in the integrated terminal or the flashing window, even when the script was reduced to a single `print()` statement followed by `input()`.

This behavior made it difficult to diagnose whether the Sentry SDK was initializing correctly, if the DSN was being loaded, or if events were being sent.

## Environment

- OS: Windows 11 Pro
- Shell: PowerShell (within Cursor IDE)
- Python virtual environment: `.venv` managed by `pip`.
- Sentry DSN: `https://f13550896217b924e2d13adac6c4e45a@o4509232102703104.ingest.us.sentry.io/4509326420803584` (stored in `.env`)

## Troubleshooting Steps Taken & Results

1.  **Initial Test**: Added `1/0` to `main.py`.
    *   Result: No error in Sentry. External window flashed and disappeared.

2.  **Added `python-dotenv`**: Ensured `load_dotenv()` was called at the start of `main.py`.
    *   Result: No change. No error in Sentry. Window flashed.

3.  **Explicit Sentry Capture**: Modified `main.py` to wrap `1/0` in `try...except` and explicitly call `sentry_sdk.capture_exception(e)`.
    *   Result: No change. No error in Sentry. Window flashed.

4.  **Sentry SDK Debug Mode**: Added `debug=True` to `sentry_sdk.init()` in `utils/sentry_integration.py`. Also added `print` statements in `setup_sentry()` and `main.py` to trace execution and DSN loading.
    *   Result: No console output visible from Sentry SDK debug or custom prints. Window flashed.

5.  **Minimal `main.py` (print + input)**: Reduced `main.py` to `print("TEST")` and `input("PAUSE")`.
    *   Result: "TEST" and "PAUSE" message appeared in a *new, separate* console window, which remained open due to `input()`. The integrated terminal remained empty.

6.  **Step-by-step uncommenting in `main.py` (output to separate window)**:
    *   `print` + `dotenv` + `print`: **Worked**. Output seen in separate window.
    *   `print` + `dotenv` + `os.getenv("SENTRY_DSN")` + `print`: **Worked**. DSN printed correctly.
    *   `print` + `dotenv` + `os` + `from utils.sentry_integration import setup_sentry` + call `setup_sentry()` (with its internal logic heavily commented out, leaving only prints): **Failed**. Window flashed and disappeared.
    *   Then, inside `utils/sentry_integration.py`, even with `setup_sentry()` containing only prints and Sentry-specific imports (`import sentry_sdk`, `from sentry_sdk.integrations.logging import LoggingIntegration`) commented out: **Failed**. Window flashed and disappeared when `main.py` tried to import `setup_sentry` from this modified file.

7.  **`python-dotenv` version check/reinstall**: Noticed `ggshield` dependency conflict (`requires python-dotenv~=0.21.0`, had `1.1.0`).
    *   Reinstalled `python-dotenv` to `1.1.0` (force): **No change** in flashing window behavior with minimal `main.py` (only `print` and `from dotenv import load_dotenv`).
    *   Installed `python-dotenv==0.21.1` (to match `ggshield`): **No change** in flashing window behavior with minimal `main.py` (only `print` and `from dotenv import load_dotenv`).

## Conclusion

The issue seems to be at a very low level, possibly related to:
- The environment in which Python scripts are executed by `.\script.py` in PowerShell on this specific Windows 11 Pro / Cursor IDE setup, causing output to go to a separate, unstable window.
- A fundamental problem with importing certain modules (potentially `dotenv` initially, or later, something triggered by the mere presence of `utils/sentry_integration.py` or its own basic imports like `os` or `logging` if the problem wasn't `dotenv` itself) that causes an immediate crash before any `print` statement in `main.py` can be effectively displayed in the new window or keep it open.

The fact that even a `print()` as the very first line of `main.py` followed by `from dotenv import load_dotenv` caused the new window to flash and disappear (before `dotenv` was version-matched to `ggshield`) points to a very early crash during the import phase of `dotenv` or an issue with the `print` to the separate window itself when an import follows.

Further local debugging is needed, focusing on the Python execution environment and basic module imports outside of the main application logic.

## Suggestion for Sentry Task

Postpone full Sentry alert setup (#17) until this local execution/Sentry communication issue is resolved. The created branch `feat/json-logging-sentry` contains preparatory work (JSON logging, Sentry context tagging) that can be used later. 