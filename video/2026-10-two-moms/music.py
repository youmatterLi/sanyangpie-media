"""Synthesize a warm, light lo-fi piano loop (original, royalty-free) -> WAV."""
import sys, wave
import numpy as np

SR = 44100
BPM = 92
BEAT = 60 / BPM
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
out = sys.argv[1]

n = int(SR * DUR)
mix = np.zeros((n, 2))

def midi(m): return 440 * 2 ** ((m - 69) / 12)

def piano(freq, length, vel=0.3):
    t = np.arange(int(SR * length)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 300))
    tone = (np.sin(2*np.pi*freq*t) + 0.45*np.sin(2*np.pi*2*freq*t)*np.exp(-t*3)
            + 0.18*np.sin(2*np.pi*3*freq*t)*np.exp(-t*5) + 0.06*np.sin(2*np.pi*4.01*freq*t)*np.exp(-t*8))
    # slight detune chorus for warmth
    tone += 0.3*np.sin(2*np.pi*freq*1.003*t)
    return tone * env * vel

def add(sig, start, pan=0.0):
    i = int(start * SR)
    if i >= n: return
    sig = sig[: n - i]
    mix[i:i+len(sig), 0] += sig * (1 - pan) / 2 * 2 ** 0.5
    mix[i:i+len(sig), 1] += sig * (1 + pan) / 2 * 2 ** 0.5

# I - V - vi - IV in F major (F, C, Dm, Bb), 2 bars each... 1 bar each, 4/4
chords = [[53, 57, 60, 64], [48, 55, 59, 62], [50, 57, 60, 65], [46, 53, 57, 62]]
bass = [41, 36, 38, 34]
melody = [  # (beat offset within 4-bar phrase, midi, length beats)
    (0, 72, 1.5), (1.5, 74, 0.5), (2, 76, 1), (3, 72, 1),
    (4, 71, 1.5), (5.5, 72, 0.5), (6, 74, 2),
    (8, 69, 1), (9, 72, 1), (10, 77, 1.5), (11.5, 76, 0.5),
    (12, 74, 1), (13, 72, 1), (14, 70, 1), (15, 72, 1),
]
bar = 4 * BEAT
t = 0.0; k = 0
while t < DUR:
    ch = chords[k % 4]
    # arpeggiated chord on 8ths
    for j in range(8):
        note = ch[[0, 1, 2, 3, 2, 1, 2, 3][j]]
        add(piano(midi(note), 1.6, 0.11), t + j * BEAT / 2, pan=-0.3 + 0.1 * (j % 3))
    add(piano(midi(bass[k % 4]), 3.0, 0.26), t, pan=0)
    add(piano(midi(bass[k % 4]), 2.0, 0.16), t + 2.5 * BEAT, pan=0)
    if k >= 1:  # melody enters on bar 2
        phrase_start = t - (k % 4) * bar
        for off, m, ln in melody:
            if (k % 4) * 4 <= off < (k % 4 + 1) * 4:
                add(piano(midi(m), ln * BEAT + 0.8, 0.17), phrase_start + off * BEAT, pan=0.25)
    # soft kick + shaker for gentle pulse
    for b in range(4):
        st = t + b * BEAT
        tt = np.arange(int(SR * 0.25)) / SR
        if b in (0, 2) and k >= 1:
            kick = np.sin(2*np.pi*(55 + 70*np.exp(-tt*30))*tt) * np.exp(-tt*14) * 0.28
            add(kick, st)
        sh = np.random.randn(int(SR*0.06)) * np.exp(-np.arange(int(SR*0.06))/SR*60) * 0.025
        add(sh, st + BEAT/2, pan=0.4)
    t += bar; k += 1

# simple reverb-ish echo
d = int(0.18 * SR)
wet = np.zeros_like(mix)
wet[d:] += mix[:-d] * 0.25
wet[2*d:] += mix[:-2*d] * 0.12
mix += wet

# fades
fi, fo = int(0.6*SR), int(2.5*SR)
mix[:fi] *= np.linspace(0, 1, fi)[:, None]
mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
mix /= np.abs(mix).max() / 0.85
pcm = (mix * 32767).astype(np.int16)
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out)
