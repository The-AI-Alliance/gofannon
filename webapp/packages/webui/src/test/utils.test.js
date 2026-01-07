import { describe, it, expect } from 'vitest';

describe('Sample Utility Tests', () => {
  describe('String utilities', () => {
    it('should format strings correctly', () => {
      const input = 'hello world';
      const expected = 'Hello World';

      const titleCase = input.replace(/\b\w/g, (char) => char.toUpperCase());

      expect(titleCase).toBe(expected);
    });

    it('should handle empty strings', () => {
      const input = '';
      expect(input).toBe('');
    });
  });

  describe('Array utilities', () => {
    it('should filter falsy values', () => {
      const input = [1, null, 2, undefined, 3, false, 4, 0];
      const result = input.filter(Boolean);

      expect(result).toEqual([1, 2, 3, 4]);
    });

    it('should deduplicate arrays', () => {
      const input = [1, 2, 2, 3, 3, 3, 4];
      const result = [...new Set(input)];

      expect(result).toEqual([1, 2, 3, 4]);
    });
  });
});
