"""The sound card's clock on the tests' clock (clock.py), so that a piece of music of thirty-five seconds is over in
nine: the page's AudioContext tells a time K times the card's, what the game schedules by that time is put back on
the card's, and every sound is decoded K times as fast (the same samples at K times their rate), its length told as
it was. To audio.js nothing has changed: a piece lasts what it lasts, a fade takes what it takes, by its own clock.
Nobody listens: a headless browser plays to no one."""

SHIM = """(() => { const K = %s; if (K === 1 || window.__soundPace) return; window.__soundPace = K;
  const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
  const base = Object.getPrototypeOf(AC.prototype), get = (o, k) => Object.getOwnPropertyDescriptor(o, k);
  const now = get(base, 'currentTime').get;
  Object.defineProperty(base, 'currentTime', {configurable: true, get() { return now.call(this) * K; }});
  const fast = new WeakSet(), len = get(AudioBuffer.prototype, 'duration').get;
  Object.defineProperty(AudioBuffer.prototype, 'duration', {configurable: true, get() { return len.call(this) * (fast.has(this) ? K : 1); }});
  const quick = (ctx, b) => { const q = ctx.createBuffer(b.numberOfChannels, b.length, Math.min(768000, b.sampleRate * K));
    for (let c = 0; c < b.numberOfChannels; c++) q.copyToChannel(b.getChannelData(c), c); fast.add(q); return q; };
  const decode = base.decodeAudioData;
  base.decodeAudioData = function (data, ok, bad) { const p = decode.call(this, data).then((b) => quick(this, b)); if (ok || bad) p.then(ok, bad); return p; };
  const start = AudioBufferSourceNode.prototype.start;
  AudioBufferSourceNode.prototype.start = function (when, offset, duration) { const f = this.buffer && fast.has(this.buffer) ? K : 1;
    return duration !== undefined ? start.call(this, (when || 0) / K, (offset || 0) / f, duration / f) : start.call(this, (when || 0) / K, (offset || 0) / f); };
  const begin = AudioScheduledSourceNode.prototype.start;
  AudioScheduledSourceNode.prototype.start = function (when) { return begin.call(this, (when || 0) / K); };
  const stop = AudioScheduledSourceNode.prototype.stop;
  AudioScheduledSourceNode.prototype.stop = function (when) { return stop.call(this, (when || 0) / K); };
  const A = AudioParam.prototype, at = (name, ...times) => { const f = A[name]; if (!f) return;
    A[name] = function (...a) { for (const i of times) if (typeof a[i] === 'number') a[i] /= K; return f.apply(this, a); }; };
  at('setValueAtTime', 1); at('linearRampToValueAtTime', 1); at('exponentialRampToValueAtTime', 1); at('setTargetAtTime', 1, 2);
  at('setValueCurveAtTime', 1, 2); at('cancelScheduledValues', 0); at('cancelAndHoldAtTime', 0); })()"""
