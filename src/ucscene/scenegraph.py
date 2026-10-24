"""Structured source-of-truth scene contract and deterministic semantic SVG rendering.

The authoring spec is a DESIGN PROPOSAL. Rendering does not prove that the software
exists or that a user has approved the layout. Exact display values and actions
are authored in the spec and validated against the source DesignPlan.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Any

from .core import SceneError, save_json
from .design.planner import validate_design_plan, _json_hash

CONTRACT_VERSION = '1.0'
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)
ID_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]{0,79}$')
SHA_RE = re.compile(r'^[a-f0-9]{64}$')
ALLOWED_TYPES = {'heading', 'text', 'metric', 'button', 'chip', 'card', 'world-object', 'art-slot', 'notice'}
DISPLAY_STATES = {'start', 'in-progress', 'waiting', 'success', 'failure'}
BG = {'header': '#182438', 'sidebar': '#172434', 'workspace': '#213249',
      'inspector': '#19293a', 'hud': '#182438', 'world': '#496a54',
      'toolbar': '#1d2d42', 'panel': '#22364a'}


def _hash(payload: Any) -> str:
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8')).hexdigest()


def _must(condition: bool, message: str) -> None:
    if not condition:
        raise SceneError(message)


def _id(value: Any, field: str) -> None:
    _must(isinstance(value, str) and ID_RE.fullmatch(value) is not None,
          field + ' must be an XML-safe stable ID')


def _rect(value: Any, width: int, height: int, field: str) -> tuple[int, int, int, int]:
    _must(isinstance(value, list) and len(value) == 4 and all(type(i) is int for i in value),
          field + ' must contain four integer coordinates')
    x, y, w, h = value
    _must(x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= width and y + h <= height,
          field + ' exceeds canvas or has invalid dimensions')
    return x, y, w, h


def _contains(outer: tuple[int, ...], inner: tuple[int, ...]) -> bool:
    x, y, w, h = outer
    a, b, c, d = inner
    return x <= a and y <= b and a + c <= x + w and b + d <= y + h


def _overlap(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return max(a[0], b[0]) < min(a[0] + a[2], b[0] + b[2]) and max(a[1], b[1]) < min(a[1] + a[3], b[1] + b[3])


def compile_scene_graph(plan: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Bind an Agent-authored typed scene spec to a validated, unapproved DesignPlan.

    This intentionally does not hallucinate layout/interaction details from free
    text. AI or the designer supplies a spec; the program enforces its invariants.
    """
    validate_design_plan(plan)
    _must(isinstance(spec, dict) and spec.get('kind') == 'scene-graph-spec'
          and spec.get('format_version') == CONTRACT_VERSION, 'Invalid scene graph spec')
    _must(set(spec) == {'kind','format_version','product_id','variant_id','authority','navigation','layout','canvas','regions','elements','objects','actions','scenes'},
          'Scene graph spec has missing or unknown fields')
    _must(spec.get('product_id') == plan['product_id'], 'Wrong product identity in scene graph spec')
    variant = spec.get('variant_id')
    candidates = [c for c in plan['candidates'] if c['id'] == variant]
    _must(len(candidates) == 1, 'Unknown scene graph design variant')
    candidate = candidates[0]
    _must(spec.get('authority') == 'proposed', 'Scene graph cannot self-approve a design')
    _must(spec.get('navigation') == candidate['navigation'], 'Scene graph navigation contradicts chosen design variant')
    _must(spec.get('layout') == candidate['layout'], 'Scene graph layout contradicts chosen design variant')
    graph = {
        'kind': 'semantic-scene-graph', 'format_version': CONTRACT_VERSION,
        'product_id': plan['product_id'], 'variant_id': variant, 'authority': 'proposed',
        'source_plan_sha256': _json_hash(plan), 'source_spec_sha256': _hash(spec),
        'design': {'layout': candidate['layout'], 'navigation': candidate['navigation'],
                   'visual_style': candidate['visual_style'], 'status': candidate['status']},
        'canvas': deepcopy(spec.get('canvas')), 'regions': deepcopy(spec.get('regions')),
        'elements': deepcopy(spec.get('elements')), 'objects': deepcopy(spec.get('objects')),
        'actions': deepcopy(spec.get('actions')), 'scenes': [],
        'notice': 'Design proposal, NOT a running product, not a user-approved design.',
    }
    supplied = spec.get('scenes')
    _must(isinstance(supplied, list) and len(supplied) == len(candidate['screens']),
          'Scene graph must cover exactly the selected candidate steps')
    for expected, scene in zip(candidate['screens'], supplied):
        _must(isinstance(scene, dict) and scene.get('scene_id') == expected['scene_id'],
              'Scene graph scene/order differs from source DesignPlan')
        _must(scene.get('step_id') == expected['step_id'], 'Scene graph step does not match DesignPlan')
        _must(set(scene) == {'scene_id', 'step_id', 'selected_object_id', 'event_id',
                             'visible_elements', 'values'}, 'Scene graph scene has missing/extra fields')
        graph['scenes'].append({**deepcopy(scene),
            'use_case_id': expected['use_case_id'], 'state': expected['state'], 'flow': expected['flow'],
            'required_evidence': deepcopy(expected['required_evidence']),
            'required_ui_text': deepcopy(expected['required_ui_text']),
            'requirement_ids': deepcopy(expected['requirement_ids']),
            'design_decision_ids': deepcopy(expected['design_decision_ids']),
        })
    graph['graph_sha256'] = _hash(graph)
    return validate_scene_graph(graph, plan=plan)


def validate_scene_graph(graph: dict[str, Any], *, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    _must(isinstance(graph, dict) and set(graph) == {'kind','format_version','product_id','variant_id','authority',
          'source_plan_sha256','source_spec_sha256','design','canvas','regions','elements','objects',
          'actions','scenes','notice','graph_sha256'}, 'Scene graph envelope invalid')
    _must(graph['kind'] == 'semantic-scene-graph' and graph['format_version'] == CONTRACT_VERSION,
          'Unsupported semantic scene graph')
    _must(graph['authority'] == 'proposed' and graph['design'].get('status') == 'proposed',
          'Unapproved scene graph cannot claim user approval')
    for key in ('source_plan_sha256', 'source_spec_sha256', 'graph_sha256'):
        _must(isinstance(graph[key],str) and SHA_RE.fullmatch(graph[key]) is not None, 'Invalid digest: '+key)
    _must(graph['graph_sha256'] == _hash({k:v for k,v in graph.items() if k != 'graph_sha256'}),
          'Scene graph digest mismatch')
    _id(graph['product_id'], 'product_id')
    _id(graph['variant_id'], 'variant_id')
    canvas=graph['canvas']
    _must(isinstance(canvas,dict) and set(canvas)=={'width','height'} and
          all(type(canvas[k]) is int for k in ('width','height')) and
          640 <= canvas['width'] <= 3840 and 360 <= canvas['height'] <= 2160,
          'Invalid scene graph canvas')
    w,h=canvas['width'],canvas['height']
    regions=graph['regions']
    _must(isinstance(regions,list) and 2 <= len(regions) <= 32,'Expected 2-32 scene regions')
    area={}
    for r in regions:
        _must(isinstance(r,dict) and set(r)=={'id','role','rect','parent'},'Invalid region structure')
        _id(r['id'],'region.id')
        _must(r['id'] not in area,'Duplicate region id: '+r['id'])
        _must(isinstance(r['role'],str) and r['role'] in BG,'Unknown region role')
        _must(r['parent'] is None or isinstance(r['parent'],str),'Invalid region parent')
        area[r['id']]=_rect(r['rect'],w,h,'region:'+r['id'])
    region_by_id={r['id']:r for r in regions}
    for r in regions:
        if r['parent'] is not None:
            _must(r['parent'] in area and r['parent']!=r['id'],'Unknown or circular region parent')
            _must(_contains(area[r['parent']],area[r['id']]),'Nested region exceeds parent')
            _must(region_by_id[r['parent']]['parent'] is None,'Region parent must be top-level')
    roots=[r for r in regions if r['parent'] is None]
    for i,a in enumerate(roots):
        for b in roots[i+1:]:
            _must(not _overlap(area[a['id']],area[b['id']]),
                  'Top-level regions overlap: '+a['id']+'/'+b['id'])
    # Enforce spatial topology for the two currently supported navigation archetypes.
    nav=graph['design']['navigation']
    if nav=='sidebar-workspace-inspector':
        for name in ('sidebar','workspace','inspector'):
            _must(name in area,'Required desktop region missing: '+name)
        s,v,i=area['sidebar'],area['workspace'],area['inspector']
        _must(s[0]+s[2]==v[0] and v[0]+v[2]==i[0] and s[1]==v[1]==i[1],
              'Desktop navigation topology differs from chosen DesignPlan')
    elif nav=='world-hud-right-panel':
        for name in ('world','hud','inspector'):
            _must(name in area,'Required game region missing: '+name)
        world,hud,ins=area['world'],area['hud'],area['inspector']
        _must(world[0]+world[2]==ins[0] and world[1]==ins[1]==hud[1]+hud[3],
              'Game viewport/HUD/inspector topology differs from chosen DesignPlan')
    else:
        _must(False,'Unsupported navigation archetype for deterministic rendering: '+str(nav))
    objects=graph['objects']
    _must(isinstance(objects,list) and objects,'Scene graph has no domain objects')
    obj={}
    for o in objects:
        _must(isinstance(o,dict) and set(o)=={'id','type','label'},'Invalid object structure')
        _id(o['id'],'object.id')
        _must(o['id'] not in obj,'Duplicate domain object')
        _must(isinstance(o['type'],str) and isinstance(o['label'],str),'Invalid object type/label')
        obj[o['id']]=o
    actions=graph['actions']
    _must(isinstance(actions,list),'Invalid actions')
    action_by_id={}
    for a in actions:
        _must(isinstance(a,dict) and set(a)=={'id','target','preconditions','effects'},'Invalid action definition')
        _id(a['id'],'action.id')
        _must(a['id'] not in action_by_id,'Duplicate action ID')
        _must(a['target'] in obj,'Action target does not exist')
        for field in ('preconditions','effects'):
            _must(isinstance(a[field],dict),'Action '+field+' invalid')
        for key, effect in a['effects'].items():
            _must(isinstance(effect,dict) and set(effect)=={'op','value'} and effect['op'] in ('set','add'),
                  'Invalid action effect for '+key)
            if effect['op']=='add':_must(type(effect['value']) in (int,float),'Add effect must be numeric')
        action_by_id[a['id']]=a
    elements=graph['elements']
    _must(isinstance(elements,list) and 1<=len(elements)<=250,'Invalid UI element list')
    elems={}
    for e in elements:
        _must(isinstance(e,dict) and set(e)=={'id','kind','region','rect','label','binding','action_id','object_id','evidence_refs'},
              'Invalid scene element envelope')
        _id(e['id'],'element.id')
        _must(e['id'] not in elems and e['id'] not in area,'Duplicate element or region ID')
        _must(e['kind'] in ALLOWED_TYPES and e['region'] in area,'Unknown element kind/region')
        b=_rect(e['rect'],w,h,'element:'+e['id'])
        _must(_contains(area[e['region']],b),'Element outside its parent region: '+e['id'])
        _must(isinstance(e['label'],str) and isinstance(e['evidence_refs'],list)
              and all(isinstance(x,str) and x for x in e['evidence_refs']), 'Invalid element label/evidence')
        _must(e['binding'] is None or isinstance(e['binding'],str),'Invalid element binding')
        _must(e['action_id'] is None or e['action_id'] in action_by_id,'Unknown element action ID')
        _must(e['object_id'] is None or e['object_id'] in obj,'Unknown element object ID')
        if e['binding'] and e['binding'].startswith('object.'):
            parts=e['binding'].split('.')
            _must(len(parts)==3 and parts[1] in obj,'Bound element references an unknown object')
            if e['object_id'] is not None:
                _must(parts[1]==e['object_id'],'Element data binding refers to different domain object')
        elems[e['id']]=e
    scenes=graph['scenes']
    _must(isinstance(scenes,list) and scenes,'No scene states')
    seen_scenes=set()
    prior=None
    for scene in scenes:
        _must(isinstance(scene,dict) and set(scene)=={'scene_id','step_id','selected_object_id',
             'event_id','visible_elements','values','use_case_id','state','flow','required_evidence',
             'required_ui_text','requirement_ids','design_decision_ids'},'Invalid scene snapshot')
        sid=scene['scene_id']
        _must(isinstance(sid,str) and sid not in seen_scenes,'Duplicate/missing scene ID')
        seen_scenes.add(sid)
        _must(scene['state'] in DISPLAY_STATES,'Invalid scene state')
        _must(scene['selected_object_id'] is None or scene['selected_object_id'] in obj,
              'Selected domain object does not exist: '+str(scene['selected_object_id']))
        _must(isinstance(scene['values'],dict),'Invalid scene state values')
        vals=scene['values']
        _must(isinstance(scene['visible_elements'],list) and len(set(scene['visible_elements']))==len(scene['visible_elements'])
              and set(scene['visible_elements'])<=set(elems),'Scene shows unknown/duplicate elements')
        _must(scene['event_id'] is None or scene['event_id'] in action_by_id,'Unknown scene event')
        _must(vals.get('ui.selected_object')==scene['selected_object_id'],
              'Selection state does not match selected domain object')
        for k,v in vals.items():
            _must(isinstance(k,str) and isinstance(v,(str,int,float,bool)) and not isinstance(v,complex),
                  'State values must be scalar and addressable')
            if k.startswith('object.'):
                prefix=k.split('.')
                _must(len(prefix)==3 and prefix[1] in obj,'State data refers to unknown object: '+k)
        required=set(scene['required_evidence'])
        actual={ev for eid in scene['visible_elements'] for ev in elems[eid]['evidence_refs']}
        _must(required<=actual,'Visible evidence missing for '+sid+': '+', '.join(sorted(required-actual)))
        visible_text=[t for eid in scene['visible_elements'] for e in [elems[eid]]
                      for t in ([e['label']] + ([str(vals[e['binding']])] if e['binding'] and e['binding'] in vals else []))]
        for label in scene['required_ui_text']:
            _must(any(label in txt for txt in visible_text),'Exact required UI text absent from '+sid+': '+label)
        for eid in scene['visible_elements']:
            e=elems[eid]
            if e['binding']:
                _must(e['binding'] in vals,'Missing state binding '+e['binding']+' in '+sid)
            if e['object_id'] is not None and e['kind'] in ('world-object','card'):
                _must(e['object_id']==scene['selected_object_id'],
                      'Rendered selected object differs from scene selection in '+sid)
            if e['action_id'] is not None:
                _must(action_by_id[e['action_id']]['target']==scene['selected_object_id'],
                      'Control action targets a different selected object')
        if prior is None:
            _must(scene['event_id'] is None,'First scene must define baseline without an action')
        else:
            _must(set(vals)==set(prior['values']),'State key set changed between steps')
            if scene['event_id'] is None:
                _must(vals==prior['values'],'State changed with no recorded action')
            else:
                action=action_by_id[scene['event_id']]
                for key,expected in action['preconditions'].items():
                    _must(prior['values'].get(key)==expected,'Action precondition failed: '+key)
                expected=deepcopy(prior['values'])
                for key,effect in action['effects'].items():
                    _must(key in expected,'Action affects untracked state: '+key)
                    if effect['op']=='add':
                        _must(type(expected[key]) in (int,float),'Cannot add to nonnumeric state: '+key)
                        expected[key]+=effect['value']
                    else:expected[key]=effect['value']
                _must(vals==expected,'State transition contradicts declared action effects for '+sid)
        prior=scene
    if plan is not None:
        validate_design_plan(plan)
        _must(graph['product_id']==plan['product_id'] and graph['source_plan_sha256']==_json_hash(plan),
              'Scene graph belongs to a different source plan')
        choices=[c for c in plan['candidates'] if c['id']==graph['variant_id']]
        _must(len(choices)==1,'Scene graph references unknown design variant')
        candidate=choices[0]
        _must(graph['design']=={'layout':candidate['layout'],'navigation':candidate['navigation'],
                                'visual_style':candidate['visual_style'],'status':candidate['status']},
              'Scene graph changed design candidate layout')
        _must(len(scenes)==len(candidate['screens']),'Scene count mismatch')
        for s,src in zip(scenes,candidate['screens']):
            for key in ('scene_id','step_id','use_case_id','state','flow','required_evidence',
                        'required_ui_text','requirement_ids','design_decision_ids'):
                _must(s[key]==src[key],'Source evidence/step changed: '+key)
    return graph


def _svg_tag(name: str) -> str:
    return '{'+SVG_NS+'}'+name


def _node(parent: ET.Element, tag: str, **attrs: Any) -> ET.Element:
    return ET.SubElement(parent,_svg_tag(tag),{k.replace('_','-'):str(v) for k,v in attrs.items() if v is not None})


def _box(parent: ET.Element, rect: list[int], fill: str, *, stroke: str='none', radius: int=0) -> None:
    x,y,w,h=rect
    _node(parent,'rect',x=x,y=y,width=w,height=h,fill=fill,stroke=stroke,rx=radius)


def _text(parent: ET.Element,x:int,y:int,message:str,size:int=15, color:str='#e8eff7', weight:int=400) -> None:
    t=_node(parent,'text',x=x,y=y,fill=color,font_size=size,font_weight=weight,
            font_family='Noto Sans CJK SC, Noto Sans, sans-serif')
    t.text=str(message)


def _make_svg(graph:dict[str,Any], scene:dict[str,Any]) -> bytes:
    w,h=graph['canvas']['width'],graph['canvas']['height']
    root=ET.Element(_svg_tag('svg'),{'width':str(w),'height':str(h),'viewBox':f'0 0 {w} {h}',
       'role':'img','data-product-id':graph['product_id'],'data-scene-id':scene['scene_id'],
       'data-step-id':scene['step_id'],'data-graph-sha256':graph['graph_sha256'],
       'data-authority':'proposed','data-source-plan-sha256':graph['source_plan_sha256']})
    title=_node(root,'title');title.text=graph['product_id']+' / '+scene['step_id']
    desc=_node(root,'desc');desc.text='Deterministic conceptual software UI; unapproved design proposal.'
    metadata=_node(root,'metadata'); metadata.text=json.dumps({'graph_sha256':graph['graph_sha256'],
      'scene_id':scene['scene_id'],'step_id':scene['step_id']},sort_keys=True,separators=(',',':'))
    _box(root,[0,0,w,h],'#101b2a')
    for region in graph['regions']:
        group=_node(root,'g',id=region['id'],data_role=region['role'],data_rect=','.join(map(str,region['rect'])))
        _box(group,region['rect'],BG[region['role']],stroke='#304459',radius=0)
    elem={e['id']:e for e in graph['elements']}
    for eid in scene['visible_elements']:
        e=elem[eid];x,y,ew,eh=e['rect'];kind=e['kind']
        text=str(scene['values'][e['binding']]) if e['binding'] else e['label']
        g=_node(root,'g',id=eid,data_role=kind,data_rect=','.join(map(str,e['rect'])),
          data_region=e['region'],data_binding=e['binding'],data_action=e['action_id'],
          data_evidence_refs='|'.join(e['evidence_refs']),
          data_object_id=e['object_id'],data_display_value=text)
        if kind=='art-slot':
            _box(g,e['rect'],'#406b5b',stroke='#91a994',radius=8)
            # This is a deterministic placeholder for optional agent-generated art;
            # never a claim of an actual executed game scene.
            _text(g,x+12,y+25,'ART SLOT · '+text,14,'#e2eedf',600)
            for k in range(2,8):
                xx=x+int(ew*k/9); yy=y+int(eh*(k%3+2)/6)
                if xx+16<x+ew and yy+20<y+eh:
                    _node(g,'polygon',points=f'{xx},{yy+20} {xx+20},{yy} {xx+40},{yy+20}',
                          fill='#315946',stroke='#8ba77b')
        elif kind=='world-object':
            _box(g,e['rect'],'#6a8654',stroke='#f6d56a',radius=12)
            _node(g,'polygon',points=f'{x+ew//2},{y+20} {x+ew-12},{y+eh//2} '
                    f'{x+ew//2},{y+eh-20} {x+12},{y+eh//2}',
                  fill='#c29f5d',stroke='#ffe67a',stroke_width=3)
            _text(g,x+16,y+eh-12,text,18,'#fff1ad',700)
        elif kind=='metric':
            _box(g,e['rect'],'#253d50',radius=7)
            _text(g,x+12,y+21,e['label'],13,'#a9bdce')
            _text(g,x+12,y+eh-10,text,20,'#ffffff',700)
        elif kind=='notice':
            _box(g,e['rect'],'#753243' if scene['state']=='failure' else '#2f5f52',radius=7)
            _text(g,x+10,y+eh//2+6,text,16,'#ffffff',700)
        elif kind=='button':
            _box(g,e['rect'],'#1c6bd0' if scene['state']!='failure' else '#49617e',radius=8)
            _text(g,x+12,y+eh//2+6,text,16,'#ffffff',650)
        elif kind=='chip':
            _box(g,e['rect'],'#246dad',stroke='#6ca1d2',radius=10)
            _text(g,x+10,y+eh//2+5,text,14,'#ffffff',550)
        elif kind=='card':
            _box(g,e['rect'],'#34495e',stroke='#537088',radius=9)
            _node(g,'rect',x=x+10,y=y+10,width=max(1,ew-20),height=max(1,eh-49),fill='#68827b',rx=4)
            _text(g,x+12,y+eh-12,text,13,'#ffffff',600)
        elif kind=='heading':
            _text(g,x,y+min(eh-8,27),text,22,'#fff5e4',700)
        else:
            _text(g,x,y+min(eh-5,20),text,15,'#dde8f3')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def render_scene_graph(graph:dict[str,Any], output_dir:str|Path,
                       *, plan:dict[str,Any]|None=None) -> dict[str,Any]:
    validate_scene_graph(graph,plan=plan)
    dest=Path(output_dir)
    _must(not dest.exists() or (dest.is_dir() and not list(dest.iterdir())),
          'Scene SVG output must be a new/empty directory')
    dest.mkdir(parents=True,exist_ok=True)
    images=[]
    for scene in graph['scenes']:
        # File name is strictly derived from known step IDs, no path traversal.
        _id(scene['step_id'],'step_id')
        filename=scene['step_id']+'.svg'
        raw=_make_svg(graph,scene)
        (dest/filename).write_bytes(raw)
        images.append({'scene_id':scene['scene_id'],'step_id':scene['step_id'],
                       'file':filename,'sha256':sha256(raw).hexdigest()})
    manifest={'kind':'semantic-svg-render-manifest','format_version':CONTRACT_VERSION,
              'product_id':graph['product_id'],'graph_sha256':graph['graph_sha256'],
              'authority':'proposed','images':images,
              'notice':'Deterministic SVG validates structure, not executable UX, user approval or AI image quality.'}
    manifest['manifest_sha256']=_hash(manifest)
    save_json(dest/'manifest.json',manifest)
    verify_scene_svgs(graph,dest/'manifest.json')
    return manifest


def verify_scene_svgs(graph:dict[str,Any], manifest_file:str|Path) -> dict[str,Any]:
    validate_scene_graph(graph)
    path=Path(manifest_file)
    manifest=json.loads(path.read_text(encoding='utf-8'))
    _must(isinstance(manifest,dict) and set(manifest)=={'kind','format_version','product_id',
          'graph_sha256','authority','images','notice','manifest_sha256'},'Invalid SVG manifest')
    _must(manifest['kind']=='semantic-svg-render-manifest' and manifest['format_version']==CONTRACT_VERSION
          and manifest['product_id']==graph['product_id'] and manifest['graph_sha256']==graph['graph_sha256']
          and manifest['authority']=='proposed', 'SVG manifest does not match graph')
    _must(manifest['manifest_sha256']==_hash({k:v for k,v in manifest.items() if k!='manifest_sha256'}),
          'SVG manifest checksum mismatch')
    _must(len(manifest['images'])==len(graph['scenes']),'SVG output missing scenes')
    for row,scene in zip(manifest['images'],graph['scenes']):
        _must(row['scene_id']==scene['scene_id'] and row['step_id']==scene['step_id'],
              'SVG manifest scene identity changed')
        _must(row['file']==scene['step_id']+'.svg','Invalid SVG output filename')
        file=path.parent/row['file']
        raw=file.read_bytes()
        _must(len(raw)<=4*1024*1024 and sha256(raw).hexdigest()==row['sha256'],
              'SVG image content changed')
        _must(raw==_make_svg(graph,scene),'SVG differs from authoritative graph projection')
    return {'svgs_verified':len(graph['scenes']),'product_id':graph['product_id'],
            'graph_sha256':graph['graph_sha256'],'authoritative_structure':'deterministically-verified',
            'user_approval':'not_checked','gameplay_executability':'not_checked'}
