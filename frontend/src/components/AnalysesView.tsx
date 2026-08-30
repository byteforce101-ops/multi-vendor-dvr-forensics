import React, {
  useEffect,
  useState,
} from 'react';

import {
  Play,
  Pause,
  Download,
  Brain,
  Clock,
} from 'lucide-react';

import {
  motion,
} from 'motion/react';

import {
  VideoAnalysisResult,
} from '../types';


interface AnalysesViewProps {

  analysis?:
    | VideoAnalysisResult
    | null;
}


const formatEventTime = (
  value: string
) => {

  const date =
    new Date(value);

  return Number.isNaN(
    date.getTime()
  )
    ? value
    : date
        .toISOString()
        .slice(
          11,
          23
        );
};


const formatDuration = (
  seconds:
    | number
    | null
    | undefined
) => {

  if (seconds == null) {
    return '--:--:--';
  }

  const wholeSeconds =
    Math.max(
      0,
      Math.floor(seconds)
    );

  const hours =
    Math.floor(
      wholeSeconds / 3600
    );

  const minutes =
    Math.floor(
      (wholeSeconds % 3600) /
        60
    );

  const remainder =
    wholeSeconds % 60;

  return (
    `${hours
      .toString()
      .padStart(2, '0')}:` +
    `${minutes
      .toString()
      .padStart(2, '0')}:` +
    `${remainder
      .toString()
      .padStart(2, '0')}`
  );
};


export const AnalysesView:
  React.FC<
    AnalysesViewProps
  > = ({
    analysis,
  }) => {

    const [
      isPlaying,
      setIsPlaying,
    ] = useState(false);

    const [
      selectedEventId,
      setSelectedEventId,
    ] = useState<number>(1);


    const timelineEvents =
      (
        analysis?.events ??
        []
      ).map(
        (
          event,
          index
        ) => ({

          id: index + 1,

          time:
            formatEventTime(
              event.start_time
            ),

          type:
            event.event_type,

          label:
            `${event.event_type.replaceAll(
              '_',
              ' '
            )}${
              event.object_type
                ? ` · ${event.object_type}`
                : ''
            }`,

          confidence:
            event.confidence ==
            null
              ? 0
              : event.confidence <=
                  1
                ? event.confidence *
                  100
                : event.confidence,
        })
      );


    useEffect(() => {

      setSelectedEventId(
        1
      );

    }, [analysis]);


    const eventCount =
      analysis?.event_count ??
      0;


    const duration =
      formatDuration(
        analysis?.metadata
          .duration_seconds
      );


    const sourceName =
      analysis?.filename ??
      'No file analyzed yet';


    const reconstructedEvents =
      analysis
        ?.reconstructed_events ??
      [];


    const summary =
      analysis
        ?.forensic_summary ??
      null;


    return (

      <motion.div
        initial={{
          opacity: 0,
          y: 8,
        }}
        animate={{
          opacity: 1,
          y: 0,
        }}
        transition={{
          duration: 0.25,
        }}
        className="space-y-7"
      >

        {/* =====================================================
            HEADER
        ===================================================== */}

        <div
          className="
            bg-[#fcfbf8]
            rounded-2xl
            border border-[#e6ded2]
            p-6 sm:p-8
            shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)]
            flex flex-col
            sm:flex-row
            sm:items-center
            justify-between
            gap-4
          "
        >

          <div>

            <span
              className="
                text-xs
                font-mono
                font-bold
                text-[#3b5749]
                uppercase
                tracking-wider
                bg-[#eaf1ed]
                border border-[#c9dcd0]
                px-3 py-0.5
                rounded-md
              "
            >
              Active Forensic Analysis
            </span>


            <h2
              className="
                text-2xl
                sm:text-3xl
                font-['DM_Sans',sans-serif]
                text-[#221e1b]
                mt-2
                font-normal
              "
            >
              {
                analysis
                  ? 'Backend Analysis • Multi-Track Video Timeline'
                  : 'No analysis run yet'
              }
            </h2>


            <p
              className="
                text-xs
                text-[#6e6459]
                font-mono
                mt-1
              "
            >
              Source: {sourceName}

              {analysis
                ? ` • Analysis ID: ${analysis.analysis_id} • ${analysis.frames_analyzed} frames analyzed`
                : ''}
            </p>

          </div>


          <button
            className="
              btn-primary-navy
              px-5 py-2.5
              rounded-xl
              text-white
              text-xs
              font-semibold
              flex items-center
              gap-2
              self-start
              sm:self-auto
              cursor-pointer
            "
          >

            <Download
              className="w-4 h-4"
            />

            <span>
              Export Certified Dossier
            </span>

          </button>

        </div>


        {/* =====================================================
            VIDEO + CHRONOLOGY
        ===================================================== */}

        <div
          className="
            grid
            grid-cols-1
            lg:grid-cols-3
            gap-6
          "
        >

          {/* VIDEO */}

          <div
            className="
              lg:col-span-2
              bg-[#fcfbf8]
              rounded-2xl
              border border-[#e6ded2]
              p-6
              shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)]
              flex flex-col
              justify-between
            "
          >

            <div
              className="
                relative
                aspect-video
                bg-[#141b22]
                rounded-xl
                overflow-hidden
                flex items-center
                justify-center
                group
                shadow-inner
              "
            >

              <div
                className="
                  absolute
                  inset-0
                  bg-gradient-to-t
                  from-black/80
                  via-transparent
                  to-black/30
                  pointer-events-none
                "
              />


              <button
                onClick={() =>
                  setIsPlaying(
                    !isPlaying
                  )
                }
                className="
                  w-14 h-14
                  rounded-full
                  bg-white/20
                  hover:bg-white/35
                  backdrop-blur-md
                  text-white
                  flex items-center
                  justify-center
                  transition-transform
                  hover:scale-105
                  cursor-pointer
                "
              >

                {isPlaying
                  ? (
                    <Pause
                      className="w-6 h-6"
                    />
                  )
                  : (
                    <Play
                      className="
                        w-6 h-6
                        ml-0.5
                      "
                    />
                  )}

              </button>


              <div
                className="
                  absolute
                  bottom-0
                  left-0
                  right-0
                  p-4
                  flex items-center
                  justify-between
                  text-white
                  text-xs
                  font-mono
                "
              >

                <span
                  className="
                    text-stone-300
                  "
                >
                  / {duration}
                </span>


                <div
                  className="
                    flex items-center
                    gap-2
                  "
                >

                  <span
                    className="
                      bg-[#0f2338]
                      px-2
                      py-0.5
                      rounded
                      text-[11px]
                    "
                  >
                    {
                      analysis
                        ?.metadata
                        .codec ??
                      'Unknown codec'
                    }
                  </span>

                </div>

              </div>

            </div>

          </div>


          {/* CHRONOLOGY */}

          <div
            className="
              bg-[#fcfbf8]
              rounded-2xl
              border border-[#e6ded2]
              p-6
              shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)]
            "
          >

            <div
              className="
                flex items-center
                justify-between
                mb-4
              "
            >

              <h3
                className="
                  font-semibold
                  text-[#221e1b]
                  font-['DM_Sans',sans-serif]
                  text-xl
                "
              >
                AI-Detected Chronology
              </h3>


              <span
                className="
                  text-xs
                  font-mono
                  text-[#3b5749]
                  bg-[#eaf1ed]
                  px-2.5
                  py-0.5
                  rounded
                  font-semibold
                "
              >
                {eventCount} Events
              </span>

            </div>


            {timelineEvents.length ===
              0 && (

              <p
                className="
                  text-xs
                  text-[#6e6459]
                "
              >
                Run a file through the pipeline from the Pipelines tab.
              </p>

            )}


            <div
              className="
                space-y-3
                max-h-[420px]
                overflow-y-auto
                pr-1
              "
            >

              {timelineEvents.map(
                (evt) => {

                  const isSelected =
                    selectedEventId ===
                    evt.id;


                  return (

                    <motion.div
                      key={evt.id}
                      whileHover={{
                        scale: 1.02,
                        y: -2,
                      }}
                      transition={{
                        duration: 0.15,
                      }}
                      onClick={() =>
                        setSelectedEventId(
                          evt.id
                        )
                      }
                      className={`
                        p-3.5
                        rounded-xl
                        border
                        transition-all
                        cursor-pointer
                        shadow-2xs
                        hover:shadow-md
                        ${
                          isSelected
                            ? 'border-[#1b4e39] bg-[#eaf1ed] shadow-xs ring-1 ring-[#1b4e39]/30'
                            : 'border-[#e4ded4] hover:border-[#1b4e39]/50 bg-[#fffdfa]'
                        }
                      `}
                    >

                      <div
                        className="
                          flex items-center
                          justify-between
                          text-xs
                          font-mono
                        "
                      >

                        <span
                          className="
                            font-bold
                            text-[#0f2338]
                          "
                        >
                          {evt.time}
                        </span>


                        <span
                          className="
                            text-[#2b4d3a]
                            font-semibold
                          "
                        >
                          {evt.confidence.toFixed(
                            1
                          )}
                          % match
                        </span>

                      </div>


                      <div
                        className="
                          text-xs
                          font-semibold
                          text-[#221e1b]
                          mt-1
                        "
                      >
                        {evt.label}
                      </div>

                    </motion.div>

                  );
                }
              )}

            </div>


            <div
              className="
                mt-5
                p-3.5
                bg-[#f5efe4]
                rounded-xl
                text-xs
                font-mono
                text-[#4a423a]
                space-y-1
                border border-[#ded5c7]
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
                Metadata Telemetry
              </div>


              <div>
                Resolution:{' '}
                {analysis?.metadata.width ??
                  '—'}
                x
                {analysis?.metadata.height ??
                  '—'}
              </div>


              <div>
                Codec:{' '}
                {analysis?.metadata.codec ??
                  'Unknown'}
                {' • '}

                {
                  analysis?.metadata.fps ==
                  null
                    ? '—'
                    : `${analysis.metadata.fps.toFixed(
                        2
                      )} FPS`
                }
              </div>


              <div>
                Audio:{' '}
                {analysis?.metadata.has_audio
                  ? 'Present'
                  : 'None'}
              </div>

            </div>

          </div>

        </div>


        {/* =====================================================
            AI FORENSIC EVENT RECONSTRUCTION
        ===================================================== */}

        {analysis && (

          <div
            className="
              bg-[#fcfbf8]
              rounded-2xl
              border border-[#e6ded2]
              p-6 sm:p-8
              shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)]
            "
          >

            <div
              className="
                flex
                flex-col
                sm:flex-row
                sm:items-center
                justify-between
                gap-3
                mb-5
              "
            >

              <div>

                <div
                  className="
                    flex items-center
                    gap-2
                  "
                >

                  <Brain
                    className="
                      w-5 h-5
                      text-[#3b5749]
                    "
                  />

                  <h3
                    className="
                      text-xl
                      font-semibold
                      text-[#221e1b]
                    "
                  >
                    AI Forensic Event Reconstruction
                  </h3>

                </div>


                <p
                  className="
                    text-xs
                    text-[#6e6459]
                    font-mono
                    mt-1
                  "
                >
                  Low-level detections grouped into higher-level forensic activities.
                </p>

              </div>


              <span
                className="
                  text-xs
                  font-mono
                  font-bold
                  text-[#3b5749]
                  bg-[#eaf1ed]
                  border border-[#c9dcd0]
                  px-3
                  py-1
                  rounded-md
                "
              >
                {
                  analysis.reconstruction_count
                } Activities
              </span>

            </div>


            {reconstructedEvents.length ===
              0 ? (

              <div
                className="
                  p-5
                  rounded-xl
                  bg-[#f5efe4]
                  border border-[#ded5c7]
                  text-sm
                  text-[#6e6459]
                "
              >
                No higher-level forensic activity could be reconstructed from the detected events.
              </div>

            ) : (

              <div
                className="
                  grid
                  grid-cols-1
                  md:grid-cols-2
                  gap-4
                "
              >

                {reconstructedEvents.map(
                  (
                    event,
                    index
                  ) => (

                    <motion.div
                      key={`${event.event_type}-${index}`}
                      initial={{
                        opacity: 0,
                        y: 5,
                      }}
                      animate={{
                        opacity: 1,
                        y: 0,
                      }}
                      transition={{
                        delay:
                          index * 0.04,
                      }}
                      className="
                        rounded-xl
                        border border-[#ded5c7]
                        bg-[#fffdfa]
                        p-5
                      "
                    >

                      <div
                        className="
                          flex
                          items-start
                          justify-between
                          gap-3
                        "
                      >

                        <div>

                          <div
                            className="
                              text-[10px]
                              uppercase
                              tracking-wider
                              font-mono
                              font-bold
                              text-[#3b5749]
                              mb-1
                            "
                          >
                            {event.event_type.replaceAll(
                              '_',
                              ' '
                            )}
                          </div>


                          <h4
                            className="
                              text-base
                              font-semibold
                              text-[#221e1b]
                            "
                          >
                            {event.title}
                          </h4>

                        </div>


                        <span
                          className="
                            shrink-0
                            text-xs
                            font-mono
                            font-bold
                            text-[#2b4d3a]
                            bg-[#eaf1ed]
                            px-2
                            py-1
                            rounded
                          "
                        >
                          {
                            (
                              event.confidence *
                              100
                            ).toFixed(1)
                          }%
                        </span>

                      </div>


                      <p
                        className="
                          text-sm
                          text-[#4a423a]
                          leading-relaxed
                          mt-3
                        "
                      >
                        {event.description}
                      </p>


                      <div
                        className="
                          mt-4
                          flex
                          flex-wrap
                          gap-2
                        "
                      >

                        {event.objects.map(
                          (
                            object,
                            objectIndex
                          ) => (

                            <span
                              key={
                                objectIndex
                              }
                              className="
                                text-[11px]
                                font-mono
                                bg-[#f5efe4]
                                border border-[#ded5c7]
                                text-[#4a423a]
                                px-2
                                py-1
                                rounded
                              "
                            >
                              {object}
                            </span>

                          )
                        )}

                      </div>


                      <div
                        className="
                          mt-4
                          pt-3
                          border-t border-[#eee6da]
                          flex
                          items-center
                          gap-2
                          text-[11px]
                          font-mono
                          text-[#6e6459]
                        "
                      >

                        <Clock
                          className="
                            w-3.5 h-3.5
                          "
                        />

                        <span>
                          {
                            formatEventTime(
                              event.start_time
                            )
                          }
                        </span>

                        <span>
                          →
                        </span>

                        <span>
                          {
                            formatEventTime(
                              event.end_time
                            )
                          }
                        </span>

                      </div>

                    </motion.div>

                  )
                )}

              </div>

            )}

          </div>

        )}


        {/* =====================================================
            FINAL FORENSIC SUMMARY
        ===================================================== */}

        {summary && (

          <div
            className="
              rounded-2xl
              border border-[#c9dcd0]
              bg-[#eaf1ed]
              p-6 sm:p-8
              shadow-[0_4px_20px_-4px_rgba(34,30,27,0.05)]
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
                  text-[#1b4e39]
                "
              />

              <span
                className="
                  text-xs
                  font-mono
                  font-bold
                  uppercase
                  tracking-wider
                  text-[#1b4e39]
                "
              >
                Final AI Forensic Summary
              </span>

            </div>


            <h3
              className="
                text-2xl
                font-semibold
                text-[#221e1b]
              "
            >
              {summary.headline}
            </h3>


            <p
              className="
                text-sm
                text-[#4a423a]
                leading-relaxed
                mt-3
                max-w-4xl
              "
            >
              {summary.summary}
            </p>


            <div
              className="
                grid
                grid-cols-1
                sm:grid-cols-3
                gap-3
                mt-5
              "
            >

              <div
                className="
                  bg-white/70
                  rounded-xl
                  p-4
                  border border-[#d8e6dd]
                "
              >

                <div
                  className="
                    text-[10px]
                    uppercase
                    font-mono
                    font-bold
                    text-[#7d7367]
                  "
                >
                  Reconstructed Activities
                </div>

                <div
                  className="
                    text-2xl
                    font-bold
                    text-[#0f2338]
                    mt-1
                  "
                >
                  {summary.event_count}
                </div>

              </div>


              <div
                className="
                  bg-white/70
                  rounded-xl
                  p-4
                  border border-[#d8e6dd]
                "
              >

                <div
                  className="
                    text-[10px]
                    uppercase
                    font-mono
                    font-bold
                    text-[#7d7367]
                  "
                >
                  Confidence
                </div>

                <div
                  className="
                    text-2xl
                    font-bold
                    text-[#0f2338]
                    mt-1
                  "
                >
                  {
                    (
                      summary.confidence *
                      100
                    ).toFixed(1)
                  }%
                </div>

              </div>


              <div
                className="
                  bg-white/70
                  rounded-xl
                  p-4
                  border border-[#d8e6dd]
                "
              >

                <div
                  className="
                    text-[10px]
                    uppercase
                    font-mono
                    font-bold
                    text-[#7d7367]
                  "
                >
                  Objects
                </div>

                <div
                  className="
                    text-sm
                    font-semibold
                    text-[#0f2338]
                    mt-2
                  "
                >
                  {
                    summary.objects_detected
                      .join(', ') ||
                    'None recorded'
                  }
                </div>

              </div>

            </div>


            {summary.key_events.length >
              0 && (

              <div
                className="
                  mt-5
                  bg-white/60
                  rounded-xl
                  p-4
                  border border-[#d8e6dd]
                "
              >

                <div
                  className="
                    text-[10px]
                    uppercase
                    font-mono
                    font-bold
                    text-[#7d7367]
                    mb-2
                  "
                >
                  Key Forensic Events
                </div>


                <div
                  className="
                    space-y-2
                  "
                >

                  {summary.key_events.map(
                    (
                      item,
                      index
                    ) => (

                      <div
                        key={index}
                        className="
                          text-xs
                          font-mono
                          text-[#4a423a]
                        "
                      >
                        {index + 1}. {item}
                      </div>

                    )
                  )}

                </div>

              </div>

            )}

          </div>

        )}

      </motion.div>
    );
  };