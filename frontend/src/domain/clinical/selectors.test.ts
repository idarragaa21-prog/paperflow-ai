import { describe, it, expect } from 'vitest';
import { deriveToc, slugify } from './selectors';

import { type ClinicalSheetDetail } from './types';

describe('slugify', () => {
  it('should handle empty or undefined strings', () => {
    expect(slugify('')).toBe('');
    expect(slugify(undefined as unknown as string)).toBe('');
    expect(slugify(null as unknown as string)).toBe('');
  });

  it('should lowercase and trim', () => {
    expect(slugify('  Hello World  ')).toBe('hello-world');
  });

  it('should remove non-alphanumeric characters except allowed ones', () => {
    expect(slugify('Hello @World!')).toBe('hello-world');
    expect(slugify('Test-Case_1')).toBe('test-case1');
  });

  it('should keep special characters like áéíóúüñ', () => {
    expect(slugify('Café niño über')).toBe('café-niño-über');
  });

  it('should replace spaces with hyphens', () => {
    expect(slugify('one two three')).toBe('one-two-three');
  });

  it('should truncate to 80 characters', () => {
    const longString = 'a'.repeat(100);
    expect(slugify(longString)).toBe('a'.repeat(80));
  });
});

describe('deriveToc', () => {
  it('should return an empty array if sheet is null', () => {
    expect(deriveToc(null)).toEqual([]);
  });

  it('should parse content_json sections for clinical_pro_v1 format', () => {
    const sheet: ClinicalSheetDetail = {
      id: '1',
      topic: 'Test',
      version: 1,
      is_current: true,
      format_version: 'clinical_pro_v1',
      content_markdown: '',
      content_json: {
        sections: [
          { id: 'sec1', title: 'Section 1' },
          { id: 'sec2', title: 'Section 2' }
        ]
      }
    };
    expect(deriveToc(sheet)).toEqual([
      { id: 'sec1', text: 'Section 1' },
      { id: 'sec2', text: 'Section 2' }
    ]);
  });

  it('should filter out invalid sections in clinical_pro_v1 format', () => {
    const sheet: ClinicalSheetDetail = {
      id: '1',
      topic: 'Test',
      version: 1,
      is_current: true,
      format_version: 'clinical_pro_v1',
      content_markdown: '',
      content_json: {
        sections: [
          { id: 'sec1', title: 'Section 1' },
          { id: 2, title: 'Section 2' }, // invalid id
          { id: 'sec3' }, // missing title
          null,
          undefined,
          { id: 'sec4', title: 'Section 4' }
        ]
      }
    };
    expect(deriveToc(sheet)).toEqual([
      { id: 'sec1', text: 'Section 1' },
      { id: 'sec4', text: 'Section 4' }
    ]);
  });

  it('should fallback to parsing content_markdown for non-clinical_pro_v1 format', () => {
    const sheet: ClinicalSheetDetail = {
      id: '1',
      topic: 'Test',
      version: 1,
      is_current: true,
      format_version: 'v1',
      content_markdown: '## Introduction\nSome text\n## Methods\nMore text\n### Ignored',
      content_json: {
        sections: [{ id: 'sec1', title: 'Section 1' }] // Should ignore this
      }
    };
    expect(deriveToc(sheet)).toEqual([
      { id: 'introduction', text: 'Introduction' },
      { id: 'methods', text: 'Methods' }
    ]);
  });

  it('should fallback to parsing content_markdown if sections are missing in clinical_pro_v1', () => {
    const sheet: ClinicalSheetDetail = {
      id: '1',
      topic: 'Test',
      version: 1,
      is_current: true,
      format_version: 'clinical_pro_v1',
      content_markdown: '## Background\nText',
      content_json: {} // missing sections
    };
    expect(deriveToc(sheet)).toEqual([
      { id: 'background', text: 'Background' }
    ]);
  });
});
