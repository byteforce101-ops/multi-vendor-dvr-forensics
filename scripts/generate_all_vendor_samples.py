"""scripts/generate_all_vendor_samples.py — Generate sample evidence files for all DVR parsers.

Takes an input video file (e.g. dashcam crash video) and packages it into valid evidence
containers / disk images for each of the 11 registered DVR parsers in TraceX:
  1. Hikvision (.dd)
  2. Dahua (.dav and .dd)
  3. Honeywell (.dd)
  4. Matrix SATATYA (.stm)
  5. TP-Link VIGI (.dav)
  6. Godrej (.bin)
  7. HeimVision (.dat)
  8. Uniview (.uvf)
  9. CP Plus (.dav)
 10. Forensic Disk Carver (.dd)
 11. Generic Video (.mp4)

Usage:
  python scripts/generate_all_vendor_samples.py "C:\\path\\to\\video.mp4" -o "C:\\path\\to\\output_dir"
"""

import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
        print(safe_msg)


def _u16(val: int) -> bytes:
    return struct.pack("<H", int(val))


def _u32(val: int) -> bytes:
    return struct.pack("<I", int(val))


def _u64(val: int) -> bytes:
    return struct.pack("<Q", int(val))


def _pack_dhav_date(dt: datetime) -> int:
    """Pack datetime into Dahua BCD-style uint32."""
    year = dt.year - 2000
    return (
        ((year & 0x3F) << 26)
        | ((dt.month & 0x0F) << 22)
        | ((dt.day & 0x1F) << 17)
        | ((dt.hour & 0x1F) << 12)
        | ((dt.minute & 0x3F) << 6)
        | (dt.second & 0x3F)
    )


def extract_video_streams(video_path: Path, temp_dir: Path) -> dict[str, Path]:
    """Transcode source video into required elementary and multiplexed streams."""
    log(f"[*] Ingesting video source: {video_path} ({video_path.stat().st_size:,} bytes)")
    
    ps_path = temp_dir / "stream.ps"
    h264_path = temp_dir / "stream.h264"
    hevc_path = temp_dir / "stream.hevc"
    
    # 1. MPEG-PS stream for Hikvision & Disk Carver
    log("  -> Generating MPEG-PS stream...")
    cmd_ps = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-c:v", "mpeg2video",
        "-b:v", "4M",
        "-f", "vob",
        str(ps_path),
    ]
    subprocess.run(cmd_ps, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    
    # 2. Raw H.264 Annex-B stream for Dahua, Honeywell, Matrix, Uniview, CP Plus, TP-Link, Godrej
    log("  -> Extracting raw H.264 Annex-B NAL stream...")
    cmd_h264 = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-c:v", "copy",
        "-bsf:v", "h264_mp4toannexb",
        "-f", "h264",
        str(h264_path),
    ]
    subprocess.run(cmd_h264, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    
    # 3. Clean Raw H.265/HEVC stream for HeimVision
    log("  -> Generating clean raw H.265/HEVC stream...")
    cmd_hevc = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-c:v", "libx265",
        "-x265-params", "no-info=1:log-level=none",
        "-crf", "23",
        "-f", "hevc",
        str(hevc_path),
    ]
    subprocess.run(cmd_hevc, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    
    return {
        "ps": ps_path,
        "h264": h264_path,
        "hevc": hevc_path,
    }


def create_dhav_stream(
    h264_data: bytes,
    channel: int = 0,
    start_time: datetime | None = None,
    brand_bytes: bytes | None = None,
) -> bytes:
    """Package H.264 Annex-B stream into fully FFmpeg-compliant Dahua DHAV frames."""
    if start_time is None:
        start_time = datetime(2024, 5, 12, 14, 23, 10, tzinfo=timezone.utc)
        
    pattern = re.compile(b'(?:\x00\x00\x00\x01|\x00\x00\x01)')
    matches = list(pattern.finditer(h264_data))
    
    dt = start_time
    date_val = _pack_dhav_date(dt)
    
    dhav_buf = bytearray()
    frame_no = 0
    
    for i in range(len(matches)):
        m = matches[i]
        start = m.start()
        end = matches[i+1].start() if i + 1 < len(matches) else len(h264_data)
        nal_payload = h264_data[start:end]
        nal_type = h264_data[m.end()] & 0x1F
        
        # In FFmpeg dhav.c: 0xfd is video stream
        ftype = 0xfd
        
        ext_bytes = bytearray()
        if i == 0 or nal_type == 5:
            # 0x80: 4 bytes (width 640 = 80*8, height 360 = 45*8)
            ext_bytes.extend(bytes([0x80, 0x00, 80, 45]))
            # 0x81: 4 bytes (codec 2 = H.264, fps 30)
            ext_bytes.extend(bytes([0x81, 0x00, 2, 30]))
            
        ext_len = len(ext_bytes)
        
        # In frame 0, embed brand inside SEI user data if provided
        if i == 0 and brand_bytes:
            sei_payload = b"\x00\x00\x00\x01\x06\x05" + bytes([len(brand_bytes)]) + brand_bytes + b"\x80"
            nal_payload = sei_payload + nal_payload
            
        total_len = len(nal_payload) + ext_len + 24 + 8
        ts_ms = (frame_no * 33) & 0xFFFF
        
        hdr = bytearray(24)
        hdr[0:4] = b"DHAV"
        hdr[4] = ftype
        hdr[5] = 0 # subtype
        hdr[6] = channel
        hdr[7] = 0 # frame_subnumber
        struct.pack_into("<I", hdr, 8, frame_no)
        struct.pack_into("<I", hdr, 12, total_len)
        struct.pack_into("<I", hdr, 16, date_val)
        struct.pack_into("<H", hdr, 20, ts_ms)
        hdr[22] = ext_len
        hdr[23] = 0 # checksum
        
        dhav_buf.extend(hdr)
        if ext_len > 0:
            dhav_buf.extend(ext_bytes)
        dhav_buf.extend(nal_payload)
        
        footer = b"dhav" + struct.pack("<I", total_len)
        dhav_buf.extend(footer)
        frame_no += 1
        
    return bytes(dhav_buf)


# ── VENDOR GENERATORS ──────────────────────────────────────────────────────────

def build_hikvision_dd(ps_data: bytes, out_path: Path, start_time: datetime) -> Path:
    """1. Hikvision DVR Raw Disk Image (.dd)"""
    SIGNATURE = b"HIKVISION@HANGZHOU"
    KNOWN_GOOD_VERSION = b"HIK.2011.03.08"
    HIKBTREE_SIGNATURE = b"HIKBTREE"
    
    ps_size = len(ps_data)
    HIKBTREE_OFFSET = 0x400000   # 4 MiB
    DATA_BLOCK_OFFSET = 0x500000 # 5 MiB
    DATA_BLOCK_SIZE = max(ps_size + 1024 * 1024, 32 * 1024 * 1024)
    start_ts = int(start_time.timestamp())
    end_ts = start_ts + 38
    
    total_size = DATA_BLOCK_OFFSET + ps_size + 4096
    image = bytearray(total_size)
    
    # Master block at 0x200
    master = bytearray(0x160)
    master[0x10:0x10 + len(SIGNATURE)] = SIGNATURE
    master[0x30:0x30 + len(KNOWN_GOOD_VERSION)] = KNOWN_GOOD_VERSION
    master[0x48:0x50] = _u64(500 * 1024 * 1024)
    master[0x88:0x90] = _u64(DATA_BLOCK_SIZE)
    master[0x90:0x94] = _u32(1)
    master[0x98:0xA0] = _u64(HIKBTREE_OFFSET)
    master[0xF0:0xF4] = _u32(start_ts - 3600)
    image[0x200:0x200 + len(master)] = master
    
    # HIKBTREE header at 0x400000
    hbtree_hdr = bytearray(0x60)
    hbtree_hdr[0x10:0x18] = HIKBTREE_SIGNATURE
    hbtree_hdr[0x58:0x60] = _u64(HIKBTREE_OFFSET + 0x60)
    image[HIKBTREE_OFFSET:HIKBTREE_OFFSET + len(hbtree_hdr)] = hbtree_hdr
    
    # HIKBTREE page at 0x400060
    page = bytearray(0x60 + 48)
    page[0x10:0x14] = _u32(1)
    page[0x20:0x28] = _u64(0xFFFFFFFFFFFFFFFF)
    off = 0x60
    page[off + 0x8:off + 0x10] = _u64(0)
    page[off + 0x11:off + 0x12] = bytes([1]) # Channel 1
    page[off + 0x18:off + 0x1C] = _u32(start_ts)
    page[off + 0x1C:off + 0x20] = _u32(end_ts)
    page[off + 0x20:off + 0x28] = _u64(DATA_BLOCK_OFFSET)
    image[HIKBTREE_OFFSET + 0x60:HIKBTREE_OFFSET + 0x60 + len(page)] = page
    
    # Data block
    image[DATA_BLOCK_OFFSET:DATA_BLOCK_OFFSET + ps_size] = ps_data
    
    out_path.write_bytes(image)
    return out_path


def build_dahua_dav(dhav_data: bytes, out_path: Path) -> Path:
    """2A. Dahua Video Stream (.dav)"""
    out_path.write_bytes(dhav_data)
    return out_path


def build_dahua_dd(dhav_data: bytes, out_path: Path) -> Path:
    """2B. Dahua DHFS4.1 Disk Image (.dd)"""
    image = bytearray(len(dhav_data) + 0x2000)
    image[0:7] = b"DHFS4.1"
    struct.pack_into("<I", image, 8, 1) # version
    image[0x1000:0x1000 + len(dhav_data)] = dhav_data
    out_path.write_bytes(image)
    return out_path


def build_honeywell_dd(h264_data: bytes, out_path: Path, start_time: datetime) -> Path:
    """3. Honeywell Performance Series Surveillance Disk Image (.dd)"""
    pattern = re.compile(b'(?:\x00\x00\x00\x01|\x00\x00\x01)')
    matches = list(pattern.finditer(h264_data))
    
    sps_payload = None
    pps_payload = None
    for i in range(len(matches)):
        m = matches[i]
        start = m.end()
        end = matches[i+1].start() if i + 1 < len(matches) else len(h264_data)
        nal_payload = h264_data[start:end]
        nal_type = nal_payload[0] & 0x1F
        if nal_type == 7 and sps_payload is None:
            sps_payload = nal_payload
        elif nal_type == 8 and pps_payload is None:
            pps_payload = nal_payload
            
    HON_NAL_MAGIC = b"\x80\x01\x00"
    body = bytearray(0x5000)
    brand_meta = b"Honeywell Performance Series NVR Model HEN-16104 SN:HON99281923"
    body[0x4400:0x4400 + len(brand_meta)] = brand_meta
    
    ts_us_base = int(start_time.timestamp() * 1_000_000)
    
    first_idr_written = False
    frame_idx = 0
    
    for i in range(len(matches)):
        m = matches[i]
        start = m.end()
        end = matches[i+1].start() if i + 1 < len(matches) else len(h264_data)
        nal_payload = h264_data[start:end]
        nal_type = nal_payload[0] & 0x1F
        ts_us = ts_us_base + int(frame_idx * 33333)
        
        if not first_idr_written:
            if nal_type == 5:
                hdr_sps = struct.pack("<4sHHIQ", bytes([0x82]) + HON_NAL_MAGIC, 640, 360, len(sps_payload), ts_us)
                body.extend(hdr_sps)
                body.extend(sps_payload)
                
                hdr_pps = struct.pack("<4sHHIQ", bytes([0x02]) + HON_NAL_MAGIC, 640, 360, len(pps_payload), ts_us)
                body.extend(hdr_pps)
                body.extend(pps_payload)
                
                hdr_idr = struct.pack("<4sHHIQ", bytes([0x02]) + HON_NAL_MAGIC, 640, 360, len(nal_payload), ts_us)
                body.extend(hdr_idr)
                body.extend(nal_payload)
                first_idr_written = True
                frame_idx += 1
            elif nal_type in (7, 8):
                continue
        else:
            if nal_type in (7, 8):
                continue
            hdr = struct.pack("<4sHHIQ", bytes([0x02]) + HON_NAL_MAGIC, 640, 360, len(nal_payload), ts_us)
            body.extend(hdr)
            body.extend(nal_payload)
            frame_idx += 1
            
    out_path.write_bytes(body)
    return out_path


def build_matrix_stm(h264_data: bytes, out_path: Path) -> Path:
    """4. Matrix Comsec SATATYA Media Container (.stm)"""
    brand_hdr = b"MATRIX COMSEC PVT. LTD. SATATYA NVR MEDIA STREAM v2.1\x00\x00"
    data = brand_hdr + h264_data
    out_path.write_bytes(data)
    return out_path


def build_tplink_dav(h264_data: bytes, out_path: Path, start_time: datetime) -> Path:
    """5. TP-Link VIGI NVR Video Stream (.dav)"""
    brand = b"TP-Link VIGI NVR1004H Security Video System"
    tplink_dhav = create_dhav_stream(h264_data, channel=0, start_time=start_time, brand_bytes=brand)
    out_path.write_bytes(tplink_dhav)
    return out_path


def build_godrej_bin(h264_data: bytes, out_path: Path) -> Path:
    """6. Godrej Security Solutions Xiongmai-line DVR Stream (.bin)"""
    brand = b"GODREJ SECURITY SOLUTIONS STE-NVR ACE Smart DVR System\x00\x00"
    data = bytearray(brand)
    
    XM_SYNC = b"\xaa\x55\xaa\x55"
    XM_IFRAME = b"\x00\x00\x01\xfd"
    
    data.extend(XM_SYNC)
    data.extend(XM_IFRAME)
    data.extend(h264_data)
    
    out_path.write_bytes(data)
    return out_path


def build_heimvision_dat(hevc_data: bytes, out_path: Path) -> Path:
    """7. HeimVision Raw HEVC Stream (.dat)"""
    out_path.write_bytes(hevc_data)
    return out_path


def build_uniview_uvf(h264_data: bytes, out_path: Path) -> Path:
    """8. Uniview UNV Ultra265 Video Export (.uvf)"""
    brand_hdr = b"UNIVIEW UNV Ultra265 NVR301 Video Export Stream\x00\x00"
    data = brand_hdr + h264_data
    out_path.write_bytes(data)
    return out_path


def build_cpplus_dav(h264_data: bytes, out_path: Path, start_time: datetime) -> Path:
    """9. CP Plus DVR/NVR Evidence (.dav)"""
    brand = b"CPPLUS CP-UVR Aditya Infotech Video Evidence"
    cpplus_dhav = create_dhav_stream(h264_data, channel=0, start_time=start_time, brand_bytes=brand)
    out_path.write_bytes(cpplus_dhav)
    return out_path


def build_carver_dd(ps_data: bytes, out_path: Path) -> Path:
    """10. Forensic Disk Carver Raw Unallocated Image (.dd)"""
    disk = bytearray(0x20000 + len(ps_data))
    disk[0x10000:0x10000 + len(ps_data)] = ps_data
    out_path.write_bytes(disk)
    return out_path


def build_generic_mp4(video_path: Path, out_path: Path) -> Path:
    """11. Generic Video File (.mp4)"""
    shutil.copy2(video_path, out_path)
    return out_path


def generate_all_samples(video_path: str | Path, output_dir: str | Path, prefix: str | None = None) -> dict[str, Path]:
    video_file = Path(video_path).expanduser().resolve()
    if not video_file.is_file():
        raise FileNotFoundError(f"Input video not found: {video_file}")
        
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if prefix is None:
        raw_stem = video_file.stem.lower()
        if "atm" in raw_stem or "shelbyville" in raw_stem:
            prefix = "atm_robbery"
        elif "dashcam" in raw_stem or "crash" in raw_stem:
            prefix = "dashcam"
        else:
            prefix = "surveillance"
            
    temp_dir = Path(tempfile.mkdtemp(prefix="tracex_gen_"))
    start_time = datetime(2024, 9, 14, 2, 37, 27, tzinfo=timezone.utc)
    generated_files: dict[str, Path] = {}
    
    try:
        # Transcode source video
        streams = extract_video_streams(video_file, temp_dir)
        ps_data = streams["ps"].read_bytes()
        h264_data = streams["h264"].read_bytes()
        hevc_data = streams["hevc"].read_bytes()
        dhav_data = create_dhav_stream(h264_data, channel=1, start_time=start_time)
        
        log(f"\n[*] Generating vendor-specific evidence packages in: {out_dir}")
        
        # 1. Hikvision
        f1 = build_hikvision_dd(ps_data, out_dir / f"hikvision_{prefix}.dd", start_time)
        generated_files["hikvision"] = f1
        log(f"  [+] 1. Hikvision:      {f1.name} ({f1.stat().st_size:,} bytes)")
        
        # 2. Dahua (.dav)
        f2a = build_dahua_dav(dhav_data, out_dir / f"dahua_{prefix}.dav")
        generated_files["dahua_dav"] = f2a
        log(f"  [+] 2a. Dahua (.dav):  {f2a.name} ({f2a.stat().st_size:,} bytes)")
        
        # 2b. Dahua (.dd)
        f2b = build_dahua_dd(dhav_data, out_dir / f"dahua_{prefix}.dd")
        generated_files["dahua_dd"] = f2b
        log(f"  [+] 2b. Dahua (.dd):   {f2b.name} ({f2b.stat().st_size:,} bytes)")
        
        # 3. Honeywell
        f3 = build_honeywell_dd(h264_data, out_dir / f"honeywell_{prefix}.dd", start_time)
        generated_files["honeywell"] = f3
        log(f"  [+] 3. Honeywell:      {f3.name} ({f3.stat().st_size:,} bytes)")
        
        # 4. Matrix
        f4 = build_matrix_stm(h264_data, out_dir / f"matrix_satatya_{prefix}.stm")
        generated_files["matrix"] = f4
        log(f"  [+] 4. Matrix:         {f4.name} ({f4.stat().st_size:,} bytes)")
        
        # 5. TP-Link VIGI
        f5 = build_tplink_dav(h264_data, out_dir / f"tplink_vigi_{prefix}.dav", start_time)
        generated_files["tplink_vigi"] = f5
        log(f"  [+] 5. TP-Link VIGI:   {f5.name} ({f5.stat().st_size:,} bytes)")
        
        # 6. Godrej
        f6 = build_godrej_bin(h264_data, out_dir / f"godrej_seethru_{prefix}.bin")
        generated_files["godrej"] = f6
        log(f"  [+] 6. Godrej:         {f6.name} ({f6.stat().st_size:,} bytes)")
        
        # 7. HeimVision
        f7 = build_heimvision_dat(hevc_data, out_dir / f"heimvision_{prefix}.dat")
        generated_files["heimvision"] = f7
        log(f"  [+] 7. HeimVision:     {f7.name} ({f7.stat().st_size:,} bytes)")
        
        # 8. Uniview
        f8 = build_uniview_uvf(h264_data, out_dir / f"uniview_{prefix}.uvf")
        generated_files["uniview"] = f8
        log(f"  [+] 8. Uniview:        {f8.name} ({f8.stat().st_size:,} bytes)")
        
        # 9. CP Plus
        f9 = build_cpplus_dav(h264_data, out_dir / f"cpplus_{prefix}.dav", start_time)
        generated_files["cpplus"] = f9
        log(f"  [+] 9. CP Plus:        {f9.name} ({f9.stat().st_size:,} bytes)")
        
        # 10. Forensic Carver
        f10 = build_carver_dd(ps_data, out_dir / f"carver_raw_disk_{prefix}.dd")
        generated_files["generic_dvr_carver"] = f10
        log(f"  [+] 10. Carver (.dd):  {f10.name} ({f10.stat().st_size:,} bytes)")
        
        # 11. Generic Video
        f11 = build_generic_mp4(video_file, out_dir / f"generic_{prefix}.mp4")
        generated_files["generic"] = f11
        log(f"  [+] 11. Generic:       {f11.name} ({f11.stat().st_size:,} bytes)")
        
        log(f"\n[OK] Generated {len(generated_files)} evidence files successfully in {out_dir}")
        return generated_files
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Generate sample evidence files for all DVR parsers.")
    parser.add_argument("input_video", help="Path to input video file (e.g. .mp4)")
    parser.add_argument("-o", "--output-dir", default="output/vendor_samples", help="Output directory")
    parser.add_argument("-p", "--prefix", default=None, help="Prefix for generated filenames")
    args = parser.parse_args()
    generate_all_samples(args.input_video, args.output_dir, prefix=args.prefix)


if __name__ == "__main__":
    main()
