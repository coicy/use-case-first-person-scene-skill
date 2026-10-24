"""Dependency-free semantic scene-graph -> SVG renderer / structural verifier.

Prototype, not yet part of the project's main repository.
This is not a runnable game or an interactive GUI implementation.
"""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

NS="http://www.w3.org/2000/svg"
UCNS="https://example.invalid/ucscene/schema/semantic-svg"
ET.register_namespace('',NS)
ET.register_namespace('uc',UCNS)
def tag(name):return '{%s}%s'%(NS,name)
ROOT=Path(__file__).resolve().parent

class ContractError(ValueError):pass

def stablehash(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(doc):
    if doc.get('kind')!='semantic-svg-scene-contract' or doc.get('schema_version')!='0.1-prototype':raise ContractError('Unsupported contract')
    if doc.get('authority')!='demonstration-proposal-not-user-approved':raise ContractError('Prototype may not assert design approval')
    vw,vh=doc['viewport']['width'],doc['viewport']['height']
    items=doc['design']['components']; ids=[x['id'] for x in items]
    if len(ids)!=len(set(ids)):raise ContractError('Duplicate component IDs')
    for item in items:
        x,y,w,h=item['rect']
        if not all(isinstance(n,int) for n in (x,y,w,h)) or min(x,y)<0 or w<=0 or h<=0 or x+w>vw or y+h>vh:
            raise ContractError('Component outside viewport: '+item['id'])
    must={'hud','world','selected-farm','inspector','worker-counter','production-counter','assign-button','commands'}
    if not must.issubset(ids):raise ContractError('Required component missing')
    c={x['id']:x for x in items}
    if c['world']['rect'][0]+c['world']['rect'][2] != c['inspector']['rect'][0]:raise ContractError('World and inspector adjacency broken')
    if c['inspector'].get('bind')!='selected_object' or c['worker-counter'].get('bind')!='objects.farm-01.workers' or c['production-counter'].get('bind')!='objects.farm-01.production_per_turn':
        raise ContractError('Incorrect object/data bindings')
    actions={a['id']:a for a in doc['actions']}
    if c['assign-button'].get('action') not in actions:raise ContractError('Unbound action control')
    objects={o['id']:o for o in doc['world_objects']}; farm=objects.get('farm-01')
    if not farm or farm['type']!='farm' or farm['capacity']<=0:raise ContractError('Missing farm')
    steps=doc['steps']; expected=['STEP-001','STEP-002','STEP-003']
    if [x['id'] for x in steps]!=expected:raise ContractError('Missing or reordered steps')
    for step in steps:
        if step['selected_object']!='farm-01':raise ContractError('Wrong selected object in '+step['id'])
        f=step['objects']['farm-01']
        if not isinstance(f['workers'],int) or not 0<=f['workers']<=farm['capacity']:raise ContractError('Worker count outside farm capacity')
        if not isinstance(f['production_per_turn'],int) or f['production_per_turn']<0:raise ContractError('Invalid production')
        if not isinstance(step['available_workers'],int) or step['available_workers']<0:raise ContractError('Invalid available workers')
        if step['state'] not in {'in-progress','success'}:raise ContractError('Wrong use-case state')
        if not step['required_evidence']:raise ContractError('Missing evidence')
    before, mid, after=steps
    if (before['objects']!=mid['objects'] or before['available_workers']!=mid['available_workers']):raise ContractError('Inspection changed business state')
    action=actions['assign-worker']
    if after['action_applied']!='assign-worker' or after['state']!='success':raise ContractError('Success step missing action/state')
    if action['target']!='farm-01':raise ContractError('Wrong action target')
    a=before['objects']['farm-01']; b=after['objects']['farm-01'];effect=action['effect']
    if (b['workers']-a['workers']!=effect['workers_delta'] or
        b['production_per_turn']-a['production_per_turn']!=effect['production_delta'] or
        after['available_workers']-before['available_workers']!=effect['available_workers_delta']):
        raise ContractError('Actual state transition does not match action effects')
    if before['available_workers']<1 or a['workers']>=farm['capacity']:raise ContractError('Action precondition violated')
    return doc

def node(parent, name, **attrs):return ET.SubElement(parent,tag(name),{k.replace('_','-'):str(v) for k,v in attrs.items()})
def text(parent,x,y,s,size=16,color='#e8edf7',weight='400',anchor=None):
    args={'x':x,'y':y,'fill':color,'font-family':'Noto Sans CJK SC, Noto Sans, sans-serif','font-size':size,'font-weight':weight}
    if anchor:args['text-anchor']=anchor
    t=node(parent,'text',**args);t.text=str(s);return t

def rect(parent,x,y,w,h,fill,rx=0,stroke=None,sw=1):
    attrs=dict(x=x,y=y,width=w,height=h,fill=fill,rx=rx)
    if stroke:attrs.update(stroke=stroke,stroke_width=sw)
    return node(parent,'rect',**attrs)

def polygon(parent,points,fill,stroke=None,sw=1):
    attrs=dict(points=' '.join(f'{a},{b}' for a,b in points),fill=fill)
    if stroke:attrs.update(stroke=stroke,stroke_width=sw)
    return node(parent,'polygon',**attrs)

def render(doc,step_id):
    validate(doc)
    step=next(x for x in doc['steps'] if x['id']==step_id)
    farm=step['objects']['farm-01']; rw,rh=doc['viewport']['width'],doc['viewport']['height']
    doc_digest=stablehash(doc)
    svg=ET.Element(tag('svg'),{'width':str(rw),'height':str(rh),'viewBox':f'0 0 {rw} {rh}',
        'role':'img','aria-label':f"{doc['title']} / {step['title']}", 'data-product-id':doc['product_id'], 'data-step-id':step_id,
        'data-scene-contract-sha256':doc_digest,'data-proposal-status':'unapproved'})
    title=node(svg,'title');title.text=doc['title']+' — '+step['title']
    desc=node(svg,'desc');desc.text='所有布局、组件标识和业务数字由 scene-contract.json 确定性生成。'
    meta=node(svg,'metadata');ET.SubElement(meta,'{%s}contract-ref'%UCNS,{'sha256':doc_digest,'product-id':doc['product_id'],'step-id':step_id,'authority':'proposal'})
    components={x['id']:x for x in doc['design']['components']}
    groups={}
    for x in sorted(doc['design']['components'],key=lambda c:(c['layer'],doc['design']['components'].index(c))):
        groups[x['id']]=node(svg,'g',id=x['id'],data_role=x['role'],data_binding=x.get('bind',''),data_action=x.get('action',''),data_rect=','.join(map(str,x['rect'])))
    g=groups['world']
    rect(g,0,70,855,576,'#577866')
    # Isometric tiles in a fixed world viewport.
    for i in range(10):
        for j in range(8):
            xx=380+(i-j)*46; yy=120+(i+j)*23
            if xx<-150 or xx>950:continue
            tile='#72966b' if (i+j)%2==0 else '#789b70'
            polygon(g,[(xx,yy),(xx+46,yy+23),(xx,yy+46),(xx-46,yy+23)],tile,stroke='#8ca886')
    # Stream / terrain decoration is intentionally non-authoritative visual styling.
    polygon(g,[(0,395),(130,380),(170,466),(55,540),(0,515)],'#568bb1')
    for xx,yy in [(120,242),(191,312),(662,277),(715,500),(523,516),(250,466)]:
        polygon(g,[(xx,yy-34),(xx-28,yy+18),(xx+28,yy+18)],'#294e42')
        polygon(g,[(xx,yy-54),(xx-23,yy-10),(xx+23,yy-10)],'#3d6851')
        rect(g,xx-4,yy+10,8,20,'#654f3b')
    for x,y in [(160,195),(600,205),(670,370)]:
        polygon(g,[(x-45,y),(x,y-25),(x+45,y),(x,y+25)],'#b98e60',stroke='#e6c18d',sw=2)
        polygon(g,[(x-30,y-3),(x,y-42),(x+30,y-3),(x,y+12)],'#774936')
        rect(g,x-10,y,20,18,'#a67b52')
    # Farm is the same game object in all three steps.
    g=groups['selected-farm'];g.set('data-object-id','farm-01');g.set('data-selected','true')
    polygon(g,[(325,355),(441,290),(580,362),(459,438)],'#bb9652',stroke='#f8d964',sw=5)
    for k in range(5):
        for j in range(3):
            x=353+k*43+j*13;y=337-k*9+j*26
            polygon(g,[(x,y),(x+25,y-12),(x+38,y-5),(x+13,y+8)],'#8c9d45',stroke='#b8ba59')
    polygon(g,[(407,317),(460,285),(506,309),(452,341)],'#c69a6f')
    polygon(g,[(400,316),(452,274),(512,309),(461,336)],'#805341')
    text(g,450,461,'FARM-01  ·  已选中',18,'#fff1a0','700','middle')
    # HUD: all content is display data, not a running UI.
    g=groups['hud'];rect(g,0,0,1200,70,'#182434')
    text(g,28,44,'HAMLET BUILDER',23,'#f3e2b1','700')
    for x,icon,val in [(275,'粮食','240'),(460,'木材','160'),(660,'可用居民',str(step['available_workers']))]:
        rect(g,x,15,155,40,'#293b4a',rx=8)
        text(g,x+13,41,icon,15,'#c3d0df');text(g,x+138,41,val,16,'#ffffff','700','end')
    text(g,1075,42,'第 3 回合',18,'#ccd4df','600')
    g=groups['inspector'];rect(g,855,70,345,650,'#172636')
    rect(g,855,70,345,64,'#223449')
    text(g,881,111,'农场',26,'#ffffff','700');text(g,1168,109,'✕',20,'#a6b6c4','600','end')
    rect(g,879,149,297,74,'#263e4c',rx=8)
    text(g,900,174,'橡树林农场  ·  FARM-01',17,'#f8e5b2','600')
    text(g,900,204,'农田建筑  /  已选中',14,'#c9d5df')
    for i,(label,key) in enumerate([('概览','overview'),('生产','production'),('工人','workers')]):
        x=885+i*95;rect(g,x,244,87,42,'#346a8c' if step['panel']==key else '#23374b',rx=8)
        text(g,x+44,271,label,15,'#fff' if step['panel']==key else '#c3d0dd',anchor='middle')
    g=groups['production-counter'];g.set('data-object-id','farm-01');g.set('data-value',str(farm['production_per_turn']))
    text(g,884,328,'生产效率',16,'#b6c7d9')
    text(g,1158,328,f"{farm['production_per_turn']} / 回合",20,'#ffffff','700','end')
    rect(g,887,340,282,10,'#30495e',rx=5)
    rect(g,887,340,100+25*farm['production_per_turn'],10,'#77b978',rx=5)
    g=groups['worker-counter'];g.set('data-object-id','farm-01');g.set('data-value',str(farm['workers']))
    text(g,884,410,'已分配工人',16,'#b6c7d9')
    text(g,1158,410,f"{farm['workers']} / 4",20,'#ffffff','700','end')
    for i in range(4):
        xx=894+i*59;rect(g,xx,443,43,40,'#64a178' if i<farm['workers'] else '#345066',rx=6)
        text(g,xx+22,468,'人' if i<farm['workers'] else '—',16,'white',anchor='middle')
    g=groups['assign-button']
    available=step['available_workers']>0 and farm['workers']<4
    rect(g,884,530,290,59,'#397eb2' if available else '#53636d',rx=8)
    text(g,1029,567,'分配工人  +' if step_id!='STEP-003' else '已分配工人 ✓',18,'white','700','middle')
    if step_id=='STEP-003':
        rect(groups['inspector'],883,608,293,55,'#234d40',rx=8)
        text(groups['inspector'],1029,642,'成功：工人数增加 1',16,'#bbf1d0','600','middle')
    g=groups['commands'];rect(g,0,646,855,74,'#1b2939')
    for idx,label in enumerate(['建造','生产','居民','研究','道路']):
        xx=22+idx*164;rect(g,xx,660,145,43,'#3d6d92' if label=='生产' else '#2d4052',rx=6)
        text(g,xx+72,688,label,16,'white','600','middle')
    return ET.ElementTree(svg)

def write_outputs(doc,directory):
    validate(doc);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    records=[]
    for step in doc['steps']:
        path=directory/f"{step['id'].lower()}.svg"
        render(doc,step['id']).write(path,encoding='utf-8',xml_declaration=True)
        # Verify the rendered file's identity and bound values against JSON canonical state.
        parsed=ET.parse(path).getroot()
        if parsed.attrib['data-step-id']!=step['id'] or parsed.attrib['data-scene-contract-sha256']!=stablehash(doc):
            raise ContractError('Output SVG contract digest mismatch')
        bound={elem.attrib.get('id'):elem for elem in parsed.iter() if elem.attrib.get('id') in ('selected-farm','worker-counter','production-counter')}
        worker=step['objects']['farm-01']['workers'];prod=step['objects']['farm-01']['production_per_turn']
        if (bound['selected-farm'].attrib['data-object-id']!='farm-01' or
            bound['worker-counter'].attrib['data-value']!=str(worker) or
            bound['production-counter'].attrib['data-value']!=str(prod)):
            raise ContractError('Rendered visual bindings inconsistent with scene contract')
        records.append({'step_id':step['id'],'svg':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'expected_worker_count':worker,'expected_production':prod})
    result={'source_contract_sha256':stablehash(doc),'design_authority':'proposed-not-user-approved','images':records}
    (directory/'render-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    source=json.loads((ROOT/'scene-contract.json').read_text(encoding='utf-8'))
    print(json.dumps(write_outputs(source,ROOT/'renders'),ensure_ascii=False,indent=2))
