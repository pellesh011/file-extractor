export interface DigitStats {
  total: Record<string, number>;
  byFile: Record<string, Record<string, number>>;
}

export function calculateStats(
  overall: Record<string, number>,
  byFile: Record<string, Record<string, number>>
): DigitStats {
  // Ensure all digits 0-9 are present
  const total: Record<string, number> = {};
  const byFileResult: Record<string, Record<string, number>> = {};

  for (let i = 0; i <= 9; i++) {
    const d = i.toString();
    total[d] = overall[d] || 0;
  }

  for (const [filename, counts] of Object.entries(byFile)) {
    byFileResult[filename] = {};
    for (let i = 0; i <= 9; i++) {
      const d = i.toString();
      byFileResult[filename][d] = counts[d] || 0;
    }
  }

  return { total, byFile: byFileResult };
}

export function formatNumber(n: number): string {
  return n.toLocaleString('ru-RU');
}
