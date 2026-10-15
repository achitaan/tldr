"""Original, trusted animation study; no model-generated code is loaded.

Run with backend/.venv Python after narrate.py. The fixed teaching sequence is
deliberately independent of the general lesson language while quality is reviewed.
"""
from pathlib import Path
import json
import os
import sys
from manim import (
    MovingCameraScene, Text, VGroup, Group, RoundedRectangle, Rectangle,
    Line, Arrow, Dot, VMobject, FadeIn, FadeOut, Transform, ReplacementTransform,
    Create, Indicate, Circumscribe, AnimationGroup, Restore, tempconfig,
    UP, DOWN, LEFT, RIGHT, WHITE, linear,
)

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'artifacts/showcase/opening'
BLUE='#68B9EF'
GREEN='#75D6B0'
GOLD='#F3CD78'
RED='#EE8D86'
MUTED='#91A2AF'
BG='#101820'


def text(value,size=28,color=WHITE):
    return Text(str(value),font='Arial',font_size=size,color=color,disable_ligatures=True)


def memory_table():
    rows=VGroup()
    for address,value in [(15,7),(16,42),(17,99)]:
        box=Rectangle(width=3.2,height=.65,stroke_color='#334651',stroke_width=1)
        values=VGroup(text(address,25,BLUE),text(value,25,GREEN)).arrange(RIGHT,buff=1.5)
        row=VGroup(box,values)
        rows.add(row)
    rows.arrange(DOWN,buff=0)
    header=VGroup(text('ADDRESS',14,MUTED),text('VALUE',14,MUTED)).arrange(RIGHT,buff=1.1).next_to(rows,UP,buff=.2)
    title=text('Memory',25).next_to(header,UP,buff=.18)
    return VGroup(rows,header,title)


class WhyWait(MovingCameraScene):
    def construct(self):
        narration=json.loads((OUTPUT/'narration.json').read_text(encoding='utf-8'))
        index={beat['id']:beat for beat in narration['beats']}
        timing=[]
        visual_events=[]
        def begin(id_):
            beat=index[id_]
            start=float(self.time)
            self.add_sound(beat['audio'],gain=-1)
            timing.append({'id':id_,'start_seconds':start,'narration':beat['text'],'audio_seconds':beat['duration_seconds'],'cues':beat['cues']})
            return start+beat['duration_seconds']+.12
        def finish(end):
            if self.time<end: self.wait(end-self.time)
            timing[-1]['end_seconds']=float(self.time)
        def cue(sentence_index,event):
            """Anchor a visual to the actual synthesized sentence, never a guess."""
            beat=timing[-1]
            target=beat['start_seconds']+beat['cues'][sentence_index]['start_seconds']
            if self.time<target: self.wait(target-self.time)
            if self.time-target>.12:
                raise ValueError(f'Visual {event} missed its narration cue by {self.time-target:.3f}s')
            visual_events.append({'event':event,'beat':beat['id'],'sentence_index':sentence_index,'cue_seconds':target,'visual_seconds':float(self.time)})

        self.camera.background_color=BG
        brand=text('TLDR  /  VISUAL STUDY',14,MUTED).to_corner(UP+LEFT,buff=.35)
        model_label=text('Original teaching model · logical sequence, not an electrical simulation',13,MUTED).to_edge(DOWN,buff=.22)
        title=text('Why a computer has to wait',40).to_edge(UP,buff=.9)
        subtitle=text('One read. Two different questions.',22,MUTED).next_to(title,DOWN,buff=.25)
        cpu_box=RoundedRectangle(width=2.1,height=1.55,corner_radius=.12,stroke_color=BLUE,stroke_width=2).move_to([-4,.2,0])
        cpu_title=text('Processor',24).move_to(cpu_box.get_center()+UP*.35)
        register=text('19',34,MUTED).move_to(cpu_box.get_center()+DOWN*.2)
        cpu=VGroup(cpu_box,cpu_title,register)
        memory=memory_table().move_to([3,.5,0])
        # Both channels bind to the selected row, never neighboring rows 15/17.
        row_y=memory[0][1].get_center()[1]
        cpu.shift(UP*(row_y-cpu_box.get_center()[1]))
        port_x=memory[0][1].get_left()[0]-.06
        address_line=Arrow([-2.95,row_y+.2,0],[port_x,row_y+.2,0],buff=0,color=BLUE,stroke_width=2.5,max_tip_length_to_length_ratio=.04)
        data_line=Arrow([port_x,row_y-.2,0],[-2.95,row_y-.2,0],buff=0,color=GREEN,stroke_width=2.5,max_tip_length_to_length_ratio=.04)
        address_label=text('address',18,BLUE).move_to([-.8,row_y+.98,0])
        data_label=text('data',18,GREEN).move_to([-.8,row_y-.96,0])
        address=text('16',32,BLUE).move_to([-.8,row_y+.58,0])
        old_data=text('19',32,MUTED).move_to([-.8,row_y-.56,0])
        self.add(brand,model_label)

        end=begin('question')
        self.play(FadeIn(title,shift=UP*.15),FadeIn(subtitle),run_time=1.3)
        self.play(FadeIn(cpu,shift=RIGHT*.25),FadeIn(memory,shift=LEFT*.25),run_time=1.4)
        self.play(Create(address_line),Create(data_line),FadeIn(address_label),FadeIn(data_label),run_time=1.5)
        self.play(FadeOut(subtitle),run_time=.6)
        finish(end)

        end=begin('where')
        self.play(FadeIn(address),FadeIn(old_data),run_time=.8)
        where=text('where?',24,BLUE).move_to([-.8,1.65,0])
        what=text('what?',24,GREEN).move_to([3,-1.2,0])
        cue(1,'address-as-location')
        self.play(Circumscribe(address,color=BLUE),run_time=1.4)
        cue(2,'stored-value-42')
        self.play(Indicate(memory[0][1][1][1],color=GREEN),run_time=1.4)
        cue(3,'address-answers-where')
        self.play(FadeIn(where),Circumscribe(address,color=BLUE),run_time=1.2)
        cue(4,'value-answers-what')
        self.play(FadeIn(what),Circumscribe(memory[0][1][1][1],color=GREEN),run_time=1.4)
        finish(end)

        end=begin('address')
        self.camera.frame.save_state()
        self.play(self.camera.frame.animate.scale(.75).move_to([1.4,.45,0]),run_time=1.6)
        token=text('16',25,BLUE).move_to(address_line.get_start())
        self.add(token)
        cue(1,'follow-address')
        self.play(token.animate.move_to(address_line.get_end()),run_time=1.8)
        row=memory[0][1]
        selection=Rectangle(width=row.width+.14,height=row.height+.1,color=BLUE,stroke_width=2).move_to(row)
        cue(2,'selected-row-16')
        self.play(FadeOut(token),Create(selection),row[0].animate.set_fill(BLUE,opacity=.1),run_time=1)
        self.play(Indicate(row[1][1],color=GREEN,scale_factor=1.2),run_time=1.2)
        self.play(Restore(self.camera.frame),run_time=1.6)
        finish(end)

        end=begin('waiting')
        self.play(FadeOut(where),FadeOut(what),run_time=.5)
        request=text('read requested',22,GOLD).move_to([-.8,1.65,0])
        wait=text('waiting for valid data',23,MUTED).move_to([0,-1.65,0])
        self.play(FadeIn(request),FadeIn(wait),old_data.animate.set_color(MUTED),run_time=1)
        old_label=text('old value',17,MUTED).next_to(old_data,RIGHT,buff=.2)
        cue(1,'old-data-19')
        self.play(FadeIn(old_label),run_time=.6)
        self.play(Indicate(old_data,color=GOLD,scale_factor=1.15),run_time=1.4)
        finish(end)

        end=begin('early')
        captured=old_data.copy().set_color(RED)
        self.add(captured)
        cue(1,'early-sample-19')
        self.play(captured.animate.move_to(register),run_time=1.2)
        error=text('present ≠ ready',30,RED).move_to([0,-2.5,0])
        self.play(FadeOut(captured),register.animate.set_color(RED),run_time=.8)
        cue(3,'present-versus-ready')
        self.play(FadeIn(error),run_time=.8)
        self.play(Circumscribe(register,color=RED),run_time=1.1)
        finish(end)

        end=begin('ready')
        valid=text('DATA VALID',22,GREEN).move_to(request)
        value=text('42',32,GREEN).move_to(old_data)
        self.play(ReplacementTransform(old_data,value),ReplacementTransform(request,valid),FadeOut(old_label),FadeOut(error),FadeOut(wait),run_time=1.1)
        packet=value.copy()
        self.add(packet)
        cue(1,'valid-sample-42')
        self.play(packet.animate.move_to(register),run_time=1.8)
        next_register=text('42',34,GREEN).move_to(register)
        self.play(FadeOut(packet),Transform(register,next_register),run_time=.7)
        accepted=text('sample accepted',23,GREEN).move_to([0,-1.65,0])
        self.play(FadeIn(accepted),Circumscribe(register,color=GREEN),run_time=1.4)
        cue(2,'address-remains-16')
        self.play(Circumscribe(address,color=BLUE),run_time=1.2)
        cue(3,'permission-to-trust')
        self.play(Indicate(valid,color=GREEN),run_time=1.2)
        finish(end)

        end=begin('timing')
        self.play(FadeOut(accepted),FadeOut(selection),run_time=.5)
        apparatus=VGroup(cpu,memory,address_line,data_line,address_label,data_label,address,value,valid)
        self.play(apparatus.animate.scale(.65).shift(UP*1.4),title.animate.scale(.75).to_edge(UP,buff=.55),run_time=1.6)
        waves=VGroup()
        left,right=-2.7,4.4
        samples=[('Read request',[0,1,1,1,0,0],BLUE),('Data valid',[0,0,1,1,0,0],GREEN),('Sample',[0,0,0,1,0,0],GOLD)]
        for row_index,(name,values,color) in enumerate(samples):
            y=-.7-row_index*.65
            pts=[[left,y+values[0]*.3,0]]
            for i,state in enumerate(values):
                x=left+i*(right-left)/len(values)
                pts.extend([[x,y+state*.3,0],[left+(i+1)*(right-left)/len(values),y+state*.3,0]])
            line=VMobject(color=color,stroke_width=2.5).set_points_as_corners(pts)
            label=text(name,19,color).move_to([-4.2,y+.12,0])
            waves.add(VGroup(line,label))
            cue(row_index+1,f'timing-{name.lower().replace(" ","-")}')
            self.play(Create(line),FadeIn(label),run_time=1.2)
        x=left+3*(right-left)/6
        sample_window=Rectangle(width=(right-left)/6,height=2.15,color=GOLD,fill_opacity=.07,stroke_opacity=.4).move_to([x+(right-left)/12,-1.15,0])
        cursor=Line([left,-2.25,0],[left,-.15,0],color=WHITE,stroke_width=1.5)
        self.play(FadeIn(sample_window),Create(cursor),run_time=.7)
        cue(4,'shared-time-axis')
        self.play(cursor.animate.shift(RIGHT*((right-left)*.58)),run_time=2.8,rate_func=linear)
        self.play(Indicate(sample_window,color=GOLD),run_time=.8)
        finish(end)

        end=begin('takeaway')
        self.play(FadeOut(cursor),FadeOut(sample_window),waves.animate.shift(UP*.2),run_time=.8)
        takeaway=VGroup(text('Address',28,BLUE),text('tells us where.',28),text('Validity',28,GREEN),text('tells us when.',28)).arrange(RIGHT,buff=.2).move_to([0,-2.65,0])
        cue(1,'closing-where')
        self.play(FadeIn(takeaway[1],shift=UP*.12),run_time=1)
        cue(2,'closing-address')
        self.play(FadeIn(takeaway[0]),run_time=1)
        cue(3,'closing-when')
        self.play(FadeIn(takeaway[3],shift=UP*.12),run_time=1)
        cue(4,'closing-validity')
        self.play(FadeIn(takeaway[2]),run_time=1)
        finish(end)
        (OUTPUT/'visual-timing.json').write_text(json.dumps({'beats':timing,'visual_events':visual_events,'duration_seconds':float(self.time)},indent=2),encoding='utf-8')


if __name__=='__main__':
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with tempconfig({'pixel_width':1920,'pixel_height':1080,'frame_rate':30,'media_dir':str(OUTPUT/'media'),'output_file':'opening','disable_caching':True,'write_to_movie':True,'preview':False,'background_color':BG,'verbosity':'WARNING'}):
        scene=WhyWait()
        scene.render()
        import shutil
        shutil.copyfile(scene.renderer.file_writer.movie_file_path,OUTPUT/'opening.mp4')
    if sys.platform=='win32':
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
