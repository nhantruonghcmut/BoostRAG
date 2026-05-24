import { describe, expect, it } from 'vitest';

import { cn } from '@/lib/utils/cn';

describe('cn()', () => {
  it('merges tailwind classes', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
  });

  it('handles falsy values', () => {
    expect(cn('text-sm', false, undefined, 'font-bold')).toBe('text-sm font-bold');
  });
});
