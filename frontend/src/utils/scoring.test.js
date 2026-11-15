import { describe, it, expect } from 'vitest';
import { starsFromAccuracy, isPass } from './scoring';

describe('starsFromAccuracy', () => {
  it('awards 3 stars for >= 90', () => {
    expect(starsFromAccuracy(90)).toBe(3);
    expect(starsFromAccuracy(100)).toBe(3);
  });
  it('awards 2 stars for 70-89', () => {
    expect(starsFromAccuracy(70)).toBe(2);
    expect(starsFromAccuracy(89)).toBe(2);
  });
  it('awards 1 star for 50-69', () => {
    expect(starsFromAccuracy(50)).toBe(1);
    expect(starsFromAccuracy(69)).toBe(1);
  });
  it('awards 0 stars below 50', () => {
    expect(starsFromAccuracy(49)).toBe(0);
    expect(starsFromAccuracy(0)).toBe(0);
  });
  it('handles invalid input as 0', () => {
    expect(starsFromAccuracy(undefined)).toBe(0);
    expect(starsFromAccuracy(null)).toBe(0);
    expect(starsFromAccuracy('abc')).toBe(0);
  });
});

describe('isPass', () => {
  it('is true at or above 50', () => {
    expect(isPass(50)).toBe(true);
    expect(isPass(95)).toBe(true);
  });
  it('is false below 50', () => {
    expect(isPass(49)).toBe(false);
  });
});
