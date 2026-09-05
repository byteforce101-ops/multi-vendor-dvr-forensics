import jsPDF from 'jspdf';

import type {
  VideoAnalysisResult,
} from '../types';

type AnyRecord =
  Record<string, unknown>;


/* =========================================================
   COLORS
========================================================= */

const NAVY = '#0F2338';
const GREEN = '#1B4E39';
const BORDER = '#DED5C7';
const TEXT = '#221E1B';
const MUTED = '#6E6459';
const RED = '#A43D31';


/* =========================================================
   HELPERS
========================================================= */

const safe = (
  value: unknown,
  fallback = '—',
): string => {

  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return fallback;
  }

  if (
    typeof value === 'object'
  ) {
    try {
      return JSON.stringify(
        value,
      );
    } catch {
      return fallback;
    }
  }

  return String(value);
};


const pct = (
  value: unknown,
): string => {

  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return '—';
  }

  return `${
    (
      number <= 1
        ? number * 100
        : number
    ).toFixed(1)
  }%`;
};


const duration = (
  value: unknown,
): string => {

  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return '—';
  }

  const total =
    Math.max(
      0,
      Math.round(number),
    );

  const hours =
    Math.floor(
      total / 3600,
    );

  const minutes =
    Math.floor(
      (total % 3600) / 60,
    );

  const seconds =
    total % 60;

  return (
    `${String(hours).padStart(2, '0')}:` +
    `${String(minutes).padStart(2, '0')}:` +
    `${String(seconds).padStart(2, '0')}`
  );
};


const time = (
  value: unknown,
): string => {

  if (!value) {
    return '—';
  }

  const date =
    new Date(
      String(value),
    );

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return String(value);
  }

  return (
    date
      .toISOString()
      .replace(
        'T',
        ' ',
      )
      .replace(
        'Z',
        ' UTC',
      )
  );
};


const label = (
  value: unknown,
): string => {

  return safe(
    value,
    'UNKNOWN',
  )
    .replaceAll(
      '_',
      ' ',
    )
    .replace(
      /\b\w/g,
      (character) =>
        character.toUpperCase(),
    );
};


const hex = (
  color: string,
): [
  number,
  number,
  number,
] => {

  const value =
    color.replace(
      '#',
      '',
    );

  return [
    parseInt(
      value.slice(0, 2),
      16,
    ),

    parseInt(
      value.slice(2, 4),
      16,
    ),

    parseInt(
      value.slice(4, 6),
      16,
    ),
  ];
};


/* =========================================================
   MAIN EXPORT
========================================================= */

export const generateForensicDossier =
  (
    analysis:
      VideoAnalysisResult,
  ): void => {

    const doc =
      new jsPDF({
        unit: 'mm',
        format: 'a4',
        orientation: 'portrait',
      });


    const pageWidth =
      doc.internal.pageSize.getWidth();

    const pageHeight =
      doc.internal.pageSize.getHeight();

    const margin = 16;

    const contentWidth =
      pageWidth -
      margin * 2;

    let y =
      margin;


    /* =====================================================
       PDF TEXT HELPERS
    ===================================================== */

    const setText = (
      color: string,
      size: number,
      bold = false,
    ) => {

      doc.setTextColor(
        ...hex(color),
      );

      doc.setFont(
        'helvetica',
        bold
          ? 'bold'
          : 'normal',
      );

      doc.setFontSize(
        size,
      );
    };


    /* =====================================================
       FOOTER
    ===================================================== */

    const footer = () => {

      const page =
        doc.getNumberOfPages();

      doc.setDrawColor(
        ...hex(BORDER),
      );

      doc.line(
        margin,
        pageHeight - 12,
        pageWidth - margin,
        pageHeight - 12,
      );

      setText(
        MUTED,
        7,
      );

      doc.text(
        'TRACEX • FORENSIC DOSSIER • CONFIDENTIAL',
        margin,
        pageHeight - 7,
      );

      doc.text(
        `Page ${page}`,
        pageWidth - margin,
        pageHeight - 7,
        {
          align: 'right',
        },
      );
    };


    /* =====================================================
       PAGE BREAK
    ===================================================== */

    const ensure = (
      needed = 12,
    ) => {

      if (
        y + needed >
        pageHeight - 18
      ) {

        footer();

        doc.addPage();

        y =
          margin;
      }
    };


    /* =====================================================
       SECTION HEADER
    ===================================================== */

    const section = (
      title: string,
      number: string,
    ) => {

      ensure(18);

      doc.setFillColor(
        ...hex(NAVY),
      );

      doc.roundedRect(
        margin,
        y,
        contentWidth,
        10,
        2,
        2,
        'F',
      );

      setText(
        '#FFFFFF',
        10,
        true,
      );

      doc.text(
        `${number}  ${title.toUpperCase()}`,
        margin + 5,
        y + 6.6,
      );

      y += 16;
    };


    /* =====================================================
       PARAGRAPH
    ===================================================== */

    const paragraph = (
      text: string,
      size = 8.5,
      color = TEXT,
    ) => {

      const lines =
        doc.splitTextToSize(
          safe(text),
          contentWidth,
        );

      const lineHeight =
        size * 0.42 + 1.8;

      ensure(
        lines.length *
          lineHeight +
          3,
      );

      setText(
        color,
        size,
      );

      doc.text(
        lines,
        margin,
        y,
      );

      y +=
        lines.length *
          lineHeight +
        3;
    };


    /* =====================================================
       KEY / VALUE ROW
    ===================================================== */

    const keyValue = (
      key: string,
      value: unknown,
      width = contentWidth,
    ) => {

      ensure(11);

      const labelWidth =
        48;

      doc.setFillColor(
        ...hex('#FCFBF8'),
      );

      doc.setDrawColor(
        ...hex(BORDER),
      );

      doc.roundedRect(
        margin,
        y,
        width,
        8.5,
        1.5,
        1.5,
        'FD',
      );

      setText(
        MUTED,
        7,
        true,
      );

      doc.text(
        key.toUpperCase(),
        margin + 3,
        y + 5.5,
      );

      setText(
        TEXT,
        8,
      );

      const valueLines =
        doc.splitTextToSize(
          safe(value),
          width -
            labelWidth -
            7,
        );

      doc.text(
        valueLines[0] ??
          '—',
        margin +
          labelWidth,
        y + 5.5,
      );

      y += 10;
    };


    /* =====================================================
       STATUS BADGE
    ===================================================== */

    const status = (
      value: unknown,
    ) => {

      const statusValue =
        safe(
          value,
          'UNKNOWN',
        ).toUpperCase();

      const color =
        statusValue === 'PASS' ||
        statusValue === 'OK' ||
        statusValue === 'COMPLETED'
          ? GREEN
          : statusValue === 'WARNING' ||
              statusValue === 'REVIEW'
            ? '#98601B'
            : RED;

      doc.setFillColor(
        ...hex(color),
      );

      doc.roundedRect(
        pageWidth -
          margin -
          34,
        y - 1,
        34,
        7,
        1.5,
        1.5,
        'F',
      );

      setText(
        '#FFFFFF',
        7,
        true,
      );

      doc.text(
        statusValue,
        pageWidth -
          margin -
          17,
        y + 3.8,
        {
          align: 'center',
        },
      );
    };


    /* =====================================================
       TABLE
    ===================================================== */

    const table = (
      headers: string[],
      rows: string[][],
      widths: number[],
    ) => {

      const rowHeight =
        7;

      const headerHeight =
        9;

      const total =
        widths.reduce(
          (
            accumulator,
            value,
          ) =>
            accumulator +
            value,
          0,
        );


      const drawHeader = () => {

        doc.setFillColor(
          ...hex(NAVY),
        );

        doc.setDrawColor(
          ...hex(NAVY),
        );

        doc.rect(
          margin,
          y,
          total,
          headerHeight,
          'F',
        );

        let x =
          margin;

        headers.forEach(
          (
            header,
            index,
          ) => {

            setText(
              '#FFFFFF',
              6.8,
              true,
            );

            doc.text(
              doc
                .splitTextToSize(
                  header,
                  widths[index] - 3,
                )[0],
              x + 1.5,
              y + 5.8,
            );

            x +=
              widths[index];
          },
        );

        y +=
          headerHeight;
      };


      ensure(
        headerHeight +
          rowHeight +
          3,
      );

      drawHeader();


      rows.forEach(
        (
          row,
          rowIndex,
        ) => {

          const wrapped =
            row.map(
              (
                cell,
                index,
              ) =>
                doc.splitTextToSize(
                  safe(cell),
                  widths[index] - 3,
                ),
            );

          const maxLines =
            Math.max(
              ...wrapped.map(
                (
                  lines,
                ) =>
                  Math.min(
                    lines.length,
                    3,
                  ),
              ),
              1,
            );

          const height =
            Math.max(
              rowHeight,
              maxLines *
                3.3 +
                3,
            );


          if (
            y + height >
            pageHeight - 18
          ) {

            footer();

            doc.addPage();

            y =
              margin;

            drawHeader();
          }


          if (
            rowIndex % 2 ===
            0
          ) {

            doc.setFillColor(
              ...hex('#FCFBF8'),
            );

            doc.rect(
              margin,
              y,
              total,
              height,
              'F',
            );
          }


          doc.setDrawColor(
            ...hex(BORDER),
          );

          doc.rect(
            margin,
            y,
            total,
            height,
            'S',
          );


          let x =
            margin;


          wrapped.forEach(
            (
              lines,
              index,
            ) => {

              setText(
                TEXT,
                6.6,
              );

              doc.text(
                lines.slice(
                  0,
                  3,
                ),
                x + 1.5,
                y + 4.2,
              );

              x +=
                widths[index];
            },
          );


          y +=
            height;
        },
      );


      y += 4;
    };


    /* =========================================================
       COVER PAGE
    ========================================================= */

    doc.setFillColor(
      ...hex(NAVY),
    );

    doc.rect(
      0,
      0,
      pageWidth,
      pageHeight,
      'F',
    );


    doc.setFillColor(
      ...hex(GREEN),
    );

    doc.rect(
      0,
      pageHeight - 38,
      pageWidth,
      38,
      'F',
    );


    setText(
      '#FFFFFF',
      9,
      true,
    );

    doc.text(
      'TRACEX',
      margin,
      34,
    );


    setText(
      '#FFFFFF',
      28,
      true,
    );

    doc.text(
      'FORENSIC DOSSIER',
      margin,
      78,
    );


    setText(
      '#D9E6DE',
      11,
    );

    doc.text(
      'Certified analytical record of a processed video evidence item',
      margin,
      89,
    );


    setText(
      '#FFFFFF',
      9,
      true,
    );

    doc.text(
      'ANALYSIS IDENTIFIER',
      margin,
      124,
    );


    setText(
      '#D9E6DE',
      9,
    );

    doc.text(
      safe(
        analysis.analysis_id,
      ),
      margin,
      132,
    );


    setText(
      '#FFFFFF',
      9,
      true,
    );

    doc.text(
      'SOURCE EVIDENCE',
      margin,
      148,
    );


    setText(
      '#D9E6DE',
      9,
    );

    doc.text(
      safe(
        analysis.filename,
      ),
      margin,
      156,
    );


    setText(
      '#FFFFFF',
      9,
      true,
    );

    doc.text(
      'GENERATED',
      margin,
      172,
    );


    setText(
      '#D9E6DE',
      9,
    );

    doc.text(
      new Date()
        .toISOString()
        .replace(
          'T',
          ' ',
        )
        .replace(
          'Z',
          ' UTC',
        ),
      margin,
      180,
    );


    setText(
      '#FFFFFF',
      7.5,
    );

    doc.text(
      'This dossier records the output returned by the TraceX forensic analysis pipeline.',
      margin,
      pageHeight - 23,
    );

    doc.text(
      'It is an analytical artifact and should be interpreted by a qualified investigator.',
      margin,
      pageHeight - 16,
    );


    footer();


    doc.addPage();

    y =
      margin;


    /* =========================================================
       01 — CASE & EVIDENCE
    ========================================================= */

    section(
      'Case & Evidence Identification',
      '01',
    );


    keyValue(
      'Analysis ID',
      analysis.analysis_id,
    );


    keyValue(
      'Source filename',
      analysis.filename,
    );


    keyValue(
      'Analysis status',
      analysis.status,
    );


    keyValue(
      'Frames analyzed',
      analysis.frames_analyzed,
    );


    keyValue(
      'Low-level events',
      analysis.event_count,
    );


    keyValue(
      'Reconstructed activities',
      analysis.reconstruction_count,
    );


    keyValue(
      'Report generated',
      new Date()
        .toISOString()
        .replace(
          'T',
          ' ',
        )
        .replace(
          'Z',
          ' UTC',
        ),
    );


    /* =========================================================
       02 — VIDEO METADATA
    ========================================================= */

    section(
      'Video Metadata',
      '02',
    );


    const meta =
      analysis.metadata;


    keyValue(
      'Duration',
      duration(
        meta?.duration_seconds,
      ),
    );


    keyValue(
      'Resolution',
      `${safe(meta?.width)} × ${safe(meta?.height)}`,
    );


    keyValue(
      'Frame rate',
      meta?.fps == null
        ? '—'
        : `${Number(meta.fps).toFixed(2)} FPS`,
    );


    keyValue(
      'Codec',
      meta?.codec,
    );


    keyValue(
      'Audio',
      meta?.has_audio
        ? 'Present'
        : 'None detected',
    );


    /* =========================================================
       03 — AI DETECTION
    ========================================================= */

    section(
      'AI Detection Results',
      '03',
    );


    const events =
      analysis.events ??
      [];


    paragraph(
      `The backend returned ${events.length} low-level forensic event(s). The table below preserves the event records exposed by the analysis response.`,
    );


    const counts:
      Record<
        string,
        number
      > = {};


    events.forEach(
      (
        event,
      ) => {

        const type =
          safe(
            event.event_type,
            'UNKNOWN',
          );

        counts[type] =
          (
            counts[type] ??
            0
          ) + 1;
      },
    );


    table(
      [
        'Event type',
        'Count',
        'Share',
      ],
      Object.entries(
        counts,
      )
        .sort(
          (
            first,
            second,
          ) =>
            second[1] -
            first[1],
        )
        .map(
          (
            [
              type,
              count,
            ],
          ) => [
            label(type),
            String(count),
            `${
              (
                (
                  count /
                  Math.max(
                    events.length,
                    1,
                  )
                ) *
                100
              ).toFixed(1)
            }%`,
          ],
        ),
      [
        92,
        30,
        40,
      ],
    );


    if (
      events.length
    ) {

      table(
        [
          'Start',
          'End',
          'Event / object',
          'Confidence',
        ],
        events.map(
          (
            event,
          ) => [
            time(
              event.start_time,
            ),

            time(
              event.end_time,
            ),

            `${
              label(
                event.event_type,
              )
            }${
              event.object_type
                ? ` • ${safe(event.object_type)}`
                : ''
            }`,

            pct(
              event.confidence,
            ),
          ],
        ),
        [
          42,
          42,
          64,
          30,
        ],
      );

    } else {

      paragraph(
        'No low-level events were returned by the backend.',
        8.5,
        MUTED,
      );
    }


    /* =========================================================
       04 — FORENSIC RECONSTRUCTION
    ========================================================= */

    section(
      'AI Forensic Reconstruction',
      '04',
    );


    const summary =
      analysis
        .forensic_summary;


    if (
      summary
    ) {

      keyValue(
        'Headline',
        summary.headline,
      );


      paragraph(
        summary.summary,
      );


      keyValue(
        'Summary confidence',
        pct(
          summary.confidence,
        ),
      );


      keyValue(
        'Objects detected',
        (
          summary
            .objects_detected ??
          []
        ).join(', ') ||
          'None recorded',
      );


      if (
        (
          summary.key_events ??
          []
        ).length
      ) {

        paragraph(
          'Key forensic events:',
          8.5,
          GREEN,
        );


        summary.key_events.forEach(
          (
            item,
            index,
          ) => {

            paragraph(
              `${index + 1}. ${item}`,
              8,
            );
          },
        );
      }
    }


    const reconstructed =
      analysis
        .reconstructed_events ??
      [];


    if (
      reconstructed.length
    ) {

      table(
        [
          'Start',
          'End',
          'Activity',
          'Objects',
          'Confidence',
        ],

        reconstructed.map(
          (
            event,
          ) => [
            time(
              event.start_time,
            ),

            time(
              event.end_time,
            ),

            `${
              label(
                event.event_type,
              )
            } — ${
              safe(
                event.title,
              )
            }`,

            (
              event.objects ??
              []
            ).join(', ') ||
              '—',

            pct(
              event.confidence,
            ),
          ],
        ),

        [
          30,
          30,
          53,
          40,
          25,
        ],
      );

    } else {

      paragraph(
        'No higher-level forensic activities were reconstructed.',
        8.5,
        MUTED,
      );
    }


    /* =========================================================
       05 — INTEGRITY
    ========================================================= */

    section(
      'Video Integrity / Tampering Analysis',
      '05',
    );


    const integrity =
      (analysis
        .integrity_analysis as unknown) as
        | AnyRecord
        | undefined;


    if (
      integrity
    ) {

      const overall =
        safe(
          integrity.overall_status,
          'UNKNOWN',
        );


      setText(
        TEXT,
        9,
        true,
      );

      doc.text(
        'Overall integrity status',
        margin,
        y,
      );


      status(
        overall,
      );


      y += 11;


      keyValue(
        'Integrity score',
        pct(
          integrity.integrity_score,
        ),
      );


      keyValue(
        'Frames checked',
        integrity.frames_checked,
      );


      keyValue(
        'Timestamp gaps',
        integrity.timestamp_gaps,
      );


      keyValue(
        'Duplicate sequences',
        integrity.duplicate_sequences,
      );


      keyValue(
        'Corrupted frames',
        integrity.corrupted_frames,
      );


      keyValue(
        'FPS changes',
        integrity.fps_changes,
      );


      keyValue(
        'Resolution changes',
        integrity.resolution_changes,
      );


      keyValue(
        'Compression changes',
        integrity.compression_changes,
      );


      table(
        [
          'Check',
          'Result',
        ],
        [
          [
            'Timestamp continuity',
            safe(
              integrity.timestamp_continuity,
            ),
          ],

          [
            'Frame continuity',
            safe(
              integrity.frame_continuity,
            ),
          ],

          [
            'FPS consistency',
            safe(
              integrity.fps_consistency,
            ),
          ],

          [
            'Duplicate frames',
            safe(
              integrity.duplicate_frames,
            ),
          ],

          [
            'Metadata consistency',
            safe(
              integrity.metadata_consistency,
            ),
          ],

          [
            'Resolution consistency',
            safe(
              integrity.resolution_consistency,
            ),
          ],

          [
            'Compression consistency',
            safe(
              integrity.compression_consistency,
            ),
          ],
        ],
        [
          130,
          48,
        ],
      );


      const anomalies =
        Array.isArray(
          integrity.anomalies,
        )
          ? integrity.anomalies
          : [];


      if (
        anomalies.length
      ) {

        paragraph(
          'Recorded anomalies:',
          8.5,
          RED,
        );


        anomalies.forEach(
          (
            item,
            index,
          ) => {

            paragraph(
              `${index + 1}. ${safe(item)}`,
              8,
            );
          },
        );

      } else {

        paragraph(
          'No anomalies were returned by the integrity analysis.',
          8.5,
          GREEN,
        );
      }

    } else {

      paragraph(
        'Integrity analysis was not included in this analysis response.',
        8.5,
        MUTED,
      );
    }


    /* =========================================================
       06 — OBJECT DISAPPEARANCE
    ========================================================= */

    section(
      'Object Disappearance Analysis',
      '06',
    );


    const disappearance =
      (analysis
        .object_disappearance_analysis as unknown) as
        | AnyRecord
        | undefined;


    const disappearances =
      Array.isArray(
        disappearance
          ?.disappearances,
      )
        ? (
            disappearance
              ?.disappearances
          ) as AnyRecord[]
        : [];


    if (
      disappearance
    ) {

      keyValue(
        'Analysis available',
        disappearance.available,
      );


      keyValue(
        'Potential disappearances',
        disappearance.count,
      );


      if (
        disappearances.length
      ) {

        table(
          [
            'Camera',
            'Object',
            'First seen',
            'Last seen',
            'Disappearance',
            'Related activity',
          ],

          disappearances.map(
            (
              item,
            ) => [
              safe(
                item.camera_id,
              ),

              safe(
                item.object_type,
              ),

              time(
                item.first_seen,
              ),

              time(
                item.last_seen,
              ),

              time(
                item.disappearance_time,
              ),

              Array.isArray(
                item.related_activity,
              )
                ? item.related_activity.join(
                    '; ',
                  )
                : safe(
                    item.related_activity,
                  ),
            ],
          ),

          [
            22,
            25,
            28,
            28,
            32,
            43,
          ],
        );

      } else {

        paragraph(
          safe(
            disappearance.note,
            'No object disappearance events were returned.',
          ),
          8.5,
          MUTED,
        );
      }

    } else {

      paragraph(
        'Object disappearance analysis was not included in this analysis response.',
        8.5,
        MUTED,
      );
    }


    /* =========================================================
       07 — CERTIFICATION
    ========================================================= */

    section(
      'Forensic Certification & Interpretation',
      '07',
    );


    paragraph(
      'This dossier is a faithful presentation of the structured results returned by the TraceX video forensic analysis pipeline at export time. It does not independently validate the underlying video, detector model, timestamps, or investigative conclusions. Any evidentiary use should follow the applicable chain-of-custody, validation, and expert-review requirements.',
    );


    keyValue(
      'Evidence source',
      analysis.filename,
    );


    keyValue(
      'Analysis identifier',
      analysis.analysis_id,
    );


    keyValue(
      'Export timestamp',
      new Date().toISOString(),
    );


    keyValue(
      'Analytical status',
      analysis.status,
    );


    paragraph(
      'CERTIFICATION RECORD',
      8,
      GREEN,
    );


    paragraph(
      'The exported document is intended as a review and documentation artifact. Preserve the original evidence and the original backend analysis response alongside this dossier when maintaining an investigative record.',
    );


    /* =========================================================
       FINALIZE
    ========================================================= */

    footer();


    const base =
      safe(
        analysis.filename,
        'forensic-analysis',
      )
        .replace(
          /[^a-z0-9._-]+/gi,
          '_',
        )
        .replace(
          /\.[^.]+$/,
          '',
        );


    doc.save(
      `${base}_forensic_dossier.pdf`,
    );
  };