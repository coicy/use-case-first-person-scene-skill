"""Offline, audit-grounded single-scene retries without silent image API calls.

Retry instructions are derived ONLY from a checked scene and machine-audit enum
statuses. Untrusted free-form auditor reasons/fixes are intentionally ignored.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from ..core import SceneError
from ..imaging import inspect_image
from .concept import SINGLE_FRAME_PREFIX, SINGLE_FRAME_SUFFIX, _digest, verify_render_packet
from .audit import AUDIT_SCHEMA, AUDIT_VERSION

MAX_RETRY_ATTEMPTS = 2
RETRY_FORMAT = '1.0'


def _hash_json(data: Any) -> str:
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':')).encode('utf-8')).hexdigest()


def verify_retry_manifest(manifest: dict[str, Any], retry_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    keys = {'format_version', 'kind', 'attempt', 'root_packet_sha256', 'parent_packet_sha256',
            'parent_image_sha256', 'audit_sha256', 'retry_packet_sha256', 'variant_id',
            'scene_id', 'repair_categories', 'prompt_sha256', 'manifest_sha256'}
    if not isinstance(manifest, dict) or set(manifest) != keys or manifest.get('kind') != 'concept-retry-manifest' or manifest.get('format_version') != RETRY_FORMAT:
        raise SceneError('Invalid concept retry manifest')
    if type(manifest['attempt']) is not int or not 1 <= manifest['attempt'] <= MAX_RETRY_ATTEMPTS:
        raise SceneError('Invalid retry attempt')
    if manifest['manifest_sha256'] != _hash_json({k: v for k, v in manifest.items() if k != 'manifest_sha256'}):
        raise SceneError('Retry manifest digest mismatch')
    if retry_packet is not None:
        verify_render_packet(retry_packet)
        if manifest['retry_packet_sha256'] != retry_packet['packet_sha256']:
            raise SceneError('Retry manifest does not match retry packet')
        items = retry_packet['items']
        if len(items) != 1 or (items[0]['variant_id'], items[0]['scene_id']) != (manifest['variant_id'], manifest['scene_id']):
            raise SceneError('Retry manifest scene mismatch')
        if manifest['prompt_sha256'] != items[0]['prompt_sha256']:
            raise SceneError('Retry manifest prompt mismatch')
    return manifest


def create_retry_packet(packet: dict[str, Any], audit: dict[str, Any], image_path: str | Path,
                        *, previous_manifest: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Produce ONE new immutable render packet and lineage manifest; NO provider call.

    A second retry requires the signed-by-digest manifest from the previous
    attempt and a fresh audit of that attempt's image. No third retry is allowed
    along a verified chain. User approval remains distinct from visual QA.
    """
    verify_render_packet(packet)
    if not isinstance(audit, dict) or audit.get('kind') != 'concept-visual-audit' or audit.get('format_version') not in ('1.0', AUDIT_VERSION):
        raise SceneError('Retry requires a concept-audit report')
    if audit.get('packet_sha256') != packet['packet_sha256']:
        raise SceneError('Audit belongs to a different render packet')
    matching = [i for i in packet['items'] if i['variant_id'] == audit.get('variant_id') and i['scene_id'] == audit.get('scene_id')]
    if len(matching) != 1:
        raise SceneError('Audited scene is absent or ambiguous')
    item = matching[0]
    if audit.get('step_id') != item['step_id'] or audit.get('prompt_sha256') != item['prompt_sha256']:
        raise SceneError('Audit refers to different step or prompt')
    info = inspect_image(image_path)
    if (audit.get('image_sha256'), audit.get('image_width'), audit.get('image_height')) != (info['sha256'], info['width'], info['height']):
        raise SceneError('Audited image hash or dimensions differ from supplied image')
    findings = audit.get('findings')
    if not isinstance(findings, dict):
        raise SceneError('Missing audit findings')
    comp = findings.get('composition')
    scope = findings.get('software_only')
    product_match = findings.get('target_product_match', 'uncertain')  # legacy audit 1.0
    if product_match not in ('pass','fail','uncertain'):
        raise SceneError('Invalid target-product match verdict')
    if audit.get('format_version') == AUDIT_VERSION:
        if set(findings) != set(AUDIT_SCHEMA['properties']):
            raise SceneError('Incomplete current visual audit findings')
        if not isinstance(findings.get('product_match_reason'),str):
            raise SceneError('Invalid target-product reason')
    if comp not in ('single-frame', 'multi-frame-board', 'uncertain') or scope not in ('pass', 'fail', 'uncertain'):
        raise SceneError('Invalid audit status')
    evidence = findings.get('step_evidence')
    if not isinstance(evidence, list) or len(evidence) != len(item['required_evidence']):
        raise SceneError('Auditor evidence count mismatch')
    status_by_evidence = {}
    for e in evidence:
        if not isinstance(e, dict) or e.get('requirement') not in item['required_evidence'] or e.get('status') not in ('pass', 'fail', 'uncertain') or e['requirement'] in status_by_evidence:
            raise SceneError('Invalid or repeated audit evidence')
        status_by_evidence[e['requirement']] = e['status']
    if len(status_by_evidence) != len(item['required_evidence']):
        raise SceneError('Audit dropped source evidence')
    # A CONFIRMED issue (e.g., multi-frame board) can be repaired even when
    # unrelated evidence items are unknown; unknowns themselves never become
    # proof of failure or pass. If nothing is clearly broken, fail closed.
    if comp == 'uncertain' and scope != 'fail' and product_match != 'fail' and 'fail' not in status_by_evidence.values():
        raise SceneError('Uncertain visual findings require human inspection before any retry')
    if comp == 'single-frame' and (findings.get('distinct_screens') != 1 or findings.get('external_presentation_chrome') is not False):
        raise SceneError('Audit contains internally contradictory single-frame findings')
    if comp != 'multi-frame-board' and scope != 'fail' and product_match != 'fail' and all(s != 'fail' for s in status_by_evidence.values()):
        raise SceneError('Audit has no confirmed failure to repair')
    repairs = []
    categories = []
    if product_match == 'fail':
        categories.append('wrong-product')
        repairs.append('PRODUCT IDENTITY REPAIR: This MUST depict the target ORIGINAL product identified by product_id='+json.dumps(packet['product_id'],ensure_ascii=False)+', for exactly scene_id='+json.dumps(item['scene_id'],ensure_ascii=False)+', step_id='+json.dumps(item['step_id'],ensure_ascii=False)+'. Render the required action and evidence from the existing source prompt; DO NOT reuse imagery, layout, logos, filenames or controls from any unrelated product or earlier image. The output remains ONE software/game frame.')
    if comp == 'multi-frame-board':
        categories.append('multi-frame-board')
        repairs.append('COMPOSITION REPAIR: This is NOT a storyboard or comparative presentation. Produce only ONE standalone full-bleed screen for the EXACT requested scene/step; do not include any other steps, screenshots, or external titles. Normal UI panels INSIDE the same application are permitted.')
    if scope == 'fail':
        categories.append('outside-software')
        repairs.append('BOUNDARY REPAIR: Crop the imagined frame to the target software or game framebuffer itself. No real-world devices, desk, human operator, frames, captions, or page margins.')
    failed = [v for v in item['required_evidence'] if status_by_evidence[v] == 'fail']
    if failed:
        categories.append('missing-step-evidence')
        repairs.append('STEP EVIDENCE REPAIR: Make the following EXACT SOURCE REQUIREMENTS visibly recognizable in this single application/game state:\n' + '\n'.join('- '+s for s in failed))
    # The original prompt already contains all hard requirements, exact text,
    # design decisions, and single-frame contract. Untrusted audit free text
    # is never interpolated into the generation prompt.
    if previous_manifest is None:
        attempt = 1
        root_sha = packet['packet_sha256']
    else:
        verify_retry_manifest(previous_manifest, packet)
        if previous_manifest['attempt'] >= MAX_RETRY_ATTEMPTS:
            raise SceneError('Retry limit reached; request human review or change the design plan')
        attempt = previous_manifest['attempt'] + 1
        root_sha = previous_manifest['root_packet_sha256']
    copied = deepcopy(packet)
    copied['items'] = [deepcopy(item)]
    old_prompt = copied['items'][0]['prompt']
    if not old_prompt.startswith(SINGLE_FRAME_PREFIX) or not old_prompt.endswith(SINGLE_FRAME_SUFFIX):
        raise SceneError('Original single-frame render contract missing')
    base = old_prompt[:-len(SINGLE_FRAME_SUFFIX)]
    prompt = base + f'\nVISUAL RETRY {attempt}/{MAX_RETRY_ATTEMPTS}:\n' + '\n'.join(repairs) + SINGLE_FRAME_SUFFIX
    copied['items'][0]['prompt'] = prompt
    copied['items'][0]['prompt_sha256'] = sha256(prompt.encode('utf-8')).hexdigest()
    copied['image_generation_status'] = 'not_started'
    copied['note'] = ('Offline retry derived from previously audited image. '
                      'Re-review the new image independently. No user design approval implied; '
                      'original DesignSystem and source requirements remain unchanged.')
    copied['packet_sha256'] = _digest(copied)
    verify_render_packet(copied)
    manifest = {
        'format_version': RETRY_FORMAT, 'kind': 'concept-retry-manifest',
        'attempt': attempt, 'root_packet_sha256': root_sha,
        'parent_packet_sha256': packet['packet_sha256'],
        'parent_image_sha256': info['sha256'],
        'audit_sha256': _hash_json(audit), 'retry_packet_sha256': copied['packet_sha256'],
        'variant_id': item['variant_id'], 'scene_id': item['scene_id'],
        'repair_categories': categories,
        'prompt_sha256': copied['items'][0]['prompt_sha256'],
    }
    manifest['manifest_sha256'] = _hash_json(manifest)
    verify_retry_manifest(manifest, copied)
    return copied, manifest


def record_visual_observation(packet: dict[str, Any], image_path: str | Path, *,
                              variant_id: str, scene_id: str, composition: str,
                              software_only: str = 'uncertain', observer: str,
                              target_product_match: str = 'uncertain') -> dict[str, Any]:
    """Record a *self-attested* visible composition assessment without AI calls.

    This is explicitly an operator/assistant observation, NOT a vision-model
    assessment, independently verified fact, or user approval. Missing
    per-step evidence is recorded as 'uncertain', not automatically passed.
    """
    verify_render_packet(packet)
    if composition not in ('single-frame', 'multi-frame-board', 'uncertain'):
        raise SceneError('Invalid manual composition verdict')
    if software_only not in ('pass', 'fail', 'uncertain'):
        raise SceneError('Invalid software-only verdict')
    if target_product_match not in ('pass','fail','uncertain'):
        raise SceneError('Invalid target-product match verdict')
    if not isinstance(observer,str) or not observer.strip() or len(observer)>120:
        raise SceneError('Visual observer identification is required')
    items=[x for x in packet['items'] if x['variant_id']==variant_id and x['scene_id']==scene_id]
    if len(items)!=1:
        raise SceneError('Unknown or ambiguous target for visual observation')
    target=items[0]
    info=inspect_image(image_path)
    findings={
        'composition':composition, 'software_only':software_only,
        'target_product_match':target_product_match,
        'product_match_reason':'Self-attested product match by '+observer.strip()+'; not independently verified',
        'distinct_screens':2 if composition=='multi-frame-board' else 1,
        'external_presentation_chrome':composition=='multi-frame-board',
        'composition_reason':'Self-attested observation by '+observer.strip()+'; not independently verified',
        'software_only_reason':'Self-attested observation by '+observer.strip(),
        'step_evidence':[{'requirement':x,'status':'uncertain','reason':'Not assessed by this composition-only observation'}
                         for x in target['required_evidence']],
        'recommended_fixes':[],
    }
    assert set(findings)==set(AUDIT_SCHEMA['properties'])
    return {
        'format_version':AUDIT_VERSION,'kind':'concept-visual-audit',
        'variant_id':variant_id,'scene_id':scene_id,'step_id':target['step_id'],
        'packet_sha256':packet['packet_sha256'],'prompt_sha256':target['prompt_sha256'],
        'image_sha256':info['sha256'],'image_width':info['width'],'image_height':info['height'],
        'method':'self-attested-visual-observation','observer':observer.strip(),
        'model':None,'visual_gate':'needs-human-review',
        'findings':findings,'human_design_approval':'not_checked',
        'caveat':'This records the named observer input; it does NOT verify that observation and is NOT user approval.',
    }
