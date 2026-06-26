import os
import sys

def convert_slowrom_to_fastrom(rom_path):
    if not os.path.exists(rom_path):
        print(f"Error: File '{rom_path}' not found.")
        return

    with open(rom_path, 'rb') as f:
        rom_data = bytearray(f.read())

    # Determine if the ROM has an SMC/FIG copier header (usually 512 bytes)
    # A standard SNES ROM size is a multiple of 1024. If it has an extra 512 bytes, it's headered.
    header_offset = len(rom_data) % 1024
    if header_offset == 512:
        print("Detected a 512-byte copier header. Adjusting offsets...")
    elif header_offset != 0:
        print("Warning: Uncommon ROM size. Proceeding assuming no copier header.")
        header_offset = 0

    # Internal SNES Header Map offset for LoROM (unheadered: 0x7FC0 to 0x7FFF)
    # The Map Mode byte is located at 0x7FDB
    map_mode_index = header_offset + 0x7FDB

    if map_mode_index >= len(rom_data):
        print("Error: ROM is too small to contain a standard SNES header.")
        return

    current_mode = rom_data[map_mode_index]
    print(f"Current Map Mode byte: 0x{current_mode:02X}")

    # 0x20 = LoROM SlowROM -> Change to 0x30 (LoROM FastROM)
    if current_mode == 0x20:
        rom_data[map_mode_index] = 0x30
        print(" -> Updated Map Mode byte to 0x30 (FastROM).")
    elif current_mode == 0x30:
        print(" -> ROM is already marked as FastROM in the header. Scanning for code mirrors anyway...")
    else:
        print(f"Warning: Unexpected Map Mode (0x{current_mode:02X}). This script is tailored for standard LoROM (0x20). Proceeding with caution...")
        rom_data[map_mode_index] = current_mode | 0x10 # Force the FastROM bit

    # --- Bank Address Translation Layer ---
    # We look for 24-bit addressing (Long addressing) pointing to banks 00-7D 
    # and map them to their FastROM mirrors 80-FF.
    # Standard LoROM mirrors bank X to bank X + 0x80.
    
    print("Scanning ROM array for 3-byte address sequences to mirror to upper banks...")
    changes_made = 0
    
    # We skip the copier header if present during evaluation loop
    start_index = header_offset
    end_index = len(rom_data) - 3 # Need space for 3 bytes

    i = start_index
    while i < end_index:
        # Simple heuristic pattern matching for common SNES 65816 Assembly instructions:
        # JSL (Jump Subroutine Long) opcode is 0x22 -> followed by [Low Byte, High Byte, Bank Byte]
        # JMP (Jump Long) opcode is 0x5C -> followed by [Low Byte, High Byte, Bank Byte]
        if rom_data[i] in [0x22, 0x5C]:
            bank_byte = rom_data[i + 3]
            # Check if bank falls into the SlowROM tracking partition (0x00 to 0x6F / 0x7D)
            if 0x00 <= bank_byte <= 0x7D:
                rom_data[i + 3] = bank_byte + 0x80
                changes_made += 1
                i += 3 # skip past instructions args
        i += 1

    print(f"Scan complete. Remapped {changes_made} static bank pointers to FastROM space.")

    # Save modified file
    root, ext = os.path.splitext(rom_path)
    output_path = f"{root}_FastROM{ext}"
    
    with open(output_path, 'wb') as f:
        f.write(rom_data)
        
    print(f"Successfully generated FastROM hack: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fastrom_converter.py <path_to_snes_rom.sfc>")
    else:
        convert_slowrom_to_fastrom(sys.argv[1])