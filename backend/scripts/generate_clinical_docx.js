#!/usr/bin/env node
/**
 * PaperFlow AI — Clinical Sheet Professional DOCX Generator
 *
 * Usage: node generate_clinical_docx.js <input.json> <output.docx>
 *
 * Input JSON shape:
 *   { topic, version, created_at, content_markdown, references_json, llm_model }
 */

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, BorderStyle, LevelFormat, Header, Footer,
  PageNumber, NumberFormat, UnderlineType, ShadingType,
  WidthType, TableRow, TableCell, Table, VerticalAlign,
} = require('docx');

// ── Args ──────────────────────────────────────────────────────────────────────
const [,, inputFile, outputFile] = process.argv;
if (!inputFile || !outputFile) {
  console.error('Usage: node generate_clinical_docx.js <input.json> <output.docx>');
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
const {
  topic = 'Clinical Sheet',
  version = 1,
  created_at,
  content_markdown = '',
  references_json = [],
  llm_model = '',
} = data;

// ── Colours ───────────────────────────────────────────────────────────────────
const C_PRIMARY   = '1E3A5F';   // navy
const C_ACCENT    = '2563EB';   // blue
const C_MUTED     = '6B7280';   // gray
const C_BORDER    = 'D1D5DB';
const C_LIGHT_BG  = 'EFF6FF';   // very light blue

// ── Page geometry (A4 with 2cm margins) ──────────────────────────────────────
const PAGE_W   = 11906;
const PAGE_H   = 16838;
const MARGIN   = 1134;  // ~2 cm in DXA
const CONTENT_W = PAGE_W - 2 * MARGIN;  // 9638 DXA

// ── Helper: parse markdown into docx Paragraphs ───────────────────────────────
function parseMarkdown(md) {
  const paragraphs = [];
  const lines = md.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // Heading 2
    if (/^## (.+)/.test(line)) {
      const text = line.replace(/^## /, '').trim();
      paragraphs.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 280, after: 100 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C_ACCENT, space: 2 } },
          children: [new TextRun({ text, color: C_PRIMARY, bold: true, size: 26, font: 'Calibri' })],
        })
      );
      i++; continue;
    }

    // Heading 3
    if (/^### (.+)/.test(line)) {
      const text = line.replace(/^### /, '').trim();
      paragraphs.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_3,
          spacing: { before: 200, after: 80 },
          children: [new TextRun({ text, color: C_PRIMARY, bold: true, size: 24, font: 'Calibri' })],
        })
      );
      i++; continue;
    }

    // Heading 4
    if (/^#### (.+)/.test(line)) {
      const text = line.replace(/^#### /, '').trim();
      paragraphs.push(
        new Paragraph({
          spacing: { before: 160, after: 60 },
          children: [new TextRun({ text, bold: true, size: 22, font: 'Calibri', color: C_MUTED })],
        })
      );
      i++; continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      paragraphs.push(
        new Paragraph({
          spacing: { before: 120, after: 120 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: C_BORDER, space: 1 } },
          children: [],
        })
      );
      i++; continue;
    }

    // Bullet list item
    if (/^[-*] (.+)/.test(line)) {
      const text = line.replace(/^[-*] /, '').trim();
      paragraphs.push(
        new Paragraph({
          numbering: { reference: 'bullets', level: 0 },
          spacing: { before: 40, after: 40 },
          children: inlineRuns(text),
        })
      );
      i++; continue;
    }

    // Numbered list item
    if (/^\d+\. (.+)/.test(line)) {
      const text = line.replace(/^\d+\. /, '').trim();
      paragraphs.push(
        new Paragraph({
          numbering: { reference: 'numbers', level: 0 },
          spacing: { before: 40, after: 40 },
          children: inlineRuns(text),
        })
      );
      i++; continue;
    }

    // Empty line
    if (!line.trim()) {
      paragraphs.push(new Paragraph({ children: [], spacing: { before: 60, after: 60 } }));
      i++; continue;
    }

    // Regular paragraph
    paragraphs.push(
      new Paragraph({
        spacing: { before: 80, after: 80 },
        children: inlineRuns(line),
      })
    );
    i++;
  }
  return paragraphs;
}

// Inline bold/italic/code handling
function inlineRuns(text) {
  const runs = [];
  // Split on **bold**, *italic*, `code`
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let m;
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) {
      runs.push(new TextRun({ text: text.slice(last, m.index), font: 'Calibri', size: 22 }));
    }
    if (m[2]) runs.push(new TextRun({ text: m[2], bold: true, font: 'Calibri', size: 22 }));
    else if (m[3]) runs.push(new TextRun({ text: m[3], italics: true, font: 'Calibri', size: 22 }));
    else if (m[4]) runs.push(new TextRun({ text: m[4], font: 'Courier New', size: 20, color: C_ACCENT }));
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    runs.push(new TextRun({ text: text.slice(last), font: 'Calibri', size: 22 }));
  }
  return runs.length ? runs : [new TextRun({ text, font: 'Calibri', size: 22 })];
}

// ── References table ──────────────────────────────────────────────────────────
function buildReferencesTable(refs) {
  if (!refs || !refs.length) return [];
  const border = { style: BorderStyle.SINGLE, size: 1, color: C_BORDER };
  const borders = { top: border, bottom: border, left: border, right: border };

  const header = new TableRow({
    tableHeader: true,
    children: [
      new TableCell({
        borders, width: { size: 600, type: WidthType.DXA },
        shading: { fill: C_PRIMARY, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: [new TextRun({ text: '#', bold: true, color: 'FFFFFF', size: 20, font: 'Calibri' })] })],
      }),
      new TableCell({
        borders, width: { size: CONTENT_W - 600, type: WidthType.DXA },
        shading: { fill: C_PRIMARY, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: [new TextRun({ text: 'Reference', bold: true, color: 'FFFFFF', size: 20, font: 'Calibri' })] })],
      }),
    ],
  });

  const rows = refs.slice(0, 60).map((ref, idx) => {
    const refText = typeof ref === 'string' ? ref : (ref.text || ref.citation || JSON.stringify(ref));
    const isEven = idx % 2 === 0;
    const fill = isEven ? 'FFFFFF' : C_LIGHT_BG;
    const cellBorders = { top: border, bottom: border, left: border, right: border };
    return new TableRow({
      children: [
        new TableCell({
          borders: cellBorders, width: { size: 600, type: WidthType.DXA },
          shading: { fill, type: ShadingType.CLEAR },
          margins: { top: 60, bottom: 60, left: 100, right: 100 },
          children: [new Paragraph({ children: [new TextRun({ text: String(idx + 1), size: 20, font: 'Calibri', color: C_ACCENT, bold: true })] })],
        }),
        new TableCell({
          borders: cellBorders, width: { size: CONTENT_W - 600, type: WidthType.DXA },
          shading: { fill, type: ShadingType.CLEAR },
          margins: { top: 60, bottom: 60, left: 100, right: 100 },
          children: [new Paragraph({ children: [new TextRun({ text: refText, size: 20, font: 'Calibri' })] })],
        }),
      ],
    });
  });

  return [
    new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 400, after: 160 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C_ACCENT, space: 2 } },
      children: [new TextRun({ text: 'References', color: C_PRIMARY, bold: true, size: 26, font: 'Calibri' })],
    }),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [600, CONTENT_W - 600],
      rows: [header, ...rows],
    }),
  ];
}

// ── Document metadata bar ─────────────────────────────────────────────────────
function metaBar() {
  const date = created_at
    ? new Date(created_at).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })
    : new Date().toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' });
  const modelLabel = llm_model ? ` · Model: ${llm_model}` : '';
  return new Paragraph({
    spacing: { before: 60, after: 280 },
    children: [
      new TextRun({ text: `PaperFlow AI · v${version} · ${date}${modelLabel}`, size: 18, color: C_MUTED, font: 'Calibri', italics: true }),
    ],
  });
}

// ── Build document ────────────────────────────────────────────────────────────
const contentParagraphs = parseMarkdown(content_markdown);
const refSection = buildReferencesTable(references_json);

const doc = new Document({
  numbering: {
    config: [
      {
        reference: 'bullets',
        levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
      },
      {
        reference: 'numbers',
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
      },
    ],
  },
  styles: {
    default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      {
        id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: 'Calibri', color: C_PRIMARY },
        paragraph: { spacing: { before: 0, after: 120 }, outlineLevel: 0 },
      },
      {
        id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: 'Calibri', color: C_PRIMARY },
        paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 },
      },
      {
        id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Calibri', color: C_PRIMARY },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: PAGE_H },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C_ACCENT, space: 2 } },
            spacing: { before: 0, after: 120 },
            children: [
              new TextRun({ text: 'PaperFlow AI', bold: true, size: 20, font: 'Calibri', color: C_ACCENT }),
              new TextRun({ text: `  ·  ${topic}`, size: 20, font: 'Calibri', color: C_MUTED }),
            ],
          }),
        ],
      }),
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            border: { top: { style: BorderStyle.SINGLE, size: 2, color: C_BORDER, space: 1 } },
            spacing: { before: 100, after: 0 },
            alignment: AlignmentType.RIGHT,
            children: [
              new TextRun({ text: 'Página ', size: 18, font: 'Calibri', color: C_MUTED }),
              new TextRun({ children: [PageNumber.CURRENT], size: 18, font: 'Calibri', color: C_MUTED }),
              new TextRun({ text: ' de ', size: 18, font: 'Calibri', color: C_MUTED }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, font: 'Calibri', color: C_MUTED }),
            ],
          }),
        ],
      }),
    },
    children: [
      // Cover title
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: topic, color: C_PRIMARY, bold: true, size: 36, font: 'Calibri' })],
      }),
      // Metadata bar
      metaBar(),
      // Body
      ...contentParagraphs,
      // References
      ...refSection,
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputFile, buffer);
  console.log(`OK:${outputFile}`);
}).catch(err => {
  console.error('ERROR:', err.message);
  process.exit(1);
});
