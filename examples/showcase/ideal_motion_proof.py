"""Render a short, silent proof of the authored ideal-read state transitions."""
from pathlib import Path
import json
import shutil

import av
from manim import tempconfig,UP,LEFT

from full_scene import BG,EVENTS,GOLD,MUTED,EvidenceChapter,txt


ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'artifacts/ece224-lesson'
MOVIE=OUTPUT/'ideal-motion-proof.mp4'
TIMING=OUTPUT/'ideal-motion-proof-timing.json'
SENTENCES=tuple(event[0] for event in EVENTS['ideal'])


class IdealMotionProof(EvidenceChapter):
    def construct(self):
        self.beat={'id':'ideal'}
        self.assets=json.loads((OUTPUT/'assets.json').read_text(encoding='utf-8'))
        self.camera.background_color=BG
        self.add(txt('Read the clock as a shared ruler',32).move_to([0,3.45,0]),
                 txt('TLDR / ECE224 STUDY · SILENT LAYOUT PROOF',13,MUTED).to_corner(UP+LEFT,buff=.2))
        self.image=None;self.page=None;self.guide=None;self.caption=None;self.source=None;self.window=None;self.detail=None;self.detail_key=None
        self.window_parts={};self.prediction_mode=None;self.detail_image=None;self.detail_roi=None
        self.ideal_parts={};self.ideal_state=None;self.ideal_motion_samples=[]
        samples=[]
        self.show_source(13)
        for sentence in SENTENCES:
            if self.caption:self.remove(self.caption)
            self.caption=txt(f'Sentence {sentence} state',21,GOLD if sentence in (13,14) else MUTED).move_to([0,-2.9,0])
            self.add(self.caption)
            self.show_ideal_read(sentence)
            samples.append({'sentence_index':sentence,'sample_seconds':float(self.time)+.25})
            self.wait(.6)
        TIMING.write_text(json.dumps({'duration_seconds':float(self.time),'samples':samples,
                                      'motion_samples':self.ideal_motion_samples},indent=2),encoding='utf-8')


def extract_frames():
    proof=json.loads(TIMING.read_text(encoding='utf-8'))
    with av.open(str(MOVIE)) as container:
        stream=container.streams.video[0]
        for sample in [*proof['samples'],*proof['motion_samples']]:
            target=sample['sample_seconds']
            container.seek(int(target/stream.time_base),stream=stream)
            for frame in container.decode(stream):
                if frame.time>=target:
                    name=sample.get('id',f's{sample["sentence_index"]}')
                    frame.to_image().save(OUTPUT/f'ideal-motion-proof-{name}.png')
                    break


def main():
    with tempconfig({'pixel_width':1280,'pixel_height':720,'frame_rate':30,
                     'media_dir':str(OUTPUT/'media-ideal-motion-proof'),
                     'output_file':'ideal-motion-proof','disable_caching':True,
                     'write_to_movie':True,'preview':False,'verbosity':'WARNING'}):
        scene=IdealMotionProof();scene.render()
        shutil.copyfile(scene.renderer.file_writer.movie_file_path,MOVIE)
    extract_frames()


if __name__=='__main__':main()
