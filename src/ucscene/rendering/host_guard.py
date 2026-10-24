"""Fail-closed host-Agent image capability preflight. Never invokes an image API."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from ..core import SceneError
from .concept import verify_render_packet

REQUIRED_CAPABILITIES = (
    'explicit_prompt_supported',
    'one_image_per_call',
    'prompt_isolation_supported',
    'png_output_available',
)


def _digest(obj: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode('utf-8')).hexdigest()


def preflight_host_agent(packet: dict[str, Any], capabilities: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic, source-bound declaration of native-host eligibility.

    This cannot authenticate the host's assertions or prove which prompt was sent.
    An unrouteable host MUST NOT silently switch to paid standalone image APIs.
    """
    verify_render_packet(packet)
    if packet['format_version'] != '1.1':
        raise SceneError('Agent preflight requires identity-bound packet v1.1')
    required = {'format_version', 'tool_id', *REQUIRED_CAPABILITIES,
                'submitted_prompt_record_available'}
    if not isinstance(capabilities, dict) or set(capabilities) != required:
        raise SceneError('Host capability declaration requires exact fields')
    if capabilities['format_version'] != '1.0':
        raise SceneError('Unsupported Agent host capability schema')
    tool_id = capabilities['tool_id']
    if not isinstance(tool_id, str) or not tool_id.strip() or len(tool_id) > 120:
        raise SceneError('Host tool_id must be a nonempty string of <= 120 characters')
    for key in (*REQUIRED_CAPABILITIES, 'submitted_prompt_record_available'):
        if type(capabilities[key]) is not bool:
            raise SceneError('Host capability flags must be literal booleans')
    missing = [key for key in REQUIRED_CAPABILITIES if not capabilities[key]]
    report = {
        'format_version': '1.0',
        'kind': 'agent-native-provider-preflight',
        'source_packet_sha256': packet['packet_sha256'],
        'product_id': packet['product_id'],
        'tasks': [{
            'variant_id': item['variant_id'],
            'scene_id': item['scene_id'],
            'step_id': item['step_id'],
            'prompt_sha256': item['prompt_sha256'],
        } for item in packet['items']],
        'tool_id': tool_id,
        'capability_claim_sha256': _digest(capabilities),
        'route': 'host-native-blocked' if missing else 'host-native-eligible',
        'blocked_reasons': missing,
        'submitted_prompt_trace': (
            'may-be-self-reported' if capabilities['submitted_prompt_record_available']
            else 'not-available'
        ),
        'images_generated': 0,
        'external_api_fallback_authorized': False,
        'warning': (
            'Host capability declarations are not third-party attestations. '
            'Actual image, prompt trace, visual quality and owner sign-off '
            'must be checked separately.'
        ),
    }
    report['report_sha256'] = _digest(report)
    return report


def verify_host_preflight(packet: dict[str, Any], capabilities: dict[str, Any],
                          report: dict[str, Any]) -> dict[str, Any]:
    expected = preflight_host_agent(packet, capabilities)
    if not isinstance(report, dict) or report != expected:
        raise SceneError('Host preflight report differs from packet and capability declaration')
    return report
