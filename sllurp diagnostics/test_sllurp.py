#!/usr/bin/env python3
"""
Test script for the newer sllurp (version 2.0+) which doesn't use Twisted
"""

def test_new_sllurp_import():
    """Test importing the newer sllurp"""
    try:
        from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient
        print("✅ Successfully imported newer sllurp (LLRPReaderClient)")
        return True
    except ImportError as e:
        print(f"❌ Failed to import new sllurp: {e}")
        return False

def test_ems_sllurp_import():
    """Test importing the EMS-TU-Ilmenau version"""
    try:
        from sllurp.reader import R420
        print("✅ Successfully imported EMS-TU-Ilmenau sllurp (R420)")
        return True
    except ImportError as e:
        print(f"❌ Failed to import EMS sllurp: {e}")
        return False

def test_twisted_removed():
    """Test that Twisted is not required"""
    try:
        import twisted
        print("⚠️  Twisted is still installed (optional, can be removed)")
    except ImportError:
        print("✅ Twisted is not installed")

def test_basic_sllurp():
    """Test basic sllurp functionality"""
    try:
        import sllurp
        print(f"✅ sllurp version available")
        
        # Check what's available in the module
        attrs = [attr for attr in dir(sllurp) if not attr.startswith('_')]
        print(f"✅ Available sllurp attributes: {attrs}")
        return True
    except Exception as e:
        print(f"❌ Error testing sllurp: {e}")
        return False

if __name__ == "__main__":
    print("Testing different sllurp installations...")
    print("-" * 50)
    
    # Test basic import first
    test_basic_sllurp()
    print()
    
    # Test newer API
    new_api = test_new_sllurp_import()
    print()
    
    # Test EMS API
    ems_api = test_ems_sllurp_import()
    print()
    
    test_twisted_removed()
    print("-" * 50)
    
    if new_api:
        print("✅ Newer sllurp API available - use LLRPReaderClient")
    elif ems_api:
        print("✅ EMS-TU-Ilmenau API available - use R420")
    else:
        print("❌ No compatible sllurp version found")
        print("Try: pip install git+https://github.com/sllurp/sllurp.git")