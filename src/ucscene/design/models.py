"""v0.7 WP-01: source-aware contracts for new-product use-case designs.

This module intentionally DOES NOT generate layouts or call image models. It only
separates user statements, unapproved proposals, and scene-design scaffolds.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..core import SceneError

SCHEMA_VERSION = '1.0'
CATEGORIES = {'desktop', 'web', 'mobile', 'game', 'other'}
STATES = {'start', 'in-progress', 'waiting', 'success', 'failure'}
AUTHORITY = {'source-stated', 'review-required'}
PROPOSAL_STATUS = {'proposed', 'approved', 'rejected'}
DECISION_SOURCES = {'ai-proposal', 'user-proposal', 'user-decision'}
FRAME_SCOPE = 'software-only'
VIEWPOINT = {'application-ui', 'gameplay'}
SCENE_STATUS = {'unresolved', 'proposed', 'approved'}


def _only(value: dict[str, Any], allowed: set[str], name: str) -> None:
    unexpected = set(value) - allowed
    if unexpected:
        raise SceneError(f'{name} contains unexpected fields: {", ".join(sorted(unexpected))}')


def _object(item: Any, name: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise SceneError(f'{name} must be an object')
    return item


def _string(item: Any, name: str) -> str:
    if not isinstance(item, str) or not item.strip():
        raise SceneError(f'{name} must be a non-empty string')
    return item


def _array(item: Any, name: str, *, allow_empty: bool = True) -> list[Any]:
    if not isinstance(item, list) or (not item and not allow_empty):
        raise SceneError(f'{name} must be a {"non-empty " if not allow_empty else ""}list')
    return item


def _version(value: dict[str, Any], name: str) -> None:
    if value.get('schema_version') != SCHEMA_VERSION:
        raise SceneError(f'{name}.schema_version must be {SCHEMA_VERSION}')


def _unique(items: list[Any], name: str) -> None:
    ids = [_string(_object(item, name + '[]').get('id'), name + '[].id') for item in items]
    if len(ids) != len(set(ids)):
        raise SceneError(f'{name} contains duplicate IDs')


def validate_product_brief(brief: Any) -> dict[str, Any]:
    b = _object(brief, 'ProductBrief')
    _version(b, 'ProductBrief')
    _only(b, {'schema_version','product_id','name','category','concept','requirements','hard_constraints','use_cases','unknowns','origin'}, 'ProductBrief')
    for key in ('product_id', 'name', 'concept'):
        _string(b.get(key), f'ProductBrief.{key}')
    if b.get('category') not in CATEGORIES:
        raise SceneError('ProductBrief.category invalid')
    reqs = _array(b.get('requirements'), 'ProductBrief.requirements')
    _unique(reqs, 'ProductBrief.requirements')
    uses = _array(b.get('use_cases'), 'ProductBrief.use_cases', allow_empty=False)
    _unique(uses, 'ProductBrief.use_cases')
    constraints = _array(b.get('hard_constraints', []), 'ProductBrief.hard_constraints')
    _unique(constraints, 'ProductBrief.hard_constraints')
    for i, item in enumerate(reqs):
        path = f'ProductBrief.requirements[{i}]'
        _only(item, {'id','text','source','authority','use_case_ids'}, path)
        _string(item.get('text'), path + '.text')
        if item.get('authority') not in AUTHORITY:
            raise SceneError(path + '.authority must be source-stated or review-required')
        if item.get('source') not in {'user-prompt', 'user-confirmed', 'legacy-case'}:
            raise SceneError(path + '.source invalid')
        if item['source'] == 'legacy-case' and item['authority'] != 'review-required':
            raise SceneError('Migrated requirements cannot claim user confirmation')
        if item.get('source') == 'user-confirmed' and item['authority'] != 'source-stated':
            raise SceneError('User-confirmed requirements must be source-stated')
        case_ids = _array(item.get('use_case_ids', []), path + '.use_case_ids')
        for use_id in case_ids:
            _string(use_id, path + '.use_case_ids[]')
    case_set = {u['id'] for u in uses}
    for item in reqs:
        if set(item.get('use_case_ids', [])) - case_set:
            raise SceneError(f"Requirement {item['id']} references unknown use case")
    for i, c in enumerate(constraints):
        p = f'ProductBrief.hard_constraints[{i}]'
        _only(c, {'id','key','value','source'}, p)
        _string(c.get('key'), p + '.key')
        if 'value' not in c or isinstance(c['value'], (dict, list)):
            raise SceneError(p + '.value must be a scalar')
        if c.get('source') not in {'user-confirmed', 'user-prompt'}:
            raise SceneError(p + '.source must be user-confirmed or user-prompt')
    keys: dict[str, Any] = {}
    for c in constraints:
        if c['key'] in keys and c['value'] != keys[c['key']]:
            raise SceneError('Contradictory hard constraints for key: ' + c['key'])
        keys[c['key']] = c['value']
    for i, use in enumerate(uses):
        p = f'ProductBrief.use_cases[{i}]'
        _only(use, {'id','title','actor','goal','steps'}, p)
        for key in ('title', 'actor', 'goal'):
            _string(use.get(key), p + '.' + key)
        steps = _array(use.get('steps'), p + '.steps', allow_empty=False)
        _unique(steps, p + '.steps')
        for j, step in enumerate(steps):
            sp = f'{p}.steps[{j}]'
            _only(step, {'id','action','state','flow','visible_evidence','ui_text'}, sp)
            _string(step.get('action'), sp + '.action')
            if step.get('state') not in STATES:
                raise SceneError(sp + '.state invalid')
            if step.get('flow') not in {'main','alternative','exception'}:
                raise SceneError(sp + '.flow invalid')
            labels = _array(step.get('ui_text'), sp + '.ui_text')
            for v in labels:
                _string(v, sp + '.ui_text[]')
            evidence = _array(step.get('visible_evidence'), sp + '.visible_evidence')
            for value in evidence:
                _string(value, sp + '.visible_evidence[]')
    unknowns = _array(b.get('unknowns', []), 'ProductBrief.unknowns')
    for value in unknowns:
        _string(value, 'ProductBrief.unknowns[]')
    origin = _object(b.get('origin'), 'ProductBrief.origin')
    _only(origin, {'mode','source_id'}, 'ProductBrief.origin')
    if origin.get('mode') not in {'direct-prompt', 'legacy-migration', 'curated'}:
        raise SceneError('ProductBrief.origin.mode invalid')
    _string(origin.get('source_id'), 'ProductBrief.origin.source_id')
    return b


def validate_design_decision(decision: Any) -> dict[str, Any]:
    d = _object(decision, 'DesignDecision')
    _version(d, 'DesignDecision')
    _only(d, {'schema_version','id','product_id','topic','proposal','rationale','status','locked','revision','source','related_use_case_ids','effects','approval'}, 'DesignDecision')
    for key in ('id', 'product_id', 'topic', 'proposal', 'rationale'):
        _string(d.get(key), 'DesignDecision.' + key)
    if d.get('status') not in PROPOSAL_STATUS:
        raise SceneError('DesignDecision.status invalid')
    if d.get('source') not in DECISION_SOURCES:
        raise SceneError('DesignDecision.source invalid')
    if type(d.get('locked')) is not bool:
        raise SceneError('DesignDecision.locked must be a boolean')
    if type(d.get('revision')) is not int or d['revision'] < 1:
        raise SceneError('DesignDecision.revision must be a positive integer')
    if d['locked'] and d['status'] != 'approved':
        raise SceneError('Only approved decisions may be locked')
    if d['source'] == 'ai-proposal' and d['status'] == 'rejected' and not d.get('approval'):
        raise SceneError('Rejecting an AI proposal requires an explicit user decision record')
    if d['status'] != 'proposed':
        approval = _object(d.get('approval'), 'DesignDecision.approval')
        _only(approval, {'by','evidence_ref'}, 'DesignDecision.approval')
        if approval.get('by') != 'user' or not isinstance(approval.get('evidence_ref'), str) or not approval['evidence_ref'].strip():
            raise SceneError('Approved/rejected decisions require user approval evidence_ref')
    elif d.get('approval') is not None:
        raise SceneError('Proposed decisions cannot claim approval')
    ids = _array(d.get('related_use_case_ids'), 'DesignDecision.related_use_case_ids')
    for use_id in ids:
        _string(use_id, 'DesignDecision.related_use_case_ids[]')
    effects = _array(d.get('effects'), 'DesignDecision.effects')
    names: set[str] = set()
    for i, effect in enumerate(effects):
        e = _object(effect, f'DesignDecision.effects[{i}]')
        _only(e, {'key','value'}, f'DesignDecision.effects[{i}]')
        k = _string(e.get('key'), f'DesignDecision.effects[{i}].key')
        if k in names:
            raise SceneError('Duplicate effect key: ' + k)
        names.add(k)
        if 'value' not in e or isinstance(e['value'], (list, dict)):
            raise SceneError('DesignDecision.effects[].value must be a scalar')
    return d


def validate_scene_design(scene: Any) -> dict[str, Any]:
    s = _object(scene, 'UseCaseScene')
    _version(s, 'UseCaseScene')
    _only(s, {'schema_version','id','product_id','use_case_id','step_id','action','state','flow','frame_scope','viewpoint_mode','design_status','requirement_ids','design_decision_ids','visible_evidence','expected_ui_text','proposed_elements'}, 'UseCaseScene')
    for key in ('id', 'product_id', 'use_case_id', 'step_id', 'action'):
        _string(s.get(key), 'UseCaseScene.' + key)
    if s.get('frame_scope') != FRAME_SCOPE:
        raise SceneError('UseCaseScene.frame_scope must be software-only')
    if s.get('viewpoint_mode') not in VIEWPOINT:
        raise SceneError('UseCaseScene.viewpoint_mode invalid')
    if s.get('design_status') not in SCENE_STATUS:
        raise SceneError('UseCaseScene.design_status invalid')
    if s.get('state') not in STATES:
        raise SceneError('UseCaseScene.state invalid')
    if s.get('flow') not in {'main','alternative','exception'}:
        raise SceneError('UseCaseScene.flow invalid')
    for key in ('requirement_ids', 'design_decision_ids', 'visible_evidence', 'expected_ui_text', 'proposed_elements'):
        vals = _array(s.get(key), 'UseCaseScene.' + key)
        if len(vals) != len(set(vals)):
            raise SceneError('UseCaseScene.' + key + ' contains duplicates')
        for value in vals:
            _string(value, 'UseCaseScene.' + key + '[]')
    if s['design_status'] == 'approved' and not s.get('design_decision_ids'):
        raise SceneError('Approved scene must cite approved design decisions')
    return s


def validate_design_bundle(bundle: Any) -> dict[str, Any]:
    b = _object(bundle, 'DesignBundle')
    _version(b, 'DesignBundle')
    _only(b, {'schema_version','brief','decisions','scenes'}, 'DesignBundle')
    brief = validate_product_brief(b.get('brief'))
    decisions = _array(b.get('decisions'), 'DesignBundle.decisions')
    scenes = _array(b.get('scenes'), 'DesignBundle.scenes')
    _unique(decisions, 'DesignBundle.decisions')
    _unique(scenes, 'DesignBundle.scenes')
    case_lookup = {u['id']: u for u in brief['use_cases']}
    req_lookup = {r['id']: r for r in brief['requirements']}
    decision_lookup = {}
    conflicts = []
    hard_by_key = {x['key']: x for x in brief.get('hard_constraints', [])}
    approved_effects: dict[str, Any] = {}
    for d in decisions:
        validate_design_decision(d)
        if d['product_id'] != brief['product_id']:
            raise SceneError(f"Decision {d['id']} belongs to another product")
        if set(d['related_use_case_ids']) - set(case_lookup):
            raise SceneError(f"Decision {d['id']} references unknown use case")
        for effect in d['effects']:
            if d['status'] == 'approved':
                if effect['key'] in approved_effects and approved_effects[effect['key']] != effect['value']:
                    raise SceneError('Approved design decisions contradict each other: ' + effect['key'])
                approved_effects[effect['key']] = effect['value']
            hard = hard_by_key.get(effect['key'])
            if hard and effect['value'] != hard['value']:
                conflicts.append({
                    'decision_id': d['id'], 'hard_constraint_id': hard['id'],
                    'key': effect['key'], 'expected': hard['value'], 'proposed': effect['value'],
                })
        decision_lookup[d['id']] = d
    for s in scenes:
        validate_scene_design(s)
        if s['product_id'] != brief['product_id']:
            raise SceneError(f"Scene {s['id']} belongs to another product")
        if s['use_case_id'] not in case_lookup:
            raise SceneError(f"Scene {s['id']} references unknown use case")
        if s['step_id'] not in {step['id'] for step in case_lookup[s['use_case_id']]['steps']}:
            raise SceneError(f"Scene {s['id']} references unknown step")
        source_step = next(step for step in case_lookup[s['use_case_id']]['steps'] if step['id'] == s['step_id'])
        for key in ('action', 'state', 'flow'):
            if s[key] != source_step[key]:
                raise SceneError(f"Scene {s['id']} overrides source use-case {key}")
        if set(source_step['visible_evidence']) - set(s['visible_evidence']):
            raise SceneError(f"Scene {s['id']} drops required visible evidence")
        if set(source_step['ui_text']) - set(s['expected_ui_text']):
            raise SceneError(f"Scene {s['id']} drops required UI text")
        if set(s['requirement_ids']) - set(req_lookup):
            raise SceneError(f"Scene {s['id']} references unknown requirement")
        for rid in s['requirement_ids']:
            target = req_lookup[rid]['use_case_ids']
            if target and s['use_case_id'] not in target:
                raise SceneError(f"Scene {s['id']} incorrectly links requirement {rid}")
        if set(s['design_decision_ids']) - set(decision_lookup):
            raise SceneError(f"Scene {s['id']} references unknown design decision")
        for did in s['design_decision_ids']:
            d = decision_lookup[did]
            if d['related_use_case_ids'] and s['use_case_id'] not in d['related_use_case_ids']:
                raise SceneError(f"Scene {s['id']} incorrectly links decision {did}")
            if d['status'] == 'rejected':
                raise SceneError(f"Scene {s['id']} links a rejected design decision {did}")
            if s['design_status'] == 'approved' and d['status'] != 'approved':
                raise SceneError(f"Approved scene {s['id']} cannot use unapproved decision {did}")
    if conflicts:
        raise SceneError('Design conflicts with confirmed hard constraints: ' + '; '.join(
            f"{x['decision_id']}:{x['key']} ({x['proposed']!r} != {x['expected']!r})" for x in conflicts
        ))
    return b


def init_brief(product_id: str, name: str, category: str, prompt: str, use_case: str) -> dict[str, Any]:
    """Preserve input verbatim; never hallucinate missing UI or user approval."""
    result = {
        'schema_version': SCHEMA_VERSION,
        'product_id': _string(product_id, 'product_id'),
        'name': _string(name, 'name'), 'category': category,
        'concept': _string(prompt, 'prompt'),
        'requirements': [
            {'id': 'REQ-001', 'text': prompt, 'source': 'user-prompt', 'authority': 'source-stated', 'use_case_ids': []},
            {'id': 'REQ-002', 'text': use_case, 'source': 'user-prompt', 'authority': 'source-stated', 'use_case_ids': ['UC-001']},
        ],
        'hard_constraints': [],
        'use_cases': [{'id': 'UC-001', 'title': use_case, 'actor': 'unspecified',
                       'goal': use_case, 'steps': [{'id': 'STEP-001', 'action': use_case,
                                                   'state': 'in-progress', 'flow': 'main', 'ui_text': [], 'visible_evidence': []}]}],
        'unknowns': ['actor', 'interaction design', 'UI layout', 'visual style', 'visible feedback'],
        'origin': {'mode': 'direct-prompt', 'source_id': 'CLI:brief-init'},
    }
    return validate_product_brief(result)


def scaffold_scenes(brief: dict[str, Any]) -> list[dict[str, Any]]:
    """Create UNRESOLVED scenes (not rendered scenes, not approved designs)."""
    b = validate_product_brief(brief)
    result: list[dict[str, Any]] = []
    for use in b['use_cases']:
        for step in use['steps']:
            req_ids = [r['id'] for r in b['requirements'] if not r['use_case_ids'] or use['id'] in r['use_case_ids']]
            scene = {
                'schema_version': SCHEMA_VERSION,
                'id': f"{b['product_id']}--{use['id']}--{step['id']}",
                'product_id': b['product_id'], 'use_case_id': use['id'], 'step_id': step['id'],
                'action': step['action'], 'state': step['state'], 'flow': step['flow'],
                'frame_scope': FRAME_SCOPE,
                'viewpoint_mode': 'gameplay' if b['category'] == 'game' else 'application-ui',
                'design_status': 'unresolved',
                'requirement_ids': req_ids, 'design_decision_ids': [],
                'visible_evidence': list(step['visible_evidence']), 'expected_ui_text': list(step['ui_text']),
                'proposed_elements': [],
            }
            validate_scene_design(scene)
            result.append(scene)
    return result


def create_bundle(brief: dict[str, Any]) -> dict[str, Any]:
    b = {'schema_version': SCHEMA_VERSION, 'brief': deepcopy(validate_product_brief(brief)), 'decisions': [], 'scenes': scaffold_scenes(brief)}
    return validate_design_bundle(b)
