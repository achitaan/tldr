"""Render short source-focus regression scenes before a full lesson export."""
import json
import wave

from manim import tempconfig
from full_scene import EvidenceChapter, EVENTS, OUTPUT


def main():
    cases = [
        (37, (.33, .245, .04, .045), 'Receiving slave: same highlight in both views'),
        (38, (.75, .42, .04, .11), 'Selection remains valid until the ready change arrives'),
        (22, (.735, .50, .20, .05), 'Receiving master: preserve the data-valid interval'),
        (24, (.82, .50, .05, .05), 'Hold: stable after the receiving edge'),
        (35, (.365, .175, .10, .12), 'Read on the left: acknowledge, then release'),
        (13, (.15, .33, .75, .05), 'Address validity: retain the complete source label'),
        (13, (.515, .185, .035, .26), 'Negative edge: complete validity labels in the detail'),
        (13, (.52, .395, .33, .05), 'Returned data: original label remains readable'),
        (13, (.835, .185, .035, .26), 'Final positive edge: retain the full address label'),
    ]
    name = 'focus-proof'
    duration = len(cases) * 4
    EVENTS[name] = [(i, page, box, caption) for i, (page, box, caption) in enumerate(cases)]
    silence = OUTPUT / 'focus-proof.wav'
    with wave.open(str(silence), 'wb') as audio:
        audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(b'\0\0' * 24000 * duration)
    beat = {'id': name, 'title': 'Original evidence, aligned focus', 'audio': str(silence),
            'duration_seconds': duration, 'cues': [{'start_seconds': i * 4} for i in range(len(cases))]}
    with tempconfig({'pixel_width': 1920, 'pixel_height': 1080, 'frame_rate': 30,
                     'media_dir': str(OUTPUT / 'media-focus-proof'), 'output_file': name,
                     'disable_caching': True, 'write_to_movie': True, 'preview': False,
                     'verbosity': 'WARNING'}):
        scene = EvidenceChapter()
        scene.beat = beat
        scene.assets = json.loads((OUTPUT / 'assets.json').read_text())
        scene.render()
        import shutil
        shutil.copyfile(scene.renderer.file_writer.movie_file_path, OUTPUT / f'{name}.mp4')
    print(OUTPUT / f'{name}.mp4', flush=True)


if __name__ == '__main__':
    main()
