/**
 * Tiny word-level diff for short rewrite comparisons.
 *
 * Tokenizes both strings into words + whitespace runs, computes the LCS,
 * then walks the matrix backwards to emit a sequence of `eq | del | add`
 * segments. Whitespace tokens are preserved so the rendered diff keeps
 * spacing intact.
 */

export type DiffSegment = { kind: "eq" | "del" | "add"; text: string };

function tokenize(s: string): string[] {
  if (!s) return [];
  return s.split(/(\s+)/).filter((t) => t.length > 0);
}

export function diffWords(a: string, b: string): DiffSegment[] {
  const A = tokenize(a);
  const B = tokenize(b);
  const m = A.length;
  const n = B.length;
  if (m === 0 && n === 0) return [];
  if (m === 0) return [{ kind: "add", text: b }];
  if (n === 0) return [{ kind: "del", text: a }];

  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (A[i] === B[j]) dp[i][j] = dp[i + 1][j + 1] + 1;
      else dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const out: DiffSegment[] = [];
  const push = (kind: DiffSegment["kind"], text: string) => {
    const last = out[out.length - 1];
    if (last && last.kind === kind) last.text += text;
    else out.push({ kind, text });
  };

  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (A[i] === B[j]) {
      push("eq", A[i]);
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      push("del", A[i]);
      i++;
    } else {
      push("add", B[j]);
      j++;
    }
  }
  while (i < m) {
    push("del", A[i]);
    i++;
  }
  while (j < n) {
    push("add", B[j]);
    j++;
  }
  return out;
}
