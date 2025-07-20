#!/usr/bin/env python3
"""
Test EPC conversion to understand the format differences
"""

def test_epc_conversion():
    """Test converting between different EPC formats"""
    
    # Your examples
    desktop_epc = "2022071511861a01101007fc"
    sllurp_epc = "323032323037313531313836316130313130313030376531"
    
    print("🔍 EPC FORMAT ANALYSIS")
    print("=" * 50)
    print(f"Desktop EPC: {desktop_epc}")
    print(f"Length: {len(desktop_epc)} chars")
    print(f"Sllurp EPC:  {sllurp_epc}")
    print(f"Length: {len(sllurp_epc)} chars")
    print()
    
    # Test if sllurp EPC is ASCII-encoded hex
    print("🧪 Testing ASCII-encoded hex theory:")
    try:
        # Convert sllurp hex string to bytes
        decoded_bytes = bytes.fromhex(sllurp_epc)
        print(f"Decoded bytes: {decoded_bytes}")
        
        # Try to decode as ASCII
        ascii_result = decoded_bytes.decode('ascii')
        print(f"ASCII decoded: {ascii_result}")
        
        # Compare with desktop version
        if ascii_result.lower() == desktop_epc.lower():
            print("✅ MATCH! Sllurp EPC is ASCII-encoded hex")
        else:
            print("❌ No match")
            
    except Exception as e:
        print(f"❌ ASCII decode failed: {e}")
    
    print()
    print("🔧 CONVERSION FUNCTIONS:")
    
    def normalize_epc_from_sllurp(epc_data):
        """Convert sllurp EPC to standard format"""
        if isinstance(epc_data, bytes):
            return epc_data.hex().lower()
        
        epc_str = str(epc_data).lower()
        
        # Check if this looks like ASCII-encoded hex
        if len(epc_str) > 24 and all(c in '0123456789abcdef' for c in epc_str):
            try:
                decoded_bytes = bytes.fromhex(epc_str)
                if all(32 <= b <= 126 for b in decoded_bytes):
                    return decoded_bytes.decode('ascii').lower()
            except:
                pass
        
        return epc_str
    
    # Test the conversion function
    test_cases = [
        desktop_epc,
        sllurp_epc,
        b'\x20\x22\x07\x15\x11\x86\x1a\x01\x10\x10\x07\xfc',  # Raw bytes
        "normalstring"
    ]
    
    for i, test_case in enumerate(test_cases):
        result = normalize_epc_from_sllurp(test_case)
        print(f"Test {i+1}: {test_case} -> {result}")

if __name__ == "__main__":
    test_epc_conversion()