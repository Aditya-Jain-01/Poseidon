export function headTailCap(text, maxLines = 16) {
  const lines = String(text ?? '').split('\n');
  if (lines.length <= maxLines) return { head: lines.join('\n'), hidden: '', tail: '', hiddenCount: 0 };
  const headCount = Math.ceil(maxLines / 2);
  const tailCount = Math.floor(maxLines / 2);
  return {
    head: lines.slice(0, headCount).join('\n'),
    hidden: lines.slice(headCount, -tailCount).join('\n'),
    tail: lines.slice(-tailCount).join('\n'),
    hiddenCount: lines.length - maxLines,
  };
}
