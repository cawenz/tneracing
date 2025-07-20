#!/usr/bin/env python3
"""
Detailed diagnosis of sllurp installation
"""

def check_sllurp_structure():
    """Check what's actually available in sllurp"""
    try:
        import sllurp
        print(f"✅ sllurp imported successfully")
        print(f"📍 sllurp location: {sllurp.__file__}")
        print(f"📦 sllurp version: {getattr(sllurp, 'sllurp_version', 'unknown')}")
        
        # Check what modules are available
        import pkgutil
        print("\n📂 Available sllurp modules:")
        for importer, modname, ispkg in pkgutil.iter_modules(sllurp.__path__):
            print(f"   {modname} {'(package)' if ispkg else '(module)'}")
        
        return True
    except Exception as e:
        print(f"❌ Error importing sllurp: {e}")
        return False

def test_llrp_imports():
    """Test different ways to import LLRP functionality"""
    print("\n🔍 Testing LLRP imports:")
    
    # Test 1: Direct llrp module
    try:
        from sllurp import llrp
        print("✅ from sllurp import llrp - SUCCESS")
        
        # Check what's in llrp
        llrp_attrs = [attr for attr in dir(llrp) if not attr.startswith('_')]
        print(f"   Available in llrp: {llrp_attrs[:10]}...")  # Show first 10
        
        # Look for key classes
        if hasattr(llrp, 'LLRPReaderClient'):
            print("✅ LLRPReaderClient found in llrp")
        if hasattr(llrp, 'LLRPReaderConfig'):
            print("✅ LLRPReaderConfig found in llrp")
        if hasattr(llrp, 'LLRPClientFactory'):
            print("✅ LLRPClientFactory found in llrp (old API)")
            
    except ImportError as e:
        print(f"❌ from sllurp import llrp - FAILED: {e}")
    
    # Test 2: Direct import from llrp
    try:
        from sllurp.llrp import LLRPReaderClient
        print("✅ from sllurp.llrp import LLRPReaderClient - SUCCESS")
    except ImportError as e:
        print(f"❌ from sllurp.llrp import LLRPReaderClient - FAILED: {e}")
    
    # Test 3: Direct import of config
    try:
        from sllurp.llrp import LLRPReaderConfig
        print("✅ from sllurp.llrp import LLRPReaderConfig - SUCCESS")
    except ImportError as e:
        print(f"❌ from sllurp.llrp import LLRPReaderConfig - FAILED: {e}")

def test_inventory_command():
    """Test if command line inventory is available"""
    print("\n🧪 Testing command line availability:")
    try:
        import subprocess
        result = subprocess.run(['sllurp', '--help'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ sllurp command line tool available")
        else:
            print("❌ sllurp command line tool not working")
    except FileNotFoundError:
        print("❌ sllurp command not found in PATH")
    except Exception as e:
        print(f"❌ Error testing sllurp command: {e}")

def suggest_fix():
    """Suggest the correct approach based on findings"""
    print("\n💡 SUGGESTED FIX:")
    print("Based on your installation, try this import in rfid_reader.py:")
    
    # Test what actually works
    try:
        from sllurp import llrp
        if hasattr(llrp, 'LLRPReaderClient'):
            print("✅ Use: from sllurp import llrp")
            print("✅ Then: client = llrp.LLRPReaderClient(...)")
            return "sllurp.llrp_direct"
    except:
        pass
    
    try:
        from sllurp.llrp import LLRPReaderClient
        print("✅ Use: from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig")
        return "sllurp.llrp_import"
    except:
        pass
    
    print("❌ No working import found. Try reinstalling:")
    print("   pip uninstall sllurp")
    print("   pip install git+https://github.com/sllurp/sllurp.git")
    return "reinstall_needed"

if __name__ == "__main__":
    print("🔍 SLLURP INSTALLATION DIAGNOSIS")
    print("=" * 50)
    
    if check_sllurp_structure():
        test_llrp_imports()
        test_inventory_command()
        suggest_fix()
    else:
        print("\n💡 sllurp is not installed properly.")
        print("   Try: pip install git+https://github.com/sllurp/sllurp.git")