const specimen = document.getElementById("specimen");
if (specimen) {
  const pen = specimen.getContext("2d");
  // Sample a pear-shaped surface and shade it with a fixed stipple screen.
  for (let y = 0; y < 65; y++) {
    const t = y / 64;
    const radius = 23 * Math.pow(t, 0.8) * Math.sqrt(1 - t) * 2.5;
    for (let x = -Math.ceil(radius); x <= radius; x++) {
      if (radius === 0 || Math.abs(x) >= radius) continue;
      const nx = x / radius;
      const shade = Math.sqrt(1 - nx * nx) - 0.55 * nx - 0.65 * t;
      const grain = ((x * 37 + y * 67 + x * y * 3) & 31) / 120;
      pen.fillStyle =
        shade + grain > 1.04
          ? "#ff8972"
          : shade + grain > 0.66
            ? "#dc4834"
            : shade + grain > 0.28
              ? "#9e251f"
              : "#52241f";
      pen.fillRect(130 + x * 2, 18 + y * 2, 2, 2);
    }
  }
  pen.fillStyle = "#878579";
  for (const x of [13, 247])
    for (const y of [13, 157]) {
      pen.fillRect(x - 4, y, 9, 1);
      pen.fillRect(x, y - 4, 1, 9);
    }
}
