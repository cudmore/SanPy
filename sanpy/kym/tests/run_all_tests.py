"""
Test runner for colin-related modules.
"""

import sys
import os
import subprocess

def run_test_file(test_file):
    """Run a test file and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            print("✅ PASSED")
            print(result.stdout)
        else:
            print("❌ FAILED")
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ ERROR running {test_file}: {e}")
        return False

def main():
    """Run all colin-related tests."""
    test_files = [
        'test_colin_global.py',
        'test_colin_stats.py'
    ]
    
    print("Running all colin-related tests...")
    
    passed = 0
    total = len(test_files)
    
    for test_file in test_files:
        if run_test_file(test_file):
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"Test Summary: {passed}/{total} tests passed")
    print(f"{'='*60}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 