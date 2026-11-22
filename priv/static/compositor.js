"use strict";
(() => {
  const width = 128, height = 96;
  const films = {
    intro: "/telethon.gif", crow: "/dr-crow.gif", beef: "/dr-beef.gif",
    peter: "/peter-thiel.gif", santa: "/santa.gif",
  };
  const cache = new Map();
  const lineIds = ["line1", "line2", "line3", "line4", "line5", "lineF"];
  const legacy = {gif: ["sd", ...lineIds], blood: ["chart"]};
  const colors = ["#fff", "#fff70e", "#c02336", "#0000ff", "#f00", "#fff"];
  const speeds = [10, 20, 40, 80, 120, 40];
  const mod = (n, m) => ((n % m) + m) % m;

  function surface(w, h) {
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    return canvas;
  }

  function unpackLzw(data, size, length) {
    const clear = 1 << size;
    const prefixes = new Uint16Array(4096), suffixes = new Uint8Array(4096);
    const stack = new Uint8Array(4097), result = new Uint8Array(length);
    let next = clear + 2, bits = size + 1, previous = -1, first = 0, bit = 0, written = 0;
    while (bit < data.length * 8 && written < length) {
      const at = bit >> 3;
      const word = data[at] | data[at + 1] << 8 | data[at + 2] << 16;
      const code = (word >>> (bit % 8)) & ((1 << bits) - 1);
      bit += bits;
      if (code === clear) {
        next = clear + 2;
        bits = size + 1;
        previous = -1;
        continue;
      }
      if (code === clear + 1) break;
      if (code > next || (code === next && previous < 0)) throw Error("Invalid GIF code");
      let cursor = code, count = 0;
      if (code === next) {
        stack[count++] = first;
        cursor = previous;
      }
      while (cursor >= clear) {
        stack[count++] = suffixes[cursor];
        cursor = prefixes[cursor];
      }
      first = cursor;
      result[written++] = first;
      while (count) result[written++] = stack[--count];
      if (previous >= 0 && next < 4096) {
        prefixes[next] = previous;
        suffixes[next++] = first;
        if (next === 1 << bits && bits < 12) bits++;
      }
      previous = code;
    }
    if (written !== length) throw Error("Incomplete GIF frame");
    return result;
  }

  async function loadFilm(path) {
    const response = await fetch(path);
    if (!response.ok) throw Error("Unable to load " + path);
    const data = new Uint8Array(await response.arrayBuffer());
    const word = p => data[p] | data[p + 1] << 8;
    let p = 13;
    function palette(flags) {
      if (!(flags & 128)) return null;
      const start = p;
      p += 3 * (2 << (flags & 7));
      return data.subarray(start, p);
    }
    function blocks() {
      const start = p;
      while (p < data.length && data[p]) p += data[p] + 1;
      if (p >= data.length) throw Error("Incomplete GIF blocks");
      const bytes = new Uint8Array(p - start);
      let pos = 0;
      for (let i = start; i < p; i += data[i] + 1) {
        bytes.set(data.subarray(i + 1, i + 1 + data[i]), pos);
        pos += data[i];
      }
      p++;
      return bytes.subarray(0, pos);
    }
    const w = word(6), h = word(8), global = palette(data[10]);
    if (!w || !h || w > width || h > height) throw Error("Invalid film size");
    const frames = [];
    let duration = 0, delay = 100, transparent = -1, disposal = 0;
    while (p < data.length) {
      const tag = data[p++];
      if (tag === 59) break;
      if (tag === 33) {
        const type = data[p++], extension = blocks();
        if (type === 249) {
          disposal = (extension[0] >> 2) & 7;
          transparent = extension[0] & 1 ? extension[3] : -1;
          delay = 10 * (extension[1] | extension[2] << 8) || 100;
        }
        continue;
      }
      if (tag !== 44) throw Error("Invalid GIF block");
      const x = word(p), y = word(p + 2), fw = word(p + 4), fh = word(p + 6);
      const flags = data[p + 8];
      p += 9;
      const table = palette(flags) || global, size = data[p++];
      duration += delay;
      frames.push({x, y, fw, fh, table, size, bytes: blocks(), interlaced: flags & 64,
        transparent, disposal, end: duration});
      transparent = -1;
      disposal = 0;
      delay = 100;
    }
    if (!frames.length) throw Error("Empty GIF");
    const columns = Math.min(16, frames.length);
    const atlas = surface(columns * w, Math.ceil(frames.length / columns) * h);
    const g = atlas.getContext("2d"), frame = g.createImageData(w, h);
    for (let i = 0; i < frames.length; i++) {
      const f = frames[i];
      const pixels = unpackLzw(f.bytes, f.size, f.fw * f.fh);
      const before = f.disposal === 3 && frame.data.slice();
      let source = 0;
      const passes = f.interlaced ? [[0, 8], [4, 8], [2, 4], [1, 2]] : [[0, 1]];
      for (const [start, step] of passes) {
        for (let row = start; row < f.fh; row += step) {
          let dest = 4 * ((row + f.y) * w + f.x);
          for (let col = 0; col < f.fw; col++, dest += 4) {
            const index = pixels[source++];
            if (index === f.transparent) continue;
            frame.data[dest] = f.table[3 * index];
            frame.data[dest + 1] = f.table[3 * index + 1];
            frame.data[dest + 2] = f.table[3 * index + 2];
            frame.data[dest + 3] = 255;
          }
        }
      }
      g.putImageData(frame, (i % columns) * w, Math.floor(i / columns) * h);
      if (f.disposal === 2) {
        for (let row = f.y; row < f.y + f.fh; row++) {
          const start = 4 * (row * w + f.x);
          frame.data.fill(0, start, start + f.fw * 4);
        }
      } else if (before) frame.data.set(before);
      if (i % 16 === 15) await new Promise(resolve => setTimeout(resolve, 0));
    }
    const ends = frames.map(frame => frame.end);
    return (ctx, elapsed) => {
      const phase = elapsed % duration;
      const i = ends.findIndex(end => phase < end);
      ctx.drawImage(atlas, i % columns * w, Math.floor(i / columns) * h, w, h,
        (width - w) / 2, (height - h) / 2, w, h);
    };
  }

  function film(key) {
    let entry = cache.get(key);
    if (!entry || Date.now() >= entry.retryAt) {
      entry = {draw: null, retryAt: Infinity};
      cache.set(key, entry);
      loadFilm(films[key]).then(draw => { entry.draw = draw; }, error => {
        console.warn(error);
        entry.retryAt = Date.now() + 10000;
      });
    }
    return entry;
  }

  const fonts = {
    small: {w: 5, h: 7, rows: atob("AAAAAAAAACAgICAAIABQUFAAAAAAAFD4UPhQAABwoHAocACAkCBAkBAAAECgQKBQACAgIAAAAAAgQEBAQCAAQCAgICBAAABQIHAgUAAAICD4ICAAAAAAADAgQAAAAPAAAAAAAAAAYGAAABAgQIAAACBQUFBQIAAgYCAgIHAAYJAQIEDwAPAQYBCQYAAgYKDwICAA8IDgEJBgAGCA4JCQYADwECAgQEAAYJBgkJBgAGCQkHAQYAAAYGAAYGAAAGBgAGBAgAAQIEAgEAAAAPAA8AAAAEAgECBAACBQECAAIABgkLCwgGAAYJCQ8JCQAOCQ4JCQ4ABgkICAkGAA4JCQkJDgAPCA4ICA8ADwgOCAgIAAYJCAsJBwAJCQ8JCQkABwICAgIHAAEBAQEJBgAJCgwMCgkACAgICAgPAAkPDwkJCQAJDQ0LCwkABgkJCQkGAA4JCQ4ICAAGCQkJDQYBDgkJDgoJAAYJBAIJBgAHAgICAgIACQkJCQkGAAkJCQkGBgAJCQkPDwkACQkGBgkJAAUFBQICAgAPAQIECA8ABwQEBAQHAAAIBAIBAAAHAQEBAQcAAgUAAAAAAAAAAAAADwAEAgAAAAAAAAAHCQsFAAgIDgkJDgAAAAYICAYAAQEHCQkHAAAABgsMBgACBQQOBAQAAAAHCQYIBwgIDgkJCQACAAYCAgcAAQABAQEFAggICgwKCQAGAgICAgcAAAAKDwkJAAAADgkJCQAAAAYJCQYAAAAOCQkOCAAABwkJBwEAAA4JCAgAAAAHDAMOAAQEDgQEAwAAAAkJCQcAAAAFBQUCAAAACQkPDwAAAAkGBgkAAAAJCQUCBAAADwIEDwABAgYCAgEAAgICAgICAAQCAwICBAAFCgAAAAAAA=")},
    large: {w: 8, h: 13, rows: atob("AAAAAAAAAAAAAAAAAAAAEBAQEBAQEAAQAAAAACQkJAAAAAAAAAAAAAAAJCR+JH4kJAAAAAAAEDxQUDgUFHgQAAAAACJSJAgIECQqRAAAAAAAADBISDBKRDoAAAAAEBAQAAAAAAAAAAAAAAQICBAQEAgIBAAAAAAgEBAICAgQECAAAAAAJBh+GCQAAAAAAAAAAAAAEBB8EBAAAAAAAAAAAAAAAAAAODBAAAAAAAAAAHwAAAAAAAAAAAAAAAAAAAAQOBAAAAACAgQIECBAgIAAAAAAGCRCQkJCQiQYAAAAABAwUBAQEBAQfAAAAAA8QkICBBggQH4AAAAAfgIECBwCAkI8AAAAAAQMFCRERH4EBAAAAAB+QEBcYgICQjwAAAAAHCBAQFxiQkI8AAAAAH4CBAgIEBAgIAAAAAA8QkJCPEJCQjwAAAAAPEJCRjoCAgQ4AAAAAAAAEDgQAAAQOBAAAAAAABA4EAAAODBAAAAAAgQIECAQCAQCAAAAAAAAAH4AAH4AAAAAAABAIBAIBAgQIEAAAAAAPEJCAgQICAAIAAAAADxCQk5SVkpAPAAAAAAYJEJCQn5CQkIAAAAAeERCRHhEQkR4AAAAADxCQEBAQEBCPAAAAAB4REJCQkJCRHgAAAAAfkBAQHhAQEB+AAAAAH5AQEB4QEBAQAAAAAA8QkBAQE5CRjoAAAAAQkJCQn5CQkJCAAAAAHwQEBAQEBAQfAAAAAAfBAQEBAQERDgAAAAAQkRIUGBQSERCAAAAAEBAQEBAQEBAfgAAAACCgsaqkpKCgoIAAAAAQkJiUkpGQkJCAAAAADxCQkJCQkJCPAAAAAB8QkJCfEBAQEAAAAAAPEJCQkJCUko8AgAAAHxCQkJ8UEhEQgAAAAA8QkBAPAICQjwAAAAA/hAQEBAQEBAQAAAAAEJCQkJCQkJCPAAAAACCgkRERCgoKBAAAAAAgoKCgpKSkqpEAAAAAIKCRCgQKESCggAAAACCgkQoEBAQEBAAAAAAfgIECBAgQEB+AAAAADwgICAgICAgPAAAAACAgEAgEAgEAgIAAAAAeAgICAgICAh4AAAAABAoRAAAAAAAAAAAAAAAAAAAAAAAAAD+AAAQCAAAAAAAAAAAAAAAAAAAADwCPkJGOgAAAABAQEBcYkJCYlwAAAAAAAAAPEJAQEI8AAAAAAICAjpGQkJGOgAAAAAAAAA8Qn5AQjwAAAAAHCIgIHwgICAgAAAAAAAAADpERDhAPEI8AABAQEBcYkJCQkIAAAAAABAAMBAQEBB8AAAAAAAEAAwEBAQEREQ4AABAQEBESHBIREIAAAAAMBAQEBAQEBB8AAAAAAAAAOySkpKSggAAAAAAAABcYkJCQkIAAAAAAAAAPEJCQkI8AAAAAAAAAFxiQmJcQEBAAAAAAAA6RkJGOgICAgAAAAAAXCIgICAgAAAAAAAAADxCMAxCPAAAAAAAICB8ICAgIhwAAAAAAAAAREREREQ6AAAAAAAAAERERCgoEAAAAAAAAACCgpKSqkQAAAAAAAAAQiQYGCRCAAAAAAAAAEJCQkY6AkI8AAAAAAB+BAgQIH4AAAAADhAQCDAIEBAOAAAAABAQEBAQEBAQEAAAAABwCAgQDBAICHAAAAAAJFRIAAAAAAAAAAA=")},
    side: {w: 6, h: 10, rows: atob("AAAAAAAAAAAAAAAgICAgIAAgAAAAUFBQAAAAAAAAAFBQ+FD4UFAAAAAgcKBwKHAgAAAASKhQIFCokAAAAECgoECokGgAAAAgICAAAAAAAAAAECBAQEAgEAAAAEAgEBAQIEAAAAAAiFD4UIgAAAAAACAg+CAgAAAAAAAAAAAAMCBAAAAAAAD4AAAAAAAAAAAAAAAgcCAAAAgIECBAgIAAAAAgUIiIiFAgAAAAIGCgICAg+AAAAHCICDBAgPgAAAD4CBAwCIhwAAAAEDBQkPgQEAAAAPiAsMgIiHAAAAAwQICwyIhwAAAA+AgQECBAQAAAAHCIiHCIiHAAAABwiJhoCBBgAAAAACBwIAAgcCAAAAAgcCAAMCBAAAAIECBAIBAIAAAAAAD4APgAAAAAAEAgEAgQIEAAAABwiBAgIAAgAAAAcIiYqLCAcAAAACBQiIj4iIgAAADwSEhwSEjwAAAAcIiAgICIcAAAAPBISEhISPAAAAD4gIDwgID4AAAA+ICA8ICAgAAAAHCIgICYiHAAAACIiIj4iIiIAAAAcCAgICAgcAAAADgQEBAQkGAAAACIkKDAoJCIAAAAgICAgICA+AAAAIiI2KiIiIgAAACIiMiomIiIAAAAcIiIiIiIcAAAAPCIiPCAgIAAAABwiIiIiKhwCAAA8IiI8KCQiAAAAHCIgHAIiHAAAAD4ICAgICAgAAAAiIiIiIiIcAAAAIiIiFBQUCAAAACIiIioqNiIAAAAiIhQIFCIiAAAAIiIUCAgICAAAAD4CBAgQID4AAAAcEBAQEBAcAAAAICAQCAQCAgAAABwEBAQEBBwAAAAIFCIAAAAAAAAAAAAAAAAAAD4ACAQAAAAAAAAAAAAAABwCHiIeAAAAICAsMiIyLAAAAAAAHCIgIhwAAAACAhomIiYaAAAAAAAcIj4gHAAAAAwSEDwQEBAAAAAAAB4iIh4CIhwAICAsMiIiIgAAAAgAGAgICBwAAAACAAYCAgISEgwAICAiJDgkIgAAABgICAgICBwAAAAAADQqKioiAAAAAAAsMiIiIgAAAAAAHCIiIhwAAAAAACwyIjIsICAAAAAaJiImGgICAAAALDIgICAAAAAAABwgHAI8AAAAEBA8EBASDAAAAAAAIiIiJhoAAAAAACIiFBQIAAAAAAAiIioqFAAAAAAAIhQIFCIAAAAAACIiJhoCIhwAAAA+BAgQPgAAAAYIBBgECAYAAAAICAgICAgIAAAAGAQIBggEGAAAABIqJAAAAAAAAA=")},
    normal: {w: 6, h: 11, rows: atob("AAAAAAAAAAAAAAAAICAgICAgACAAAABQUFAAAAAAAAAAAFBQ+FD4UFAAAAAAIHCooHAoqHAgAAAASKhQIFCokAAAAABgkKBAqJBoAAAAICAgAAAAAAAAAAAQICBAQEAgIBAAAEAgIBAQECAgQAAAAAAgqHCoIAAAAAAAACAg+CAgAAAAAAAAAAAAAGBgIEAAAAAAAPgAAAAAAAAAAAAAAABgYAAAAAgIEBAgIEBAgIAAAHCIiIiIiHAAAAAAIGCgICAgIAAAAABwiAgQIED4AAAAAHCICDAIiHAAAAAAEDBQkPgQEAAAAAD4gPAICIhwAAAAAHCA8IiIiHAAAAAA+AgQECAgIAAAAABwiIhwiIhwAAAAAHCIiHgICHAAAAAAAAAwMAAwMAAAAAAAAGBgAGBgIEAAAAgQIEAgEAgAAAAAAAD4APgAAAAAAABAIBAIECBAAAAAAHCICBAgACAAAAAAcIi4qLiAeAAAAHCIiPiIiIiIAAAA8IiI8IiIiPAAAABwiICAgICIcAAAAPCIiIiIiIjwAAAA+ICA8ICAgPgAAAD4gIDwgICAgAAAAHCIgLiIiIhwAAAAiIiI+IiIiIgAAABwICAgICAgcAAAAAgICAgIiIhwAAAAiJCgwKCQiIgAAACAgICAgICA+AAAAIjYqKiIiIiIAAAAiMjIqKiYmIgAAABwiIiIiIiIcAAAAPCIiPCAgICAAAAAcIiIiIiokGgIAADwiIjwkIiIiAAAAHCIgHAICIhwAAAA+CAgICAgICAAAACIiIiIiIiIcAAAAIiIiIhQUCAgAAAAiIiIqKioUFAAAACIiFAgUIiIiAAAAIiIUCAgICAgAAAA+AgQIECAgPgAAAA4ICAgICAgIDgAAEBAICAQEAgIBAQA4CAgICAgICDgAAAAIFCIAAAAAAAAAAAAAAAAAAAA/AAAQCAQAAAAAAAAAAAAAABwCHiIeAAAAICAgLDIiIjwAAAAAAAAeICAgHgAAAAICAh4iIiYaAAAAAAAAHCI+IB4AAAAMEBAcEBAQEAAAAAAAAB4iIiYaAhwAICAgLDIiIiIAAAAACAAYCAgIDAAAAAAIABgICAgICDAAICAgJCg4JCIAAAAYCAgICAgIBgAAAAAAADwqKioqAAAAAAAAPCIiIiIAAAAAAAAcIiIiHAAAAAAAACwyIiI8ICAAAAAAHiIiJhoCAgAAAAAsMiAgIAAAAAAAABwgHAI8AAAAEBAQPBAQEAwAAAAAAAAiIiImGgAAAAAAACIiFBQIAAAAAAAAIioqKhQAAAAAAAAiFAgUIgAAAAAAACIiIiYaAhwAAAAAPgQIED4AAAYICAgIMAgICAgGAAgICAgICAgICAAwCAgICAYICAgIMAAAAAAQKgQAAAAAA==")},
    bold: {w: 6, h: 11, rows: atob("AAAAAAAAAAAAAAAAADAwMDAwADAAAABsbGwAAAAAAAAAAABo/Gj8aAAAAAAAMHi0sHg0tHgwAAAASKhQIFCokAAAAABwyNBg1Mh0AAAAMDAwAAAAAAAAAAAYMDBgYGAwMBgAAGAwMBgYGDAwYAAAAAAwtHi0MAAAAAAAADAw/DAwAAAAAAAAAAAAAHBwMGAAAAAAAPgAAAAAAAAAAAAAAAA4OAAAAAwMGBgwMGBgwMAAAHDY2NjY2HAAAAAAMHCwMDAwMAAAAABw2BgwYMD4AAAAAHDYGDAY2HAAAAAAEDBwsPgwMAAAAAD4wPAYGNhwAAAAAHDA8NjY2HAAAAAA+BgwMGBgYAAAAABw2Nhw2NhwAAAAAHDY2HgYGHAAAAAAAABwcABwcAAAAAAAAHBwAHBwMGAAABgwYMBgMBgAAAAAAAD4APgAAAAAAABgMBgMGDBgAAAAAHCYGBAgACAAAAAAcMjY2NjAeAAAAHDY2PjY2NjYAAAA8NjY8NjY2PAAAABwyMDAwMDIcAAAAPDQ2NjY2NDwAAAA+MDA8MDAwPgAAAD4wMDwwMDAwAAAAHDIwNjIyMhwAAAA2NjY+NjY2NgAAAB4MDAwMDAweAAAABgYGBgY2NhwAAAAyNDgwODQyMgAAADAwMDAwMDA+AAAAIjY+PjY2NjYAAAAiMjI6Oj42MgAAABw2NjY2NjYcAAAAPDY2PDAwMDAAAAAcNjY2Nj42HgIAADw2Njw8NjY2AAAAHDIwHAYGJhwAAAA/DAwMDAwMDAAAADY2NjY2NjYcAAAANjY2PhwcHAgAAAA2NjY2Pj42FAAAADY2FAgUNjY2AAAANjY2HgwMDAwAAAA+Bg4cODAwPgAAAB4YGBgYGBgYHgAAMDAYGAwMBgYDAwA8DAwMDAwMDDwAAAAMHjMAAAAAAAAAAAAAAAAAAAA/AAAQGAwAAAAAAAAAAAAAABwGHjYeAAAAMDAwPDY2NjwAAAAAAAAeMDAwHgAAAAYGBh42NjYaAAAAAAAAHDY+MB4AAAAOGBgeGBgYGAAAAAAAAB42NjYeBhwAMDAwPDY2NjYAAAAADAAcDAwMDgAAAAAMABwMDAwMDDgAMDAwNDg4NDIAAAAcDAwMDAwMBgAAAAAAAD41NTU1AAAAAAAAPDIyMjIAAAAAAAAcNjY2HAAAAAAAACw2NjY8MDAAAAAAHjY2Nh4GBgAAAAAsNjAwMAAAAAAAABwwHAY8AAAADAwMHgwMDAYAAAAAAAA2NjY2GgAAAAAAADY2HBwIAAAAAAAANTU1NQoAAAAAAAAzHgweMwAAAAAAADY2NjYeBhwAAAAAPgYMGD4AAAYMDAwMOAwMDAwGAAwMDAwMDAwMDAAYDAwMDAcMDAwMGAAAAAAaLAAAAAAAA==")},
  };

  const glyphSheets = new Map();

  function lettering(g, font, color, text, x, y, span = width) {
    const key = font.w + "/" + font.h + "/" + (font === fonts.bold) + "/" + color;
    let sheet = glyphSheets.get(key);
    if (!sheet) {
      sheet = surface(font.w * 95, font.h);
      const ink = sheet.getContext("2d");
      ink.fillStyle = color;
      for (let glyph = 0; glyph < 95; glyph++) {
        for (let row = 0; row < font.h; row++) {
          const bits = font.rows.charCodeAt(glyph * font.h + row);
          for (let col = 0; col < font.w; col++) {
            if (bits & (128 >> col)) ink.fillRect(glyph * font.w + col, row, 1, 1);
          }
        }
      }
      if (glyphSheets.size >= 32) glyphSheets.delete(glyphSheets.keys().next().value);
      glyphSheets.set(key, sheet);
    }
    const first = Math.max(0, Math.floor(-x / font.w));
    for (let i = first; i < text.length && x + i * font.w < span; i++) {
      const code = text.charCodeAt(i);
      const glyph = code >= 32 && code <= 126 ? code - 32 : 31;
      g.drawImage(sheet, glyph * font.w, 0, font.w, font.h, x + i * font.w, y, font.w, font.h);
    }
  }

  function chart(g, scene) {
    g.fillStyle = "#050811";
    g.fillRect(0, 0, width, height);
    lettering(g, fonts.small, "#fe4455", "CROW BLOOD", 3, 1);
    const candles = scene.candles || [];
    if (!candles.length) {
      lettering(g, fonts.small, "#f8efc9", "AWAITING MARK", 3, 17);
      return;
    }
    lettering(g, fonts.large, "#f8efc9", ((scene.mark_cents || 0) / 100).toFixed(2), 3, 10);
    const low = Math.min(...candles.map(c => c.low)), high = Math.max(...candles.map(c => c.high));
    const y = price => high === low ? 51 : 73 - Math.floor((price - low) * 44 / (high - low));
    g.fillStyle = "#253b41";
    for (let row = 29; row <= 73; row += 11) g.fillRect(3, row, 122, 1);
    candles.forEach((c, i) => {
      const x = 122 - (candles.length - i - 1) * 5;
      g.fillStyle = c.close >= c.open ? "#4cf19c" : "#fe4455";
      g.fillRect(x, y(c.high), 1, y(c.low) - y(c.high) + 1);
      g.fillRect(x - 1, Math.min(y(c.open), y(c.close)), 3, Math.abs(y(c.open) - y(c.close)) + 1);
    });
    lettering(g, fonts.small, "#4cf19c", "BULL " + (scene.up || 0), 3, 78);
    lettering(g, fonts.small, "#fe4455", "BEAR " + (scene.down || 0), 66, 78);
  }

  const scrollFonts = [fonts.bold, fonts.normal, fonts.large, fonts.side, fonts.small, fonts.small];
  const scrollRows = [43, 19, 67, 91, 91, 1];
  function scroll(g, index, layer, travel) {
    if (!layer || !layer.text) return;
    g.save();
    const vertical = index === 3 || index === 4;
    const span = vertical ? height : width;
    if (vertical) {
      if (index === 3) g.translate(0, height);
      else g.translate(width, 0);
      g.rotate(index === 3 ? -Math.PI / 2 : Math.PI / 2);
    }
    const font = scrollFonts[index];
    const len = layer.text.length * font.w - 1;
    const cycle = span + len;
    const wrap = index === 0 || index === 3;
    const bounce = Math.abs(mod(travel, 2 * cycle) - cycle);
    let x = wrap ? span - mod(travel, cycle) : bounce - len;
    if (index === 2) x = span - bounce;
    if (layer.speed === 0) x = 0;
    lettering(g, font, colors[index], layer.text, Math.round(x), scrollRows[index], span);
    g.restore();
  }

  function ticker(g, quotes, elapsed) {
    if (!quotes || !quotes.length) return;
    const labels = quotes.map(q => q.symbol + " " + (q.price_cents / 100).toFixed(2));
    const advances = labels.map(label => label.length * 5 + 12);
    const period = advances.reduce((a, b) => a + b, 0);
    let x = Math.floor(mod(elapsed / 40, period)) - period;
    while (x < width) {
      labels.forEach((label, i) => {
        if (x + advances[i] > 0 && x < width) lettering(g, fonts.small, quotes[i].color, label, x, 88);
        x += advances[i];
      });
    }
  }

  function effects(g, melt, hue, now) {
    const frame = g.getImageData(0, 0, width, height), pixels = frame.data;
    const t = now % 60000 * (2 * Math.PI / 60000);
    for (let x = 0; x < width; x++) {
      const wave = 0.5 + 0.32 * Math.sin(x * 0.11 + t * 9) + 0.18 * Math.sin(x * 0.27 - t * 5);
      const drop = Math.floor(wave * wave * melt * 0.48);
      const angle = hue * 0.030 * Math.sin(x * 0.044 + t * 11);
      const cosine = Math.cos(angle);
      const a = Math.round((1 + 2 * cosine) * 256 / 3);
      const b = Math.round(((1 - cosine) / 3 - Math.sin(angle) / Math.sqrt(3)) * 256);
      const c = 256 - a - b;
      for (let y = height - 1; y >= 0; y--) {
        const dest = 4 * (y * width + x), src = dest - 4 * drop * width;
        const r = pixels[src] || 0, green = pixels[src + 1] || 0, blue = pixels[src + 2] || 0;
        pixels[dest] = (a * r + b * green + c * blue + 128) >> 8;
        pixels[dest + 1] = (c * r + a * green + b * blue + 128) >> 8;
        pixels[dest + 2] = (b * r + c * green + a * blue + 128) >> 8;
      }
    }
    g.putImageData(frame, 0, 0);
  }

  window.QyronCanvas = function (canvas) {
    canvas.width = width;
    canvas.height = height;
    const g = canvas.getContext("2d", {alpha: false, willReadFrequently: true});
    const started = new Map();
    const chartCanvas = surface(width, height);
    let scene, visible = [], layers = [], motion = [], request = 0, previousFrame = -Infinity;
    let destroyed = false;

    function render(now) {
      request = requestAnimationFrame(render);
      if (now - previousFrame < 32) return;
      previousFrame = now;
      g.fillStyle = "#000";
      g.fillRect(0, 0, width, height);
      for (const id of visible) {
        const elapsed = Math.max(0, now - started.get(id));
        if (id === "sd") {
          if (!scene.gif || scene.gif.playing !== false) {
            lettering(g, fonts.small, "#667480", "PANEL SD MEDIA", 29, 39);
            lettering(g, fonts.small, "#89959e", "HARDWARE ONLY", 32, 50);
          }
        } else if (id === "chart") {
          g.drawImage(chartCanvas, 0, 0);
        } else if (id === "ticker") {
          ticker(g, scene.tickers, elapsed);
        } else if (Object.prototype.hasOwnProperty.call(films, id)) {
          const entry = film(id);
          if (entry.draw) entry.draw(g, elapsed);
          else if (entry.retryAt !== Infinity)
            lettering(g, fonts.small, "#ff846e", "MEDIA UNAVAILABLE", 21, 44);
        } else {
          const index = lineIds.indexOf(id);
          if (index >= 0) {
            const m = motion[index];
            scroll(g, index, layers[index], m.distance + Math.max(0, now - m.since) * m.speed / 1000);
          }
        }
      }
      if (scene.melt || scene.hue) effects(g, scene.melt || 0, scene.hue || 0, now);
      if (scene.brightness != null && scene.brightness < 255) {
        g.fillStyle = "rgba(0,0,0," + (1 - scene.brightness / 255) + ")";
        g.fillRect(0, 0, width, height);
      }
    }

    return {
      update(nextScene) {
        if (destroyed) return;
        scene = nextScene;
        const now = performance.now();
        const widgets = scene.widgets || legacy[scene.mode] || [scene.mode];
        for (const id of started.keys()) if (!widgets.includes(id)) started.delete(id);
        for (const id of widgets) if (!started.has(id)) started.set(id, now);
        let first = 0;
        widgets.forEach((id, i) => {
          if (id === "sd" || id === "intro" || id === "chart") first = i;
        });
        visible = widgets.slice(first);
        if (visible.includes("chart")) chart(chartCanvas.getContext("2d"), scene);
        layers = lineIds.map((_, i) => (scene.layers || []).find(layer => layer.id === i + 1));
        motion = lineIds.map((id, i) => {
          const old = motion[i], layer = layers[i];
          const speed = layer && layer.speed != null ? layer.speed : speeds[i];
          const active = widgets.includes(id) && !!(layer && layer.text);
          const distance = active && old && old.active && old.speed && speed
            ? old.distance + (now - old.since) * old.speed / 1000 : 0;
          return {active, distance, speed, since: now};
        });
        if (!request) render(now);
      },
      destroy() {
        destroyed = true;
        cancelAnimationFrame(request);
      },
    };
  };
})();
