"""WP-03: apply an approved product visual language to NEW use-case steps.

Existing approved decisions remain unchanged. A newly entered brief may add use
cases, but cannot silently override protected approved design or hard keys.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from ..core import SceneError
from .models import scaffold_scenes, validate_product_brief
from .planner import _json_hash, _step_interaction
from .system import DESIGN_KEYS, FIELDS, validate_design_system

APPLIED_VERSION = '1.0'


def _prompt(brief: dict[str, Any], scene: dict[str, Any], system: dict[str, Any],
            use_case: dict[str, Any], step: dict[str, Any], interaction: dict[str, Any]) -> str:
    design = system['approved_design']
    reqs = [r for r in brief['requirements'] if r['id'] in scene['requirement_ids']]
    return '\n'.join([
        'DESIGN A CONCEPT SCREEN FOR THIS NEW PRODUCT, USING AN EXPLICITLY APPROVED DESIGN SYSTEM.',
        'FRAME SCOPE: software-only; full-bleed application or game output, no users, hardware, photo of screens or physical surroundings.',
        'PRODUCT: ' + brief['name'] + ' | CONCEPT: ' + brief['concept'],
        'USE CASE: ' + use_case['id'] + ' | GOAL: ' + use_case['goal'],
        'SCENE STEP: ' + scene['step_id'] + ' | ACTION: ' + scene['action'],
        'STATE: ' + scene['state'] + ' | FLOW: ' + scene['flow'],
        'DESIGN BASELINE (APPROVED, DO NOT CHANGE WITHOUT AUTHORIZATION): revision=' + str(system['revision'])
            + ', digest=' + system['digest_sha256'],
        'APPROVED UI LAYOUT: ' + design['layout'],
        'APPROVED NAVIGATION: ' + design['navigation'],
        'APPROVED VISUAL STYLE: ' + design['visual_style'],
        'APPROVED CONTROLS: ' + '; '.join(design['controls']),
        'INFORMATION HIERARCHY: ' + ' > '.join(design['information_priority']),
        'APPROVED GENERAL FEEDBACK: ' + design['feedback'],
        'USER REQUIREMENTS: ' + ('; '.join(f"[{r['id']}] {r['text']}" for r in reqs) or 'none'),
        'HARD CONSTRAINTS: ' + ('; '.join(f"{x['key']}={x['value']}" for x in brief['hard_constraints']) or 'none'),
        'REQUIRED VISUAL EVIDENCE: ' + ('; '.join(scene['visible_evidence']) or 'none specified; depict action and correct state'),
        'EXACT UI TEXT: ' + ('; '.join(scene['expected_ui_text']) or 'not specified; any labels beyond requirements are design proposals'),
        'STEP INTERACTION: ' + interaction['purpose'] + ' | OBJECT: ' + interaction['primary_object'],
        'STEP CONTROLS (PROPOSED, MUST FIT APPROVED BASELINE): ' + '; '.join(interaction['proposed_controls']),
        'STEP FEEDBACK: ' + interaction['proposed_feedback'],
        'Show WHAT can be done, WHERE it happens, and the correct current-state outcome. Never invent product requirements, never alter the approved layout/navigation/style.',
        'This is a DESIGN CONCEPT, NOT a screenshot of functioning software.',
    ])


def apply_design_system(system: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    validate_design_system(system)
    validate_product_brief(brief)
    if brief['product_id'] != system['product_id']:
        raise SceneError('Cannot apply DesignSystem to a different product')
    # A new use-case brief may add requirements but cannot contradict a selected
    # approved property or the hard constraints in the approved product baseline.
    stored_hard = {c['key']: c['value'] for c in system['hard_constraints']}
    actual_hard = {c['key']: c['value'] for c in brief['hard_constraints']}
    for k, v in stored_hard.items():
        if k not in actual_hard or actual_hard[k] != v:
            raise SceneError('New brief omits or changes previously confirmed hard constraint: ' + k)
    design = system['approved_design']
    for key, field in zip(DESIGN_KEYS, FIELDS):
        if key in actual_hard and actual_hard[key] != design[field]:
            raise SceneError('New use case contradicts approved DesignSystem: ' + key)
    cases = {u['id']: u for u in brief['use_cases']}
    step_scenes = scaffold_scenes(brief)
    compiled = []
    for scene in step_scenes:
        use = cases[scene['use_case_id']]
        step = next(s for s in use['steps'] if s['id'] == scene['step_id'])
        interaction = _step_interaction(brief, step, design)
        prompt = _prompt(brief, scene, system, use, step, interaction)
        compiled.append({
            'scene_id': scene['id'], 'use_case_id': use['id'], 'step_id': step['id'],
            'state': scene['state'], 'flow': scene['flow'],
            'requirement_ids': list(scene['requirement_ids']),
            'required_evidence': list(scene['visible_evidence']),
            'required_ui_text': list(scene['expected_ui_text']),
            'design_status': 'approved-baseline',
            'design_decision_ids': [d['id'] for d in system['approved_decisions']],
            'interaction': interaction,
            'prompt': prompt, 'prompt_sha256': sha256(prompt.encode('utf-8')).hexdigest(),
        })
    result = {
        'format_version': APPLIED_VERSION,
        'kind': 'consistent-scene-plan',
        'product_id': brief['product_id'],
        'source_brief_sha256': _json_hash(brief),
        'design_system_sha256': system['digest_sha256'],
        'design_system_revision': system['revision'],
        'approved_layout': design['layout'],
        'approved_navigation': design['navigation'],
        'approved_visual_style': design['visual_style'],
        'approval': dict(system['approval']),
        'scenes': compiled,
        'generated_images': 0,
        'warning': 'This binds a human-approved DESIGN baseline to NEW step prompts. It does not generate pixels or certify functioning UI.',
    }
    return validate_consistent_plan(result, system=system, brief=brief)


def validate_consistent_plan(plan: Any, *, system: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != {
        'format_version', 'kind', 'product_id', 'source_brief_sha256',
        'design_system_sha256', 'design_system_revision', 'approved_layout',
        'approved_navigation', 'approved_visual_style', 'approval', 'scenes',
        'generated_images', 'warning',
    }:
        raise SceneError('ConsistentScenePlan envelope invalid')
    if plan['format_version'] != APPLIED_VERSION or plan['kind'] != 'consistent-scene-plan':
        raise SceneError('ConsistentScenePlan format invalid')
    validate_design_system(system)
    validate_product_brief(brief)
    if plan['product_id'] != brief['product_id'] or plan['source_brief_sha256'] != _json_hash(brief):
        raise SceneError('ConsistentScenePlan brief changed')
    if plan['design_system_sha256'] != system['digest_sha256'] or plan['design_system_revision'] != system['revision']:
        raise SceneError('ConsistentScenePlan design baseline mismatch')
    design = system['approved_design']
    if (plan['approved_layout'], plan['approved_navigation'], plan['approved_visual_style']) != tuple(design[f] for f in FIELDS):
        raise SceneError('ConsistentScenePlan approved design changed')
    if plan['approval'] != system['approval'] or plan['generated_images'] != 0:
        raise SceneError('ConsistentScenePlan approval/generation status invalid')
    # Full regeneration makes unapproved changes to prompts, feedback, evidence,
    # or design metadata fail without a fragile partial syntax check.
    expected = _rebuild_without_validation(system, brief)
    if plan != expected:
        raise SceneError('ConsistentScenePlan contents diverge from approved design/source')
    return plan


def _rebuild_without_validation(system: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    cases = {u['id']: u for u in brief['use_cases']}
    design = system['approved_design']
    scenes = []
    for scene in scaffold_scenes(brief):
        use = cases[scene['use_case_id']]
        step = next(s for s in use['steps'] if s['id'] == scene['step_id'])
        interaction = _step_interaction(brief, step, design)
        prompt = _prompt(brief, scene, system, use, step, interaction)
        scenes.append({
            'scene_id': scene['id'], 'use_case_id': use['id'], 'step_id': step['id'],
            'state': scene['state'], 'flow': scene['flow'],
            'requirement_ids': list(scene['requirement_ids']),
            'required_evidence': list(scene['visible_evidence']),
            'required_ui_text': list(scene['expected_ui_text']),
            'design_status': 'approved-baseline',
            'design_decision_ids': [d['id'] for d in system['approved_decisions']],
            'interaction': interaction, 'prompt': prompt,
            'prompt_sha256': sha256(prompt.encode('utf-8')).hexdigest(),
        })
    return {
        'format_version': APPLIED_VERSION, 'kind': 'consistent-scene-plan',
        'product_id': brief['product_id'],
        'source_brief_sha256': _json_hash(brief),
        'design_system_sha256': system['digest_sha256'],
        'design_system_revision': system['revision'],
        'approved_layout': design['layout'], 'approved_navigation': design['navigation'],
        'approved_visual_style': design['visual_style'], 'approval': dict(system['approval']),
        'scenes': scenes, 'generated_images': 0,
        'warning': 'This binds a human-approved DESIGN baseline to NEW step prompts. It does not generate pixels or certify functioning UI.',
    }
