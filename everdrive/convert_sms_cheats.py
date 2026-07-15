def address_value_to_ar(address, value, system="md"):
    """
    Convert address + value into Action Replay style.

    Mega Drive:
      FF1234:09

    Master System / Game Gear:
      C123:09
    """
    address_hex = normalize_hex(address)
    value_hex = normalize_hex(value)

    if not address_hex or not value_hex:
        return None

    if len(value_hex) <= 2:
        value_hex = value_hex.zfill(2)
    elif len(value_hex) <= 4:
        value_hex = value_hex.zfill(4)
    else:
        return None

    try:
        # Master System / Game Gear: 16-bit Z80 address
        if system in ("sms", "gg"):
            if len(address_hex) > 4:
                address_hex = address_hex[-4:]

            address_hex = address_hex.zfill(4)
            address_int = int(address_hex, 16)

            if 0xC000 <= address_int <= 0xDFFF:
                return f"{address_hex}:{value_hex}"

            return None

        # Mega Drive: 24-bit 68000 address
        if len(address_hex) > 6:
            address_hex = address_hex[-6:]

        address_hex = address_hex.zfill(6)
        address_int = int(address_hex, 16)

        if 0xFF0000 <= address_int <= 0xFFFFFF:
            return f"{address_hex}:{value_hex}"

        return None

    except ValueError:
        return None