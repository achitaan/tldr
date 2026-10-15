"""Short real-render inspection of the timing diagram's changing endpoints."""
import os
import sys
import shutil
from full_scene import EvidenceChapter,OUTPUT,BG,txt,tempconfig


class WindowProof(EvidenceChapter):
    def construct(self):
        self.camera.background_color=BG;self.window_parts={};self.window=None
        self.add(txt('A sampling edge has two sides',32).move_to([0,3.45,0]))
        for sentence in (2,3,4,5,7,8,9,10,11,12,13):
            self.show_window(sentence);self.wait(.2)
        self.wait(1)


if __name__=='__main__':
    with tempconfig({'pixel_width':1920,'pixel_height':1080,'frame_rate':30,'media_dir':str(OUTPUT/'window-proof-media'),'output_file':'window-proof','disable_caching':True,'preview':False,'verbosity':'WARNING'}):
        scene=WindowProof();scene.render();shutil.copyfile(scene.renderer.file_writer.movie_file_path,OUTPUT/'window-proof.mp4')
    if sys.platform=='win32':sys.stdout.flush();sys.stderr.flush();os._exit(0)
