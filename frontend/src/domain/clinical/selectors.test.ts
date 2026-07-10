import { describe, it, expect } from 'vitest';
import { deriveToc, slugify } from './selectors';
import type { ClinicalSheetDetail } from './types';

describe('slugify', () => {
  it('converts text to lowercase', () => {
    expect(slugify('HEADING')).toBe('heading');
  });

  it('trims whitespace', () => {
    expect(slugify('  heading  ')).toBe('heading');
  });

  it('replaces spaces with hyphens', () => {
    expect(slugify('heading with spaces')).toBe('heading-with-spaces');
  });

  it('removes special characters but keeps alphanumeric, spaces, hyphens and some accents', () => {
    expect(slugify('heading! @#with $special% characters^')).toBe('heading-with-special-characters');
    expect(slugify('áéíóúüñ')).toBe('áéíóúüñ');
  });

  it('collapses multiple spaces into a single hyphen', () => {
    expect(slugify('heading   with   multiple    spaces')).toBe('heading-with-multiple-spaces');
  });

  it('truncates to 80 characters', () => {
    const longString = 'a'.repeat(100);
    expect(slugify(longString).length).toBe(80);
    expect(slugify(longString)).toBe('a'.repeat(80));
  });

  it('handles null or undefined gracefully', () => {
    expect(slugify(undefined as any)).toBe('');
    expect(slugify(null as any)).toBe('');
  });
});

describe('deriveToc', () => {
  it('returns empty array if sheet is null', () => {
    expect(deriveToc(null)).toEqual([]);
  });

  it('extracts TOC from sections when format_version is clinical_pro_v1', () => {
    const sheet: Partial<ClinicalSheetDetail> = {
      format_version: 'clinical_pro_v1',
      content_json: {
        sections: [
          { id: 'sec-1', title: 'Section 1' },
          { id: 'sec-2', title: 'Section 2' },
          { id: 123, title: 'Invalid ID' }, // Should be ignored
          { id: 'sec-3' }, // Should be ignored (no title)
          { title: 'No ID' }, // Should be ignored (no id)
          null, // Should be ignored
        ],
      },
    };

    expect(deriveToc(sheet as ClinicalSheetDetail)).toEqual([
      { id: 'sec-1', text: 'Section 1' },
      { id: 'sec-2', text: 'Section 2' },
    ]);
  });

  it('falls back to markdown extraction if format_version is clinical_pro_v1 but no valid sections', () => {
    const sheet: Partial<ClinicalSheetDetail> = {
      format_version: 'clinical_pro_v1',
      content_json: {}, // Missing sections
      content_markdown: '## Markdown Heading\nSome text\n## Another Heading',
    };

    expect(deriveToc(sheet as ClinicalSheetDetail)).toEqual([
      { id: 'markdown-heading', text: 'Markdown Heading' },
      { id: 'another-heading', text: 'Another Heading' },
    ]);
  });

  it('extracts TOC from markdown headers (## ) when format_version is not clinical_pro_v1', () => {
    const sheet: Partial<ClinicalSheetDetail> = {
      format_version: 'legacy_v1',
      content_markdown: [
        '# Main Title (Should be ignored)',
        '## First Heading',
        'Some paragraph text here.',
        '### Subheading (Should be ignored)',
        '## Second Heading',
        '##   Heading with extra spaces  ',
      ].join('\n'),
    };

    expect(deriveToc(sheet as ClinicalSheetDetail)).toEqual([
      { id: 'first-heading', text: 'First Heading' },
      { id: 'second-heading', text: 'Second Heading' },
      { id: 'heading-with-extra-spaces', text: 'Heading with extra spaces' },
    ]);
  });

  it('handles empty markdown content', () => {
    const sheet: Partial<ClinicalSheetDetail> = {
      format_version: 'legacy_v1',
      content_markdown: '',
    };

    expect(deriveToc(sheet as ClinicalSheetDetail)).toEqual([]);
  });

  it('handles undefined markdown content', () => {
    const sheet: Partial<ClinicalSheetDetail> = {
      format_version: 'legacy_v1',
    };

    expect(deriveToc(sheet as ClinicalSheetDetail)).toEqual([]);
  });
});
