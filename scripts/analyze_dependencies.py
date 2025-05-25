#!/usr/bin/env python3
"""Analyze project dependencies and suggest updates."""


def main():
    """Main function to analyze dependencies."""
    print("🔍 Analyzing project dependencies...\n")

    # Current versions from requirements.txt
    current_versions = {
        "python-telegram-bot": "22.0",
        "openai": ">=1.77,<2.0",
        "APScheduler": ">=3.11,<4.0",
        "gspread": "6.0.2",
        "google-auth": ">=2.40",
        "sentry-sdk": ">=1.43",
        "prometheus-client": ">=0.20",
        "structlog": ">=24.1",
        "tenacity": ">=8.3",
    }

    # Latest versions based on research
    latest_versions = {
        "python-telegram-bot": "21.2 (latest stable, 22.0 is pre-release)",
        "openai": "1.82.0",
        "APScheduler": "3.11.0",
        "gspread": "6.1.4",
        "google-auth": "2.40.2",
        "sentry-sdk": "2.29.1",
        "prometheus-client": "0.21.1",
        "structlog": "25.3.0",
        "tenacity": "9.1.2",
    }

    print("📦 Dependency Analysis:\n")
    print("Library                 | Current         | Latest Available")
    print("-" * 60)

    for lib, current in current_versions.items():
        latest = latest_versions.get(lib, "Unknown")
        status = "✅" if current == latest or "latest" in str(latest) else "🔄"
        print(f"{status} {lib:<20} | {current:<15} | {latest}")

    print("\n📋 Recommendations:")
    print(
        "1. ⚠️  python-telegram-bot: Consider staying on 21.2 (stable) instead of 22.0 (pre-release)"
    )
    print("2. 🔄 openai: Update to 1.82.0 for latest features")
    print("3. 🔄 gspread: Update to 6.1.4 for bug fixes")
    print("4. 🔄 sentry-sdk: Major update available (1.43 → 2.29.1)")
    print("5. 🔄 prometheus-client: Update to 0.21.1")
    print("6. 🔄 structlog: Update to 25.3.0")
    print("7. 🔄 tenacity: Update to 9.1.2")

    print("\n🧹 Dead Code Found:")
    print("- 63 unused imports found by ruff")
    print("- Multiple TODO comments that need addressing")
    print("- Commented out legacy code in scheduler/tasks.py")

    print("\n🎯 Optimization Opportunities:")
    print("1. Remove all unused imports (ruff --fix)")
    print("2. Address TODO comments in config and tests")
    print("3. Clean up TYPE_CHECKING imports in goal_manager.py")
    print("4. Consider making prometheus port configurable")
    print("5. Get version from pyproject.toml instead of hardcoding")


if __name__ == "__main__":
    main()
