# Brag Plan: TraceX DVR Forensics

## What is this app?
TraceX is an open-architecture digital video evidence acquisition, filesystem parsing, and forensic event reconstruction platform for surveillance disk dumps and video streams.

## The angle
Surveillance recordings from crime scenes and security incidents are frequently trapped in unindexed or proprietary DVR storage formats. TraceX parses proprietary filesystems directly from raw disk dumps (`.dd`, `.raw`), carves deleted video streams, and runs fast local ONNX neural tracking with zero external dependencies.

## Hook (first 2-3 seconds)
A raw physical disk dump (`evidence.dd`) inspected at sector level, showing proprietary header detection and automated container carving.

## Key moments (the middle)
- **Multi-Vendor Filesystem Decoders:** Automated sector-level parsing for Hikvision (HIKBT), Dahua (DHFS/DHAV), Xiongmai (XM), CP Plus, Godrej, Honeywell, and Matrix Comsec.
- **Deleted Frame & Stream Carving:** Header/footer stream recovery across unallocated sectors and corrupt container boundaries.
- **ONNX Deep Vision & Kinematics:** CPU neural inference (~35ms/frame) with multi-frame entity tracking, pixel velocity ($px/s$), and 8-point compass trajectory mapping.
- **Cryptographic Provenance:** Automated SHA-256 and MD5 evidence hashing with presentation timestamp (PTS/DTS) validation.

## Outro / punchline
"From raw unallocated sectors to structured forensic dossiers in seconds. TraceX."

## User flow worth showing
1. Ingest raw physical disk image (`.dd`)
2. Auto-decode proprietary DVR sectors and carve recoverable recordings
3. Run ONNX neural vision tracking and export structured forensic dossier

## Tone
- Preset: `polished`
- Creative direction: Technical digital forensics software overview
- Interpretation: Clean typography, forensic HUD telemetry, verified metric counters, and focused technical pacing with zero hype.

## Format: landscape — 1920x1080
## Duration: 20 seconds

## Visual identity (from the project)
- Background: `#0B1120` (Deep Space Navy)
- Card Surface: `#0F172A` / `#1E293B`
- Accent: `#0891B2` (Forensic Cyan) / `#38BDF8` (Sky Blue)
- Verification Badge: `#10B981` (Emerald)
- Text: `#F8FAFC` (White) / `#94A3B8` (Muted Slate)
- Display font: Plus Jakarta Sans / Space Grotesk
- Body font: JetBrains Mono / Inter

## Share copy (draft)
Built TraceX: Parse proprietary DVR filesystems, carve unindexed video streams, and run CPU ONNX neural vision tracking across raw surveillance disk dumps. Standalone .exe & portable .zip available.

## Audio direction
- Role: Restrained technical pulse with precise UI clicks
- Music: Clean electronic background track with steady rhythmic momentum
- Music treatment: Low baseline swell, building through neural detection reveal, resolving cleanly under the final logo lock
- SFX posture: Sparse, motion-matched digital clicks, sector verification chime, and subtle impact on logo lock
- Restraint rule: No sensationalized sirens, alarms, or cinematic explosions; preserve laboratory-grade technical focus.

## Storyboard

### Scene 1 — Ingestion: Raw Forensic Disk Dump — 3.5s
- **Visual:** Terminal telemetry grid displaying `evidence.dd` mounting in read-only mode. Sector scanner identifies proprietary partition structure.
- **Copy:** "Proprietary DVR Filesystems. Raw Disk Dumps. Unindexed Sectors."
- **Sequential/interaction:** Read-only mount verified (`SHA-256: C857803F...`), sector status flips to `PARSED`.
- **Audio intent:** Low baseline hum with subtle data clicks.
- **Transition mood:** Clean slide → Scene 2

### Scene 2 — Multi-Vendor Decoder Matrix — 4.5s
- **Visual:** Structured decoder badges: Hikvision (HIKBT), Dahua (DHFS/DHAV), Xiongmai (XM), CP Plus, Godrej, Honeywell, Matrix Comsec.
- **Copy:** "Multi-Vendor Filesystem Decoders. Deleted Video Stream Carving."
- **Sequential/interaction:** Vendor decoders lock into place with recovery counts (`Allocated & Unallocated Chunks Reassembled`).
- **Audio intent:** Crisp sequential card snaps and confirmation tone.
- **Transition mood:** Zoom transition → Scene 3

### Scene 3 — ONNX Neural Vision & Kinematics — 6.5s
- **Visual:** Surveillance stream playback with real-time bounding boxes and telemetry tags (`Track #04 | 42.8 px/s | Eastbound (→)`, `Track #09 | 86.4 px/s | Vehicle`).
- **Copy:** "ONNX Neural Inference (~35ms/frame). Pixel Velocity & Trajectory Vectors."
- **Sequential/interaction:** Entity bounding boxes track across frames; velocity badges update dynamically.
- **Audio intent:** Rhythmic pulse sync with tracking indicators.
- **Transition mood:** Smooth pull-back → Scene 4

### Scene 4 — Structured Forensic Dossier & Release — 5.5s
- **Visual:** Forensic report dossier summary generated with SHA-256 evidence integrity validation. TraceX logo locks into center with release tag `v1.0.1` and distribution badges: `Standalone .exe` & `Portable .zip`.
- **Copy:** "Structured Forensic Dossier Export. Standalone Executable & Portable ZIP."
- **Sequential/interaction:** Dossier summary card appears, release badges highlight, final logo settles.
- **Audio intent:** Clean bass tone with crisp decaying resonance.

**Music mood for this video:** Minimal technical electronic pulse  
**Audio summary:** Progresses from forensic ingestion analysis into high-throughput neural tracking, concluding on a clean, authoritative technical resolve.
