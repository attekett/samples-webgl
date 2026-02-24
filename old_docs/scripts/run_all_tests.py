#!/usr/bin/env python3
"""
Script to run all WebGL test cases and analyze results for issues.
"""

import os
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Any

def find_html_test_files() -> List[str]:
    """Find all HTML test files in the testcases directory."""
    testcases_dir = Path("testcases")
    html_files = []
    
    for html_file in testcases_dir.rglob("*.html"):
        html_files.append(str(html_file))
    
    return sorted(html_files)

def run_single_test(test_file: str) -> Dict[str, Any]:
    """Run a single test file and return the results."""
    print(f"Running test: {test_file}")
    
    try:
        # Run the test
        result = subprocess.run([
            "./run_tests.sh",
            "--test-file", test_file,
            "--browsers", "chromium"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"  ❌ Test failed to run: {result.stderr}")
            return {"error": result.stderr}
        
        # Find the JSON output file
        json_file = test_file.replace('.html', '.json')
        if not os.path.exists(json_file):
            print(f"  ❌ JSON output not found: {json_file}")
            return {"error": "JSON output not found"}
        
        # Read and parse the JSON results
        with open(json_file, 'r') as f:
            test_results = json.load(f)
        
        return test_results
        
    except subprocess.TimeoutExpired:
        print(f"  ⏰ Test timed out: {test_file}")
        return {"error": "Test timed out"}
    except Exception as e:
        print(f"  ❌ Error running test: {e}")
        return {"error": str(e)}

def analyze_test_results(test_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze test results for issues."""
    analysis = {
        "passed": False,
        "errors": [],
        "warnings": [],
        "console_logs": [],
        "issues_found": []
    }
    
    if "error" in test_results:
        analysis["issues_found"].append(f"Test execution error: {test_results['error']}")
        return analysis
    
    if "results" not in test_results or not test_results["results"]:
        analysis["issues_found"].append("No results found in test output")
        return analysis
    
    result = test_results["results"][0]
    
    analysis["passed"] = result.get("passed", False)
    analysis["errors"] = result.get("errors", [])
    analysis["warnings"] = result.get("warnings", [])
    analysis["console_logs"] = result.get("console_logs", [])
    
    # Check for specific issues
    if not analysis["passed"]:
        analysis["issues_found"].append("Test failed")
    
    if analysis["errors"]:
        analysis["issues_found"].append(f"Found {len(analysis['errors'])} errors")
    
    if analysis["warnings"]:
        analysis["issues_found"].append(f"Found {len(analysis['warnings'])} warnings")
    
    # Check console logs for specific WGSL parsing error patterns
    for log in analysis["console_logs"]:
        message = log.get("message", "").lower()
        level = log.get("level", "")
        
        # Only flag actual WGSL parsing errors, not expected validation warnings
        if "error while parsing wgsl" in message:
            analysis["issues_found"].append(f"WGSL Parsing Error: {log.get('message', '')}")
        elif "unresolved value" in message or "unresolved type" in message:
            analysis["issues_found"].append(f"WGSL Error: {log.get('message', '')}")
        elif "expected" in message and ("error" in message or "syntax" in message):
            analysis["issues_found"].append(f"WGSL Syntax Error: {log.get('message', '')}")
        elif "cannot use" in message and "error" in message:
            analysis["issues_found"].append(f"WGSL Error: {log.get('message', '')}")
        elif "built-in cannot be used" in message:
            analysis["issues_found"].append(f"WGSL Error: {log.get('message', '')}")
        elif "storage requires" in message and "error" in message:
            analysis["issues_found"].append(f"WGSL Error: {log.get('message', '')}")
    
    return analysis

def main():
    """Main function to run all tests and analyze results."""
    print("🚀 WebGPU Test Runner - Batch Mode")
    print("=" * 50)
    
    # Find all HTML test files
    html_files = find_html_test_files()
    print(f"Found {len(html_files)} HTML test files")
    
    # Results tracking
    total_tests = len(html_files)
    passed_tests = 0
    failed_tests = 0
    tests_with_issues = []
    
    # Run all tests
    for i, html_file in enumerate(html_files, 1):
        print(f"\n[{i}/{len(html_files)}] Testing: {html_file}")
        
        # Run the test
        test_results = run_single_test(html_file)
        
        # Analyze results
        analysis = analyze_test_results(test_results)
        
        if analysis["passed"] and not analysis["issues_found"]:
            print(f"  ✅ PASS - No issues found")
            passed_tests += 1
        else:
            print(f"  ❌ FAIL - Issues found:")
            failed_tests += 1
            for issue in analysis["issues_found"]:
                print(f"    • {issue}")
            
            tests_with_issues.append({
                "file": html_file,
                "analysis": analysis
            })
        
        # Small delay between tests
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    if tests_with_issues:
        print(f"\n❌ Tests with issues ({len(tests_with_issues)}):")
        for test in tests_with_issues:
            print(f"  • {test['file']}")
            for issue in test['analysis']['issues_found']:
                print(f"    - {issue}")
    else:
        print("\n🎉 All tests passed with no issues!")
    
    # Save detailed results
    summary_file = "test_analysis_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests
            },
            "tests_with_issues": tests_with_issues
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {summary_file}")

if __name__ == "__main__":
    main()
