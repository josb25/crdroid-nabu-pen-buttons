#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce the tested crDroid nabu v25 pen-button repair. No device access."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

INPUT_SHA256 = "d66d15f3dff35292e42e0d301bf53a7fcea6b6fc1b93bca90bb66d765bcfba9b"
OUTPUT_SHA256 = "851066943c2c0a77a53efb9b9892563c1c3f2a9ab24c8bb0bad5b561a53624d8"
OUTPUT_IHEX_SHA256 = "8f7f8c33910f6f3c08226531c753707667eadee8b073689001d10b12fec035aa"
SIZE = 196608
START = 0x15924
OLD = bytes.fromhex("84001003004c00010041")
NEW = bytes.fromhex("020100201003004c9208")
ALLOWED = ((0x18, 0x1c), (0xfc, 0x100), (0x118, 0x11c),
           (0x1fc, 0x200), (START, START + len(NEW)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def crc32_mpeg2(data):
    crc = 0xffffffff
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04c11db7 if crc & 0x80000000 else 0)) & 0xffffffff
    return crc


def decode_ihex(text):
    data = bytearray(SIZE)
    written = bytearray(SIZE)
    records = []
    base = 0
    eof = False
    for number, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        require(not eof and line.startswith(":"), f"Invalid record at line {number}")
        record = bytearray.fromhex(line[1:])
        require(len(record) >= 5 and len(record) == record[0] + 5,
                f"Invalid record length at line {number}")
        require(sum(record) % 256 == 0, f"Invalid record checksum at line {number}")
        count, relative, kind = record[0], int.from_bytes(record[1:3], "big"), record[3]
        absolute = None
        if kind == 0:
            absolute = base + relative
            require(relative + count <= 0x10000 and absolute + count <= SIZE,
                    f"Record outside firmware at line {number}")
            require(not any(written[absolute:absolute + count]), "Overlapping data records")
            data[absolute:absolute + count] = record[4:4 + count]
            written[absolute:absolute + count] = b"\x01" * count
        elif kind in (2, 4):
            require(count == 2 and relative == 0, "Invalid address record")
            base = int.from_bytes(record[4:6], "big") << (4 if kind == 2 else 16)
        elif kind == 1:
            require(count == 0 and relative == 0, "Invalid EOF record")
            eof = True
        else:
            raise ValueError(f"Unsupported record type {kind}")
        records.append((record, absolute))
    require(eof and all(written), "Firmware must contain EOF and all 196608 bytes")
    return bytes(data), records


def encode_ihex(records, data):
    lines = []
    for source, absolute in records:
        record = bytearray(source)
        if absolute is not None:
            record[4:4 + record[0]] = data[absolute:absolute + record[0]]
            record[-1] = (-sum(record[:-1])) & 0xff
        require(sum(record) % 256 == 0, "Generated record checksum failed")
        lines.append(":" + record.hex().upper())
    return ("\n".join(lines) + "\n").encode("ascii")


def verify_sections(data):
    headers = []
    require(data[0x20] & 2, "Expected cascade layout")
    for base in (0, 0x100):
        require(struct.unpack_from("<III", data, base) == (0x200, 0, 108583),
                "Unexpected ILM layout")
        header_crc, = struct.unpack_from("<I", data, base + 0xfc)
        require(crc32_mpeg2(data[base:base + 0xfc]) == header_crc, "Header CRC failed")
        section_crcs = []
        for index in range(2):
            offset, _, size = struct.unpack_from("<III", data, base + index * 12)
            require(offset + size + 1 <= len(data), "Section outside firmware")
            crc, = struct.unpack_from("<I", data, base + 0x18 + index * 4)
            require(crc32_mpeg2(data[offset:offset + size + 1]) == crc, "Section CRC failed")
            section_crcs.append(f"{crc:08x}")
        headers.append({"base": f"0x{base:x}", "ilm_crc": section_crcs[0],
                        "dlm_crc": section_crcs[1], "header_crc": f"{header_crc:08x}"})
    return headers


def patch(text):
    original, records = decode_ihex(text)
    require(sha256(original) == INPUT_SHA256, "Unsupported firmware SHA256; no patch applied")
    require(original[START:START + len(OLD)] == OLD, "Instruction window mismatch")
    original_headers = verify_sections(original)
    modified = bytearray(original)
    modified[START:START + len(NEW)] = NEW
    ilm_crc = crc32_mpeg2(modified[0x200:0x200 + 108584])
    for base in (0, 0x100):
        struct.pack_into("<I", modified, base + 0x18, ilm_crc)
        struct.pack_into("<I", modified, base + 0xfc,
                         crc32_mpeg2(modified[base:base + 0xfc]))
    modified_headers = verify_sections(modified)
    changes = [i for i, (a, b) in enumerate(zip(original, modified)) if a != b]
    require(len(modified) == len(original) == SIZE and len(changes) == 25,
            "Unexpected size or change count")
    require(all(any(low <= i < high for low, high in ALLOWED) for i in changes),
            "Changes outside instruction/CRC fields")
    require(sha256(modified) == OUTPUT_SHA256, "Patched binary hash mismatch")
    output = encode_ihex(records, modified)
    reconstructed, _ = decode_ihex(output.decode("ascii"))
    require(reconstructed == modified, "Generated Intel HEX payload differs")
    require(sha256(output) == OUTPUT_IHEX_SHA256, "Unexpected Intel HEX record layout")
    manifest = {"input_binary_sha256": INPUT_SHA256, "output_binary_sha256": OUTPUT_SHA256,
                "output_ihex_sha256": sha256(output), "firmware_bytes": SIZE,
                "changed_byte_offsets": changes, "instruction_file_offset": "0x15924",
                "old_instructions": OLD.hex(), "new_instructions": NEW.hex(),
                "original_headers": original_headers, "patched_headers": modified_headers,
                "all_section_and_header_crcs_valid": True,
                "intel_hex_checksums_and_payload_valid": True,
                "all_other_firmware_bytes_identical": True}
    return output, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Original crDroid v25 .ihex")
    parser.add_argument("--output", type=Path, required=True, help="Patched .ihex")
    parser.add_argument("--manifest", type=Path, help="Optional verification JSON")
    args = parser.parse_args()
    require(args.input.resolve() != args.output.resolve(), "Use a separate output file")
    if args.manifest:
        require(args.manifest.resolve() not in (args.input.resolve(), args.output.resolve()),
                "Manifest must be a separate file")
    output, manifest = patch(args.input.read_text(encoding="ascii"))
    args.output.write_bytes(output)
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Error: {error}") from error
