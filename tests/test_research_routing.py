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


@pytest.mark.parametrize('query,expected', [
    ('Snowball research from this expert tip about reliable coding hooks', 'seeded_snowball'),
    ('Expand this idea into related useful guidance', 'seeded_snowball'),
    ('Analyze Acme quarterly earnings and guidance', 'earnings_analysis'),
    ('Find what changed this quarter in results and guidance', 'earnings_analysis'),
    ('Explain why operating margin fell despite growth', 'financial_mechanisms'),
    ('Compare demand, supply and cost scenarios using one baseline', 'scenario_analysis'),
    ('Synthesize these interviews into themes and dissent', 'thematic_synthesis'),
    ('Update previous research with the new evidence', 'longitudinal_update'),
    ('Prepare expert interview questions to fill our evidence gaps', 'expert_interview'),
])
def test_raw_queries_offer_candidates_without_selecting_or_executing(query, expected):
    route = research._research_route({'query': query})
    assert expected in [c['approach'] for c in route['approach_candidates']]
    assert all(c['status'] == 'tentative' for c in route['approach_candidates'])
    assert route['approaches'] == []
    assert route['approach_contracts'] == []
    assert route['approach_selection_required'] is True
    assert route['allowed_execution'] == 'plan_only'


@pytest.mark.parametrize('query', ['What is earnings per share?', 'Define snowball sampling',
                                  'Research finance', 'Explain a Python function'])
def test_topic_labels_and_definitions_do_not_select_an_approach(query):
    route = research._research_route({'query': query})
    assert route['approach_candidates'] == []
    assert route['approaches'] == []
    assert route['approach_selection_required'] is False


@pytest.mark.parametrize('approach', sorted(research.RESEARCH_APPROACHES))
def test_selected_approaches_return_contracts_and_existing_reference(approach):
    route = research._research_route({'query': 'Investigate the supplied evidence',
        'task_shape': 'explain', 'methods': [], 'approaches': [approach]})
    assert route['approaches'] == [approach]
    assert route['confidence'] == 'clear'
    assert route['approach_selection_required'] is False
    contract = route['approach_contracts'][0]
    assert contract['required_inputs'] and contract['completion_rule']
    assert (Path(research.__file__).parent / contract['reference'].split('#')[0]).is_file()


def test_override_can_reject_all_candidates_without_changing_independent_controls():
    route = research._research_route({'query': 'Analyze quarterly earnings; do not save',
        'task_shape': 'compare', 'methods': [], 'approaches': ['earnings_analysis'],
        'depth': 'light', 'source_policy': 'supplied',
        'overrides': {'approaches': [], 'persist': False}})
    assert route['approaches'] == route['approach_candidates'] == []
    assert route['depth'] == 'light' and route['persist'] is False
    assert route['source_policy'] == 'supplied'
    assert route['field_origins']['approaches'] == 'user_override'


def test_scenario_selection_requires_computation_but_does_not_grant_permission():
    route = research._research_route({'query': 'Assess these possible outcomes',
        'task_shape': 'compare', 'methods': [], 'approaches': ['scenario_analysis'],
        'computation': 'forbidden', 'source_policy': 'supplied'})
    assert route['computation'] == 'forbidden'
    assert route['allowed_execution'] == 'plan_only'
    assert route['status'] == 'blocked_missing_input'
    assert 'python' in route['required_capabilities']


def test_ordered_approaches_do_not_invent_scientific_methods():
    selected = ['earnings_analysis', 'financial_mechanisms', 'scenario_analysis']
    route = research._research_route({'query': 'Review these supplied statements',
        'task_shape': 'compare', 'methods': [], 'approaches': selected})
    assert [c['approach'] for c in route['approach_contracts']] == selected
    assert route['methods'] == []
    assert route['computation'] == 'required'


@pytest.mark.parametrize('approaches', [None, 'earnings_analysis', [{}], ['unknown'],
                                       ['earnings_analysis', 'earnings_analysis']])
def test_approach_contract_rejects_bad_values(approaches):
    with pytest.raises(ValueError, match='approaches'):
        research._research_route({'query': 'Research this', 'approaches': approaches})


def test_approach_receipt_cli_is_read_only(tmp_path):
    request = tmp_path / 'request.json'
    request.write_text(json.dumps({'query': 'Expand this tip into related guidance',
        'task_shape': 'survey', 'methods': [], 'approaches': ['seeded_snowball'],
        'overrides': {'persist': False, 'source_policy': 'supplied'}}))
    env = {**os.environ, 'RESEARCH_CONTENT_DIR': str(tmp_path / 'corpus'),
           'RESEARCH_INDEX_DIR': str(tmp_path / 'index')}
    result = subprocess.run([sys.executable, str(Path(research.__file__)), 'route',
        '--request-file', str(request), '--json'], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    route = json.loads(result.stdout)
    assert route['approaches'] == ['seeded_snowball'] and route['persist'] is False
    assert not (tmp_path / 'corpus').exists() and not (tmp_path / 'index').exists()
