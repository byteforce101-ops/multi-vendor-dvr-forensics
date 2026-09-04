from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.ai.pipeline.ai_service import (
    AIService,
)

from backend.ai.events.event_builder import (
    build_detection_events,
)

from backend.video.analysis.models import (
    Detection,
    VideoEvent,
)

from backend.video.analysis.motion import (
    detect_motion,
)

from backend.video.analysis.timestamps import (
    frame_to_absolute_timestamp,
)

from backend.video.extraction.frame_extractor import (
    FrameSample,
    iter_frames,
)

from backend.video.probe.video_probe import (
    VideoMetadata,
    probe_video,
)

from backend.video.timeline.service import (
    build_timeline,
)

from backend.video.reconstruction.models import (
    ForensicSummary,
    ReconstructedEvent,
)

from backend.video.reconstruction.reconstructor import (
    reconstruct_events,
)

from backend.video.reconstruction.summarizer import (
    build_forensic_summary,
)


from backend.video.reconstruction.opencv_reconstructor import (
    OpenCVForensicReconstructor,
)


@dataclass
class VideoAnalysisResult:

    video_id: str
    camera_id: str

    metadata: VideoMetadata

    events: list[VideoEvent]

    timeline: list

    frame_count_analyzed: int

    reconstructed_events: list[
        ReconstructedEvent
    ]

    forensic_summary: ForensicSummary


class VideoAnalysisService:

    def __init__(
        self,
        yolo_model: str = "yolo26n.pt",
        ai_confidence: float = 0.25,
        ai_iou: float = 0.50,
        device: str | None = None,
        enable_grounding_dino: bool = False,
        enable_enhancement: bool = True,
        enable_motion_rois: bool = True,
        detector_engine: str = "opencv",  # "opencv" | "hybrid" | "yolo"
    ):
        self.detector_engine = detector_engine
        self.opencv_reconstructor = OpenCVForensicReconstructor()

        self.ai = AIService(
            model_path=yolo_model,
            confidence=ai_confidence,
            iou=ai_iou,
            device=device,
            enable_grounding_dino=(
                enable_grounding_dino
            ),
            enable_enhancement=enable_enhancement,
            enable_motion_rois=enable_motion_rois,
            detector_engine=detector_engine,
        )

    def analyze(
        self,
        video_id: str,
        camera_id: str,
        video_path: str | Path,
        video_start_time: datetime,
        frame_sample_fps: float = 2.0,
    ) -> VideoAnalysisResult:

        # =====================================================
        # 1. VIDEO METADATA
        # =====================================================

        metadata = probe_video(
            video_path
        )

        # =====================================================
        # 2. FRAME EXTRACTION
        # =====================================================

        frames: list[FrameSample] = list(
            iter_frames(
                video_path,
                sample_fps=frame_sample_fps,
            )
        )

        # =====================================================
        # 3. MOTION
        # =====================================================

        motion_events = detect_motion(
            frames
        )

        # =====================================================
        # 4. AI
        # =====================================================

        ai_results = (
            self.ai.analyze_frames(
                frames
            )
        )

        # =====================================================
        # 5. AI → DETECTIONS
        # =====================================================

        detections: list[
            Detection
        ] = []

        for result in ai_results:

            absolute_timestamp = (
                frame_to_absolute_timestamp(
                    video_start_time,
                    result.timestamp_seconds,
                )
            )

            detections.append(
                Detection(
                    video_id=video_id,
                    camera_id=camera_id,

                    frame_number=(
                        result.frame_number
                    ),

                    timestamp=(
                        absolute_timestamp
                    ),

                    object_type=(
                        result.object_type
                    ),

                    confidence=(
                        result.confidence
                    ),

                    bbox=result.bbox,

                    track_id=(
                        result.track_id
                    ),

                    metadata={
                        "source": (
                            result.source
                        ),

                        "dino_confidence": (
                            result.dino_confidence
                        ),

                        "verified": (
                            result.verified
                        ),

                        "entity_id": (
                            result.entity_id
                        ),

                        "velocity": getattr(
                            result,
                            "velocity",
                            (0.0, 0.0),
                        ),

                        "attributes": getattr(
                            result,
                            "attributes",
                            {},
                        ),
                    },
                )
            )

        # =====================================================
        # 6. BUILD OBJECT EVENTS
        # =====================================================

        ai_events = (
            build_detection_events(
                detections
            )
        )

        # =====================================================
        # 7. MOTION EVENTS
        # =====================================================

        converted_motion_events: list[
            VideoEvent
        ] = []

        for motion in motion_events:

            start = (
                frame_to_absolute_timestamp(
                    video_start_time,
                    motion.start_seconds,
                )
            )

            end = (
                frame_to_absolute_timestamp(
                    video_start_time,
                    motion.end_seconds,
                )
            )

            converted_motion_events.append(
                VideoEvent(
                    video_id=video_id,
                    camera_id=camera_id,

                    event_type="MOTION",

                    start_time=start,
                    end_time=end,

                    confidence=(
                        motion.peak_score
                    ),

                    metadata={
                        "source": (
                            "opencv_motion"
                        ),
                    },
                )
            )

        # =====================================================
        # 8. COMBINE
        # =====================================================

        all_events = (
            converted_motion_events
            + ai_events
        )

        all_events.sort(
            key=lambda event:
            event.start_time
        )

        # =====================================================
        # 9. TIMELINE
        # =====================================================

        timeline = build_timeline(
            all_events
        )

        # =====================================================
        # 10. RECONSTRUCTION & FORENSIC SUMMARY
        # =====================================================

        if self.detector_engine == "opencv" and ai_results:
            reconstructed_events, forensic_summary = self.opencv_reconstructor.reconstruct_from_detections(
                [(r.timestamp_seconds, [r]) for r in ai_results],
                video_start_time=video_start_time,
                video_id=video_id,
                camera_id=camera_id,
            )
        else:
            reconstructed_events = (
                reconstruct_events(
                    all_events
                )
            )
            forensic_summary = (
                build_forensic_summary(
                    video_id=video_id,
                    camera_id=camera_id,
                    events=reconstructed_events,
                )
            )

        # =====================================================
        # 12. RESULT
        # =====================================================

        return VideoAnalysisResult(
            video_id=video_id,
            camera_id=camera_id,

            metadata=metadata,

            events=all_events,

            timeline=timeline,

            frame_count_analyzed=(
                len(frames)
            ),

            reconstructed_events=(
                reconstructed_events
            ),

            forensic_summary=(
                forensic_summary
            ),
        )