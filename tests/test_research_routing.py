"""Routing controls must remain independent and must not claim execution."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import research


def test_explicit_controls_win_without_disabling_calculation():
    route = research._research_route({
        'query': 'deep research calculate percentage change',
        'task_shape': 'explain', 'methods': ['measurement'], 'depth': 'deep',
        'overrides': {'depth': 'light', 'persist': False},
    })
    assert route['depth'] == 'light'
    assert route['persist'] is False
    assert route['computation'] == 'required'
    assert route['status'] == 'planned'
    assert route['field_origins']['depth'] == 'user_override'


def test_no_save_does_not_reduce_depth():
    query = 'deep research architecture risks'
    before = research._research_depth_profile(query)
    after = research._research_depth_profile(query + ' do not save')
    assert before['depth'] == after['depth'] == 'deep'
    assert before['score'] == after['score']
    assert after['persist'] is False
    assert all('persist' not in phase for phase in after['phases'])


def test_long_quick_request_does_not_silently_escalate():
    route = research._research_depth_profile('quick research ' + 'architecture risks and recommendations ' * 10)
    assert route['depth'] == 'light'


def test_ordered_methods_preserve_dependencies_and_gaps():
    route = research._research_route({'query': 'Investigate an intervention', 'task_shape': 'explain',
        'methods': ['qualitative', 'hypothesis', 'experiment', 'causal'],
        'available_capabilities': ['python']})
    assert route['missing_capabilities'] == ['experiment_executor']
    assert route['status'] == 'blocked_missing_input'
    assert route['stages'][2]['depends_on'] == ['stage-2']
    assert route['stages'][3]['depends_on'] == ['stage-3']


@pytest.mark.parametrize('changes', [
    {'depth': 'maximum'}, {'methods': ['causal', 'causal']}, {'methods': [{}]},
    {'persist': 'false'}, {'task_shape': []}, {'independent_tasks': True},
    {'available_capabilities': 'python'}, {'extra': True}, {'overrides': {'query': 'changed'}},
    {'query': ''}, {'domain': None}, {'overrides': []},
])
def test_invalid_contracts_fail_closed(changes):
    with pytest.raises(ValueError):
        research._research_route({'query': 'Research a topic', **changes})


def test_fanout_needs_independence_and_permission():
    request = {'query': 'Compare vendors', 'task_shape': 'compare', 'methods': [], 'independent_tasks': 3}
    assert research._research_route(request)['stages'][0]['structure'] == 'single_loop'
    request['allowed_execution'] = 'agents'
    assert research._research_route(request)['stages'][0]['structure'] == 'bounded_fanout_merge'
    request['independent_tasks'] = 0
    assert research._research_route(request)['stages'][0]['structure'] == 'single_loop'


def test_computation_and_source_restrictions_remain_visible():
    route = research._research_route({'query': 'calculate latest pricing', 'source_policy': 'local', 'computation': 'forbidden'})
    assert route['computation'] == 'forbidden'
    assert len(route['blockers']) == 2
    assert route['status'] == 'blocked_missing_input'


def test_domain_does_not_choose_method():
    route = research._research_route({'query': 'Research psychology', 'domain': 'psychology'})
    assert route['methods'] == []
    assert route['confidence'] == 'tentative'


@pytest.mark.parametrize('method', sorted(research.RESEARCH_METHODS))
def test_every_method_declares_evidence_not_completion(method):
    route = research._research_route({'query': 'Investigate this', 'task_shape': 'explain', 'methods': [method]})
    assert route['stages'][0]['required_inputs']
    assert route['stages'][0]['completion_rule']
    assert route['status'] == 'planned'
    assert route['capabilities_checked'] is False


def test_cli_is_read_only_and_rejects_unknown_fields(tmp_path):
    request = tmp_path / 'request.json'
    request.write_text(json.dumps({'query': 'Calculate a percentage', 'persist': False}))
    env = {**os.environ, 'RESEARCH_CONTENT_DIR': str(tmp_path / 'corpus'), 'RESEARCH_INDEX_DIR': str(tmp_path / 'index')}
    command = [sys.executable, str(Path(research.__file__)), 'route', '--request-file', str(request), '--json']
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['computation'] == 'required'
    assert not (tmp_path / 'corpus').exists()
    assert not (tmp_path / 'index').exists()
    request.write_text('{"query":"test","methods":["made_up"]}')
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert 'Traceback' not in result.stderr


def test_generated_analysis_does_not_claim_to_answer_custom_question(tmp_path):
    # Execute the actual generated script against known numbers, with a matching input hash.
    import hashlib
    data = tmp_path / 'data.csv'
    data.write_text('value\n2\n4\n')
    script = tmp_path / 'analysis.py'
    script.write_text(research._analysis_script_text())
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps({'question': 'What caused the change?', 'inputs': [{
        'path': str(data), 'input_type': 'csv', 'sha256': hashlib.sha256(data.read_bytes()).hexdigest()}]}))
    output = tmp_path / 'output'
    result = subprocess.run([sys.executable, str(script), '--plan', str(plan), '--out-dir', str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    artifact = json.loads((output / 'results.json').read_text())
    assert artifact['analysis_scope'] == 'profiling_only'
    assert artifact['question_answered'] is False
    assert artifact['findings'][0]['profile']['columns'][0]['numeric']['mean'] == '3'
    data.write_text('value\n2\n400\n')
    result = subprocess.run([sys.executable, str(script), '--plan', str(plan), '--out-dir', str(output)], capture_output=True, text=True)
    assert result.returncode == 2
    artifact = json.loads((output / 'results.json').read_text())
    assert artifact['status'] == 'validation_failed'
    assert artifact['findings'][0]['certainty'] == 'Low'


def test_contested_is_verification_overlay():
    route = research._research_route({'query': 'Compare conflicting evidence', 'task_shape': 'compare', 'methods': []})
    assert route['verification'] == 'adjudication'
    assert route['stages'][0]['structure'] == 'single_loop'
