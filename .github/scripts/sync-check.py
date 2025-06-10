#!/usr/bin/env python3
"""
Documentation Synchronization Checker

Проверяет синхронизацию между русской (основной) и английской (эквивалентной) 
документацией согласно архитектуре мультиязычной системы.
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class DocumentationSyncValidator:
    """
    Automated validation для bilingual documentation consistency
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.languages = ["ru", "en"]
        self.critical_files = [
            "README.md",
            "CONTRIBUTING.md",
            "DEVELOPMENT_CHECKLIST.md",
            "docs/setup/installation.md",
            "docs/api/reference.md",
            "docs/user_guide.md",
            "docs/faq.md",
        ]
        self.sync_report: Dict[str, str] = {}

    def validate_language_parity(self) -> Dict[str, str]:
        """
        Check if English docs are up-to-date с Russian versions
        """
        print("🔍 Checking bilingual documentation synchronization...")

        for file_path in self.critical_files:
            ru_file = self.root_dir / file_path
            en_file = self._get_english_equivalent(file_path)

            if not ru_file.exists():
                self.sync_report[file_path] = "MISSING_RUSSIAN_VERSION"
                continue

            if not en_file.exists():
                self.sync_report[file_path] = "MISSING_ENGLISH_VERSION"
                continue

            ru_modified = os.path.getmtime(ru_file)
            en_modified = os.path.getmtime(en_file)

            # Check if Russian version is newer
            if ru_modified > en_modified + 60:  # 1 minute tolerance
                self.sync_report[file_path] = "ENGLISH_OUTDATED"
            else:
                self.sync_report[file_path] = "IN_SYNC"

        return self.sync_report

    def _get_english_equivalent(self, ru_file_path: str) -> Path:
        """Generate corresponding English file path"""
        file_path = Path(ru_file_path)

        if file_path.suffix == ".md":
            # For .md files, add _EN suffix before extension
            en_name = file_path.stem + "_EN" + file_path.suffix
            return self.root_dir / file_path.parent / en_name
        else:
            # For other files, add _EN suffix
            return self.root_dir / (str(file_path) + "_EN")

    def check_template_compliance(self) -> Dict[str, List[str]]:
        """
        Check if documentation follows template standards
        """
        print("📋 Checking template compliance...")

        compliance_report = {}
        template_requirements = [
            "---",  # YAML front matter
            "language:",
            "type:",
            "audience:",
            "last_updated:",
        ]

        for file_path in self.critical_files:
            issues = []

            ru_file = self.root_dir / file_path
            en_file = self._get_english_equivalent(file_path)

            # Check Russian file
            if ru_file.exists():
                ru_issues = self._check_file_template(
                    ru_file, template_requirements, "ru"
                )
                if ru_issues:
                    issues.extend([f"RU: {issue}" for issue in ru_issues])

            # Check English file
            if en_file.exists():
                en_issues = self._check_file_template(
                    en_file, template_requirements, "en"
                )
                if en_issues:
                    issues.extend([f"EN: {issue}" for issue in en_issues])

            if issues:
                compliance_report[file_path] = issues

        return compliance_report

    def _check_file_template(
        self, file_path: Path, requirements: List[str], language: str
    ) -> List[str]:
        """Check if file follows template requirements"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for YAML front matter
            if not content.startswith("---"):
                issues.append("Missing YAML front matter")
                return issues

            # Check for required fields
            for requirement in requirements:
                if requirement not in content[:500]:  # Check first 500 chars
                    issues.append(f"Missing {requirement}")

            # Check language field matches expected
            if f"language: {language}" not in content[:500]:
                issues.append(f"Incorrect language field (expected: {language})")

        except Exception as e:
            issues.append(f"Error reading file: {str(e)}")

        return issues

    def check_link_validity(self) -> Dict[str, List[str]]:
        """
        Check for broken links in documentation
        """
        print("🔗 Checking link validity...")

        link_report = {}

        for file_path in self.critical_files:
            broken_links = []

            # Check both language versions
            for lang_file in [
                self.root_dir / file_path,
                self._get_english_equivalent(file_path),
            ]:
                if lang_file.exists():
                    file_broken_links = self._check_file_links(lang_file)
                    if file_broken_links:
                        broken_links.extend(file_broken_links)

            if broken_links:
                link_report[file_path] = broken_links

        return link_report

    def _check_file_links(self, file_path: Path) -> List[str]:
        """Check links in a specific file"""
        import re

        broken_links = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find markdown links [text](url)
            link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
            links = re.findall(link_pattern, content)

            for link_text, url in links:
                if url.startswith(("http://", "https://")):
                    # Skip external links (would need network call)
                    continue
                elif url.startswith("#"):
                    # Skip anchor links (would need more complex validation)
                    continue
                else:
                    # Check local file links
                    link_path = (file_path.parent / url).resolve()
                    if not link_path.exists():
                        broken_links.append(f"Broken link: {url} (from {link_text})")

        except Exception as e:
            broken_links.append(f"Error checking links: {str(e)}")

        return broken_links

    def generate_summary_report(self) -> Dict:
        """Generate comprehensive summary report"""

        # Run all checks
        sync_results = self.validate_language_parity()
        template_results = self.check_template_compliance()
        link_results = self.check_link_validity()

        # Calculate statistics
        total_files = len(self.critical_files)
        in_sync_files = len(
            [f for f, status in sync_results.items() if status == "IN_SYNC"]
        )
        missing_en_files = len(
            [
                f
                for f, status in sync_results.items()
                if status == "MISSING_ENGLISH_VERSION"
            ]
        )
        outdated_en_files = len(
            [f for f, status in sync_results.items() if status == "ENGLISH_OUTDATED"]
        )

        sync_percentage = (in_sync_files / total_files) * 100 if total_files > 0 else 0

        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_files_checked": total_files,
                "files_in_sync": in_sync_files,
                "sync_percentage": round(sync_percentage, 1),
                "missing_english_files": missing_en_files,
                "outdated_english_files": outdated_en_files,
                "template_compliance_issues": len(template_results),
                "broken_links_found": sum(
                    len(links) for links in link_results.values()
                ),
            },
            "detailed_results": {
                "synchronization": sync_results,
                "template_compliance": template_results,
                "broken_links": link_results,
            },
            "recommendations": self._generate_recommendations(
                sync_results, template_results, link_results
            ),
        }

        return report

    def _generate_recommendations(
        self, sync_results: Dict, template_results: Dict, link_results: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Sync recommendations
        missing_files = [
            f
            for f, status in sync_results.items()
            if status == "MISSING_ENGLISH_VERSION"
        ]
        if missing_files:
            recommendations.append(
                f"📄 Create English versions for: {', '.join(missing_files)}"
            )

        outdated_files = [
            f for f, status in sync_results.items() if status == "ENGLISH_OUTDATED"
        ]
        if outdated_files:
            recommendations.append(
                f"🔄 Update English versions for: {', '.join(outdated_files)}"
            )

        # Template recommendations
        if template_results:
            recommendations.append(
                "📋 Fix template compliance issues in documentation files"
            )

        # Link recommendations
        if link_results:
            recommendations.append("🔗 Fix broken links in documentation")

        if not recommendations:
            recommendations.append(
                "✅ All documentation is properly synchronized and compliant!"
            )

        return recommendations


def main():
    """Main execution function"""
    print("🌐 Documentation Synchronization Checker")
    print("=" * 50)

    validator = DocumentationSyncValidator()
    report = validator.generate_summary_report()

    # Print summary
    summary = report["summary"]
    print("\n📊 SUMMARY:")
    print(f"   Total files checked: {summary['total_files_checked']}")
    print(f"   Files in sync: {summary['files_in_sync']}")
    print(f"   Sync percentage: {summary['sync_percentage']}%")
    print(f"   Missing English files: {summary['missing_english_files']}")
    print(f"   Outdated English files: {summary['outdated_english_files']}")
    print(f"   Template issues: {summary['template_compliance_issues']}")
    print(f"   Broken links: {summary['broken_links_found']}")

    # Print recommendations
    print("\n💡 RECOMMENDATIONS:")
    for rec in report["recommendations"]:
        print(f"   {rec}")

    # Save detailed report
    with open("doc-sync-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n📄 Detailed report saved to: doc-sync-report.json")

    # Exit with error code if issues found
    if (
        summary["sync_percentage"] < 100
        or summary["template_compliance_issues"] > 0
        or summary["broken_links_found"] > 0
    ):
        print("\n⚠️  Issues found - see report for details")
        sys.exit(1)
    else:
        print("\n✅ All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
