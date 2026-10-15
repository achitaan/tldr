"""Prepare local original-source crops for the explicitly supplied ECE224 sample.

Only IDs and generated lesson code are tracked. Source pixels, local paths and
page/region snapshots are written into ignored artifacts, never the public demo.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'artifacts/ece224-lesson'
sys.path.insert(0,str(ROOT/'backend/tldr_backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','tldr_backend.settings')

SOURCE_DIGEST='b795febff84591aff468b4b6c14a8e67e5829f1f8b645f7ffc2f19d599098687'
CROPS={5:(.02,.21,.92,.34),13:(.045,.17,.89,.31),
       19:(.005,.175,.99,.61),22:(.005,.175,.99,.61),24:(.005,.175,.99,.61),
       34:(.005,.17,.99,.34),35:(.005,.17,.99,.34),
       37:(.005,.16,.99,.59),38:(.005,.16,.99,.59),40:(.005,.16,.99,.79)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--course',type=int,default=8)
    parser.add_argument('--source',type=int,default=12)
    args=parser.parse_args()
    import django
    django.setup()
    from study.models import Source,Region
    from study.retrieval import bind_source_assets,resolve_revision_assets
    source=Source.objects.get(pk=args.source,course_id=args.course,status='ready')
    if source.digest!=SOURCE_DIGEST:
        raise ValueError('The source must be the inspected ECE224 Part Va PDF; refuse a different document.')
    if not source.original or hashlib.sha256(Path(source.original.path).read_bytes()).hexdigest()!=SOURCE_DIGEST:
        raise ValueError('The original PDF differs from the inspected document.')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    entries={}
    citations=[]
    objects=[]
    for number,bounds in CROPS.items():
        page=source.pages.get(number=number)
        crop=dict(zip(('x','y','width','height'),bounds))
        region,_=Region.objects.get_or_create(page=page,label=f'TLDR bus lesson — diagram, page {number}',**crop,defaults={'text':'','confirmed':False})
        ref=f'r{region.id}'
        citations.append({'page_id':page.id,'region_id':region.id,'source_id':source.id,
                          'source_title':source.title,'page_number':number,'quote':'','visual':True})
        objects.append({'id':f'source-{number}','kind':'source_image','label':f'Original ECE224 Part Va, page {number}','source_ref':ref})
        entries[str(number)]={'page_id':page.id,'region_id':region.id,'ref':ref,'crop':crop}
    citations=bind_source_assets(citations,args.course)
    fake=SimpleNamespace(lesson=SimpleNamespace(course_id=args.course),citations=citations,
                         spec={'chapters':[{'scenes':[{'objects':objects}]}]})
    assets=resolve_revision_assets(fake)
    for number,entry in entries.items():
        asset=assets[entry['ref']]
        path=OUTPUT/f'source-{number}.png'
        path.write_bytes(asset['content'])
        entry.update(path=str(path),sha256=asset['sha256'],width=asset['width'],height=asset['height'])
    manifest={'course_id':args.course,'source_id':source.id,'source_digest':source.digest,'pages':entries,'citations':citations}
    (OUTPUT/'assets.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'pages':len(entries),'course_id':args.course,'source_id':source.id,'originals_modified':False}))


if __name__=='__main__':main()
