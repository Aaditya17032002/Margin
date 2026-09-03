// Dev-only helper: converts the brand hex palette to OKLCH for the token sheet.
const srgbToLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);

function hexToOklch(hex) {
  const m = hex.replace("#", "");
  const r = srgbToLinear(parseInt(m.slice(0, 2), 16) / 255);
  const g = srgbToLinear(parseInt(m.slice(2, 4), 16) / 255);
  const b = srgbToLinear(parseInt(m.slice(4, 6), 16) / 255);

  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const mm = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);

  const L = 0.2104542553 * l + 0.793617785 * mm - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * mm + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * mm - 0.808675766 * s;

  const C = Math.sqrt(A * A + B * B);
  let H = (Math.atan2(B, A) * 180) / Math.PI;
  if (H < 0) H += 360;

  return `oklch(${(L * 100).toFixed(2)}% ${C.toFixed(4)} ${H.toFixed(2)})`;
}

const palette = {
  paper: "#F6F2E9",
  "paper-raised": "#FCFAF4",
  "paper-sunk": "#EFEADD",
  line: "#E4DCCB",
  "line-strong": "#D6CBB3",
  ink: "#211D17",
  "ink-soft": "#5B5347",
  "ink-faint": "#8A8072",
  patina: "#2F6F63",
  "patina-hover": "#275C52",
  "patina-tint": "#E7F0EC",
  seal: "#9B2D28",
  "seal-tint": "#F3E2DF",
  ochre: "#B4791E",
  "ochre-tint": "#F6ECD6",
  leaf: "#3F7D53",
  "leaf-tint": "#E7F0E3",
  slate: "#3F5C8C",
  "slate-tint": "#E4E9F2",
};

for (const [name, hex] of Object.entries(palette)) {
  console.log(`--${name}: ${hexToOklch(hex)}; /* ${hex} */`);
}
