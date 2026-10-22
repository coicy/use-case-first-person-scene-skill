"""Non-destructive compatibility bridge from v0.6 structured use cases.

Legacy source facts are marked for review. No migrated field acquires approval.
"""
from __future__ import annotations

from typing import Any

from ..core import SceneError, validate_use_case
from .models import CATEGORIES, validate_product_brief


def migrate_legacy_case(case: dict[str, Any], *, product_id: str,
                        name: str, category: str = 'other') -> dict[str, Any]:
    old = validate_use_case(case)
    if category not in CATEGORIES:
        raise SceneError('Invalid new-product category')
    steps = []
    for step in old['steps']:
        steps.append({
            'id': step['id'], 'action': step['action'],
            'state': step.get('state', 'in-progress'), 'flow': step.get('branch','main'),
            'ui_text': list(step.get('ui_text', [])),
            'visible_evidence': list(step['visible_evidence']),
        })
    facts = [
        (old['title'], [old['id']]),
        (old['goal'], [old['id']]),
        (old['environment'], [old['id']]),
    ]
    for legacy_key in ('viewpoint_mode', 'game_camera', 'style', 'frame_scope'):
        if legacy_key in old:
            facts.append((f'Legacy {legacy_key}: {old[legacy_key]}', [old['id']]))
    for value in old.get('constraints', {}).get('must_show', []):
        facts.append((f'Legacy must_show: {value}', [old['id']]))
    for value in old.get('constraints', {}).get('must_not_show', []):
        facts.append((f'Legacy must_not_show: {value}', [old['id']]))
    for step in old['steps']:
        for text in step.get('ui_text', []) + step.get('carry_forward', []):
            facts.append((text, [old['id']]))
    result = {
        'schema_version': '1.0', 'product_id': product_id, 'name': name,
        'category': category, 'concept': old['goal'],
        'requirements': [
            {'id': f'LEGACY-REQ-{i:03}', 'text': text, 'source': 'legacy-case',
             'authority': 'review-required', 'use_case_ids': related}
            for i, (text, related) in enumerate(facts, 1)
        ],
        'hard_constraints': [],
        'use_cases': [{'id': old['id'], 'title': old['title'], 'actor': old['actor'],
                       'goal': old['goal'], 'steps': steps}],
        'unknowns': ['approval status for migrated source', 'new-product interaction design', 'visual design system'],
        'origin': {'mode': 'legacy-migration', 'source_id': old['id']},
    }
    return validate_product_brief(result)
