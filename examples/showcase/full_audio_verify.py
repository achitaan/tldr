"""Check decoded final narration against local WAVs, without a perceptual score."""
from pathlib import Path
import json
import wave

import av
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'artifacts/ece224-lesson'
RATE = 24000


def read_wav(path):
    with wave.open(str(path), 'rb') as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, RATE):
            raise ValueError('Expected mono PCM16 at 24 kHz.')
        return np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768


def best_match(audio, template, expected):
    start = max(0, round((expected - .3) * RATE))
    stop = round((expected + len(template) / RATE + .3) * RATE)
    search = audio[start:stop].astype(np.float64)
    template = template.astype(np.float64)
    template -= template.mean()
    energy = np.sum(template ** 2)
    if energy < 1e-6 or len(search) < len(template):
        raise ValueError('Insufficient voiced samples for alignment.')
    size = 1 << (len(search) + len(template) - 2).bit_length()
    convolution = np.fft.irfft(np.fft.rfft(search, size) * np.fft.rfft(template[::-1], size), size)
    count = len(template)
    sums = np.concatenate(([0.0], np.cumsum(search)))
    squares = np.concatenate(([0.0], np.cumsum(search ** 2)))
    local_energy = squares[count:] - squares[:-count] - (sums[count:] - sums[:-count]) ** 2 / count
    scores = convolution[count - 1:len(search)] / np.sqrt(np.maximum(local_energy * energy, 1e-20))
    index = int(np.argmax(scores))
    return {'offset_seconds': (start + index) / RATE - expected, 'correlation': float(scores[index])}


def main():
    manifest = json.loads((OUTPUT / 'assembled/manifest.preinstall.json').read_text())
    narration = json.loads((OUTPUT / 'audio/narration.json').read_text())
    resampler = av.AudioResampler(format='fltp', layout='mono', rate=RATE)
    # Preserve encoded timestamps: AAC chapters can contain intentional silent
    # gaps between packets. Concatenating decoded arrays would erase those gaps
    # and falsely report accumulating narration drift.
    audio = np.zeros(round((manifest['duration_seconds'] + 1) * RATE), dtype=np.float32)
    def place(frame):
        if frame.pts is None:
            raise ValueError('Decoded audio has no presentation timestamp.')
        start = round(float(frame.pts * frame.time_base) * RATE)
        samples = frame.to_ndarray().ravel()
        if start < 0 or start + len(samples) > len(audio):
            raise ValueError('Audio timestamp outside the final timeline.')
        audio[start:start + len(samples)] = samples
    with av.open(str(OUTPUT / 'assembled/lesson.mp4')) as movie:
        for frame in movie.decode(audio=0):
            for output in resampler.resample(frame):
                place(output)
        for output in resampler.resample(None):
            place(output)
    results = []
    for beat in narration['beats']:
        chapter = next(c for c in manifest['chapters'] if c['id'] == beat['id'])
        original = read_wav(beat['audio'])
        # Sample voiced narration near the start, middle and end of each chapter.
        for cue_index in (0, len(beat['cues']) // 2, len(beat['cues']) - 1):
            cue = beat['cues'][cue_index]
            at = cue['start_seconds'] + .2
            length = min(2, cue['end_seconds'] - at)
            if length < .5:
                raise ValueError('Narration cue too short for this verification sample.')
            template = original[round(at * RATE):round((at + length) * RATE)]
            result = {'chapter': beat['id'], 'cue_index': cue_index,
                      **best_match(audio, template, chapter['start_seconds'] + at)}
            if abs(result['offset_seconds']) > .12 or result['correlation'] < .9:
                raise ValueError(f'Final audio alignment failed: {result}')
            results.append(result)
    report = {'samples': results, 'maximum_absolute_offset_seconds': max(abs(r['offset_seconds']) for r in results),
              'minimum_correlation': min(r['correlation'] for r in results),
              'scope': '21 decoded audio samples against original narration; not human listening or a teaching-quality score'}
    (OUTPUT / 'audio-alignment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
