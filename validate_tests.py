#!/usr/bin/env python3
"""
Validate test files for syntax errors and import issues.
"""

import sys
import importlib.util
from pathlib import Path

def validate_test_file(filepath: Path) -> tuple[bool, str]:
    """Validate a test file for syntax errors."""
    try:
        # First check syntax by compiling
        with open(filepath, 'r') as f:
            code = f.read()
        compile(code, str(filepath), 'exec')
        
        # Try to import (may fail due to missing pytest, which is OK)
        try:
            spec = importlib.util.spec_from_file_location("test_module", filepath)
            if spec is None or spec.loader is None:
                return False, "Could not create spec"
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True, "OK (imported successfully)"
        except ImportError as e:
            if 'pytest' in str(e):
                return True, "OK (syntax valid, pytest not installed)"
            return False, f"Import error: {e}"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Validate all test files."""
    test_dir = Path(__file__).parent / "tests"
    
    if not test_dir.exists():
        print("ERROR: Tests directory not found")
        return 1
    
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print("ERROR: No test files found")
        return 1
    
    print(f"Validating {len(test_files)} test files...\n")
    
    all_ok = True
    for test_file in sorted(test_files):
        ok, message = validate_test_file(test_file)
        status = "PASS" if ok else "FAIL"
        print(f"{status} {test_file.name}: {message}")
        if not ok:
            all_ok = False
    
    print()
    if all_ok:
        print("All test files validated successfully!")
        print("\nTo run tests, install pytest and run:")
        print("  pip install pytest pytest-mock")
        print("  pytest tests/ -v")
        return 0
    else:
        print("ERROR: Some test files have errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())

