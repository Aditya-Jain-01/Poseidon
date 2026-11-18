import React from 'react';

const pixels = [];
const columns = 75;
const rows = 45;
const size = 16;

for (let row = 0; row < rows; row += 1) {
  for (let column = 0; column < columns; column += 1) {
    const noise = (column * 37 + row * 61 + column * row * 17) % 23;
    const openCenter = column > 17 && column < 58 && row > 1;
    const top = row < 7 && !openCenter && noise < 20 - row * 2;
    const edge = row < 31 && (column < 7 || column > 67) && noise < 13 - Math.min(column, columns - column - 1);
    const foot = row > 40 && noise < (row - 40) * 3 && (column < 20 || column > 53);

    if (top || edge || foot) {
      pixels.push({
        x: column * size,
        y: row * size,
        variant: (column + row * 3) % 5 === 0 ? 'soft' : 'bright',
      });
    }
  }
}

export default function PixelField() {
  return (
    <svg className="hero-pixel-field" viewBox="0 0 1200 720" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
      <defs>
        <pattern id="hero-pixel-dither" width="4" height="4" patternUnits="userSpaceOnUse">
          <rect width="2" height="2" fill="#08a4fb" />
        </pattern>
      </defs>
      {pixels.map((pixel) => (
        <rect key={`${pixel.x}-${pixel.y}`} x={pixel.x} y={pixel.y} width={size} height={size} className={`hero-pixel-${pixel.variant}`} />
      ))}
    </svg>
  );
}
