"""Agent-native image handoff and PNG import. No independent API key required."""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
from ..core import SceneError, save_json
from ..imaging import inspect_image
from .concept import _safe_id, verify_render_packet

def _digest(obj, field):
    raw=json.dumps({k:v for k,v in obj.items() if k!=field},ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def _asset(root, rel):
    if not isinstance(rel,str) or not rel or Path(rel).is_absolute():
        raise SceneError('Unsafe agent asset path')
    base=Path(root).resolve()
    p=(base/rel).resolve()
    if not p.is_relative_to(base) or not p.is_file():
        raise SceneError('Agent asset missing or outside allowed directory')
    return p

def _new_dir(root):
    root=Path(root).resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise SceneError('Agent output must be a new/empty directory')
    return root

def export_agent_handoff(packet,output_dir):
    verify_render_packet(packet)
    if packet['format_version']!='1.1':
        raise SceneError('Agent handoff needs an identity-locked packet v1.1')
    out=_new_dir(output_dir)
    tasks=[]
    for index,item in enumerate(packet['items'],1):
        tasks.append({
            'product_id':packet['product_id'], 'variant_id':item['variant_id'],
            'scene_id':item['scene_id'],'step_id':item['step_id'],
            'source_packet_sha256':packet['packet_sha256'],
            'prompt_file':f"tasks/task-{index:03d}-{_safe_id(item['step_id'])}.txt",
            'prompt_sha256':item['prompt_sha256']})
    if len(set(t['prompt_file'] for t in tasks))!=len(tasks):
        raise SceneError('Agent handoff task names collide')
    manifest={'format_version':'1.0','kind':'agent-image-handoff',
        'product_id':packet['product_id'],'source_packet_sha256':packet['packet_sha256'],
        'provider_priority':'host-agent-native-first','execution_status':'not_executed',
        'tasks':tasks,'instructions':('Agent must call its OWN image tool once per task using ONLY that prompt; '
            'one product, one scene and one step per image. Save actual PNGs and import them. '
            'Standalone API calls are explicit user-authorized fallback only.'),
        'notice':'Export does not produce an image or establish user approval.'}
    manifest['manifest_sha256']=_digest(manifest,'manifest_sha256')
    out.mkdir(parents=True)
    (out/'tasks').mkdir()
    for task,item in zip(tasks,packet['items']):
        (out/task['prompt_file']).write_bytes(item['prompt'].encode('utf-8'))
    save_json(out/'manifest.json',manifest)
    return verify_agent_handoff(packet,out/'manifest.json')

def verify_agent_handoff(packet,manifest_path):
    verify_render_packet(packet)
    manifest_path=Path(manifest_path).resolve()
    try:m=json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise SceneError('Invalid Agent handoff manifest') from exc
    if (not isinstance(m,dict) or m.get('kind')!='agent-image-handoff'
        or m.get('format_version')!='1.0'
        or m.get('product_id')!=packet['product_id']
        or m.get('source_packet_sha256')!=packet['packet_sha256']
        or m.get('execution_status')!='not_executed'
        or m.get('manifest_sha256')!=_digest(m,'manifest_sha256')):
        raise SceneError('Wrong/tampered Agent handoff')
    tasks=m.get('tasks')
    if not isinstance(tasks,list) or len(tasks)!=len(packet['items']):
        raise SceneError('Agent task count differs from source')
    seen=set()
    for task,item in zip(tasks,packet['items']):
        if (task.get('product_id')!=packet['product_id']
            or task.get('source_packet_sha256')!=packet['packet_sha256']
            or any(task.get(k)!=item[k] for k in ('variant_id','scene_id','step_id'))
            or task.get('prompt_sha256')!=item['prompt_sha256']):
            raise SceneError('Agent task identity/expected prompt mismatch')
        name=task.get('prompt_file')
        if not isinstance(name,str) or not name.startswith('tasks/') or name in seen:
            raise SceneError('Agent prompt file missing/duplicated')
        seen.add(name)
        if _asset(manifest_path.parent,name).read_bytes()!=item['prompt'].encode('utf-8'):
            raise SceneError('Agent prompt bytes differ from signed-off scene task')
    return m

def import_agent_images(packet,handoff_path,mapping_path,images_dir,output_dir):
    handoff=verify_agent_handoff(packet,handoff_path)
    mapping_path=Path(mapping_path).resolve()
    try:m=json.loads(mapping_path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise SceneError('Invalid Agent image mapping') from exc
    if not isinstance(m,dict) or set(m)!={'images'} or not isinstance(m['images'],list) or not m['images']:
        raise SceneError('Agent mapping must have a nonempty images array')
    jobs=[];seen=set()
    tasks={(t['variant_id'],t['scene_id']):t for t in handoff['tasks']}
    if len(m['images'])>len(tasks):raise SceneError('Too many Agent images')
    for num,row in enumerate(m['images'],1):
        if not isinstance(row,dict) or set(row)-{'variant_id','scene_id','file','tool','tool_call_ref','submitted_prompt_file'}:
            raise SceneError('Unknown Agent mapping fields')
        key=(row.get('variant_id'),row.get('scene_id'))
        if key not in tasks or key in seen:raise SceneError('Unknown or duplicate Agent scene')
        seen.add(key)
        tool=row.get('tool')
        if not isinstance(tool,str) or not tool.strip() or len(tool)>160:
            raise SceneError('Declare the actual host-Agent image tool')
        call=row.get('tool_call_ref')
        if call is not None and (not isinstance(call,str) or len(call)>240):
            raise SceneError('Bad host tool call reference')
        source=_asset(images_dir,row.get('file'))
        if source.suffix.lower()!='.png' or source.read_bytes()[:8]!=bytes.fromhex('89504e470d0a1a0a'):
            raise SceneError('Host Agent import requires real PNG bytes')
        info=inspect_image(source)
        sent=row.get('submitted_prompt_file')
        actual=None;provenance='not_verified'
        if sent is not None:
            actual=hashlib.sha256(_asset(mapping_path.parent,sent).read_bytes()).hexdigest()
            provenance=('matches-handoff-self-reported' if actual==tasks[key]['prompt_sha256']
                        else 'differs-from-handoff-self-reported')
        filename=f'image-{num:03d}.png'
        jobs.append((source,filename,{
          'product_id':packet['product_id'],'variant_id':key[0],
          'scene_id':key[1],'step_id':tasks[key]['step_id'],
          'origin':'agent-native-image-tool','tool':tool,'tool_call_ref':call,
          'image':'images/'+filename,'sha256':info['sha256'],
          'width':info['width'],'height':info['height'],
          'source_prompt_sha256':tasks[key]['prompt_sha256'],
          'submitted_prompt_sha256':actual,'prompt_provenance':provenance,
          'provenance_verification':'self-reported-not-third-party-attested',
          'visual_quality':'not_evaluated','human_design_approval':'not_checked'}))
    out=_new_dir(output_dir);out.mkdir(parents=True);(out/'images').mkdir()
    for src,name,_ in jobs:shutil.copyfile(src,out/'images'/name)
    result={'format_version':'1.0','kind':'agent-image-import',
        'product_id':packet['product_id'],
        'source_packet_sha256':packet['packet_sha256'],
        'handoff_sha256':handoff['manifest_sha256'],
        'images':[r for _,_,r in jobs],
        'missing_tasks':[{'variant_id':t['variant_id'],'scene_id':t['scene_id']}
            for t in handoff['tasks'] if (t['variant_id'],t['scene_id']) not in seen],
        'notice':'Hashes prove byte integrity only, not a real Agent invocation or image quality.'}
    result['import_sha256']=_digest(result,'import_sha256')
    save_json(out/'manifest.json',result)
    save_json(out/'gallery-selection.json',{'samples':[
        {'variant_id':r['variant_id'],'scene_id':r['scene_id'],
         'image':Path(r['image']).name,'origin':'agent-native-image-tool',
         'notes':'Host-tool self report: '+r['tool']+'. Prompt: '+r['prompt_provenance']}
         for r in result['images']]})
    verify_agent_import(packet,handoff_path,out/'manifest.json')
    return result

def verify_agent_import(packet,handoff_path,manifest_path):
    handoff=verify_agent_handoff(packet,handoff_path)
    path=Path(manifest_path).resolve()
    try:m=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise SceneError('Invalid Agent image manifest') from exc
    if (not isinstance(m,dict) or m.get('kind')!='agent-image-import'
        or m.get('format_version')!='1.0'
        or m.get('product_id')!=packet['product_id']
        or m.get('source_packet_sha256')!=packet['packet_sha256']
        or m.get('handoff_sha256')!=handoff['manifest_sha256']
        or m.get('import_sha256')!=_digest(m,'import_sha256')):
        raise SceneError('Agent image provenance mismatch')
    tasks={(t['variant_id'],t['scene_id']):t for t in handoff['tasks']}
    rows=m.get('images')
    if not isinstance(rows,list) or not rows or len(rows)>len(tasks):
        raise SceneError('Wrong Agent image count')
    seen=set()
    for row in rows:
        key=(row.get('variant_id'),row.get('scene_id'))
        if key not in tasks or key in seen:raise SceneError('Wrong/duplicate scene in imported PNGs')
        seen.add(key)
        if (row.get('product_id')!=packet['product_id']
            or row.get('step_id')!=tasks[key]['step_id']
            or row.get('source_prompt_sha256')!=tasks[key]['prompt_sha256']
            or row.get('origin')!='agent-native-image-tool'
            or row.get('human_design_approval')!='not_checked'
            or row.get('visual_quality')!='not_evaluated'):
            raise SceneError('Invalid Agent provenance/approval assertion')
        name=row.get('image')
        if not isinstance(name,str) or len(Path(name).parts)!=2 or Path(name).parts[0]!='images' or Path(name).suffix.lower()!='.png':
            raise SceneError('Unsafe imported image path')
        image=inspect_image(_asset(path.parent,name))
        if (image['sha256'],image['width'],image['height'])!=(row.get('sha256'),row.get('width'),row.get('height')):
            raise SceneError('Agent image changed after import')
        submitted=row.get('submitted_prompt_sha256')
        status=row.get('prompt_provenance')
        if (status=='not_verified' and submitted is not None
            or status=='matches-handoff-self-reported' and submitted!=tasks[key]['prompt_sha256']
            or status=='differs-from-handoff-self-reported' and (not isinstance(submitted,str) or submitted==tasks[key]['prompt_sha256'])
            or status not in ('not_verified','matches-handoff-self-reported','differs-from-handoff-self-reported')):
            raise SceneError('Invalid Agent submitted prompt provenance')
    expected=set(tasks)-seen
    if (not isinstance(m.get('missing_tasks'),list)
        or {(r['variant_id'],r['scene_id']) for r in m['missing_tasks']}!=expected):
        raise SceneError('Incorrect incomplete Agent import ledger')
    return {'images_verified':len(rows),'expected_images':len(tasks),
            'remaining_tasks':len(expected),'visual_quality':'not_evaluated',
            'human_design_approval':'not_checked','prompt_use_verified':'no'}
