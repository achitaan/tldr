"""Trusted, authored source-preserving choreography for one lesson chapter.

No model-generated program is loaded. All crop coordinates refer to inspected
original source pages; numerical interval diagrams come from timing_math.py.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import numpy as np
from PIL import Image

from manim import (Scene,Text,ImageMobject,Rectangle,Line,Dot,Arrow,VGroup,Group,
                   FadeIn,FadeOut,Create,Transform,Circumscribe,Indicate,
                   tempconfig,UP,DOWN,LEFT,RIGHT,WHITE,linear)
from timing_math import timing_window
from source_focus import box_in_view
from ideal_read_motion import EDGE_X,ideal_context_objects,ideal_read_state

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'artifacts/ece224-lesson'
BLUE='#68B9EF';GREEN='#75D6B0';GOLD='#F3CD78';RED='#EE8D86';MUTED='#91A2AF';BG='#101820'


def txt(value,size=24,color=WHITE,width=12):
    result=Text(str(value),font='Arial',font_size=size,color=color,disable_ligatures=True)
    if result.width>width:result.scale_to_fit_width(width)
    return result


# Sentence indices are tied to the reviewed narration text. Boxes use full-page
# normalized coordinates, not post-zoom guesses. A missing box clears the guide.
EVENTS={
 'ownership':[(0,5,None,'One shared bus'),(2,5,(.115,.46,.79,.036),'Address: master → selected slave'),
 (3,5,(.435,.325,.44,.04),'Each slave decodes the address'),(4,5,None,'Connected does not mean driving'),
 (5,5,(.115,.515,.79,.035),'Read: selected slave → master'),
 (6,5,None,'Reverse the transfer, preserve the wiring'),(7,5,(.115,.515,.79,.035),'Write: master → selected slave'),
 (9,5,(.115,.415,.79,.033),'Control can travel in either direction'),
 (10,5,(.737,.23,.15,.135),'DMA interface: role depends on the transfer'),
 (12,5,(.14,.23,.12,.135),'One master already won arbitration'),
 (14,5,None,'PAUSE · Who drives address? Who drives data?'),
 (15,5,None,'READ · Master: address | selected slave: data')],
 'ideal':[(0,13,None,'Original course model · ideal synchronous read'),
 (2,13,(.20,.175,.66,.30),'One shared time axis'),(3,13,(.194,.185,.035,.205),'1 · Master sets address and R/W'),
 (4,13,(.15,.25,.75,.05),'R/W = 1 means read in this diagram'),
 (5,13,(.15,.33,.75,.05),'Valid address is not yet returned data'),
 (6,13,(.515,.185,.035,.26),'2 · Negative edge'),(7,13,(.52,.395,.33,.05),'Slave supplies the data'),
 (8,13,(.835,.185,.035,.26),'3 · Next positive edge'),
 (9,13,(.835,.395,.035,.055),'Master stores the data'),
 (10,13,(.15,.33,.75,.115),'Bands represent multiple wires'),
 (11,13,(.54,.395,.29,.05),'Valid describes timing, not a bit pattern'),
 (13,13,None,'PAUSE · Which edge completes this read?'),
 (14,13,(.835,.185,.035,.26),'Storage occurs at the final positive edge')],
 'propagation':[(0,19,None,'M = master endpoint · S = slave endpoint'),
 (2,19,(.145,.37,.84,.112),'Compare the two address rows'),
 (3,19,(.21,.37,.04,.06),'Stable at M first'),(4,19,(.325,.43,.035,.055),'Stable at S later'),
 (6,19,(.21,.37,.15,.112),'Transition is not a stable value'),
 (8,22,None,'Now follow the return path'),(9,22,(.44,.60,.20,.12),'Register selection → access'),
 (10,22,(.59,.665,.24,.05),'Internal Data Valid at the slave'),
 (11,22,(.62,.50,.22,.105),'Driver + bus delay still remain'),
 (12,22,(.625,.55,.20,.06),'Valid at S'),(13,22,(.735,.50,.20,.05),'Sampling uses the receiving M endpoint'),
 (15,22,(.40,.725,.44,.055),'Follow every stage of the path'),
 (16,22,(.735,.50,.20,.05),'PAUSE · Locate the receiving endpoint')],
 'window':[(0,22,(.79,.50,.05,.05),'Setup: stable BEFORE the edge'),
 (1,24,(.82,.50,.05,.05),'Hold: stable AFTER the edge'),
 (2,None,None,'Original calculated example · times in ns'),
 (3,None,None,'Sample at 10 · setup 2 · hold 1'),(4,None,None,'Required stable interval: [8, 11] ns'),
 (5,None,None,'Actual stable interval: [6, 12] ns'),(6,None,None,'Compare both intervals on the same scale'),
 (7,None,None,'Setup margin = 8 − 6 = 2 ns'),(8,None,None,'Hold margin = 12 − 11 = 1 ns'),
 (9,None,None,'PASS · both boundaries are contained'),
 (10,None,None,'Move arrival to 8.5 ns'),(11,None,None,'FAIL setup · margin −0.5 ns'),
 (12,None,None,'Restore arrival; move next change to 10.5 ns'),
 (13,None,None,'FAIL hold · margin −0.5 ns'),(14,None,None,'Two boundaries. Two independent checks.')],
 'handshake':[(0,34,None,'Fully interlocked asynchronous read'),
 (2,34,(.145,.175,.34,.31),'Follow ONLY the read on the left'),
 (3,34,(.20,.175,.025,.245),'1 · Master requests'),
 (4,34,(.285,.235,.025,.24),'2 · Slave supplies data + ready'),
 (5,34,(.365,.175,.025,.245),'3 · Master stores, then acknowledges'),
 (6,34,(.445,.235,.025,.24),'4 · Slave releases'),
 (7,35,(.145,.175,.34,.31),'Original causal arrows · left-hand read'),
 (8,35,(.205,.175,.265,.125),'Each ready transition permits the next'),
 (9,35,(.365,.175,.10,.12),'Returning inactive completes the agreement'),
 (10,35,(.60,.175,.34,.31),'The second transaction is a WRITE'),
 (11,35,(.145,.175,.34,.31),'Return to the READ on the left'),
 (12,35,(.365,.175,.10,.12),'PAUSE · What permits the slave to release?'),
 (13,35,(.365,.175,.10,.12),'Master-Ready falls → slave observes → release'),
 (15,35,None,'No shared clock ≠ no physical timing constraints')],
 'async-delays':[(0,37,None,'Asynchronous edges also propagate'),
 (1,37,(.005,.18,.975,.115),'Master-Ready at M and at S'),
 (2,37,(.005,.48,.975,.05),'Address leaves M; check its arrival at S'),
 (3,37,(.33,.245,.04,.045),'Guard ordering at the receiving slave'),
 (5,38,None,'Follow the reply toward the master'),
 (6,38,(.005,.305,.975,.05),'Slave-Ready must reach M'),
 (7,38,None,'Wait for stable received data, then store'),
 (8,38,(.73,.18,.035,.05),'After storing: Master-Ready falls'),
 (9,38,(.75,.42,.04,.11),'Preserve selection until the ready change arrives'),
 (11,40,(.70,.74,.28,.075),'Receiving-side hold still applies'),
 (12,40,(.17,.84,.69,.095),'Hold uses EARLIEST change · minimum delays'),
 (14,40,None,'One endpoint · one causal path · original evidence')],
 'predict':[(0,None,None,'Three predictions · pause before revealing'),
 (1,None,None,'Address 16 · data wires show 19'),
 (2,None,None,'Is 19 already the accepted answer?'),
 (3,None,None,'PAUSE · Give a reason'),(4,None,None,'No · present is not necessarily ready'),
 (5,None,None,'Sample 10 · setup 2 · hold 1 ns'),
 (6,None,None,'Actual [7, 11.5] · does it cover [8, 11]?'),
 (7,None,None,'Yes · both boundaries are contained'),
 (8,None,None,'Setup margin 1 ns · hold margin 0.5 ns'),
 (9,35,(.365,.175,.10,.12),'Master stored data and lowered Master-Ready. Next?'),
 (10,35,(.365,.175,.10,.12),'Slave observes → lowers Slave-Ready → releases'),
 (12,None,None,'Pause · select evidence · ask with context'),
 (14,None,None,'WHERE · WHO · WHEN')],
}


class EvidenceChapter(Scene):
    def construct(self):
        beat=self.beat
        self.camera.background_color=BG
        title=txt(beat['title'],32).move_to([0,3.45,0])
        self.add(title,txt('TLDR / ECE224 STUDY',13,MUTED).to_corner(UP+LEFT,buff=.2))
        self.image=None;self.page=None;self.guide=None;self.caption=None;self.source=None;self.window=None;self.detail=None;self.detail_key=None
        self.window_parts={};self.prediction_mode=None;self.detail_image=None;self.detail_roi=None
        self.ideal_parts={};self.ideal_state=None;self.ideal_motion_samples=[]
        self.events=[];self.intervals=[]
        self.add_sound(beat['audio'],gain=-1)
        for i,(sentence,page,box,label) in enumerate(EVENTS[beat['id']]):
            target=beat['cues'][sentence]['start_seconds']
            if self.time<target:self.wait(target-self.time)
            if abs(self.time-target)>.08:raise ValueError(f'Missed cue {beat["id"]}/{sentence}')
            start=float(self.time)
            self.events.append({'sentence_index':sentence,'cue_seconds':target,'visual_seconds':start,'label':label,'page':page})
            if self.caption:self.remove(self.caption)
            self.caption=txt(label,23,GOLD if 'PAUSE' in label or '?' in label else WHITE).move_to([0,-2.9,0])
            self.add(self.caption)
            if self.guide:self.remove(self.guide);self.guide=None
            if page is not None:
                self.show_source(page)
                if beat['id']=='ideal':
                    self.show_ideal_read(sentence)
                elif box:
                    self.show_detail(page,sentence)
                    self.guide=self.source_box(page,box)
                    self.play(Create(self.guide),run_time=.45)
                elif self.detail:
                    self.remove(self.detail);self.detail=None;self.detail_key=None
                    self.detail_image=None;self.detail_roi=None
                    self.play(self.image.animate.restore(),run_time=.55)
            else:
                self.clear_source()
                if beat['id']=='window':self.show_window(sentence)
                elif beat['id']=='predict':self.show_prediction(sentence)
            interval={'id':f'{beat["id"]}-{i}','sentence_index':sentence,
                      'start_seconds':start,'page':page,'label':label}
            if beat['id']=='ideal':interval['objects']=ideal_context_objects(ideal_read_state(sentence))
            self.intervals.append(interval)
        end=beat['duration_seconds']+.15
        if self.time<end:self.wait(end-self.time)
        for i,event in enumerate(self.intervals):
            event['end_seconds']=self.intervals[i+1]['start_seconds'] if i+1<len(self.intervals) else float(self.time)
        (OUTPUT/f'{beat["id"]}-timing.json').write_text(json.dumps({'duration_seconds':float(self.time),'events':self.events,'scenes':self.intervals},indent=2),encoding='utf-8')

    def clear_source(self):
        if self.detail:self.remove(self.detail);self.detail=None;self.detail_key=None
        self.detail_image=None;self.detail_roi=None
        if self.image:self.remove(self.image);self.image=None;self.page=None
        if self.source:self.remove(self.source);self.source=None

    def show_source(self,page):
        if self.page==page:return
        self.clear_source()
        if self.window:self.remove(self.window);self.window=None
        asset=self.assets['pages'][str(page)]
        path=Path(asset['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=asset['sha256']:raise ValueError('Source snapshot changed.')
        self.image=ImageMobject(str(path))
        self.image.scale_to_fit_width(11.2 if self.beat['id']=='ideal' else 12.5)
        if self.image.height>4.95:self.image.scale_to_fit_height(4.95)
        self.image.move_to([0,-1.15 if self.beat['id']=='ideal' else .15,0])
        self.image.save_state()
        self.page=page
        self.source=txt(f'ORIGINAL ECE224 · Part Va · page {page} · diagram crop · overlays separate',14,MUTED).move_to([0,-3.35,0])
        self.play(FadeIn(self.image),run_time=.35)
        self.add(self.source)

    def ideal_cursor(self,edge):
        """Place a separate reading cursor over an unchanged source image."""
        asset=self.assets['pages']['13'];crop=asset['crop']
        x=(EDGE_X[edge]-crop['x'])/crop['width']
        if not 0<=x<=1:raise ValueError('Ideal-read cursor is outside the reviewed source crop.')
        px=self.image.get_left()[0]+self.image.width*x
        line=Line([px,self.image.get_bottom()[1],0],[px,self.image.get_top()[1],0],color=GOLD,stroke_width=4)
        return VGroup(line)

    def show_ideal_read(self,sentence):
        """Keep one logical read connected to the three original clock edges."""
        state=ideal_read_state(sentence)
        parts=self.ideal_parts
        if not parts:
            cpu_box=Rectangle(width=2.35,height=1.25,color=BLUE,stroke_width=2).move_to([-4.1,1.65,0])
            memory_box=Rectangle(width=2.65,height=1.25,color=GREEN,stroke_width=2).move_to([4.1,1.65,0])
            register=txt(str(state['register_value']),31,MUTED).move_to(cpu_box.get_center()+DOWN*.2)
            row=txt('16  →  42',29,GREEN).move_to(memory_box.get_center()+DOWN*.2)
            selection=Rectangle(width=2.35,height=.55,color=MUTED,stroke_width=2).move_to(row)
            address=Arrow([-2.85,1.88,0],[2.72,1.88,0],buff=0,color=MUTED,stroke_width=2.5,max_tip_length_to_length_ratio=.045)
            returned=Arrow([2.72,1.42,0],[-2.85,1.42,0],buff=0,color=MUTED,stroke_width=2.5,max_tip_length_to_length_ratio=.045)
            address_label=txt('address 16',18,MUTED).move_to([0,2.18,0])
            return_label=txt('not yet valid',18,MUTED).move_to([0,1.12,0])
            status=txt('Prior MDR value 19 · new read example',18,MUTED,width=8).move_to([0,.78,0])
            footer=txt('ORIGINAL LOGICAL ILLUSTRATION · values 16 / 19 / 42 · ordering only, not an analog delay simulation',12,MUTED,width=11.5).move_to([0,.47,0])
            model=VGroup(cpu_box,memory_box,txt('Master / MDR',18,BLUE).move_to(cpu_box.get_center()+UP*.35),
                         txt('Memory',18,GREEN).move_to(memory_box.get_center()+UP*.35),register,row,selection,
                         address,returned,address_label,return_label,status,footer)
            parts.update(model=model,register=register,selection=selection,address=address,returned=returned,
                         address_label=address_label,return_label=return_label,status=status,cursor=None,result=None)
            self.play(FadeIn(model,shift=UP*.12),run_time=.5)
        previous=self.ideal_state or ideal_read_state(0)
        animations=[]
        address_color=BLUE if state['address_selected'] else MUTED
        return_color=GREEN if state['returned_data_available'] else MUTED
        if state['address_selected']!=previous['address_selected']:
            animations.extend([parts['address'].animate.set_color(address_color),parts['address_label'].animate.set_color(address_color),parts['selection'].animate.set_color(address_color)])
        if state['returned_data_available']!=previous['returned_data_available']:
            animations.append(parts['returned'].animate.set_color(return_color))
            next_return=txt('data 42' if state['returned_data_available'] else 'not yet valid',18,return_color).move_to(parts['return_label'])
            animations.append(Transform(parts['return_label'],next_return))
        if state['register_value']!=previous['register_value']:
            next_register=txt(str(state['register_value']),31,GOLD if state['storage_visible'] else MUTED).move_to(parts['register'])
            animations.append(Transform(parts['register'],next_register))
        status_text={
            'prior_register_example':'Prior MDR value 19 · new read example',
            'address_selected':'Address 16 selects the illustrated row · MDR remains 19',
            'address_valid_data_pending':'Selection is not completion · MDR remains 19',
            'slave_response_edge':'Edge 2 · follow the slave response',
            'returned_data_available':'42 is available on the return path · MDR remains 19',
            'edge_three_before_storage':'At edge 3 · watch the receiving register',
            'stored':'The master stores 42 in its MDR',
            'prediction_replay':'PREDICT · Which edge completes the read?',
            'answer_revealed':'Edge 3 · the master stores 42 in its MDR',
        }[state['phase']]
        if state['phase']!=previous['phase']:
            animations.append(Transform(parts['status'],txt(status_text,18,GOLD if state['answer_hidden'] or state['storage_visible'] else MUTED,width=8).move_to(parts['status'])))
        if animations:self.play(*animations,run_time=.4)

        if state['address_token_motion']:
            token=txt('16',23,BLUE).move_to(parts['address'].get_start())
            self.add(token)
            self.ideal_motion_samples.append({'id':'address-motion','sentence_index':sentence,'sample_seconds':float(self.time)+.45})
            self.play(token.animate.move_to(parts['address'].get_end()),run_time=.9,rate_func=linear)
            self.play(FadeOut(token),run_time=.15)
        if state['return_token_motion']:
            token=txt('42',23,GREEN).move_to(parts['returned'].get_start())
            self.add(token)
            self.ideal_motion_samples.append({'id':'return-motion','sentence_index':sentence,'sample_seconds':float(self.time)+.45})
            self.play(token.animate.move_to(parts['returned'].get_end()),run_time=.9,rate_func=linear)
            self.play(FadeOut(token),run_time=.15)

        edge=state['cursor_edge']
        prior_edge=previous['cursor_edge']
        if edge!=prior_edge:
            if edge is None and parts['cursor'] is not None:
                self.play(FadeOut(parts['cursor']),run_time=.25);parts['cursor']=None
            elif edge is not None:
                next_cursor=self.ideal_cursor(edge)
                if parts['cursor'] is None:
                    parts['cursor']=next_cursor;self.play(FadeIn(next_cursor),run_time=.3)
                else:self.play(Transform(parts['cursor'],next_cursor),run_time=.35)
        if state['storage_visible'] and not previous['storage_visible']:
            badge=txt('STORED AT EDGE 3',16,GOLD).move_to([0,2.55,0])
            parts['result']=badge;self.play(FadeIn(badge),run_time=.25)
        elif not state['storage_visible'] and previous['storage_visible'] and parts['result'] is not None:
            self.play(FadeOut(parts['result']),run_time=.2);parts['result']=None
        self.ideal_state=state

    def show_detail(self,page,sentence):
        """Magnify original pixels beside their overview; never redraw a figure."""
        boxes={5:(.115,.215,.45,.335),19:(.005,.175,.43,.61),
               22:(.39,.47,.60,.315),24:(.65,.47,.34,.315),
               34:(.005,.17,.49,.34),35:(.005,.17,.49,.34),
               37:(.005,.16,.42,.59),38:(.58,.16,.41,.59),40:(.17,.74,.81,.195)}
        roi=boxes.get(page)
        if page==5 and sentence in (10,11):roi=(.72,.215,.20,.335)
        # Retain the complete original validity labels beside both clock edges.
        if page==13:roi=(.175,.17,.58,.31) if sentence<8 else (.43,.17,.505,.31)
        key=(page,roi)
        if self.detail_key==key:return
        asset=self.assets['pages'][str(page)];crop=asset['crop']
        x,y,w,h=roi
        a,b=(x-crop['x'])/crop['width'],(y-crop['y'])/crop['height']
        c,d=w/crop['width'],h/crop['height']
        if min(a,b)<-.00001 or a+c>1.00001 or b+d>1.00001:raise ValueError('Magnification outside original source crop.')
        with Image.open(asset['path']) as original:
            original=original.convert('RGB');pw,ph=original.size
            pixels=np.asarray(original.crop((int(a*pw),int(b*ph),min(pw,int((a+c)*pw)),min(ph,int((b+d)*ph)))))
        lens=ImageMobject(pixels).scale_to_fit_width(5.8)
        if lens.height>4.7:lens.scale_to_fit_height(4.7)
        lens.move_to([3.8,.15,0])
        detail=Group(lens,txt('MAGNIFIED ORIGINAL · same source pixels',13,MUTED,width=5.8).move_to([3.8,2.8,0]),
                     txt('ORIGINAL · overview',13,MUTED,width=7).move_to([-3.45,2.8,0]))
        if self.detail:self.remove(self.detail)
        self.detail=detail;self.detail_key=key;self.detail_image=lens;self.detail_roi=roi
        self.play(self.image.animate.scale_to_fit_width(7).move_to([-3.45,.15,0]),FadeIn(detail,shift=LEFT*.2),run_time=.7)

    def source_box(self,page,box):
        asset=self.assets['pages'][str(page)];crop=asset['crop']
        x,y,w,h=box
        x=(x-crop['x'])/crop['width'];y=(y-crop['y'])/crop['height']
        w=w/crop['width'];h=h/crop['height']
        if min(x,y)<-.015 or x+w>1.015 or y+h>1.015:raise ValueError(f'Overlay outside crop: {page}/{box}')
        guide=Rectangle(width=self.image.width*w,height=self.image.height*h,color='#B47A00',stroke_width=4)
        guide.move_to([self.image.get_left()[0]+self.image.width*(x+w/2),self.image.get_top()[1]-self.image.height*(y+h/2),0])
        guides=VGroup(guide)
        if self.detail_image is not None and self.detail_roi is not None:
            visible=box_in_view(box,self.detail_roi)
            if visible:
                dx,dy,dw,dh=visible;lens=self.detail_image
                detail_guide=Rectangle(width=lens.width*dw,height=lens.height*dh,color='#B47A00',stroke_width=4)
                detail_guide.move_to([lens.get_left()[0]+lens.width*(dx+dw/2),lens.get_top()[1]-lens.height*(dy+dh/2),0])
                guides.add(detail_guide)
        return guides

    def axis(self):
        def point(t,y):return [-5.7+t*.81,y,0]
        axis=Line(point(0,1.2),point(14,1.2),color=MUTED)
        ticks=VGroup()
        for value in (0,2,4,6,8,10,12,14):
            ticks.add(Line(point(value,1.1),point(value,1.3),color=MUTED),txt(value,18,MUTED).move_to(point(value,1.55)))
        return VGroup(axis,ticks,txt('Time at the receiving register (ns)',19,MUTED).move_to([0,2.2,0]))

    def window_picture(self,arrival=6,release=12,show_actual=True,show_required=True,neutral=False):
        result=timing_window(10,2,1,arrival,release)
        def point(t,y):return [-5.7+t*.81,y,0]
        group=self.axis()
        sample=Line(point(10,-1.7),point(10,1.9),color=GOLD,stroke_width=2)
        required=Rectangle(width=3*.81,height=.55,color=GOLD,fill_opacity=.18).move_to(point(9.5,.35))
        group.add(sample,txt('sample at 10 ns',18,GOLD).move_to([3.65,1.95,0]))
        if show_required:group.add(required,txt('REQUIRED  [8, 11]',21,GOLD).move_to([0,-.15,0]))
        else:group.add(txt('Setup: 2 ns before · Hold: 1 ns after',24,GOLD).move_to([0,-.3,0]))
        if show_actual:
            color=MUTED if neutral else GREEN if result['passes'] else RED
            actual=Rectangle(width=(release-arrival)*.81,height=.55,color=color,fill_opacity=.16).move_to(point((arrival+release)/2,-.8))
            group.add(actual,txt(f'ACTUAL  [{arrival:g}, {release:g}]',21,color).move_to([0,-1.35,0]))
        group.add(txt('Original checked interval example · not a device specification or circuit simulation',14,MUTED).move_to([0,-3.35,0]))
        return group

    def show_window(self,sentence):
        # The ruler and required window persist. Move the actual interval, not
        # every glyph in the diagram, when a timing assumption changes.
        def point(t,y):return [-5.7+t*.81,y,0]
        parts=self.window_parts
        if sentence==2:
            intro=txt('A receiving edge has a BEFORE and an AFTER',27).move_to([0,-.3,0])
            axis=self.axis();footer=txt('Original checked interval example · not a device specification or circuit simulation',14,MUTED).move_to([0,-3.35,0])
            parts['intro']=intro;self.play(FadeIn(axis),FadeIn(intro),FadeIn(footer),run_time=.45)
        elif sentence==3:
            self.remove(parts.pop('intro'))
            parts['sample']=VGroup(Line(point(10,-1.7),point(10,1.9),color=GOLD,stroke_width=2),txt('sample at 10 ns',18,GOLD).move_to([3.65,1.95,0]))
            parts['rule']=txt('Setup: 2 ns before · Hold: 1 ns after',24,GOLD).move_to([0,-.3,0])
            self.play(Create(parts['sample'][0]),FadeIn(parts['sample'][1]),FadeIn(parts['rule']),run_time=.6)
        elif sentence==4:
            self.remove(parts.pop('rule'))
            parts['required']=VGroup(Rectangle(width=3*.81,height=.55,color=GOLD,fill_opacity=.18).move_to(point(9.5,.35)),txt('REQUIRED  [8, 11]',21,GOLD).move_to([0,-.15,0]))
            self.play(Create(parts['required'][0]),FadeIn(parts['required'][1]),run_time=.65)
        elif sentence in (5,10,12):
            arrival,release=(6,12) if sentence==5 else (8.5,12) if sentence==10 else (6,10.5)
            result=timing_window(10,2,1,arrival,release);color=GREEN if result['passes'] else RED
            rectangle=Rectangle(width=(release-arrival)*.81,height=.55,color=color,fill_opacity=.16).move_to(point((arrival+release)/2,-.8))
            label=txt(f'ACTUAL  [{arrival:g}, {release:g}]',21,color).move_to([0,-1.35,0])
            if 'margins' in parts:self.remove(parts.pop('margins'))
            if 'actual' in parts:
                self.remove(parts['actual_label']);self.play(Transform(parts['actual'],rectangle),run_time=.7)
            else:
                parts['actual']=rectangle;self.play(Create(rectangle),run_time=.65)
            parts['actual_label']=label;self.add(label)
        elif sentence in (7,8,11,13):
            arrival,release=(6,12) if sentence<=8 else (8.5,12) if sentence==11 else (6,10.5)
            result=timing_window(10,2,1,arrival,release)
            if 'margins' in parts:self.remove(parts.pop('margins'))
            margins=VGroup()
            for a,b,name,value in [(arrival,8,'setup',result['setup_margin']),(11,release,'hold',result['hold_margin'])]:
                if sentence==7 and name=='hold':continue
                color=GREEN if value>=0 else RED
                bracket=VGroup(Line(point(a,-1.9),point(b,-1.9),color=color),Line(point(a,-1.8),point(a,-2),color=color),Line(point(b,-1.8),point(b,-2),color=color))
                label=txt(f'{name} {value:+g} ns',18,color).move_to(point((a+b)/2,-2.25))
                margins.add(bracket,label)
            parts['margins']=margins;self.play(FadeIn(margins),run_time=.45)
        elif sentence==9:self.play(Circumscribe(parts['actual'],color=GREEN),run_time=.65)

    def show_prediction(self,sentence):
        mode='bus' if sentence<5 else 'timing-neutral' if sentence<7 else 'timing-revealed' if sentence<9 else 'takeaway' if sentence>=12 else None
        if mode==self.prediction_mode:return
        self.prediction_mode=mode
        if sentence<5:
            cpu=Rectangle(width=2.4,height=1.7,color=BLUE).move_to([-4,0,0])
            memory=Rectangle(width=2.4,height=1.7,color=GREEN).move_to([4,0,0])
            group=VGroup(cpu,memory,txt('Master',24,BLUE).move_to([-4,0,0]),txt('Memory',24,GREEN).move_to([4,0,0]),
               Arrow([-2.7,.4,0],[2.7,.4,0],color=BLUE),Arrow([2.7,-.4,0],[-2.7,-.4,0],color=MUTED),
               txt('address 16',25,BLUE).move_to([0,.95,0]),txt('data 19',25,MUTED).move_to([0,-1,0]),
               txt('Original logical example · sampling permission has not been established',16,MUTED).move_to([0,-2,0]))
        elif sentence<9:group=self.window_picture(7,11.5,neutral=sentence<7)
        elif sentence>=12:
            group=VGroup(*[VGroup(txt(top,40,color),txt(bottom,23,MUTED)).arrange(DOWN,buff=.35) for top,bottom,color in [('WHERE','Selected address',BLUE),('WHO','Permitted driver',GREEN),('WHEN','Receiving-side validity',GOLD)]]).arrange(RIGHT,buff=.65).move_to([0,.15,0])
        else:return
        if self.window:self.play(FadeOut(self.window),FadeIn(group),run_time=.45)
        else:self.play(FadeIn(group),run_time=.45)
        self.window=group


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--beat',required=True,choices=list(EVENTS));args=parser.parse_args()
    narration=json.loads((OUTPUT/'audio/narration.json').read_text(encoding='utf-8'))
    beat=next(b for b in narration['beats'] if b['id']==args.beat)
    assets=json.loads((OUTPUT/'assets.json').read_text(encoding='utf-8'))
    with tempconfig({'pixel_width':1920,'pixel_height':1080,'frame_rate':30,'media_dir':str(OUTPUT/f'media-{args.beat}'),
                     'output_file':args.beat,'disable_caching':True,'write_to_movie':True,'preview':False,'verbosity':'WARNING'}):
        scene=EvidenceChapter();scene.beat=beat;scene.assets=assets;scene.render()
        import shutil
        shutil.copyfile(scene.renderer.file_writer.movie_file_path,OUTPUT/f'{args.beat}.mp4')
    if sys.platform=='win32':sys.stdout.flush();sys.stderr.flush();os._exit(0)


if __name__=='__main__':main()
