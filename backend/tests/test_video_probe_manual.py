from pathlib import Path

from backend.video.probe.video_probe import probe_video


VIDEO_PATH = Path(
    r"E:\Downloads\WhatsApp Video 2026-08-27 at 9.39.49 PM.mp4"
)


def main():
    print()
    print("==============================")
    print("       VIDEO PROBE TEST")
    print("==============================")

    print()
    print("Video:")
    print(VIDEO_PATH)

    if not VIDEO_PATH.exists():
        print()
        print("ERROR: Video file does not exist!")
        return

    print()
    print("Video file exists")

    try:
        metadata = probe_video(VIDEO_PATH)

    except Exception as e:
        print()
        print("VIDEO PROBE FAILED")
        print("Error type:", type(e).__name__)
        print("Details:", e)
        return

    print()
    print("VIDEO PROBE SUCCESSFUL")

    print()
    print("Video Metadata")
    print("------------------------------")
    print("Path         :", metadata.path)
    print("Format       :", metadata.format_name)
    print("Duration     :", metadata.duration_seconds)
    print("Width        :", metadata.width)
    print("Height       :", metadata.height)
    print("FPS          :", metadata.fps)
    print("Frame Count  :", metadata.frame_count)
    print("Codec        :", metadata.codec)
    print("Pixel Format :", metadata.pixel_format)
    print("Start Time   :", metadata.start_time_seconds)
    print("Has Audio    :", metadata.has_audio)

    print()
    print("==============================")
    print("        TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()