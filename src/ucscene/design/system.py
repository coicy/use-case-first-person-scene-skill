"""WP-03: approved product design baseline and controlled revisions.

This module records *explicit self-attested* user decisions; CLI flags do not
provide external proof of consent. Inputs are immutable; validation is strict.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any

from ..core import SceneError
from .models import validate_design_decision, validate_product_brief
from .planner import _json_hash, validate_design_plan

DESIGN_SYSTEM_VERSION = '1.0'
DESIGN_KEYS = ('ui.layout', 'ui.navigation', 'ui.visual_style')
FIELDS = ('layout', 'navigation', 'visual_style')
_SYSTEM_FIELDS = {
    'schema_version', 'kind', 'product_id', 'source_brief_sha256',
    'source_plan_sha256', 'selected_variant_id', 'revision', 'locked',
    'approved_design', 'approved_decisions', 'hard_constraints', 'approval',
    'history', 'digest_sha256',
}
_APPROVED_DESIGN_FIELDS = {
    'layout', 'navigation', 'visual_style', 'controls', 'information_priority',
    'feedback', 'label', 'tradeoff',
}
_HISTORY_FIELDS = {'revision', 'action', 'changed_keys', 'evidence_ref', 'previous_sha256'}
_SHA_RE = re.compile(r'^[0-9a-f]{64}$')


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SceneError(f'{name} must be a nonempty string')
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise SceneError(f'{name} must be a SHA-256 digest')
    return value


def _list_of_strings(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(s, str) or not s.strip() for s in value):
        raise SceneError(f'{name} must be a nonempty list of strings')
    if len(value) != len(set(value)):
        raise SceneError(f'{name} contains duplicates')
    return value


def _digest(system: dict[str, Any]) -> str:
    data = {k: v for k, v in system.items() if k != 'digest_sha256'}
    return _json_hash(data)


def validate_design_system(system: Any, *, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(system, dict) or set(system) != _SYSTEM_FIELDS:
        raise SceneError('DesignSystem envelope has missing/unknown fields')
    if system['schema_version'] != DESIGN_SYSTEM_VERSION or system['kind'] != 'design-system':
        raise SceneError('DesignSystem format is unsupported')
    _nonempty(system['product_id'], 'product_id')
    _sha(system['source_brief_sha256'], 'source_brief_sha256')
    _sha(system['source_plan_sha256'], 'source_plan_sha256')
    _sha(system['digest_sha256'], 'digest_sha256')
    if not re.fullmatch(r'VAR-\d\d', _nonempty(system['selected_variant_id'], 'selected_variant_id')):
        raise SceneError('DesignSystem selected_variant_id invalid')
    if type(system['revision']) is not int or system['revision'] < 1:
        raise SceneError('DesignSystem revision must be positive integer')
    if type(system['locked']) is not bool:
        raise SceneError('DesignSystem locked must be boolean')
    design = system['approved_design']
    if not isinstance(design, dict) or set(design) != _APPROVED_DESIGN_FIELDS:
        raise SceneError('DesignSystem approved_design structure invalid')
    for field in (*FIELDS, 'feedback', 'label', 'tradeoff'):
        _nonempty(design[field], 'approved_design.' + field)
    for field in ('controls', 'information_priority'):
        _list_of_strings(design[field], 'approved_design.' + field)
    hard = system['hard_constraints']
    if not isinstance(hard, list) or any(not isinstance(x, dict) or set(x) != {'id','key','value','source'} for x in hard):
        raise SceneError('DesignSystem hard_constraints invalid')
    hard_keys = {}
    for c in hard:
        _nonempty(c['id'], 'hard_constraint.id')
        key = _nonempty(c['key'], 'hard_constraint.key')
        if key in hard_keys and hard_keys[key] != c['value']:
            raise SceneError('Conflicting hard constraints: ' + key)
        hard_keys[key] = c['value']
    for key, field in zip(DESIGN_KEYS, FIELDS):
        if key in hard_keys and design[field] != hard_keys[key]:
            raise SceneError('Approved design contradicts hard constraint: ' + key)
    decisions = system['approved_decisions']
    if not isinstance(decisions, list) or len(decisions) != 3:
        raise SceneError('DesignSystem requires 3 approved design decisions')
    effects = {}
    ids = set()
    for d in decisions:
        validate_design_decision(d)
        if d['id'] in ids or d['product_id'] != system['product_id']:
            raise SceneError('DesignSystem decision ID/product mismatch')
        ids.add(d['id'])
        if d['status'] != 'approved' or d['locked'] != system['locked']:
            raise SceneError('DesignSystem decisions must share approved/locked status')
        if len(d['effects']) != 1:
            raise SceneError('DesignSystem decisions must have one effect each')
        e = d['effects'][0]
        if e['key'] in effects:
            raise SceneError('Duplicate DesignSystem effect key')
        effects[e['key']] = e['value']
        if d['revision'] > system['revision']:
            raise SceneError('Decision revision exceeds DesignSystem revision')
    if effects != dict(zip(DESIGN_KEYS, (design[f] for f in FIELDS))):
        raise SceneError('DesignSystem decisions differ from approved design')
    approval = system['approval']
    if not isinstance(approval, dict) or set(approval) != {'by', 'evidence_ref'} or approval['by'] != 'user':
        raise SceneError('DesignSystem approval requires explicit self-attested user authorization')
    _nonempty(approval['evidence_ref'], 'approval.evidence_ref')
    history = system['history']
    if not isinstance(history, list) or len(history) != system['revision']:
        raise SceneError('DesignSystem history/revision mismatch')
    for i, event in enumerate(history):
        if not isinstance(event, dict) or set(event) != _HISTORY_FIELDS or event['revision'] != i+1:
            raise SceneError('DesignSystem history event invalid')
        _nonempty(event['evidence_ref'], 'history.evidence_ref')
        if not isinstance(event['changed_keys'], list) or any(k not in DESIGN_KEYS for k in event['changed_keys']):
            raise SceneError('DesignSystem history changed_keys invalid')
        if i == 0:
            if event['action'] != 'approve' or event['previous_sha256'] is not None or set(event['changed_keys']) != set(DESIGN_KEYS):
                raise SceneError('DesignSystem first history event must be approve')
        else:
            if event['action'] not in {'revise', 'revise-locked'} or len(event['changed_keys']) != 1:
                raise SceneError('DesignSystem revision history is invalid')
            _sha(event['previous_sha256'], 'history.previous_sha256')
    if history[-1]['evidence_ref'] != approval['evidence_ref']:
        raise SceneError('DesignSystem approval/history mismatch')
    if _digest(system) != system['digest_sha256']:
        raise SceneError('DesignSystem digest mismatch')
    if plan is not None:
        validate_design_plan(plan)
        if system['source_plan_sha256'] != _json_hash(plan):
            raise SceneError('DesignSystem source plan changed')
        if system['source_brief_sha256'] != plan['source_brief_sha256'] or system['product_id'] != plan['product_id']:
            raise SceneError('DesignSystem source brief mismatch')
        if hard != plan['design_bundle']['brief']['hard_constraints']:
            raise SceneError('DesignSystem source hard constraints mismatch')
        candidate = next((c for c in plan['candidates'] if c['id'] == system['selected_variant_id']), None)
        if candidate is None:
            raise SceneError('Selected DesignSystem variant is not in source plan')
        if {d['id'] for d in decisions} != set(candidate['design_decision_ids']):
            raise SceneError('Approved decision IDs differ from selected source candidate')
        if system['revision'] == 1:
            expected = {f: deepcopy(candidate[f]) for f in _APPROVED_DESIGN_FIELDS}
            expected['label'] = candidate['label']
            if design != expected:
                raise SceneError('Initial approved design does not match source candidate')
    return system


def create_design_system(plan: dict[str, Any], variant_id: str, *,
                         evidence_ref: str, locked: bool = False) -> dict[str, Any]:
    """Records user approval asserted via an explicit caller action; never auto-approves."""
    validate_design_plan(plan)
    evidence_ref = _nonempty(evidence_ref, 'evidence_ref')
    if type(locked) is not bool:
        raise SceneError('locked must be a boolean')
    variant = next((c for c in plan['candidates'] if c['id'] == variant_id), None)
    if variant is None:
        raise SceneError('Unknown design variant: ' + str(variant_id))
    by_id = {d['id']: d for d in plan['design_bundle']['decisions']}
    decisions = []
    for did in variant['design_decision_ids']:
        d = deepcopy(by_id[did])
        d['status'] = 'approved'
        d['locked'] = locked
        d['approval'] = {'by': 'user', 'evidence_ref': evidence_ref}
        decisions.append(d)
    data = {
        'schema_version': DESIGN_SYSTEM_VERSION,
        'kind': 'design-system', 'product_id': plan['product_id'],
        'source_brief_sha256': plan['source_brief_sha256'],
        'source_plan_sha256': _json_hash(plan),
        'selected_variant_id': variant_id, 'revision': 1, 'locked': locked,
        'approved_design': {k: deepcopy(variant[k]) for k in sorted(_APPROVED_DESIGN_FIELDS)},
        'approved_decisions': decisions,
        'hard_constraints': deepcopy(plan['design_bundle']['brief']['hard_constraints']),
        'approval': {'by': 'user', 'evidence_ref': evidence_ref},
        'history': [{'revision': 1, 'action': 'approve', 'changed_keys': list(DESIGN_KEYS),
                     'evidence_ref': evidence_ref, 'previous_sha256': None}],
    }
    data['digest_sha256'] = _digest(data)
    return validate_design_system(data, plan=plan)


def revise_design_system(system: dict[str, Any], key: str, value: str, *,
                         evidence_ref: str, override_lock: bool = False) -> dict[str, Any]:
    """Explicit re-approval for one changed key; refuses locked edits without override."""
    validate_design_system(system)
    if key not in DESIGN_KEYS:
        raise SceneError('Editable design key must be one of: ' + ', '.join(DESIGN_KEYS))
    value = _nonempty(value, 'value')
    evidence_ref = _nonempty(evidence_ref, 'evidence_ref')
    if type(override_lock) is not bool:
        raise SceneError('override_lock must be bool')
    if system['locked'] and not override_lock:
        raise SceneError('DesignSystem is locked; re-approval and explicit --override-lock required')
    field = FIELDS[DESIGN_KEYS.index(key)]
    if system['approved_design'][field] == value:
        raise SceneError('Design revision has no change')
    for hard in system['hard_constraints']:
        if hard['key'] == key and hard['value'] != value:
            raise SceneError('Design change conflicts with product hard constraint: ' + key)
    changed = deepcopy(system)
    prev = changed['digest_sha256']
    changed['revision'] += 1
    changed['approved_design'][field] = value
    changed['approval'] = {'by': 'user', 'evidence_ref': evidence_ref}
    for d in changed['approved_decisions']:
        if d['effects'][0]['key'] == key:
            d['effects'][0]['value'] = value
            d['proposal'] = value
            d['revision'] = changed['revision']
            d['approval'] = {'by': 'user', 'evidence_ref': evidence_ref}
    changed['history'].append({
        'revision': changed['revision'], 'action': 'revise-locked' if system['locked'] else 'revise',
        'changed_keys': [key], 'evidence_ref': evidence_ref, 'previous_sha256': prev,
    })
    changed['digest_sha256'] = _digest(changed)
    return validate_design_system(changed)


def compare_design_system(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Check one authorized revision and report which product-level properties changed."""
    validate_design_system(before)
    validate_design_system(after)
    for k in ('product_id', 'source_plan_sha256', 'source_brief_sha256', 'selected_variant_id'):
        if before[k] != after[k]:
            raise SceneError('Cannot diff DesignSystems with different provenance: ' + k)
    if after['revision'] != before['revision'] + 1 or after['history'][:-1] != before['history']:
        raise SceneError('DesignSystem diff requires consecutive revisions and unchanged history')
    if after['history'][-1]['previous_sha256'] != before['digest_sha256']:
        raise SceneError('DesignSystem revision does not point to previous digest')
    changed = []
    for key, field in zip(DESIGN_KEYS, FIELDS):
        if before['approved_design'][field] != after['approved_design'][field]:
            changed.append({'key': key, 'before': before['approved_design'][field], 'after': after['approved_design'][field]})
    if len(changed) != 1 or after['history'][-1]['changed_keys'] != [changed[0]['key']]:
        raise SceneError('DesignSystem revision declares incorrect changed keys')
    return {'product_id': before['product_id'], 'from_revision': before['revision'],
            'to_revision': after['revision'], 'changes': changed,
            'impact': 'All prior scenes using this approved design property require review and possibly new renders',
            'requires_scene_review': True}
