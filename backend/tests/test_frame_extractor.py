from pathlib import Path

import cv2

from backend.video.extraction.frame_extractor import iter_frames


VIDEO_PATH = Path(
    r"E:\Downloads\WhatsApp Video 2026-08-27 at 9.39.49 PM.mp4"
)

OUTPUT_DIR = Path("test_output/frames")


def main():

    print()
    print("==============================")
    print("   FRAME VISUAL TEST")
    print("==============================")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    count = 0

    for sample in iter_frames(
        VIDEO_PATH,
        sample_fps=2.0,
    ):

        filename = (
            OUTPUT_DIR
            / f"frame_{count:02d}_"
              f"{sample.timestamp_seconds:.3f}s.jpg"
        )

        cv2.imwrite(
            str(filename),
            sample.image,
        )

        print(
            f"Saved: {filename}"
        )

        count += 1

        if count >= 10:
            break

    print()
    print(f"Saved {count} frames.")
    print()
    print("Output folder:")
    print(OUTPUT_DIR)
    print()
    print("==============================")
    print("       TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()