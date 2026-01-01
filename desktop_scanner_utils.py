# desktop_scanner_utils.py

import tkinter.messagebox as messagebox
# Import the necessary components from the chafon_rfid library
try:
    from chafon_rfid.base import CommandRunner, ReaderCommand
    from chafon_rfid.command import G2_TAG_INVENTORY
    from chafon_rfid.response import G2_TAG_INVENTORY_STATUS_MORE_FRAMES
    from chafon_rfid.transport_serial import SerialTransport
    from chafon_rfid.uhfreader18 import G2InventoryResponseFrame as G2InventoryResponseFrameConcrete
    RFID_LIB_AVAILABLE = True
except ImportError:
    RFID_LIB_AVAILABLE = False
    print("WARNING: chafon_rfid library not found. Desktop RFID scanning will be simulated.")
    # Create dummy classes to prevent crashes if the library is missing
    class ReaderCommand: pass
    class G2_TAG_INVENTORY: pass
    class G2InventoryResponseFrameConcrete: pass
    class SerialTransport: pass
    class CommandRunner: pass
    G2_TAG_INVENTORY_STATUS_MORE_FRAMES = None

# --- Configuration Constant ---
# It's better to keep configuration in one place. You can add this to your config.py
# For now, we define it here.
#SERIAL_PORT = 'COM4'  # <<< IMPORTANT: Ensure this is your correct COM port
SERIAL_PORT = '/dev/ttyUSB0'

def scan_single_rfid_tag():
    """
    Scans for a single RFID tag using the Chafon desktop reader.
    Returns the tag EPC as a hex string, or None if an error occurs or no tag is found.
    """
    if not RFID_LIB_AVAILABLE:
        # Provide a simulated tag for testing if the library isn't installed
        print("SIMULATION: Returning a simulated desktop tag.")
        return "SIMULATED_TAG_12345"

    try:
        transport = SerialTransport(device=SERIAL_PORT, timeout=0.5)
        inventory_command_to_send = ReaderCommand(G2_TAG_INVENTORY)
        transport.write(inventory_command_to_send.serialize())
        
        inventory_status = None
        scanned_tag = None
        attempts = 0
        
        # Try a few times to get a response
        while (inventory_status is None or inventory_status == G2_TAG_INVENTORY_STATUS_MORE_FRAMES) and attempts < 5:
            attempts += 1
            try:
                frame_data = transport.read_frame()
                if not frame_data:
                    if scanned_tag: break
                    if inventory_status is None and attempts >= 1: break
                    continue
                
                g2_response = G2InventoryResponseFrameConcrete(frame_data)
                inventory_status = g2_response.result_status
                
                # We only need the first tag found
                for tag_object in g2_response.get_tag():
                    scanned_tag = tag_object.epc.hex()
                    break # Exit after finding the first tag
                
                if scanned_tag:
                    break
            except Exception:
                break # Exit on a frame processing error
        
        transport.close()
        return scanned_tag

    except Exception as e:
        error_type = type(e).__name__
        messagebox.showerror("RFID Scanner Error", 
                             f"Could not connect to or read from RFID reader on {SERIAL_PORT}.\n"
                             f"Error: {error_type}: {e}")
        return None