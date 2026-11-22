"use strict";
(() => {
  const width = 128, height = 96;
  const axisX = [1024, 887, 512, 0, -512, -887, -1024, -887, -512, 0, 512, 887];
  const axisY = [0, 512, 887, 1024, 887, 512, 0, -512, -887, -1024, -887, -512];
  const spectrum = [0xff487a, 0xff842e, 0xffdb54, 0x65f679, 0x35dbe6, 0x5d8bff, 0xaf70ff, 0xff69cf];
  const trunc = Math.trunc;
  let glass;

  function mix(n) {
    n = Math.imul(n ^ n >>> 16, 0x7feb352d);
    n = Math.imul(n ^ n >>> 15, 0x846ca68b);
    return (n ^ n >>> 16) >>> 0;
  }

  function triangle(n) { return Math.abs((n & 15) - 8) - 4; }

  function split(seed) {
    const hitX = 38 + mix(seed) % 52, hitY = 23 + mix(seed + 1) % 42;
    const cells = new Uint8Array(width * height);
    const cuts = Array.from({length: 12}, (_, i) => {
      const hash = mix(seed + i + 11);
      return [7+(hash&7), 25+((hash>>>8)&15), 51+((hash>>>16)&31)];
    });
    for (let y = 0; y < height; ++y) {
      for (let x = 0; x < width; ++x) {
        const dx = x-hitX, dy = y-hitY;
        const u = dx + trunc(triangle(dy + trunc(dx/3))/2);
        const v = dy + trunc(triangle(dx - trunc(dy/2))/2);
        let wedge = 0, projection = u*axisX[0];
        for (let i = 1; i < 12; ++i) {
          const p = u*axisX[i]+v*axisY[i];
          if (p > projection) { wedge = i; projection = p; }
        }
        const radial = trunc(projection/1024) + trunc((v*axisX[wedge]-u*axisY[wedge])/4096);
        let band = 0;
        while (band < 3 && radial > cuts[wedge][band]) ++band;
        cells[y*width+x] = wedge*4+band;
      }
    }
    for (let i = 0; i < cells.length; ++i) {
      const id = cells[i];
      if ((i%width && (cells[i-1]&63) !== id) ||
          (i >= width && (cells[i-width]&63) !== id)) cells[i] |= 128;
      else if ((i%width !== width-1 && cells[i+1] !== id) ||
               (i < width*(height-1) && cells[i+width] !== id)) cells[i] |= 64;
    }
    return {seed, hitX, hitY, cells, fall: new Int32Array(48), slide: new Int32Array(48), lag: new Int32Array(48)};
  }

  function tint(data, p, rgb, alpha) {
    const keep = 256-alpha;
    data[p] = (data[p]*keep + (rgb>>>16)*alpha) >> 8;
    data[p+1] = (data[p+1]*keep + ((rgb>>>8)&255)*alpha) >> 8;
    data[p+2] = (data[p+2]*keep + (rgb&255)*alpha) >> 8;
    data[p+3] = 255;
  }

  function crack(data, ms, seed) {
    if (!glass || glass.seed !== seed) glass = split(seed);
    const {hitX, hitY, cells, fall, slide, lag} = glass;
    for (let i = 0; i < 48; ++i) {
      const hash = mix(seed+i+73);
      lag[i] = (hash&63)*4;
      const age = ms-(2400+(i%4)*790+(hash>>>8)%3000);
      fall[i] = age <= 0 ? 0 : trunc(age*age/38000);
      slide[i] = fall[i] ? trunc((((hash>>>24)&31)-15)*age/900) : 0;
    }
    for (let y = height-1; y >= 0; --y) {
      for (let x = 0; x < width; ++x) {
        const index = y*width+x, p = index*4, cell = cells[index], id = cell&63;
        if ((cell&192) || ms < 230) {
          const dx = Math.abs(x-hitX), dy = Math.abs(y-hitY);
          const radius = Math.max(dx,dy) + trunc(Math.min(dx,dy)/2);
          const arrival = radius*25+lag[id];
          if ((cell&192) && ms >= arrival) {
            if (cell&128) tint(data, p, 0x050914, 220);
            else tint(data, p, 0xc1e4f4, ms < arrival+210 ? 218 : 117);
          }
          if (ms < 230 && radius <= 5 && ms < 230-radius*30) tint(data, p, 0xffe6c9, 216);
        }
        if (!fall[id]) continue;
        const tx = x+slide[id], ty = y+fall[id];
        if (tx >= 0 && tx < width && ty < height) {
          const dst = (ty*width+tx)*4;
          data[dst] = data[p];
          data[dst+1] = data[p+1];
          data[dst+2] = data[p+2];
          data[dst+3] = 255;
        }
        data[p] = 2; data[p+1] = 3; data[p+2] = 8; data[p+3] = 255;
      }
    }
  }

  function dot(data, x, y, color, alpha) {
    if (x >= 0 && y >= 0 && x < width && y < height) tint(data, (y*width+x)*4, color, alpha);
  }

  function stars(data, ms, seed) {
    ms += 510;
    const last = trunc(ms/79);
    for (let shot = Math.max(0,last-17); shot <= last; ++shot) {
      const age = ms-shot*79;
      const hash = mix(seed+shot), path = mix(hash);
      const bx = 6+trunc((path&127)*115/127), by = 11+trunc(((path>>>8)&127)*74/127);
      const vx = 136+((hash>>>12)&63), vy = 59+((hash>>>20)&31);
      const flight = 325+((hash>>>4)&511), color = hash&7, remain = flight-age;
      const hx = bx+trunc(remain*vx/1000), hy = by-trunc(remain*vy/1000);
      if (remain >= 0) {
        const length = 21+((path>>>18)&15);
        for (let j = length; j >= 0; --j) {
          const x = hx+j, y = hy-trunc(j*vy/vx);
          const shade = spectrum[(color+trunc(j/6))&7], alpha = 32+trunc((length-j)*208/length);
          dot(data, x, y, shade, alpha);
          if (j < 20) dot(data, x, y+1, shade, trunc(alpha*3/4));
          if (j < 7) dot(data, x, y-1, shade, trunc(alpha/3));
        }
        dot(data, hx, hy, 0xfff8f2, 256);
        dot(data, hx-1, hy, 0xfff8f2, 192);
        dot(data, hx, hy+2, spectrum[color], 146);
        dot(data, hx, hy-1, 0xfff8f2, 168);
      } else if (remain > -425) {
        const burst = -remain;
        for (let k = 0; k < 6; ++k) {
          const ray = (k*2+(hash&1))%12;
          const reach = trunc(burst*(20+((path>>>(3*k))&15))/1000);
          const x = bx+trunc(axisX[ray]*reach/1024);
          const y = by+trunc(axisY[ray]*reach/1024)+trunc(burst*burst/32000);
          dot(data, x, y, spectrum[(color+k)&7], 220-trunc(burst/2));
        }
      }
    }
  }

  window.QyronScreenCues = {
    draw(ctx, type, elapsedMs, seed) {
      if ((type !== 1 && type !== 2) || elapsedMs < 0 || elapsedMs >= 10000) return;
      const image = ctx.getImageData(0, 0, width, height);
      if (type === 1) crack(image.data, trunc(elapsedMs), seed >>> 0);
      else stars(image.data, trunc(elapsedMs), seed >>> 0);
      ctx.putImageData(image, 0, 0);
    },
  };
})();
