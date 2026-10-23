# Validation and remaining coverage

Test date: 2026-10-03. Device: Xiaomi Pad 5 (`nabu`), CSOT/Novatek NT36523,
crDroid 12, bundled v25 touch firmware. Pen: Dell PN7522W.

## Isolated original-driver device test

1. Decompress the kernel from the backed-up original installed boot image.
2. Locate its single exact original v25 firmware blob by full-byte matching.
3. Substitute the corrected same-size blob. Verify that exactly 25 uncompressed
   kernel bytes differ, all inside that blob, and all other bytes remain identical.
4. Repack a temporary boot image. Independently verify its decompressed kernel
   equals the prepared payload and its decompressed ramdisk equals the original.
   Boot header bytes remain identical except for compressed payload sizes.
5. Use `fastboot boot`, with no partition writes. The controller logged successful
   firmware loading and reported normal v25 dimensions. The original compiled
   kernel identity was preserved; that identity alone cannot prove the patch
   is running. The verified temporary image and native packet capture provide
   the evidence of the firmware effect.
6. Verify both SPI-workaround sysfs nodes are absent and `/proc/modules` is empty.
   The user confirmed normal operation before the capture.
7. Passively observe the SPI reads already performed by the driver, Linux input
   events, Android stylus events in a test app, and kernel logs over 60.2 seconds.
   No packet editing or additional internal-state SPI reads were performed.
8. Verify the installed boot partition hash still matches the original.

Recompressing the kernel/ramdisk changes compressed boot-image bytes; the
25-byte claim applies to the uncompressed kernel, not to its compressed container.
The controller firmware is downloaded by the original driver at boot. A normal
reboot returns to the installed kernel and its original embedded firmware.

## Capture result

| Observation | Result |
| --- | --- |
| Normal pen packets | 1891 |
| Native button byte `0 / 1 / 2 / 3` | `884 / 497 / 503 / 7` packets |
| Invalid normal-pen checksums | 0 |
| `BTN_STYLUS` down/up | 6 / 6 |
| `BTN_STYLUS2` down/up | 5 / 5 |
| Android states `0 / 32 / 64 / 96` | `101 / 52 / 47 / 1` events |
| Recorded first-contact native/Android matches | 9 / 9 |
| Extra two-byte internal-state SPI reads | 0 |
| Captured SPI transactions / lost events | 1939 / 0 |
| Detected controller/kernel faults during capture | 0 |

Timestamp comparison allows one millisecond for Android event-time quantization.
The nine stroke starts cover released and individually held button states;
they do not demonstrate every possible entry speed or pen history. Hover/contact
and fast-entry actions were user-controlled, with no instrumented physical timing.
The pre-capture user reply was "works"; a separate subjective post-capture rating
was not collected. Native, Linux and Android records establish button delivery.

Summarized evidence is in [native-test-summary.json](../evidence/native-test-summary.json).
Raw device logs and traces are omitted from the public repository.

## Additional offline check

An original-source kernel rebuild used the same pinned baseline and configuration.
A full source archive comparison checked 73336 tracked regular files plus symlinks;
only `firmware/novatek_nt36523_fw01.bin.ihex` changed. The driver sources were restored
to baseline, and the resulting image had no SPI fallback code. The corrected
firmware was present exactly once and 37 stock vendor-module symbol checks passed.
This separate rebuild was not booted; the actual device test used the exact
original compiled kernel, which isolates the firmware change more strictly.

## Additional user report: first-generation Xiaomi pen

On October 23, 2026, the user reported testing the original first-generation
Xiaomi pen: its side buttons work without a Bluetooth connection. No additional
instrumented packet capture accompanies that manual report. It does not establish
charging, suspend/resume, sustained use or Android 17 runtime coverage.
See [the separate user report](../evidence/xiaomi-first-generation-user-report.json).

## Required before release inclusion

- Broader Xiaomi pen behavior and other supported pens: writing, buttons and battery behavior.
- Finger touch, hover/contact, rapid entry, release away from the screen and palm interaction.
- Pen charging, repeated suspend/resume and longer use.
- Other supported panels, if maintainers determine this blob applies to them.
- Firmware selection: Generation 2 and game-mode paths are separate, unmodified blobs.

Application eraser behavior is separate from correct Android button delivery.
No claim of universal pen support, repaired palm rejection or broad regression
safety follows from this short Dell/CSOT/v25 test.
