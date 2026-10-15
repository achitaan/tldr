"""Local, cached sentence narration. Run using artifacts/voice/.venv Python.

The two model files come from the documented kokoro-onnx model-files-v1.1
release. No text or course material is sent over a network by this program.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import time
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / 'artifacts/voice/models'
OUTPUT = ROOT / 'artifacts/showcase/opening'
MODEL_HASHES = {'kokoro-v1.0.onnx':'beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a', 'voices-v1.0.bin':'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d'}


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): value.update(chunk)
    return value.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script',type=Path,default=Path(__file__).with_name('opening.json'))
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    output=args.output.resolve()
    for name, expected in MODEL_HASHES.items():
        if not (MODELS/name).is_file() or digest(MODELS/name) != expected:
            raise ValueError(f'Install the documented and pinned model first: {name}')
    script=json.loads(args.script.read_text(encoding='utf-8'))
    output.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'artifacts/voice/sentence-cache'
    cache.mkdir(parents=True,exist_ok=True)
    voice='am_michael'
    speed=.96
    model=None
    beats=[]
    start=time.perf_counter()
    for beat in script['beats']:
        pieces=[]
        cues=[]
        offset=0.
        sentences=re.findall(r'\S.*?(?:[.!?](?=\s|$)|$)',beat['text'])
        pauses={p['after_sentence']:p.get('dwell_seconds',3) for p in beat.get('practice',[])}
        if any(not isinstance(i,int) or isinstance(i,bool) or not 0<=i<len(sentences) or not isinstance(v,(int,float)) or not 1<=v<=5 for i,v in pauses.items()):
            raise ValueError('Practice dwell requires an existing sentence and 1–5 seconds')
        for sentence_index,text in enumerate(sentences):
            text=text.strip()
            key=hashlib.sha256(json.dumps({'text':text,'voice':voice,'speed':speed,'models':MODEL_HASHES,'format':1},sort_keys=True).encode()).hexdigest()
            file=cache/(key+'.wav')
            if not file.exists():
                model=model or Kokoro(str(MODELS/'kokoro-v1.0.onnx'),str(MODELS/'voices-v1.0.bin'))
                audio,rate=model.create(text,voice=voice,speed=speed,lang='en-us')
                if rate != 24000 or not np.isfinite(audio).all() or len(audio)<2400:
                    raise ValueError('Invalid local speech output')
                sf.write(file,audio,rate,subtype='PCM_16')
            audio,rate=sf.read(file,dtype='float32')
            duration=len(audio)/rate
            pieces.append(audio)
            cues.append({'start_seconds':offset,'end_seconds':offset+duration,'text':text})
            offset+=duration
            if sentence_index in pauses:
                pause=np.zeros(round(24000*pauses[sentence_index]),dtype='float32')
                pieces.append(pause);offset+=len(pause)/24000
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',beat['id']):
            raise ValueError('Narration beat requires a safe identifier')
        path=output/(beat['id']+'.wav')
        sf.write(path,np.concatenate(pieces),24000,subtype='PCM_16')
        beats.append(beat|{'audio':str(path),'duration_seconds':offset,'cues':cues})
        print(json.dumps({'beat':beat['id'],'seconds':offset}),flush=True)
    result=script|{'beats':beats,'voice':voice,'engine':'Kokoro ONNX 0.6.1 (local)','alignment':'independently synthesized sentence boundaries','model_hashes':MODEL_HASHES,'narration_wall_seconds':time.perf_counter()-start}
    (output/'narration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Narration ready.',flush=True)


if __name__=='__main__': main()
