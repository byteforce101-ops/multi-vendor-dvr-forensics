import React, {
  useState,
  useEffect,
} from 'react';

import {
  X,
  Shield,
  Cpu,
  Activity,
  FileText,
  ArrowRight,
  Brain,
  ShieldAlert,
  EyeOff,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

import {
  EvidenceFile,
  VideoAnalysisResult,
} from '../types';

import {
  API_BASE,
  getAuthHeaders,
} from '../api/client';


interface ProcessingModalProps {

  isOpen: boolean;

  onClose: () => void;

  caseName: string;

  evidenceId: string;

  file: EvidenceFile | null;

  onCompleteStep: (
    stepId: number
  ) => void;

  onAnalysisComplete: (
    result: VideoAnalysisResult
  ) => void;
}


export const ProcessingModal: React.FC<
  ProcessingModalProps
> = ({
  isOpen,
  onClose,
  caseName,
  evidenceId,
  file,
  onCompleteStep,
  onAnalysisComplete,
}) => {

  const [
    progress,
    setProgress,
  ] = useState(0);

  const [
    currentPhase,
    setCurrentPhase,
  ] = useState(1);

  const [
    logs,
    setLogs,
  ] = useState<string[]>([]);

  const [
    isCompleted,
    setIsCompleted,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState('');

  const [
    analysisResult,
    setAnalysisResult,
  ] = useState<
    VideoAnalysisResult | null
  >(null);


  const fileName =
    file?.name ||
    'evidence.mp4';

  const fileHash =
    file?.hash ||
    '';


  useEffect(() => {

    if (!isOpen) {

      setProgress(0);

      setCurrentPhase(1);

      setLogs([]);

      setIsCompleted(false);

      setError('');

      setAnalysisResult(null);

      return;
    }


    const sourceFile =
      file?.sourceFile;


    if (!sourceFile) {

      setError(
        'Select a video file before starting the forensic pipeline.'
      );

      return;
    }


    const controller =
      new AbortController();

    let isActive = true;


    const runAnalysis =
      async () => {

        setError('');

        setProgress(10);

        setCurrentPhase(1);

        setLogs([
          `[INGEST] Uploading ${sourceFile.name} to the FastAPI analysis service.`,
          `[CRYPTO] Client-side preview seal: ${fileHash.substring(0, 32)}...`,
        ]);


        try {

          const formData =
            new FormData();

          formData.append(
            'file',
            sourceFile,
            sourceFile.name,
          );


          setProgress(25);

          setCurrentPhase(2);

          setLogs(
            (prev) => [
              ...prev,
              '[FFPROBE] Backend is inspecting the video container and metadata.',
            ]
          );


          const headers =
            await getAuthHeaders();


          const response =
            await fetch(
              `${API_BASE}/video/analyze`,
              {
                method: 'POST',
                headers,
                body: formData,
                signal: controller.signal,
              }
            );


          if (!response.ok) {

            let detail =
              `Backend analysis failed (${response.status}).`;

            try {

              const body =
                await response.json();

              if (
                typeof body.detail ===
                'string'
              ) {

                detail =
                  body.detail;
              }

            } catch {
              // Keep HTTP status message.
            }

            throw new Error(
              detail
            );
          }


          const result =
            (
              await response.json()
            ) as VideoAnalysisResult;


          if (!isActive) {
            return;
          }


          setAnalysisResult(
            result
          );


          setProgress(60);

          setCurrentPhase(3);

          setLogs(
            (prev) => [
              ...prev,

              `[AI_INFERENCE] ${result.frames_analyzed} frames analyzed by the backend pipeline.`,

              `[DETECTION] ${result.event_count} low-level forensic events detected.`,

              `[RECONSTRUCTION] ${result.reconstruction_count} higher-level forensic activities reconstructed.`,

              `[SUMMARY] ${result.forensic_summary.headline}`,
            ]
          );


          onAnalysisComplete(
            result
          );


          setProgress(100);

          setCurrentPhase(4);

          setIsCompleted(true);


          setLogs(
            (prev) => [
              ...prev,
              '[READY] AI forensic reconstruction and summary are ready for review.',
            ]
          );


          onCompleteStep(8);

        } catch (caught) {

          if (
            !isActive ||
            (
              caught instanceof DOMException &&
              caught.name === 'AbortError'
            )
          ) {
            return;
          }


          setError(
            caught instanceof Error
              ? caught.message
              : 'The backend analysis could not be completed.'
          );


          setLogs(
            (prev) => [
              ...prev,
              '[ERROR] The forensic pipeline stopped before completion.',
            ]
          );
        }
      };


    void runAnalysis();


    return () => {

      isActive = false;

      controller.abort();
    };

  }, [
    isOpen,
    file,
  ]);


  if (!isOpen) {
    return null;
  }


  return (

    <div
      className="
        fixed inset-0 z-50
        flex items-center justify-center
        p-4
        bg-[#1e1b18]/60
        backdrop-blur-xs
        animate-in fade-in duration-200
      "
    >

      <div
        className="
          bg-[#fcfbf8]
          rounded-2xl
          max-w-3xl
          w-full
          border border-[#e6ded2]
          shadow-2xl
          overflow-hidden
          animate-in zoom-in-95 duration-200
          max-h-[92vh]
          overflow-y-auto
        "
      >

        {/* =====================================================
            HEADER
        ===================================================== */}

        <div
          className="
            px-6 py-5
            border-b border-[#e6ded2]
            flex items-center justify-between
            bg-[#f5efe4]
          "
        >

          <div>

            <div
              className="
                flex items-center gap-2
              "
            >

              <span
                className={`
                  inline-block
                  w-2.5 h-2.5
                  rounded-full
                  ${
                    error
                      ? 'bg-[#c2593f]'
                      : 'bg-[#3b5749] animate-pulse'
                  }
                `}
              />

              <h3
                className="
                  text-[18px]
                  font-semibold
                  text-[#221e1b]
                  font-['DM_Sans',sans-serif]
                "
              >
                Forensic Pipeline Execution
              </h3>

            </div>


            <p
              className="
                text-xs
                text-[#6e6459]
                font-mono
                mt-0.5
              "
            >

              Case:{' '}

              <span
                className="
                  font-semibold
                  text-[#221e1b]
                "
              >
                {caseName}
              </span>

              {' • '}

              Evidence:{' '}

              <span
                className="
                  font-semibold
                  text-[#221e1b]
                "
              >
                {evidenceId}
              </span>

              {' • '}

              File:{' '}

              <span
                className="
                  font-semibold
                  text-[#221e1b]
                "
              >
                {fileName}
              </span>

            </p>

          </div>


          <button
            onClick={onClose}
            className="
              p-1.5
              text-[#8c8275]
              hover:text-[#221e1b]
              rounded-lg
              hover:bg-black/5
              cursor-pointer
            "
          >
            <X className="w-5 h-5" />
          </button>

        </div>


        <div
          className="
            p-6
            space-y-6
          "
        >

          {/* ===================================================
              PROGRESS
          =================================================== */}

          <div>

            <div
              className="
                flex justify-between
                text-xs
                font-medium
                text-[#221e1b]
                mb-2
                font-mono
              "
            >

              <span
                className="font-semibold"
              >
                {
                  error
                    ? 'Pipeline failed'
                    : isCompleted
                      ? 'Analysis Completed'
                      : 'Executing evidence dissection...'
                }
              </span>

              <span
                className="
                  font-bold
                  text-[#0f2338]
                "
              >
                {progress}%
              </span>

            </div>


            <div
              className="
                w-full
                h-2.5
                bg-[#e8dfd2]
                rounded-full
                overflow-hidden
              "
            >

              <div
                className={`
                  h-full
                  transition-all
                  duration-300
                  rounded-full
                  ${
                    error
                      ? 'bg-[#c2593f]'
                      : 'bg-[#0f2338]'
                  }
                `}
                style={{
                  width: `${progress}%`,
                }}
              />

            </div>

          </div>


          {/* ===================================================
              PHASES
          =================================================== */}

          <div
            className="
              grid
              grid-cols-2
              sm:grid-cols-4
              gap-3
              text-center
              text-xs
            "
          >

            {[
              {
                id: 1,
                label: 'Upload',
                icon: Shield,
              },
              {
                id: 2,
                label: 'FFprobe',
                icon: Cpu,
              },
              {
                id: 3,
                label: 'AI Detection',
                icon: Activity,
              },
              {
                id: 4,
                label: 'Forensic Reconstruction',
                icon: Brain,
              },
            ].map(
              ({
                id,
                label,
                icon: Icon,
              }) => (

                <div
                  key={id}
                  className={`
                    p-2.5
                    rounded-xl
                    border
                    transition-all
                    ${
                      currentPhase >= id
                        ? 'border-[#3b5749] bg-[#eaf1ed] text-[#2b4d3a] font-bold'
                        : 'border-[#e6ded2] text-[#8c8275]'
                    }
                  `}
                >

                  <Icon
                    className="
                      w-4 h-4
                      mx-auto mb-1
                      text-[#3b5749]
                    "
                  />

                  <span>
                    {id}. {label}
                  </span>

                </div>

              )
            )}

          </div>


          {/* ===================================================
              LOG
          =================================================== */}

          <div>

            <div
              className="
                text-[11px]
                font-bold
                text-[#6e6459]
                uppercase
                tracking-wider
                mb-1.5
                font-mono
              "
            >
              Live Bitstream Telemetry & Forensic Log
            </div>


            <div
              className="
                bg-[#141b22]
                text-[#c9dcd0]
                rounded-xl
                p-3.5
                font-mono
                text-[11.5px]
                min-h-36
                max-h-48
                overflow-y-auto
                space-y-1
                scrollbar-thin
                border border-[#232f3d]
              "
            >

              {logs.map(
                (
                  log,
                  index
                ) => (

                  <div
                    key={index}
                    className="
                      leading-relaxed
                    "
                  >
                    {log}
                  </div>

                )
              )}


              {!isCompleted &&
                !error && (

                  <div
                    className="
                      flex items-center
                      gap-1.5
                      text-[#eaf1ed]
                    "
                  >

                    <span
                      className="
                        w-1.5 h-1.5
                        rounded-full
                        bg-[#5e7d6f]
                        animate-ping
                      "
                    />

                    <span>
                      Processing video frames...
                    </span>

                  </div>

                )}


              {error && (

                <div
                  className="
                    text-[#ffb39d]
                  "
                >
                  {error}
                </div>

              )}

            </div>

          </div>


          {/* ===================================================
              FORENSIC SUMMARY
          =================================================== */}

          {isCompleted &&
            analysisResult && (

              <div
                className="
                  rounded-xl
                  border border-[#c9dcd0]
                  bg-[#eaf1ed]
                  p-5
                "
              >

                <div
                  className="
                    flex
                    items-center
                    gap-2
                    mb-3
                  "
                >

                  <Brain
                    className="
                      w-5 h-5
                      text-[#2b4d3a]
                    "
                  />

                  <h4
                    className="
                      font-semibold
                      text-[#221e1b]
                    "
                  >
                    AI Forensic Summary
                  </h4>

                </div>


                <div
                  className="
                    text-sm
                    font-semibold
                    text-[#1b4e39]
                    mb-2
                  "
                >
                  {
                    analysisResult
                      .forensic_summary
                      .headline
                  }
                </div>


                <p
                  className="
                    text-sm
                    text-[#4a423a]
                    leading-relaxed
                  "
                >
                  {
                    analysisResult
                      .forensic_summary
                      .summary
                  }
                </p>


                <div
                  className="
                    grid
                    grid-cols-2
                    gap-3
                    mt-4
                    text-xs
                    font-mono
                  "
                >

                  <div
                    className="
                      bg-white/70
                      rounded-lg
                      p-3
                    "
                  >
                    <div
                      className="
                        text-[#7d7367]
                        uppercase
                        text-[10px]
                        font-bold
                      "
                    >
                      Reconstructed Activities
                    </div>

                    <div
                      className="
                        text-lg
                        font-bold
                        text-[#0f2338]
                      "
                    >
                      {
                        analysisResult
                          .reconstruction_count
                      }
                    </div>
                  </div>


                  <div
                    className="
                      bg-white/70
                      rounded-lg
                      p-3
                    "
                  >
                    <div
                      className="
                        text-[#7d7367]
                        uppercase
                        text-[10px]
                        font-bold
                      "
                    >
                      Confidence
                    </div>

                    <div
                      className="
                        text-lg
                        font-bold
                        text-[#0f2338]
                      "
                    >
                      {
                        (
                          analysisResult
                            .forensic_summary
                            .confidence *
                          100
                        ).toFixed(1)
                      }%
                    </div>
                  </div>

                </div>

              </div>

            )}

        </div>



          {/* ===================================================
              VIDEO INTEGRITY / TAMPERING
          =================================================== */}

          {isCompleted &&
            analysisResult?.integrity_analysis && (
              <div className="rounded-xl border border-[#e6ded2] bg-[#fcfbf8] p-5">
                <div className="flex items-center justify-between gap-3 mb-4">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-5 h-5 text-[#3b5749]" />
                    <h4 className="font-semibold text-[#221e1b]">
                      Video Integrity & Tampering Analysis
                    </h4>
                  </div>

                  <span className={`
                    px-2.5 py-1 rounded-full text-[10px] font-bold font-mono
                    ${
                      analysisResult.integrity_analysis.overall_status === 'PASS'
                        ? 'bg-[#eaf1ed] text-[#2b4d3a]'
                        : analysisResult.integrity_analysis.overall_status === 'ERROR'
                          ? 'bg-[#f9e5df] text-[#9d3f2b]'
                          : 'bg-[#fff1d6] text-[#8a5a00]'
                    }
                  `}>
                    {analysisResult.integrity_analysis.overall_status}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                  <div className="bg-[#f5efe4] rounded-lg p-3">
                    <div className="text-[10px] uppercase font-bold text-[#7d7367]">
                      Integrity Score
                    </div>
                    <div className="text-lg font-bold text-[#0f2338]">
                      {analysisResult.integrity_analysis.integrity_score.toFixed(1)}%
                    </div>
                  </div>

                  <div className="bg-[#f5efe4] rounded-lg p-3">
                    <div className="text-[10px] uppercase font-bold text-[#7d7367]">
                      Frames Checked
                    </div>
                    <div className="text-lg font-bold text-[#0f2338]">
                      {analysisResult.integrity_analysis.frames_checked}
                    </div>
                  </div>

                  <div className="bg-[#f5efe4] rounded-lg p-3">
                    <div className="text-[10px] uppercase font-bold text-[#7d7367]">
                      Timestamp Gaps
                    </div>
                    <div className="text-lg font-bold text-[#0f2338]">
                      {analysisResult.integrity_analysis.timestamp_gaps}
                    </div>
                  </div>

                  <div className="bg-[#f5efe4] rounded-lg p-3">
                    <div className="text-[10px] uppercase font-bold text-[#7d7367]">
                      Duplicate Sequences
                    </div>
                    <div className="text-lg font-bold text-[#0f2338]">
                      {analysisResult.integrity_analysis.duplicate_sequences}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  {[
                    ['Timestamp continuity', analysisResult.integrity_analysis.timestamp_continuity],
                    ['Frame continuity', analysisResult.integrity_analysis.frame_continuity],
                    ['FPS consistency', analysisResult.integrity_analysis.fps_consistency],
                    ['Duplicate frames', analysisResult.integrity_analysis.duplicate_frames],
                    ['Metadata consistency', analysisResult.integrity_analysis.metadata_consistency],
                    ['Resolution consistency', analysisResult.integrity_analysis.resolution_consistency],
                    ['Compression consistency', analysisResult.integrity_analysis.compression_consistency],
                  ].map(([label, passed]) => (
                    <div
                      key={String(label)}
                      className="flex items-center justify-between rounded-lg border border-[#e6ded2] px-3 py-2 text-xs"
                    >
                      <span className="text-[#4a423a]">{String(label)}</span>

                      {Boolean(passed) ? (
                        <span className="flex items-center gap-1 text-[#2b4d3a] font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          PASS
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[#9d3f2b] font-semibold">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          REVIEW
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                {analysisResult.integrity_analysis.anomalies.length > 0 && (
                  <div className="mt-4 rounded-lg border border-[#ead6ae] bg-[#fff8e8] p-3">
                    <div className="text-[10px] uppercase tracking-wider font-bold text-[#8a5a00] mb-2">
                      Potential Anomalies
                    </div>

                    <div className="space-y-1">
                      {analysisResult.integrity_analysis.anomalies
                        .slice(0, 10)
                        .map((anomaly, index) => (
                          <div
                            key={`${anomaly}-${index}`}
                            className="text-xs text-[#5f5138] leading-relaxed"
                          >
                            • {anomaly}
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                <p className="mt-3 text-[10px] leading-relaxed text-[#7d7367] font-mono">
                  Integrity findings are forensic review flags and do not independently prove that the video was edited.
                </p>
              </div>
            )}

          {/* ===================================================
              OBJECT DISAPPEARANCE
          =================================================== */}

          {isCompleted &&
            analysisResult?.object_disappearance_analysis && (
              <div className="rounded-xl border border-[#e6ded2] bg-[#fcfbf8] p-5">
                <div className="flex items-center gap-2 mb-4">
                  <EyeOff className="w-5 h-5 text-[#3b5749]" />
                  <h4 className="font-semibold text-[#221e1b]">
                    Object Disappearance Detection
                  </h4>
                </div>

                {analysisResult.object_disappearance_analysis.count === 0 ? (
                  <div className="rounded-lg border border-[#c9dcd0] bg-[#eaf1ed] p-4 text-sm text-[#2b4d3a]">
                    No significant object disappearance patterns detected.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {analysisResult.object_disappearance_analysis.disappearances.map(
                      (item, index) => (
                        <div
                          key={`${item.camera_id}-${item.object_type}-${index}`}
                          className="rounded-lg border border-[#ead6ae] bg-[#fff8e8] p-4"
                        >
                          <div className="flex items-center justify-between gap-2 mb-3">
                            <div className="text-sm font-bold text-[#221e1b] uppercase">
                              {item.object_type}
                            </div>
                            <div className="text-[10px] font-mono text-[#7d7367]">
                              {item.camera_id}
                            </div>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                            <div>
                              <span className="text-[#7d7367]">First observed:</span>{' '}
                              {new Date(item.first_seen).toLocaleString()}
                            </div>

                            <div>
                              <span className="text-[#7d7367]">Last observed:</span>{' '}
                              {new Date(item.last_seen).toLocaleString()}
                            </div>

                            <div>
                              <span className="text-[#7d7367]">No longer seen:</span>{' '}
                              {new Date(item.disappearance_time).toLocaleString()}
                            </div>

                            <div>
                              <span className="text-[#7d7367]">Observations:</span>{' '}
                              {item.observation_count}
                            </div>
                          </div>

                          {item.related_activity.length > 0 && (
                            <div className="mt-3">
                              <div className="text-[10px] uppercase tracking-wider font-bold text-[#7d7367] mb-1">
                                Related activity
                              </div>

                              <div className="space-y-1">
                                {item.related_activity.map(
                                  (activity, activityIndex) => (
                                    <div
                                      key={`${activity}-${activityIndex}`}
                                      className="text-xs text-[#5f5138]"
                                    >
                                      • {activity}
                                    </div>
                                  )
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    )}
                  </div>
                )}

                <p className="mt-3 text-[10px] leading-relaxed text-[#7d7367] font-mono">
                  {analysisResult.object_disappearance_analysis.note}
                </p>
              </div>
            )}

        {/* =====================================================
            FOOTER
        ===================================================== */}

        <div
          className="
            px-6 py-4
            bg-[#f5efe4]
            border-t border-[#e6ded2]
            flex items-center
            justify-between
          "
        >

          <span
            className="
              text-xs
              font-mono
              text-[#6e6459]
            "
          >
            {
              error
                ? 'Check the log above'
                : isCompleted
                  ? '✓ AI forensic, integrity and disappearance analysis completed'
                  : 'Preserving evidentiary bitstream...'
            }
          </span>


          <div
            className="
              flex gap-2
            "
          >

            <button
              onClick={onClose}
              className="
                px-4 py-2
                text-xs
                font-semibold
                text-[#5c544c]
                bg-white
                border border-[#ded5c7]
                rounded-lg
                hover:bg-black/5
                transition-colors
                cursor-pointer
              "
            >
              Close
            </button>


            {isCompleted &&
              !error && (

                <button
                  onClick={onClose}
                  className="
                    btn-primary-navy
                    px-4 py-2
                    text-xs
                    font-semibold
                    text-white
                    rounded-lg
                    flex items-center
                    gap-1.5
                    cursor-pointer
                  "
                >

                  <span>
                    Review Generated Timeline
                  </span>

                  <ArrowRight
                    className="
                      w-3.5 h-3.5
                    "
                  />

                </button>

              )}

          </div>

        </div>

      </div>

    </div>
  );
};