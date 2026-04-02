import { describe, expect, it } from 'vitest';
import { slugify } from '../selectors';

describe('slugify', () => {
  it('converts to lowercase and replaces spaces with dashes', () => {
    expect(slugify('Hello World')).toBe('hello-world');
  });

  it('removes special characters not in the whitelist', () => {
    expect(slugify('Hello @World!')).toBe('hello-world');
  });

  it('preserves accented characters in the whitelist', () => {
    expect(slugify('Niña con un camión áéíóúüñ')).toBe('niña-con-un-camión-áéíóúüñ');
  });

  it('handles empty or undefined-like strings gracefully', () => {
    expect(slugify('')).toBe('');
    expect(slugify(undefined as any)).toBe('');
    expect(slugify(null as any)).toBe('');
  });

  it('trims leading and trailing spaces', () => {
    expect(slugify('  hello world  ')).toBe('hello-world');
  });

  it('replaces multiple spaces with a single dash', () => {
    expect(slugify('hello    world')).toBe('hello-world');
  });

  it('truncates strings at 80 characters', () => {
    const longString = 'a'.repeat(100);
    expect(slugify(longString).length).toBe(80);
    expect(slugify(longString)).toBe('a'.repeat(80));
  });

  it('handles strings with numbers', () => {
    expect(slugify('Version 2.0 is great!')).toBe('version-20-is-great');
  });

  it('preserves existing dashes', () => {
    expect(slugify('already-has-dashes')).toBe('already-has-dashes');
  });
});
