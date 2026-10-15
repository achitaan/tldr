"""Render authored chapters serially, preserving validated completed chapters."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

import av
import psutil

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'artifacts/ece224-lesson'


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def validate(path,expected):
    with av.open(str(path)) as container:
        stream=container.streams.video[0]
        duration=container.duration/av.time_base
        if (stream.width,stream.height)!=(1920,1080) or float(stream.average_rate)!=30 or len(container.streams.audio)!=1 or abs(duration-expected)>.15:
            raise ValueError('Rendered chapter stream or duration mismatch.')
    return duration


def chapter_identity(beat,assets,digester=digest):
    identity={'beat':beat,'audio':digester(beat['audio']),
              'program':digester(Path(__file__).with_name('full_scene.py')),
              'math':digester(Path(__file__).with_name('timing_math.py')),
              'source_focus':digester(Path(__file__).with_name('source_focus.py')),
              'assets':{str(n):assets['pages'][str(n)] for n in beat['pages']}}
    # The shared renderer remains in every chapter key.  The ideal-only helper
    # is conditional so later state-only edits do not invalidate six unrelated
    # chapters.
    if beat['id']=='ideal':identity['ideal_motion']=digester(Path(__file__).with_name('ideal_read_motion.py'))
    return identity


def chapter_key(beat,assets,digester=digest):
    identity=chapter_identity(beat,assets,digester)
    return hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--only');args=parser.parse_args()
    narration=json.loads((OUTPUT/'audio/narration.json').read_text(encoding='utf-8'))
    assets=json.loads((OUTPUT/'assets.json').read_text(encoding='utf-8'))
    beats=[b for b in narration['beats'] if not args.only or b['id']==args.only]
    if not beats:raise ValueError('Unknown chapter.')
    finished=threading.Event();peak=[0]
    def monitor():
        root=psutil.Process()
        while not finished.is_set():
            total=0
            for proc in [root,*root.children(recursive=True)]:
                try:total+=proc.memory_info().rss
                except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            peak[0]=max(total,peak[0]);finished.wait(.2)
    watcher=threading.Thread(target=monitor,daemon=True);watcher.start()
    started=time.perf_counter();results=[]
    try:
        for beat in beats:
            name=beat['id'];path=OUTPUT/f'{name}.mp4';marker=OUTPUT/f'complete-{name}.json'
            key=chapter_key(beat,assets)
            cached=False
            try:
                saved=json.loads(marker.read_text())
                cached=saved['key']==key and saved['sha256']==digest(path)
                if cached:validate(path,beat['duration_seconds']+.15)
            except (OSError,ValueError,KeyError,TypeError,IndexError,av.FFmpegError):cached=False
            if not cached:
                progress={'status':'rendering','chapter':name,'completed':results}
                (OUTPUT/'render-progress.json').write_text(json.dumps(progress,indent=2))
                with (OUTPUT/f'render-{name}.log').open('w',encoding='utf-8') as log:
                    child=subprocess.Popen([sys.executable,str(Path(__file__).with_name('full_scene.py')),'--beat',name],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
                    try:
                        if child.wait(timeout=1800)!=0:raise RuntimeError(f'Chapter {name} failed; inspect its local render log.')
                    except BaseException:
                        if child.poll() is None:
                            if sys.platform=='win32':subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
                            else:child.terminate()
                        raise
                duration=validate(path,beat['duration_seconds']+.15)
                marker.write_text(json.dumps({'key':key,'sha256':digest(path),'duration_seconds':duration},indent=2))
            else:duration=validate(path,beat['duration_seconds']+.15)
            results.append({'id':name,'cached':cached,'duration_seconds':duration})
            print(json.dumps(results[-1]),flush=True)
    finally:
        finished.set();watcher.join()
    result={'status':'complete','chapters':results,'wall_seconds':time.perf_counter()-started,
            'peak_sampled_process_tree_rss_bytes':peak[0],'measurement_scope':'one functional observation; shared working sets may be counted more than once'}
    (OUTPUT/'render-progress.json').write_text(json.dumps(result,indent=2))
    (OUTPUT/('render-measurements-'+(args.only or 'all')+'.json')).write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
