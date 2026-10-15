"""Bounded offline math-to-SVG data conversion; no TeX programs or shell input."""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET

POLICY_PATH=Path(__file__).with_name('math-policy.json')
POLICY=json.loads(POLICY_PATH.read_text(encoding='utf-8'))
FRONTEND=Path(__file__).resolve().parents[4]/'frontend/tldr-frontend'
SCRIPT=FRONTEND/'scripts/math-svg.mjs'


def validate_math(tex):
    if not isinstance(tex,str) or not tex.strip() or len(tex)>POLICY['max_length']:
        raise ValueError('LaTeX equations require 1–600 characters.')
    if any(ord(c)<32 and c not in '\n\r\t' for c in tex):
        raise ValueError('Control characters are not allowed in equations.')
    depth=0;position=0;rows=0
    while position<len(tex):
        char=tex[position]
        if char=='\\':
            match=re.match(r'\\([A-Za-z]+|[\s\S])',tex[position:])
            if not match or match[1] not in POLICY['commands']+POLICY['escaped']:
                raise ValueError('Unsupported LaTeX command. Use the bounded mathematical notation supported by TLDR.')
            if match[1]=='\\':rows+=1
            position+=len(match[0]);continue
        if char=='{':depth+=1
        elif char=='}':depth-=1
        if depth<0 or depth>POLICY['max_depth']:
            raise ValueError('Equation braces are unbalanced or too deeply nested.')
        position+=1
    if depth or rows>POLICY['max_rows'] or tex.count('&')>120:
        raise ValueError('Use balanced braces and at most twelve equation rows.')
    for environment in re.findall(r'\\(?:begin|end)\s*\{([^{}]+)\}',tex):
        if environment not in POLICY['environments']:
            raise ValueError('Unsupported mathematical environment.')
    return tex


def math_dependencies():
    packages={}
    for name in ('@mathjax/src','@mathjax/mathjax-newcm-font'):
        try:packages[name]=json.loads((FRONTEND/'node_modules'/name/'package.json').read_text())['version']
        except (OSError,ValueError,KeyError):pass
    return {'ready':bool(shutil.which('node') and SCRIPT.is_file() and len(packages)==2),'packages':packages}


def fingerprint():
    paths=(Path(__file__),POLICY_PATH,SCRIPT,FRONTEND/'package-lock.json')
    return {'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'packages':math_dependencies()['packages']}


def checked_svg(content):
    if not isinstance(content,str) or len(content)>1000000 or '<!DOCTYPE' in content.upper() or '<!ENTITY' in content.upper():
        raise ValueError('Invalid equation SVG.')
    root=ET.fromstring(content)
    allowed={'svg','g','path','rect','line','polygon','polyline'}
    nodes=list(root.iter())
    if root.tag!='{http://www.w3.org/2000/svg}svg' or len(nodes)>5000:
        raise ValueError('Invalid equation SVG structure.')
    bounds=[float(v) for v in root.attrib.get('viewBox','').split()]
    if len(bounds)!=4 or not all(math.isfinite(v) and abs(v)<=1e6 for v in bounds) or min(bounds[2:])<=0:
        raise ValueError('Invalid equation bounds.')
    for node in nodes:
        if node.tag not in {'{http://www.w3.org/2000/svg}'+tag for tag in allowed}:
            raise ValueError('Equation SVG contains unsupported content.')
        for key,value in list(node.attrib.items()):
            name=key.split('}')[-1].lower()
            if name.startswith('on') or name in {'href','src'} or 'url(' in value.lower() or 'javascript:' in value.lower():
                raise ValueError('Equation SVG cannot contain links or active content.')
            if name=='style':node.attrib.pop(key)
            elif value=='currentColor':node.set(key,'#ffffff')
    ET.register_namespace('','http://www.w3.org/2000/svg')
    return ET.tostring(root,encoding='unicode')


def prepare_equations(lesson,folder,run,cancelled):
    expressions=list(dict.fromkeys(o['latex'] for c in lesson['chapters'] for s in c['scenes'] for o in s['objects'] if o.get('latex')))
    if not expressions:return {},{}
    if not math_dependencies()['ready']:
        raise ValueError('Local LaTeX rendering requires Node.js and npm ci in frontend/tldr-frontend.')
    identity=fingerprint();folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    assets={}
    for tex in expressions:
        validate_math(tex)
        key=hashlib.sha256(json.dumps({'tex':tex,'engine':identity},sort_keys=True).encode()).hexdigest()
        path=folder/f'{key}.svg';marker=folder/f'{key}.json'
        try:
            content=path.read_text(encoding='utf-8');record=json.loads(marker.read_text())
            if not isinstance(record,dict) or not isinstance(record.get('sha256'),str):
                raise ValueError('Invalid equation cache marker.')
            if hashlib.sha256(content.encode()).hexdigest()!=record['sha256']:raise ValueError('Equation cache changed.')
            checked_svg(content)
        except (OSError,ValueError,KeyError,ET.ParseError):
            request=folder/f'{key}.request.json';response=folder/f'{key}.response.json'
            request.write_text(json.dumps([tex]),encoding='utf-8')
            run([shutil.which('node'),str(SCRIPT),str(request),str(response)],cancelled=cancelled,timeout=30)
            values=json.loads(response.read_text(encoding='utf-8'))
            if not isinstance(values,list) or len(values)!=1:raise ValueError('Invalid equation conversion result.')
            content=checked_svg(values[0]);path.write_text(content,encoding='utf-8')
            marker.write_text(json.dumps({'sha256':hashlib.sha256(content.encode()).hexdigest()}))
        assets[tex]={'path':str(path.resolve()),'sha256':hashlib.sha256(content.encode()).hexdigest()}
    return assets,identity
