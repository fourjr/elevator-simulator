def i2b(num: int) -> bytes:
    """Converts an integer to 4 bytes (big endian)"""
    return int(num).to_bytes(4, byteorder='big')


def b2i(data: bytes) -> int:
    """Converts 4 bytes to an integer (big endian)"""
    return int.from_bytes(data, byteorder='big')
