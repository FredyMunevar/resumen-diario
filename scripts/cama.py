# genera una cama musical suave (pad lo-fi) de N segundos: python3 cama.py salida.wav segundos
import sys, numpy as np, soundfile as sf
out, dur = sys.argv[1], float(sys.argv[2]); sr = 44100
n = lambda m: 440 * 2 ** ((m - 69) / 12)
acordes = [[48,55,59,64],[45,52,55,60],[41,48,52,57],[43,50,55,59]]  # Cmaj7 Am7 Fmaj7 G
seg = 4.0; t = np.arange(int(sr*seg)) / sr
env = np.minimum(1, t/1.2) * np.minimum(1, (seg - t)/1.0)
bloques = []
for i in range(int(np.ceil(dur/seg))):
    c = acordes[i % 4]; x = np.zeros_like(t)
    for m in c:
        f = n(m); x += 0.6*np.sin(2*np.pi*f*t) + 0.25*np.sin(2*np.pi*2*f*t + 0.3) + 0.1*np.sin(2*np.pi*f*1.003*t)
    bajo = 0.5*np.sin(2*np.pi*n(c[0]-12)*t) * np.exp(-t*0.6)
    bloques.append((x*env + bajo) )
y = np.concatenate(bloques)[:int(sr*dur)]
y = y / np.max(np.abs(y)) * 0.5
sf.write(out, np.stack([y, np.roll(y, 300)], 1), sr)
