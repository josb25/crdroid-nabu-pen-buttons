# crDroid nabu pen side-button firmware fix

Experimental, reproducible firmware-only correction for Dell PN7522W side buttons
on Xiaomi Pad 5 (`nabu`) running crDroid 12. Tested on one CSOT/Novatek NT36523
tablet with the bundled **v25** firmware and the original compiled Linux driver.
The user also reports successful side-button operation with the original
first-generation Xiaomi pen without a Bluetooth connection; this additional
manual test has no instrumented capture.

The controller decodes both side buttons internally, but its normal pen-report
formatter writes zero to the button field. This repair copies the decoded state
into the existing field. The existing driver then reports `BTN_STYLUS` and
`BTN_STYLUS2`, which Android exposes as primary and secondary stylus buttons.

Only **nine instruction bytes and sixteen checksum bytes** change in the 196608-byte
firmware. No driver changes, extra SPI reads, settings toggle, Bluetooth mapping
or application changes are included. Apps still decide how to use Android's
stylus button events; this does not promise eraser support in every app.

This repository is focused on the crDroid change. It is an independent proposal,
not an official crDroid release or a universal fix for all pens/panels/firmware.

## Upstream target

- Repository: [crdroidandroid/android_kernel_xiaomi_sm8150](https://github.com/crdroidandroid/android_kernel_xiaomi_sm8150)
- Submission branch: `17.0`, as requested by the nabu maintainer
- Verified submission baseline: [`a17239b2eda3ccba274456d87aab4fd6f0bb734d`](https://github.com/crdroidandroid/android_kernel_xiaomi_sm8150/commit/a17239b2eda3ccba274456d87aab4fd6f0bb734d)
- Tested baseline: [`a07a230b6811f8e2d8c15a04e99eefd0d49c3b82`](https://github.com/crdroidandroid/android_kernel_xiaomi_sm8150/commit/a07a230b6811f8e2d8c15a04e99eefd0d49c3b82)
- Only upstream file changed: `firmware/novatek_nt36523_fw01.bin.ihex`
- Firmware provenance: [upstream v25 update from Xiaomi OS1.0.3.0.TKXCNXM](https://github.com/crdroidandroid/android_kernel_xiaomi_sm8150/commit/9681392465ddfd47ea8a4f2efbdf55f1bed0c387)

The firmware and complete NT36523 driver subtree on the verified `17.0` baseline
are identical to the tested `16.0` baseline. The patch applies cleanly and matches
the tested output hashes. Android 17 has not been built or booted for this submission.

[Download the patched binary, Intel HEX and reproducible package](https://github.com/josb25/crdroid-nabu-pen-buttons/releases/tag/nabu-v25-pen-buttons-17.0).

The Generation 2 and game-mode firmware blobs are separate and remain untouched.
Do not apply these offsets to a different firmware version. The generator refuses
a different input hash.

## Reproduce the firmware-only change

Python 3.9 or newer is sufficient; no third-party packages or device access.
Obtain the original `.ihex` from the pinned upstream tree linked above, then run:

```sh
mkdir -p out
python3 scripts/patch_firmware.py \
  --input /path/to/original/novatek_nt36523_fw01.bin.ihex \
  --output out/novatek_nt36523_fw01.bin.ihex \
  --manifest out/verification.json
```

The script validates every Intel HEX record, both cascade headers and all four
ILM/DLM section CRC entries before and after the repair. It preserves size and
record layout, independently decodes the generated output, and verifies exact
output hashes and the 25 changed-byte positions.

| Artifact | SHA256 |
| --- | --- |
| Original decoded v25 binary | `d66d15f3dff35292e42e0d301bf53a7fcea6b6fc1b93bca90bb66d765bcfba9b` |
| Patched decoded v25 binary | `851066943c2c0a77a53efb9b9892563c1c3f2a9ab24c8bb0bad5b561a53624d8` |
| Patched Intel HEX file, LF | `8f7f8c33910f6f3c08226531c753707667eadee8b073689001d10b12fec035aa` |

The generated Intel HEX is the only replacement required in the upstream tree.
Alternatively, from the pinned kernel checkout, apply the small prepared patch:

```sh
git apply --check /path/to/crdroid-nabu-pen-buttons/patches/0001-nabu-v25-report-pen-side-buttons.patch
git apply /path/to/crdroid-nabu-pen-buttons/patches/0001-nabu-v25-report-pen-side-buttons.patch
```

Build using crDroid's normal kernel/ROM process. This firmware is compiled into
the kernel: changing an unrelated file under Android's `/vendor/firmware` will
not select the corrected embedded blob in the tested path. No controller source
build or persistent touchscreen flashing utility is supplied here.

## What was verified

The strongest device test replaced the firmware blob inside the **original
installed compiled kernel**, then temporarily booted a repacked image. Exactly
25 uncompressed kernel bytes differed; every other kernel byte, including the
compiled driver, remained identical. The original decompressed Android ramdisk
was preserved. No partition was flashed, no SPI fallback code was present and
no diagnostic module was loaded.

Controller startup succeeded and the user confirmed normal operation. A 60.2-second
passive capture recorded:

- 1891 normal pen packets, all with valid checksums; native states `0/1/2/3`.
- Six balanced `BTN_STYLUS` press/release pairs and five `BTN_STYLUS2` pairs.
- Android primary, secondary and combined button states (`32/64/96`).
- Matching native/Android button state on all nine recorded stroke starts,
  within one millisecond timestamp precision.
- Zero internal-state SPI reads, lost capture events or detected controller/kernel faults.

A separate original-source rebuild was audited against 73336 tracked regular
files; this firmware file was the only changed tracked file. That rebuilt kernel
was prepared and verified offline, but was **not** the image used for the device test.

The instrumented tests cover one Dell/CSOT/v25 combination. The user's additional
first-generation Xiaomi pen report confirms side buttons without Bluetooth.
Regression coverage for other pens/panels, charging, suspend/resume and sustained
use is still needed before release inclusion. Physical approach
speed was not instrumented; the capture does not certify every fast-entry case.

Details: [repair analysis](docs/repair.md), [test report](docs/validation.md),
[summarized evidence](evidence/native-test-summary.json), and
[suggested upstream commit description](docs/upstream-commit-message.txt).

## Contents and licensing

This repository contains the small upstream patch, the standalone generator,
technical notes and summarized evidence. The linked release supplies the patched
controller firmware in decoded binary and Intel HEX form. No boot images, device
serials, Bluetooth identities or raw device logs are included.

The original generator code is [MIT-licensed](LICENSE). That license does not
relicense the vendor firmware, its patch context or the crDroid kernel. Their
upstream terms remain applicable. No public buildable controller firmware source
was found in the examined Xiaomi/crDroid trees; a supplier-built correction would
be preferable if the maintainer can obtain one.
