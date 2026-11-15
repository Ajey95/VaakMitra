/**
 * Shared scoring helpers used across the therapy flow (Slide5_Rewards,
 * dashboards, reports). Keeping this in one place avoids the star-threshold
 * logic drifting between components.
 */

/** Map an accuracy percentage (0-100) to a star rating (0-3). */
export function starsFromAccuracy(accuracy) {
  const a = Number(accuracy) || 0;
  if (a >= 90) return 3;
  if (a >= 70) return 2;
  if (a >= 50) return 1;
  return 0;
}

/** Whether a session counts as a "pass" (earns at least one star). */
export function isPass(accuracy) {
  return starsFromAccuracy(accuracy) >= 1;
}
