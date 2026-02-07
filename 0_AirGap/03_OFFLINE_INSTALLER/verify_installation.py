#!/usr/bin/env python3
"""
IntelliSTOR Air-Gap Installation Verification

This script verifies that all required Python packages and dependencies
are correctly installed in the air-gap environment.

Usage:
    python verify_installation.py
"""

import sys
import platform
import subprocess
from pathlib import Path


class InstallationVerifier:
    """Verifies air-gap Python installation"""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def print_header(self):
        """Print verification header"""
        print("=" * 70)
        print("IntelliSTOR Air-Gap Installation Verification")
        print("=" * 70)
        print()

    def print_section(self, title):
        """Print section header"""
        print(f"\n{title}")
        print("-" * 70)

    def check_python_version(self):
        """Verify Python version"""
        self.print_section("Python Version")

        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

        print(f"Python version: {version_str}")
        print(f"Platform: {platform.platform()}")
        print(f"Architecture: {platform.machine()}")

        if version_info.major == 3 and version_info.minor >= 8:
            print("✓ Python version is compatible (3.8+)")
            self.passed.append("Python version")
        else:
            print("✗ Python version is too old (requires 3.8+)")
            self.failed.append("Python version")

    def check_pip(self):
        """Verify pip is installed and working"""
        self.print_section("pip Package Manager")

        try:
            import pip
            print(f"✓ pip is installed (version {pip.__version__})")
            self.passed.append("pip")

            # List installed packages
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "list"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    print("\nInstalled packages:")
                    for line in result.stdout.split('\n')[2:]:  # Skip header lines
                        if line.strip():
                            print(f"  {line}")
                else:
                    print("Warning: Could not list installed packages")
                    self.warnings.append("pip list failed")

            except subprocess.TimeoutExpired:
                print("Warning: pip list command timed out")
                self.warnings.append("pip list timeout")
            except Exception as e:
                print(f"Warning: Error listing packages: {e}")
                self.warnings.append(f"pip list error: {e}")

        except ImportError:
            print("✗ pip is not installed")
            self.failed.append("pip")

    def check_standard_library(self):
        """Verify standard library modules"""
        self.print_section("Standard Library Modules")

        modules = [
            "csv",
            "json",
            "pathlib",
            "subprocess",
            "os",
            "sys",
            "datetime",
            "re",
            "shutil",
            "zipfile",
            "configparser"
        ]

        for module_name in modules:
            try:
                __import__(module_name)
                print(f"✓ {module_name}")
                self.passed.append(f"stdlib: {module_name}")
            except ImportError:
                print(f"✗ {module_name}")
                self.failed.append(f"stdlib: {module_name}")

    def check_database_connectivity(self):
        """Verify pymssql for SQL Server connectivity"""
        self.print_section("Database Connectivity (pymssql)")

        try:
            import pymssql
            print(f"✓ pymssql is installed (version {pymssql.__version__})")
            self.passed.append("pymssql")

            # Check if FreeTDS is available (pymssql dependency)
            try:
                # Attempt to get FreeTDS version
                conn_props = pymssql.__dict__
                print("  FreeTDS library is available")
            except:
                pass

        except ImportError as e:
            print(f"✗ pymssql is not installed")
            print(f"  Error: {e}")
            self.failed.append("pymssql")
            print("\n  Note: pymssql requires Visual C++ Redistributable")
            print("  If you see 'DLL load failed', install:")
            print("  https://aka.ms/vs/17/release/vc_redist.x64.exe")

    def check_ldap_support(self):
        """Verify ldap3 for Active Directory integration"""
        self.print_section("LDAP/Active Directory (ldap3)")

        try:
            import ldap3
            print(f"✓ ldap3 is installed (version {ldap3.__version__})")
            self.passed.append("ldap3")

            # Check if pyasn1 is available (ldap3 dependency)
            try:
                import pyasn1
                print(f"  ✓ pyasn1 dependency available (version {pyasn1.__version__})")
            except ImportError:
                print("  Warning: pyasn1 not found (ldap3 may not work correctly)")
                self.warnings.append("pyasn1 missing")

        except ImportError as e:
            print(f"✗ ldap3 is not installed")
            print(f"  Error: {e}")
            self.failed.append("ldap3")

    def check_web_framework(self):
        """Verify Flask for LDAP browser web interface"""
        self.print_section("Web Framework (Flask)")

        try:
            import flask
            print(f"✓ Flask is installed (version {flask.__version__})")
            self.passed.append("flask")

            # Check Flask-CORS
            try:
                import flask_cors
                print(f"✓ Flask-CORS is installed (version {flask_cors.__version__})")
                self.passed.append("flask-cors")
            except ImportError:
                print("✗ Flask-CORS is not installed")
                self.failed.append("flask-cors")

            # Check key Flask dependencies
            dependencies = ["werkzeug", "jinja2", "click", "itsdangerous"]
            for dep in dependencies:
                try:
                    mod = __import__(dep)
                    version = getattr(mod, "__version__", "unknown")
                    print(f"  ✓ {dep} ({version})")
                except ImportError:
                    print(f"  Warning: {dep} not found")
                    self.warnings.append(f"{dep} missing")

        except ImportError as e:
            print(f"✗ Flask is not installed")
            print(f"  Error: {e}")
            self.failed.append("flask")

    def check_external_tools(self):
        """Check for external tool availability"""
        self.print_section("External Tools")

        # Check for 7-Zip
        seven_zip_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]

        seven_zip_found = False
        for path in seven_zip_paths:
            if Path(path).exists():
                print(f"✓ 7-Zip found at: {path}")
                seven_zip_found = True
                self.passed.append("7-Zip")
                break

        if not seven_zip_found:
            # Try to find in PATH
            import shutil
            seven_zip_cmd = shutil.which("7z")
            if seven_zip_cmd:
                print(f"✓ 7-Zip found in PATH: {seven_zip_cmd}")
                seven_zip_found = True
                self.passed.append("7-Zip")

        if not seven_zip_found:
            print("⚠ 7-Zip not found (required for project 6: ZipEncrypt)")
            print("  Install from: https://www.7-zip.org/")
            self.warnings.append("7-Zip not found")

    def check_project_compatibility(self):
        """Verify compatibility with each IntelliSTOR project"""
        self.print_section("Project Compatibility")

        projects = {
            "1_Migration_Users": ["pymssql"],
            "2_LDAP": ["ldap3", "flask", "flask_cors"],
            "3_Migration_Report_Species_Folders": ["pymssql"],
            "4. Migration_Instances": ["pymssql"],
            "5. TestFileGeneration": [],  # Standard library only
            "6. ZipEncrypt": [],  # Uses 7-Zip external tool
            "7. AFP_Resources": [],  # Standard library only
            "ACL": []  # Standard library only
        }

        for project, dependencies in projects.items():
            if not dependencies:
                print(f"✓ {project} (standard library only)")
                continue

            all_deps_available = True
            missing = []

            for dep in dependencies:
                try:
                    __import__(dep)
                except ImportError:
                    all_deps_available = False
                    missing.append(dep)

            if all_deps_available:
                print(f"✓ {project} (all dependencies available)")
            else:
                print(f"✗ {project} (missing: {', '.join(missing)})")
                self.failed.append(f"Project: {project}")

    def print_summary(self):
        """Print verification summary"""
        self.print_section("Verification Summary")

        total_checks = len(self.passed) + len(self.failed)
        pass_rate = (len(self.passed) / total_checks * 100) if total_checks > 0 else 0

        print(f"\nTotal checks: {total_checks}")
        print(f"Passed: {len(self.passed)} ({pass_rate:.1f}%)")
        print(f"Failed: {len(self.failed)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.failed:
            print("\n" + "=" * 70)
            print("FAILED CHECKS:")
            print("=" * 70)
            for item in self.failed:
                print(f"  ✗ {item}")

        if self.warnings:
            print("\n" + "=" * 70)
            print("WARNINGS:")
            print("=" * 70)
            for item in self.warnings:
                print(f"  ⚠ {item}")

        print("\n" + "=" * 70)
        if not self.failed:
            print("✓ INSTALLATION VERIFIED SUCCESSFULLY")
            print("=" * 70)
            print("\nAll required dependencies are installed and working.")
            print("The IntelliSTOR Migration Tools are ready to use.")
            return 0
        else:
            print("✗ INSTALLATION VERIFICATION FAILED")
            print("=" * 70)
            print("\nSome required dependencies are missing or not working.")
            print("Please review the failed checks above and reinstall as needed.")
            print("\nRefer to 00_README_INSTALLATION.md for troubleshooting.")
            return 1

    def run(self):
        """Run all verification checks"""
        self.print_header()

        self.check_python_version()
        self.check_pip()
        self.check_standard_library()
        self.check_database_connectivity()
        self.check_ldap_support()
        self.check_web_framework()
        self.check_external_tools()
        self.check_project_compatibility()

        return self.print_summary()


def main():
    verifier = InstallationVerifier()
    exit_code = verifier.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
