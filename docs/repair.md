# Native report correction

Target: the exact CSOT NT36523 v25 blob bundled in the pinned crDroid kernel.
Its original decoded binary SHA256 is
`d66d15f3dff35292e42e0d301bf53a7fcea6b6fc1b93bca90bb66d765bcfba9b`.

## Root cause

In the examined v25 image, the pen object at RAM `0x2ec50` contains the decoded
two-bit side-button state at `+0x40` (`0x2ec90`). The adjacent byte at `+0x41`
holds battery identification. Earlier captures showed the Dell buttons changing
this internal state while the corresponding normal report field stayed zero.

The normal formatter, at RAM `0x15724` / firmware file offset `0x15924`, explicitly
stores zero at report `+0x4c`. The report buffer starts at `0x2d334`. The existing
host driver reads the corresponding `point_data[77]` bits 0 and 1 and maps them
to `BTN_STYLUS` and `BTN_STYLUS2`. No new input ABI is necessary.

## Same-length instruction replacement

Architecture: Andes NDS32; instruction encoding is big-endian and firmware data
is little-endian. GNU binutils 2.40 NDS32 disassembly was used to check the ten-byte
replacement. Each sequence occupies ten bytes, so following addresses stay fixed.

Original bytes: `84 00 10 03 00 4c 00 01 00 41`

```asm
movi55 r0, 0
sbi    r0, [r6+0x4c]
lbi    r0, [r2+0x41]
```

Replacement bytes: `02 01 00 20 10 03 00 4c 92 08`

```asm
lhi    r0, [r2+0x40]
sbi    r0, [r6+0x4c]
srli45 r0, 8
```

The halfword load fetches buttons in the low byte and battery identification in
the high byte. The byte store reports the buttons, then the shift leaves the
original battery value in `r0` for the unchanged following branches. The aligned
load does not change code length or the rest of the report layout. An arithmetic
model checked all 1024 combinations of two button bits and an eight-bit battery
value; this is not full firmware emulation or proof for other pen object paths.

The existing normal-report checksum calculation already includes offsets
`+0x41..+0x4d` and writes the negative byte sum at `+0x4e`. It automatically covers
the newly populated button field; its code is unchanged.

## Firmware integrity dependencies

The two 256-byte cascade headers point to the same ILM and DLM payloads. The ILM
starts at file `0x200`, RAM address zero, and its stored size is `108583`; the CRC
covers `size + 1` bytes. Use CRC-32/MPEG-2: polynomial `0x04c11db7`, initial
`0xffffffff`, no reflection and no final XOR. CRC values are stored little-endian.

| Field | File offset | Original | Patched |
| --- | --- | --- | --- |
| First ILM CRC | `0x18` | `c0f3ab59` | `c9ed43fe` |
| First header CRC | `0xfc` | `341a7081` | `a96528b0` |
| Second ILM CRC | `0x118` | `c0f3ab59` | `c9ed43fe` |
| Second header CRC | `0x1fc` | `166c0731` | `8b135f00` |

Each header CRC covers its preceding 252 header bytes. DLM and its CRC values
remain unchanged. Both headers, all four ILM/DLM CRC entries and Intel HEX
record checksums are validated by the generator. The final binary changes
exactly nine instruction bytes and sixteen CRC bytes, without resizing.

An initial development candidate updated only the first ILM CRC. It failed
controller startup because the other integrity dependencies were stale, and a
normal reboot restored touch with the original firmware. The final candidate
updates all four fields above and passed controller startup and native capture.

## Review boundaries

The exact tested input hash is mandatory. Separate firmware variants and alternate
pen/report paths have not been established as safe by this test. Original Xiaomi
pen regression, sleep/resume, charging and longer use remain outstanding.

This proposal does not include the earlier SPI workaround: the final test used
the original compiled driver, with no additional internal-state reads.

Pinned host-source references:

- [Native button decoding](https://github.com/crdroidandroid/android_kernel_xiaomi_sm8150/blob/a07a230b6811f8e2d8c15a04e99eefd0d49c3b82/drivers/input/touchscreen/xiaomi/nt36523/nt36xxx.c)
- [Embedded firmware loader and CRC handling](https://github.com/crdroidandroid/android_kernel_xiaomi_sm8150/blob/a07a230b6811f8e2d8c15a04e99eefd0d49c3b82/drivers/input/touchscreen/xiaomi/nt36523/nt36xxx_fw_update.c)
- [Original firmware file](https://github.com/crdroidandroid/android_kernel_xiaomi_sm8150/blob/a07a230b6811f8e2d8c15a04e99eefd0d49c3b82/firmware/novatek_nt36523_fw01.bin.ihex)
