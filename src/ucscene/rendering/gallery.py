"""Human-reviewed concept gallery: copies real image bytes and preserves provenance.

Imported external images never claim to have been created by CLI prompts.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path
from typing import Any

from ..core import SceneError, save_json
from ..imaging import inspect_image
from .concept import ORIGINS, verify_render_packet, verify_generation_report


def _safe_file(base: Path, filename: str) -> Path:
    if not isinstance(filename, str) or not filename or Path(filename).is_absolute():
        raise SceneError('Image path must be a safe relative path')
    root = base.resolve()
    path = (root/filename).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise SceneError('Image missing or outside image root: '+filename)
    return path


def build_concept_gallery(packet: dict[str, Any], images_dir: str | Path,
                          out_dir: str | Path, *, selection: dict[str, Any] | None = None,
                          generation_report: dict[str, Any] | None = None) -> dict[str, Any]:
    verify_render_packet(packet)
    if (selection is None) == (generation_report is None):
        raise SceneError('Pass exactly one of --selection (external images) or --report (CLI images)')
    originals = {(v['variant_id'],v['scene_id']):v for v in packet['items']}
    if generation_report is not None:
        verification=verify_generation_report(packet,generation_report,images_dir)
        if generation_report.get('status')!='completed' or verification['image_integrity_verified']!=len(originals):
            raise SceneError('CLI image gallery requires a COMPLETED validated generation report')
        picks=[{
            'variant_id':x['variant_id'], 'scene_id':x['scene_id'], 'image':x['path'],
            'origin':'ucscene-cli', 'notes':'CLI-generated PNG; image contents not human-verified',
            'generation_prompt_sha256':x['prompt_sha256'],
        } for x in generation_report['images']]
    else:
        if not isinstance(selection,dict) or set(selection)!={'samples'} or not isinstance(selection['samples'],list) or not selection['samples']:
            raise SceneError('Selection must contain non-empty samples list')
        picks=selection['samples']
    selected=set()
    jobs=[]
    for sample in picks:
        if not isinstance(sample,dict) or not {'variant_id','scene_id','image','origin'}<=set(sample):
            raise SceneError('Gallery sample missing required fields')
        variant,scene_id=sample['variant_id'],sample['scene_id']
        key=(variant,scene_id)
        if key not in originals or key in selected:
            raise SceneError('Gallery samples must be distinct known scene/variant pairs')
        selected.add(key)
        origin=sample['origin']
        if origin not in ORIGINS:
            raise SceneError('Unsupported provenance origin')
        if selection is not None and origin=='ucscene-cli':
            raise SceneError('External selection cannot claim ucscene-cli generation; supply validated --report')
        if selection is not None and 'generation_prompt_sha256' in sample:
            raise SceneError('External image prompt hash cannot be asserted as verified CLI prompt provenance')
        src=_safe_file(Path(images_dir),sample['image'])
        info=inspect_image(src)
        label=f"{variant}--{scene_id}"
        filename=f"img-{len(jobs)+1:03d}.png"
        jobs.append((src,filename,{
            'variant_id':variant,'scene_id':scene_id,
            'step_id':originals[key]['step_id'],
            'state':originals[key]['state'],'flow':originals[key]['flow'],
            'origin':origin,
            'source_prompt_sha256':originals[key]['prompt_sha256'],
            'generation_prompt_sha256':sample.get('generation_prompt_sha256') if generation_report else None,
            'prompt_matches_source': True if generation_report else 'not_verified',
            'required_evidence':originals[key]['required_evidence'],
            'required_ui_text':originals[key]['required_ui_text'],
            'image':'images/'+filename,'sha256':info['sha256'],
            'width':info['width'],'height':info['height'],
            'notes':sample.get('notes',''),
            'human_verdict':'pending',
        }))
    output=Path(out_dir).resolve()
    if output.exists() and any(output.iterdir()):
        raise SceneError('Gallery output must be a new/empty directory; refusing to replace existing review artifacts')
    output.mkdir(parents=True,exist_ok=True)
    (output/'images').mkdir(exist_ok=True)
    for src,filename,_ in jobs:
        shutil.copyfile(src,output/'images'/filename)
    manifest={
        'format_version':'1.0','kind':'original-concept-acceptance-gallery',
        'product_id':packet['product_id'],'mode':packet['mode'],
        'packet_sha256':packet['packet_sha256'],
        'design_system_sha256':packet['design_system_sha256'],
        'images':[j[2] for j in jobs],
        'missing_scene_variants':sorted([{'variant_id':x[0],'scene_id':x[1]} for x in set(originals)-selected],key=lambda x:(x['variant_id'],x['scene_id'])),
        'approval':'pending-human-review',
        'notice':'This gallery does not assign visual pass scores or user design approval. External images are not verified to follow the current CLI prompt.',
    }
    save_json(output/'manifest.json',manifest)
    (output/'index.html').write_text(_html(manifest),encoding='utf-8')
    verify_concept_gallery(output/'manifest.json')
    return manifest


def verify_concept_gallery(path: str | Path) -> dict[str, Any]:
    dest=Path(path).resolve()
    try: data=json.loads(dest.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc: raise SceneError('Invalid concept gallery manifest') from exc
    if not isinstance(data,dict) or data.get('kind')!='original-concept-acceptance-gallery' or data.get('format_version')!='1.0':
        raise SceneError('Unknown concept gallery format')
    images=data.get('images')
    if not isinstance(images,list) or not images:
        raise SceneError('Empty concept gallery')
    for item in images:
        if item.get('human_verdict')!='pending':
            raise SceneError('Gallery manifests cannot imply human approval')
        rel=item.get('image','')
        if not isinstance(rel,str) or len(Path(rel).parts)!=2 or Path(rel).parts[0]!='images' or not Path(rel).name.endswith('.png'):
            raise SceneError('Unsafe gallery path')
        info=inspect_image(dest.parent/rel)
        if (info['sha256'],info['width'],info['height'])!=(item.get('sha256'),item.get('width'),item.get('height')):
            raise SceneError('Gallery source image changed')
        if item.get('origin')!='ucscene-cli' and item.get('prompt_matches_source') != 'not_verified':
            raise SceneError('External gallery image must not claim source prompt identity')
    return {'image_integrity_verified':len(images),'human_verdict':'not_checked',
            'visual_quality':'not_evaluated','software_frame':'not_evaluated'}


def _html(manifest: dict[str, Any]) -> str:
    payload=json.dumps(manifest,ensure_ascii=False).replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    # Embedded model/source text is rendered via textContent only, not innerHTML.
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>新软件概念场景验收</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#111923;color:#eef2f8}
body{max-width:1250px;margin:0 auto;padding:24px}h1{font-size:24px;margin-bottom:4px}
.note{color:#a6b8c9;font-size:13px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px;margin-top:24px}
.card{border:1px solid #35465c;border-radius:12px;overflow:hidden;background:#1c2938}
.card img{display:block;width:100%;height:auto;background:#000}.body{padding:15px}.title{font-weight:650;font-size:16px}
.meta{font-size:12px;color:#a6b8c9;line-height:1.8}.check{font-size:13px;margin:10px 0}
textarea,select{width:100%;box-sizing:border-box;background:#0c1420;color:#eff6ff;border:1px solid #576b81;border-radius:7px;padding:8px}
textarea{min-height:62px}label{display:block;margin:9px 0;font-size:12px}button{background:#5a8db8;color:white;border:0;border-radius:6px;padding:10px 16px;cursor:pointer}
</style></head><body><h1>原创软件 / 游戏用例概念图验收</h1>
<div class="note">单张图仅展示一个用例步骤，不得是九宫格、演示板或分镜。只呈现软件内部内容。请核对需求覆盖、交互清晰、文字可读、视觉品质、多图一致性。选择和评语仅保存在当前页面内存中；导出文件后才可持续保存。不能代替产品批准记录。</div>
<button id="export">导出人工审查 JSON</button><div id="gallery" class="grid"></div>
<script>const packet=''' +payload+''';
const checks=['单张图仅一个用例步骤（不是分镜/展示板）','需求覆盖','操作可理解','信息与文字清晰','视觉与构图','跨步骤一致性','仅软件内部画面'];
const reviews={};const host=document.querySelector('#gallery');
function node(tag,cl,txt){const el=document.createElement(tag);if(cl)el.className=cl;if(txt!==undefined)el.textContent=txt;return el}
for (const item of packet.images){const key=item.variant_id+' / '+item.scene_id;const card=node('div','card');
const img=node('img');img.src=item.image;img.alt=key;card.appendChild(img);
const body=node('div','body');body.appendChild(node('div','title',key));
body.appendChild(node('div','meta',item.origin+' · '+item.state+' · '+item.sha256.slice(0,12)));
body.appendChild(node('div','check','用例证据：'+(item.required_evidence.join('；')||'按动作状态检查')));
body.appendChild(node('div','meta','来源 prompt 匹配：'+item.prompt_matches_source+'；软件概念图，不是可运行截图'));
const select=node('select');for(const [val,text] of [['pending','未审查'],['pass','通过'],['revise','需要修改'],['uncertain','不确定']]){const opt=node('option',null,text);opt.value=val;select.appendChild(opt)}
const notes=node('textarea');notes.placeholder='注明未满足的用例、需要修改的控件或布局…';
const fields={};for(const field of checks){const lab=node('label',null,field);const choice=node('select');for(const [v,t] of [['unrated','尚未评分'],['pass','通过'],['fail','不通过'],['uncertain','不确定']]){const opt=node('option',null,t);opt.value=v;choice.appendChild(opt)}lab.appendChild(choice);body.appendChild(lab);fields[field]=choice}
body.appendChild(node('div','meta','总评'));body.appendChild(select);body.appendChild(notes);
reviews[key]={item,select,notes,fields};card.appendChild(body);host.appendChild(card)}
document.querySelector('#export').addEventListener('click',()=>{
const result={format_version:'1.0',kind:'human-concept-review',product_id:packet.product_id,
packet_sha256:packet.packet_sha256,reviewer:'user-entered-in-browser',
ratings:Object.entries(reviews).map(([key,v])=>({variant_id:v.item.variant_id,scene_id:v.item.scene_id,
image_sha256:v.item.sha256,verdict:v.select.value,notes:v.notes.value,
dimensions:Object.fromEntries(Object.entries(v.fields).map(([field,ctl])=>[field,ctl.value]))}))};
const blob=new Blob([JSON.stringify(result,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='human-concept-review.json';a.click();URL.revokeObjectURL(a.href);
});</script></body></html>'''
