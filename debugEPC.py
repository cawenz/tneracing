#!/usr/bin/env python3
"""
Debug EPC conversion with actual values from your system
"""

def test_epc_conversion_live():
    """Test with your actual EPC values"""
    
    # Your actual values
    impinj_epc = "323032323037313531313836316130313130313030376531"
    desktop_epc = "2022071511861a01101007e1"
    
    print("🔍 LIVE EPC CONVERSION TEST")
    print("=" * 60)
    print(f"Impinj EPC:  {impinj_epc}")
    print(f"Desktop EPC: {desktop_epc}")
    print(f"Length check: {len(impinj_epc)} == 48? {len(impinj_epc) == 48}")
    print(f"All hex chars? {all(c in '0123456789abcdef' for c in impinj_epc)}")
    print()
    
    # Test the exact conversion logic from your code
    def convert_epc_like_code(epc_str):
        """Exact same logic as in your rfid_reader.py"""
        epc_str = str(epc_str).lower()
        
        print(f"Input: {epc_str}")
        print(f"Length: {len(epc_str)}")
        
        if len(epc_str) == 48 and all(c in '0123456789abcdef' for c in epc_str):
            print("✅ Matches conversion criteria")
            try:
                decoded_bytes = bytes.fromhex(epc_str)
                print(f"Decoded bytes: {decoded_bytes}")
                tag_id = decoded_bytes.decode('ascii').lower()
                print(f"Final tag_id: {tag_id}")
                return tag_id
            except Exception as e:
                print(f"❌ Conversion failed: {e}")
                return epc_str
        else:
            print("❌ Does not match conversion criteria")
            return epc_str
    
    # Test conversion
    print("🧪 TESTING CONVERSION:")
    result = convert_epc_like_code(impinj_epc)
    print(f"Conversion result: {result}")
    print(f"Matches desktop EPC? {result == desktop_epc}")
    print()
    
    # Test what should be in ALLOWED_TAGS
    print("🎯 CHECKING ALLOWED_TAGS FORMAT:")
    print("Your ALLOWED_TAGS should contain:", repr(desktop_epc))
    print("Converted Impinj EPC:", repr(result))
    print("Match?", result == desktop_epc)
    print()
    
    # Show what the log should look like
    print("📝 EXPECTED LOG OUTPUT:")
    print(f"Converted ASCII-encoded hex: {impinj_epc} -> {result}")
    print(f"Read tag: {result} (converted), race_active: True, in allowed tags: {result == desktop_epc}")

if __name__ == "__main__":
    test_epc_conversion_live()