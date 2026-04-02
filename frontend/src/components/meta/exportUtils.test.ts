import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { downloadBlob } from './exportUtils';

describe('downloadBlob', () => {
  const originalCreateObjectURL = window.URL.createObjectURL;
  const originalRevokeObjectURL = window.URL.revokeObjectURL;

  beforeEach(() => {
    window.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    window.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;
    vi.restoreAllMocks();
  });

  it('should create an anchor element, trigger download, and clean up', () => {
    const mockBlob = new Blob(['test content'], { type: 'text/plain' });
    const filename = 'test-file.txt';

    const originalCreateElement = document.createElement.bind(document);
    let createdAnchor: HTMLAnchorElement | null = null;
    let clickSpy: any;
    let removeSpy: any;

    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const el = originalCreateElement(tagName);
      if (tagName === 'a') {
        createdAnchor = el as HTMLAnchorElement;
        clickSpy = vi.spyOn(el, 'click');
        removeSpy = vi.spyOn(el, 'remove');
      }
      return el;
    });

    const appendChildSpy = vi.spyOn(document.body, 'appendChild');

    downloadBlob(mockBlob, filename);

    // Verify URL creation
    expect(window.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);

    // Verify anchor creation
    expect(createElementSpy).toHaveBeenCalledWith('a');
    expect(createdAnchor).not.toBeNull();

    // Check properties assigned to the anchor
    expect(createdAnchor!.href).toContain('blob:mock-url');
    expect(createdAnchor!.download).toBe(filename);

    // Verify DOM manipulation
    expect(appendChildSpy).toHaveBeenCalledWith(createdAnchor);

    // Verify interaction and cleanup
    expect(clickSpy).toHaveBeenCalled();
    expect(removeSpy).toHaveBeenCalled();
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });
});
