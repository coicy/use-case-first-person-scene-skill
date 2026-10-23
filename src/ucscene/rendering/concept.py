"""WP-04 original-software concept rendering: explicit paid opt-in and provenance.

Creates immutable render packets from validated WP-02 / WP-03 plans. No AI call
occurs during packet creation; the API path is an explicit separate operation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from ..core import SceneError, save_json
from ..provider import ProviderError, edit_openai_image, generate_openai_image
from ..imaging import inspect_image
from ..design.planner import _json_hash, validate_design_plan
from ..design.continuity import validate_consistent_plan

PACKET_VERSION = '1.1'
LEGACY_PACKET_VERSION = '1.0'
MODES = ('explore', 'draft', 'consistent', 'revise')
ORIGINS = ('ucscene-cli', 'conversation-image-generation', 'external-image-model', 'manual-artwork')

# Applied to EVERY individual request, including a plan with multiple candidates.
# This constrains the request; provider compliance still requires real-image QA.
SINGLE_FRAME_PREFIX = (
    'IMAGE DELIVERABLE CONTRACT: EXACTLY ONE FULL-BLEED SOFTWARE SCREEN FOR EXACTLY ONE USE-CASE STEP. '
    'Render a SINGLE continuous application interface or in-game viewport at ONE instant. '
    'Individual in-app panes and game HUD are allowed; multiple separate screenshots are NOT. '
    'NO montage, multi-panel board, storyboard, contact sheet, split-screen comparison, '
    'portfolio presentation, numbered steps, captions, annotations, headings outside the UI, '
    'device mockups, decorative frame or presentation background.\n'
)
SINGLE_FRAME_SUFFIX = (
    '\nFINAL COMPOSITION CHECK: Output ONLY the single software/game framebuffer for THIS step. '
    'Use every pixel for the same application state. '
    'No neighboring steps, no before/after comparison, no alternative candidates, '
    'no collage, no infographic, no outside-software captions.'
)



def _identity_line(product_id: str, item: dict[str, Any]) -> str:
    """Exact, machine-verifiable route from a chosen new product to one request.

    Encode values as JSON, so a newline in a user-supplied ID cannot silently
    make a second prompt directive. The line itself is not a permission token.
    """
    binding = {key: str(item[key]) for key in ('variant_id', 'scene_id', 'step_id')}
    binding['product_id'] = product_id
    return 'TARGET IDENTITY JSON: ' + json.dumps(binding, ensure_ascii=False,
                                                 sort_keys=True, separators=(',', ':'))


def _digest(d: dict[str, Any]) -> str:
    return _json_hash({k: v for k, v in d.items() if k != 'packet_sha256'})


def make_render_packet(plan: dict[str, Any], *, mode: str,
                       variant_id: str | None = None, system: dict[str, Any] | None = None,
                       brief: dict[str, Any] | None = None, change_request: str | None = None,
                       step_ids: list[str] | None = None) -> dict[str, Any]:
    """Build an explicit rendering queue; reject stale/mismatched design plans."""
    if mode not in MODES:
        raise SceneError('Unsupported concept render mode')
    if step_ids is not None and (not step_ids or len(step_ids) != len(set(step_ids))):
        raise SceneError('Step IDs must be nonempty and unique')
    if mode == 'consistent':
        if system is None or brief is None:
            raise SceneError('consistent mode requires both --system and --brief')
        validate_consistent_plan(plan, system=system, brief=brief)
        if variant_id or change_request:
            raise SceneError('consistent mode cannot select new design variants or change locked design')
        candidates = [('APPROVED-' + system['selected_variant_id'], plan['scenes'])]
        product_id = plan['product_id']
        ds_sha = system['digest_sha256']
        rev = system['revision']
        authority = 'approved-design-system-self-attested'
    else:
        if system is not None or brief is not None:
            raise SceneError('DesignSystem is only used in consistent mode; changing it requires WP-03 revision')
        validate_design_plan(plan)
        choices = {c['id']: c for c in plan['candidates']}
        if mode == 'explore':
            if variant_id is not None:
                raise SceneError('explore mode compares ALL candidate variants; omit --variant')
            candidates = [(c['id'], c['screens']) for c in plan['candidates']]
        else:
            if not variant_id or variant_id not in choices:
                raise SceneError('draft/revise mode requires a valid --variant')
            candidates = [(variant_id, choices[variant_id]['screens'])]
        product_id = plan['product_id']
        ds_sha, rev = None, None
        authority = 'proposal-unapproved'
    if mode == 'revise':
        if not isinstance(change_request, str) or not change_request.strip():
            raise SceneError('revise mode requires a nonempty --change-request')
        if len(change_request) > 2500:
            raise SceneError('Revision request exceeds maximum length')
    elif change_request:
        raise SceneError('--change-request only applies to revise mode')
    available_steps = {s['step_id'] for _, screens in candidates for s in screens}
    if step_ids and set(step_ids) - available_steps:
        raise SceneError('Unknown selected step(s): ' + ','.join(sorted(set(step_ids)-available_steps)))
    items = []
    for candidate_id, screens in candidates:
        for screen in screens:
            if step_ids and screen['step_id'] not in step_ids:
                continue
            prompt = screen['prompt']
            if mode == 'revise':
                prompt += ('\nTARGETED REVISION REQUEST (UNAPPROVED PROPOSAL; preserve original source requirements'
                           ' and the selected candidate layout/navigation): ' + change_request.strip())
            identity = {'variant_id': candidate_id, 'scene_id': screen['scene_id'], 'step_id': screen['step_id']}
            prompt = SINGLE_FRAME_PREFIX + _identity_line(product_id, identity) + '\n' + prompt + SINGLE_FRAME_SUFFIX
            pid = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
            items.append({
                'variant_id': candidate_id,
                'scene_id': screen['scene_id'],
                'step_id': screen['step_id'],
                'state': screen['state'],
                'flow': screen['flow'],
                'required_evidence': list(screen['required_evidence']),
                'required_ui_text': list(screen['required_ui_text']),
                'requirement_ids': list(screen['requirement_ids']),
                'design_decision_ids': list(screen['design_decision_ids']),
                'prompt': prompt,
                'prompt_sha256': pid,
            })
    if not items:
        raise SceneError('No scenes selected for rendering')
    packet = {
        'format_version': PACKET_VERSION, 'kind': 'concept-render-packet',
        'product_id': product_id, 'mode': mode,
        'source_plan_sha256': _json_hash(plan),
        'design_system_sha256': ds_sha, 'design_system_revision': rev,
        'design_authority': authority,
        'change_request': change_request.strip() if mode == 'revise' else None,
        'items': items,
        'image_generation_status': 'not_started',
        'note': 'A render packet is a request plan, NOT evidence that images exist or designs are user approved.',
    }
    packet['packet_sha256'] = _digest(packet)
    return verify_render_packet(packet)


def verify_render_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict) or set(packet) != {
        'format_version','kind','product_id','mode','source_plan_sha256',
        'design_system_sha256','design_system_revision','design_authority',
        'change_request','items','image_generation_status','note','packet_sha256',
    } or packet['format_version'] not in (PACKET_VERSION, LEGACY_PACKET_VERSION) or packet['kind'] != 'concept-render-packet':
        raise SceneError('Invalid concept render packet')
    if packet['mode'] not in MODES or packet['image_generation_status'] != 'not_started':
        raise SceneError('Invalid render mode/status')
    if packet['mode'] == 'consistent':
        if packet['design_authority'] != 'approved-design-system-self-attested' or not packet['design_system_sha256']:
            raise SceneError('Missing approved design baseline provenance')
    elif packet['design_system_sha256'] is not None or packet['design_system_revision'] is not None or packet['design_authority'] != 'proposal-unapproved':
        raise SceneError('Candidate proposals must not claim a DesignSystem approval')
    if packet['mode'] == 'revise' and not packet['change_request']:
        raise SceneError('Missing revision request')
    if not isinstance(packet['items'], list) or not packet['items']:
        raise SceneError('Render packet has no images to produce')
    seen = set()
    for i in packet['items']:
        if not isinstance(i, dict) or set(i) != {
            'variant_id','scene_id','step_id','state','flow','required_evidence',
            'required_ui_text','requirement_ids','design_decision_ids','prompt','prompt_sha256'
        }:
            raise SceneError('Invalid render item contract')
        key=(i['variant_id'],i['scene_id'])
        if key in seen:
            raise SceneError('Repeated variant and scene')
        seen.add(key)
        if not isinstance(i['prompt'],str) or not i['prompt'].strip():
            raise SceneError('Empty image prompt')
        if hashlib.sha256(i['prompt'].encode('utf-8')).hexdigest()!=i['prompt_sha256']:
            raise SceneError('Render prompt digest mismatch')
        if not all(isinstance(i[k],list) for k in ('required_evidence','required_ui_text','requirement_ids','design_decision_ids')):
            raise SceneError('Render item requirement fields invalid')
        if not i['prompt'].startswith(SINGLE_FRAME_PREFIX) or not i['prompt'].endswith(SINGLE_FRAME_SUFFIX):
            raise SceneError('Single-frame render contract missing; regenerate the concept packet')
        if packet['format_version'] == PACKET_VERSION:
            expected_prefix = SINGLE_FRAME_PREFIX + _identity_line(packet['product_id'],i) + '\n'
            if not i['prompt'].startswith(expected_prefix):
                raise SceneError('Target product/scene/step identity mismatch in submitted prompt')
        if 'software-only' not in i['prompt'].lower():
            raise SceneError('Rendered frame must remain entirely in software')
    if packet['packet_sha256'] != _digest(packet):
        raise SceneError('Render packet integrity mismatch')
    return packet


def _safe_id(s: str) -> str:
    name = re.sub(r'[^A-Za-z0-9_.-]+','_',s).strip('._')
    if not name or len(name)>160:
        raise SceneError('Unsafe render output filename')
    return name


def render_concepts(packet: dict[str, Any], out_dir: str | Path, *,
                    execute: bool = False, max_images: int | None = None,
                    model: str = 'gpt-image-1.5', size: str = '1536x1024',
                    quality: str = 'medium', reference_image: str | Path | None = None,
                    chain: bool = False,
                    generate_fn: Callable[..., dict[str, Any]] | None = None,
                    edit_fn: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    """No paid calls without --execute, caller-supplied cap and configured key.

    Callable injection is for local tests; CLI always uses real provider calls.
    """
    verify_render_packet(packet)
    if execute and packet['format_version'] != PACKET_VERSION:
        raise SceneError('Legacy render packet has no target identity lock; regenerate packet before paid API execution')
    if type(execute) is not bool or type(chain) is not bool:
        raise SceneError('execute/chain must be boolean')
    count = len(packet['items'])
    if execute and (type(max_images) is not int or max_images < count or max_images > 12):
        raise SceneError(f'--execute requires --max-images >= {count} and <= 12 to explicitly cap potential paid requests')
    if max_images is not None and (type(max_images) is not int or max_images < 1 or max_images > 12):
        raise SceneError('max_images must be in 1..12')
    if chain and packet['mode'] == 'explore':
        raise SceneError('Sequential-chain reference cannot mix competing layout variants')
    if chain and reference_image:
        raise SceneError('Choose chain or fixed reference, not both')
    if not isinstance(model,str) or not model.strip() or size not in ('1024x1024','1536x1024','1024x1536','auto') or quality not in ('auto','low','medium','high'):
        raise SceneError('Unsupported image model configuration')
    reference = Path(reference_image).resolve() if reference_image else None
    reference_sha = inspect_image(reference)['sha256'] if reference else None
    if execute and not os.environ.get('OPENAI_API_KEY') and generate_fn is None and edit_fn is None:
        raise ProviderError('OPENAI_API_KEY missing. The render packet is valid, but no image request was sent.')
    output = Path(out_dir).resolve()
    names = [_safe_id(i['variant_id'])+'--'+_safe_id(i['scene_id'])+'.png' for i in packet['items']]
    if len(set(names)) != len(names):
        raise SceneError('Render file name collision')
    images = []
    report = {
        'format_version':'1.0', 'kind':'concept-generation-report',
        'product_id':packet['product_id'], 'mode':packet['mode'],
        'source_packet_sha256':packet['packet_sha256'],
        'source_plan_sha256':packet['source_plan_sha256'],
        'design_system_sha256':packet['design_system_sha256'],
        'design_system_revision':packet['design_system_revision'],
        'reference_sha256':reference_sha,
        'generation_origin':'ucscene-cli' if execute else 'none',
        'model':model,'size':size,'quality':quality,
        'status':'pending' if not execute else 'running',
        'images':images,
        'warning':'Image file integrity is not visual correctness. Design approval is never inferred from generation.',
    }
    output.mkdir(parents=True,exist_ok=True)
    if not execute:
        for item,name in zip(packet['items'],names):
            images.append({'variant_id':item['variant_id'],'scene_id':item['scene_id'],
                           'step_id':item['step_id'],'prompt_sha256':item['prompt_sha256'],
                           'path':name, 'status':'not_generated'})
        save_json(output/'generation-report.json',report)
        return report
    gen=generate_fn or generate_openai_image
    edit=edit_fn or edit_openai_image
    previous=None
    for item,name in zip(packet['items'],names):
        filename=output/name
        if filename.exists():
            raise SceneError('Refusing to overwrite existing image: '+str(filename))
        source=reference or (previous if chain else None)
        try:
            if source:
                meta=edit(item['prompt'],str(source),str(filename),model=model,size=size,quality=quality)
            else:
                meta=gen(item['prompt'],str(filename),model=model,size=size,quality=quality)
            img=inspect_image(filename)
            images.append({
                'variant_id':item['variant_id'],'scene_id':item['scene_id'],
                'step_id':item['step_id'],'product_id':packet['product_id'],
                'identity_bound':packet['format_version']==PACKET_VERSION,
                'step_prompt_sha256':hashlib.sha256(item['prompt'].encode('utf-8')).hexdigest(),
                'prompt_sha256':item['prompt_sha256'],
                'path':name, 'status':'generated', 'sha256':img['sha256'],
                'width':img['width'],'height':img['height'],
                'reference_sha256':inspect_image(source)['sha256'] if source else None,
            })
            previous=filename
            save_json(output/'generation-report.json',report)
        except (OSError,ValueError,SceneError,ProviderError):
            report['status']='incomplete'
            save_json(output/'generation-report.json',report)
            raise
    report['status']='completed'
    save_json(output/'generation-report.json',report)
    return report


def verify_generation_report(packet: dict[str, Any], report: dict[str, Any], images_dir: str | Path) -> dict[str, Any]:
    verify_render_packet(packet)
    if not isinstance(report,dict) or report.get('source_packet_sha256')!=packet['packet_sha256']:
        raise SceneError('Generation report has wrong source packet')
    expected={(x['variant_id'],x['scene_id']):x for x in packet['items']}
    results=report.get('images')
    if not isinstance(results,list) or len(results)>len(expected):
        raise SceneError('Generation report item count invalid')
    checked=0
    for item in results:
        key=(item.get('variant_id'),item.get('scene_id'))
        if key not in expected or item.get('prompt_sha256')!=expected[key]['prompt_sha256']:
            raise SceneError('Generated image does not match an original scene prompt')
        if item.get('status')=='generated' and packet['format_version']==PACKET_VERSION:
            if (item.get('product_id')!=packet['product_id']
                    or item.get('identity_bound') is not True
                    or item.get('step_prompt_sha256')!=expected[key]['prompt_sha256']):
                raise SceneError('Generated image lacks matching product identity or actual submitted prompt')
        if item.get('status')=='generated':
            path=Path(item.get('path',''))
            if path.is_absolute() or path.name!=str(path) or path.suffix.lower()!='.png':
                raise SceneError('Unsafe generated image path')
            info=inspect_image(Path(images_dir)/path)
            if (info['sha256'],info['width'],info['height']) != (item.get('sha256'),item.get('width'),item.get('height')):
                raise SceneError('Generated image file changed after recording')
            checked+=1
        elif item.get('status')!='not_generated':
            raise SceneError('Unsupported render item status')
    if report.get('status')=='completed' and checked!=len(expected):
        raise SceneError('Completed generation report is missing images')
    return {'image_integrity_verified':checked, 'expected_images':len(expected),
            'visual_quality':'not_evaluated', 'human_approval':'not_checked'}
