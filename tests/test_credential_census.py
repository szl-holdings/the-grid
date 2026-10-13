"""Exercise the exact metadata predicate embedded in both workflow censuses.

Synthetic identities follow the Hub's GET /api/whoami-v2 response schema; no
token, Hub call or secret is used. Entity types and fields come from the Hub
OpenAPI description (as generated in alchemy-run/distilled
packages/huggingface/src/services/auth.ts@bf695406) and agree with Hugging
Face's own reader (huggingface/hf-mcp-server
packages/app/src/server/utils/hf-whoami.ts@29fc634f):
  auth.accessToken.role                    read | write | god | fineGrained
  auth.accessToken.fineGrained.scoped[]    {entity: {_id, type, name?}, permissions: [str]}
  entity.type                              dataset | model | space | bucket | kernel | container |
                                           collection | org | user | resource-group | oauth-app
  auth.accessToken.fineGrained.global[]    discussion.write | post.write
Repository write is the `repo.write` permission; on an `org` entity it is the
organization-wide grant ("all repos in selected organizations").
"""
import ast
import copy
import io
import json
import os
import tempfile
import unittest
import unittest.mock
import urllib.error
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPACE = 'SZLHOLDINGS/the-grid'
GROUP = 'a' * 24


def fixture():
    return {'type': 'user', 'orgs': [{'name': 'SZLHOLDINGS', 'roleInOrg': 'admin'}],
            'auth': {'accessToken': {'role': 'write'}}}


class CredentialCensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow = yaml.safe_load((ROOT / '.github/workflows/hf-space-drift.yml').read_text())
        source = workflow['jobs']['credential']['steps'][0]['run']
        parsed = ast.parse(source)
        declarations = ast.Module(body=[n for n in parsed.body if isinstance(n, (ast.Import, ast.FunctionDef))], type_ignores=[])
        cls.scope = {'org': 'SZLHOLDINGS', 'space': SPACE}
        exec(compile(declarations, '<actual-census-functions>', 'exec'), cls.scope)

    def allows(self, who, info=None):
        return self.scope['can_write_target'](who, {'id': SPACE} if info is None else info)

    def test_fine_grained_grant_is_for_exact_resource_and_repo_write(self):
        entities = (({'type': 'org', 'name': 'SZLHOLDINGS'}, True),
                    ({'type': 'space', 'name': SPACE}, True),
                    ({'type': 'space', 'name': 'SZLHOLDINGS/other'}, False),
                    ({'type': 'model', 'name': SPACE}, False),
                    ({'type': 'dataset', 'name': SPACE}, False),
                    ({'type': 'user', 'name': 'SZLHOLDINGS'}, False),
                    ({'type': 'org', 'name': 'other'}, False))
        for entity, expected in entities:
            for permissions in (['repo.write'], ['repo.content.read'], ['collection.write']):
                with self.subTest(entity=entity, permissions=permissions):
                    who = fixture()
                    who['auth']['accessToken'] = {'role': 'fineGrained', 'fineGrained': {'scoped': [{'entity': entity, 'permissions': permissions}]}}
                    self.assertEqual(self.allows(who), expected and permissions == ['repo.write'])

    def test_unknown_read_or_oauth_kind_is_not_write_authority(self):
        for role in ('read', 'unknown', 'oauth', '', None):
            who = fixture()
            who['auth']['accessToken']['role'] = role
            self.assertFalse(self.allows(who), role)
        self.assertTrue(self.allows(fixture()))

    def test_security_restrictions_and_org_roles_cannot_be_bypassed(self):
        for restrictions in (['token-policy'], ['mfa'], ['sso'], ['token-revoked'], ['ip'], '', None, {}):
            who = fixture()
            who['orgs'][0]['securityRestrictions'] = restrictions
            self.assertFalse(self.allows(who), restrictions)
        for role in ('read', 'contributor', 'no_access', None):
            who = fixture()
            who['orgs'][0]['roleInOrg'] = role
            self.assertFalse(self.allows(who), role)
        who = fixture()
        who['orgs'] *= 2
        self.assertFalse(self.allows(who))

    def test_group_membership_is_exact_and_omission_is_not_authority(self):
        who = fixture()
        who['orgs'][0]['roleInOrg'] = 'write'
        self.assertFalse(self.allows(who))
        info = {'id': SPACE, 'resourceGroup': {'id': GROUP}}
        for gid, role, expected in ((GROUP, 'write', True), (GROUP, 'admin', True),
                                    (GROUP, 'read', False), (GROUP, 'contributor', False), ('b'*24, 'write', False)):
            who['orgs'][0]['resourceGroups'] = [{'id': gid, 'role': role}]
            self.assertEqual(self.allows(who, info), expected)
        self.assertTrue(self.allows(fixture(), info))
        for group in ({}, False, [], 'group', {'id': 42}):
            self.assertFalse(self.allows(fixture(), {'id': SPACE, 'resourceGroup': group}))

    def test_malformed_or_other_space_metadata_cannot_pass(self):
        for field, value in (('orgs', {}), ('orgs', None), ('auth', []), ('auth', None)):
            who = copy.deepcopy(fixture())
            who[field] = value
            self.assertFalse(self.allows(who))
        self.assertFalse(self.allows(fixture(), {'id': 'SZLHOLDINGS/other'}))

    @staticmethod
    def fine_grained(fine):
        who = fixture()
        who['auth']['accessToken'] = {'role': 'fineGrained'}
        if fine is not ABSENT:
            who['auth']['accessToken']['fineGrained'] = fine
        return who

    def test_only_org_or_exact_space_entities_carry_repo_write(self):
        # Every entity type in the whoami-v2 schema, named like the org and like
        # the Space; only the org-wide grant and the exact Space may write.
        for kind in SCHEMA_ENTITY_TYPES:
            for name in ('SZLHOLDINGS', SPACE):
                with self.subTest(type=kind, name=name):
                    scope = {'entity': {'_id': OBJECT_ID, 'type': kind, 'name': name}, 'permissions': ['repo.write']}
                    expected = (kind, name) in {('org', 'SZLHOLDINGS'), ('space', SPACE)}
                    self.assertIs(self.allows(self.fine_grained({'scoped': [scope]})), expected)

    def test_near_miss_names_and_types_are_other_resources(self):
        for kind, name in (('space', 'szlholdings/the-grid'), ('space', 'SZLHOLDINGS/THE-GRID'),
                           ('space', SPACE + ' '), ('space', SPACE + '/'), ('space', 'SZLHOLDINGS/the-grid-staging'),
                           ('space', 'other/the-grid'), ('space', 'the-grid'), ('space', None),
                           ('Space', SPACE), ('spaces', SPACE), ('org', 'szlholdings'), ('org', 'SZLHOLDINGS/'),
                           ('org', None), (None, SPACE)):
            with self.subTest(type=kind, name=name):
                scope = {'entity': {'_id': OBJECT_ID, 'type': kind, 'name': name}, 'permissions': ['repo.write']}
                self.assertFalse(self.allows(self.fine_grained({'scoped': [scope]})))

    def test_read_only_and_unrelated_write_permissions_are_not_repo_write(self):
        for permissions in ([], ['repo.content.read'], ['repo.content.read', 'discussion.write'],
                            ['collection.write', 'inference.endpoints.write', 'job.write', 'post.write'],
                            ['repo.writer'], ['Repo.Write'], ['repo.write ']):
            for entity in ({'_id': OBJECT_ID, 'type': 'org', 'name': 'SZLHOLDINGS'},
                           {'_id': OBJECT_ID, 'type': 'space', 'name': SPACE}):
                with self.subTest(permissions=permissions, entity=entity['type']):
                    who = self.fine_grained({'scoped': [{'entity': entity, 'permissions': permissions}]})
                    self.assertFalse(self.allows(who))
        # Global permissions are not bound to any repository.
        global_only = self.fine_grained({'scoped': [], 'global': ['discussion.write', 'post.write', 'repo.write']})
        self.assertFalse(self.allows(global_only))

    def test_missing_or_malformed_fine_grained_scope_cannot_write(self):
        exact = {'_id': OBJECT_ID, 'type': 'space', 'name': SPACE}
        for fine in (ABSENT, None, [], 'repo.write', {}, {'scoped': None}, {'scoped': {}},
                     {'scoped': 'repo.write'}, {'scoped': {'entity': exact, 'permissions': ['repo.write']}},
                     {'scoped': [None]}, {'scoped': [SPACE]}, {'scoped': [['repo.write']]},
                     {'scoped': [{'permissions': ['repo.write']}]},
                     {'scoped': [{'entity': None, 'permissions': ['repo.write']}]},
                     {'scoped': [{'entity': SPACE, 'permissions': ['repo.write']}]},
                     {'scoped': [{'entity': exact}]},
                     {'scoped': [{'entity': exact, 'permissions': None}]},
                     {'scoped': [{'entity': exact, 'permissions': 'repo.write'}]},
                     {'scoped': [{'entity': exact, 'permissions': {'repo.write': True}}]},
                     {'scoped': [{'entity': exact, 'permissions': [None, ['repo.write']]}]}):
            with self.subTest(fineGrained=fine):
                self.assertIs(self.allows(self.fine_grained(fine)), False)

    def test_an_exact_grant_is_found_among_other_scopes_in_any_order(self):
        other = {'entity': {'_id': OBJECT_ID, 'type': 'space', 'name': 'SZLHOLDINGS/other'}, 'permissions': ['repo.write']}
        read = {'entity': {'_id': OBJECT_ID, 'type': 'space', 'name': SPACE}, 'permissions': ['repo.content.read']}
        exact = {'entity': {'_id': OBJECT_ID, 'type': 'space', 'name': SPACE},
                 'permissions': ['repo.content.read', 'repo.write']}
        self.assertFalse(self.allows(self.fine_grained({'scoped': [other, read]})))
        for scoped in ([other, read, exact], [exact, other], [read, None, exact]):
            self.assertTrue(self.allows(self.fine_grained({'scoped': scoped})))
        # A destination grant never overrides the membership and Space checks.
        who = self.fine_grained({'scoped': [exact]})
        who['orgs'][0]['roleInOrg'] = 'read'
        self.assertFalse(self.allows(who))
        self.assertFalse(self.allows(self.fine_grained({'scoped': [exact]}), {'id': 'SZLHOLDINGS/other'}))

    def test_god_role_and_unknown_roles_are_not_write_authority(self):
        org_wide = {'entity': {'_id': OBJECT_ID, 'type': 'org', 'name': 'SZLHOLDINGS'}, 'permissions': ['repo.write']}
        for role in ('god', 'admin', 'Write', 'fine-grained', 'fine_grained', ['write'], {'write': True}):
            with self.subTest(role=role):
                who = fixture()
                who['auth']['accessToken'] = {'role': role, 'fineGrained': {'scoped': [org_wide]}}
                self.assertFalse(self.allows(who))


ABSENT = object()
OBJECT_ID = '0' * 24
SCHEMA_ENTITY_TYPES = ('dataset', 'model', 'space', 'bucket', 'kernel', 'container', 'collection', 'org', 'user',
                       'resource-group', 'oauth-app')
ORG_TOKEN = 'SYNTHETIC-ORG-CANDIDATE-VALUE-0001'
REPO_TOKEN = 'SYNTHETIC-REPO-CANDIDATE-VALUE-0002'


class FakeResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, limit=-1):
        return self.body if limit < 0 else self.body[:limit]


class CensusSelection(unittest.TestCase):
    """Run each workflow's whole census step against a fake Hub.

    This pins which secret the deploy receives: `pick` from hf-space.yml is the
    only thing that chooses HF_ORG_TOKEN or HF_TOKEN for the deployer.
    """

    WORKFLOWS = ('.github/workflows/hf-space.yml', '.github/workflows/hf-space-drift.yml')

    def run_census(self, workflow, hub, tokens):
        step = yaml.safe_load((ROOT / workflow).read_text(encoding='utf-8'))['jobs']['credential']['steps'][0]
        calls = []

        def urlopen(req, timeout=None):
            token = req.get_header('Authorization', '').removeprefix('Bearer ')
            calls.append((req.full_url, token, timeout))
            answer = hub[token][req.full_url]
            if isinstance(answer, int):
                raise urllib.error.HTTPError(req.full_url, answer, 'synthetic', {}, io.BytesIO(b'{}'))
            return FakeResponse(answer)

        with tempfile.TemporaryDirectory() as tmp:
            summary, output = Path(tmp, 'summary.md'), Path(tmp, 'output.txt')
            summary.touch()
            output.touch()
            env = {'HUB_ORG': step['env']['HUB_ORG'], 'HUB_SPACE': step['env']['HUB_SPACE'],
                   'CANDIDATE_HF_ORG_TOKEN': tokens.get('HF_ORG_TOKEN', ''),
                   'CANDIDATE_HF_TOKEN': tokens.get('HF_TOKEN', ''),
                   'GITHUB_STEP_SUMMARY': str(summary), 'GITHUB_OUTPUT': str(output)}
            stdout, exit_message = io.StringIO(), None
            with unittest.mock.patch.dict(os.environ, env), \
                 unittest.mock.patch('urllib.request.urlopen', side_effect=urlopen), \
                 unittest.mock.patch('sys.stdout', stdout):
                try:
                    exec(compile(step['run'], f'<{workflow} census>', 'exec'), {'__name__': '__census__'})
                except SystemExit as stop:
                    exit_message = str(stop.code)
            text = stdout.getvalue() + summary.read_text(encoding='utf-8') + output.read_text(encoding='utf-8')
            pick = dict(line.split('=', 1) for line in output.read_text(encoding='utf-8').splitlines()).get('pick')
            rows = json.loads(stdout.getvalue().splitlines()[0])
        for value in (ORG_TOKEN, REPO_TOKEN):
            self.assertNotIn(value, text + (exit_message or ''), 'a credential value reached the job output')
        for url, _token, timeout in calls:
            self.assertIn(url, (WHOAMI, SPACE_INFO))
            self.assertEqual(timeout, 30)
        return pick, rows, exit_message, calls

    @staticmethod
    def hub(org_who=None, org_code=None, repo_who=None, repo_code=None, info=None):
        info = {'id': SPACE} if info is None else info
        hub = {}
        for token, who, code in ((ORG_TOKEN, org_who, org_code), (REPO_TOKEN, repo_who, repo_code)):
            hub[token] = {WHOAMI: code if code is not None else who, SPACE_INFO: info}
        return hub

    @staticmethod
    def classic(role='write'):
        who = fixture()
        who['auth'] = {'type': 'access_token', 'accessToken': {'role': role}}
        return who

    @staticmethod
    def scoped(kind, name):
        who = fixture()
        scope = {'entity': {'_id': OBJECT_ID, 'type': kind, 'name': name},
                 'permissions': ['repo.content.read', 'repo.write']}
        who['auth'] = {'type': 'access_token', 'accessToken': {'role': 'fineGrained', 'fineGrained': {'scoped': [scope]}}}
        return who

    def each_workflow(self, hub, tokens=None):
        tokens = {'HF_ORG_TOKEN': ORG_TOKEN, 'HF_TOKEN': REPO_TOKEN} if tokens is None else tokens
        results = [self.run_census(workflow, hub, tokens) for workflow in self.WORKFLOWS]
        self.assertEqual(results[0], results[1], 'deploy and drift censuses disagree')
        return results[0]

    def test_current_production_shape_still_selects_hf_token(self):
        # The census rows printed by deploy run 38439774145 and drift run
        # 38440140726 on b740f7a: HF_ORG_TOKEN rejected with HTTP 400, HF_TOKEN a
        # classic write token that can write. That selection must not change.
        pick, rows, exit_message, calls = self.each_workflow(self.hub(org_code=400, repo_who=self.classic()))
        self.assertEqual(pick, 'HF_TOKEN')
        self.assertIsNone(exit_message)
        self.assertEqual(rows, [{'secret': 'HF_ORG_TOKEN', 'present': True, 'valid': False, 'http': 400},
                                {'secret': 'HF_TOKEN', 'present': True, 'valid': True, 'kind': 'write',
                                 'expires': None, 'can_write': True}])
        self.assertEqual([(url, token) for url, token, _ in calls],
                         [(WHOAMI, ORG_TOKEN), (WHOAMI, REPO_TOKEN), (SPACE_INFO, REPO_TOKEN)])

    def test_organization_candidate_is_preferred_when_it_can_write(self):
        for org_who in (self.classic(), self.scoped('org', 'SZLHOLDINGS'), self.scoped('space', SPACE)):
            with self.subTest(org=org_who['auth']['accessToken']):
                pick, rows, exit_message, _ = self.each_workflow(self.hub(org_who=org_who, repo_who=self.classic()))
                self.assertEqual((pick, exit_message), ('HF_ORG_TOKEN', None))
                self.assertTrue(rows[0]['can_write'])

    def test_valid_token_for_another_destination_is_skipped_not_selected(self):
        for org_who in (self.scoped('space', 'SZLHOLDINGS/other'), self.scoped('model', SPACE),
                        self.scoped('dataset', SPACE), self.scoped('org', 'other'), self.classic('read')):
            with self.subTest(org=org_who['auth']['accessToken']):
                pick, rows, exit_message, _ = self.each_workflow(self.hub(org_who=org_who, repo_who=self.classic()))
                self.assertEqual((pick, exit_message), ('HF_TOKEN', None))
                self.assertEqual((rows[0]['valid'], rows[0]['can_write']), (True, False))

    def test_malformed_provider_answer_for_one_candidate_does_not_stop_the_next(self):
        bad_role = self.classic()
        bad_role['orgs'][0]['roleInOrg'] = ['admin']
        for org_who, error in (([], 'ValueError'), ('write', 'ValueError'), (bad_role, 'TypeError')):
            with self.subTest(error=error, org=org_who):
                pick, rows, exit_message, _ = self.each_workflow(self.hub(org_who=org_who, repo_who=self.classic()))
                self.assertEqual((pick, exit_message), ('HF_TOKEN', None))
                self.assertEqual(rows[0], {'secret': 'HF_ORG_TOKEN', 'present': True, 'valid': False, 'error': error})

    def test_fails_closed_naming_the_space_when_nothing_can_write(self):
        cases = (({'HF_ORG_TOKEN': ORG_TOKEN, 'HF_TOKEN': REPO_TOKEN},
                  self.hub(org_who=self.scoped('space', 'SZLHOLDINGS/other'), repo_who=self.classic('read'))),
                 ({'HF_ORG_TOKEN': ORG_TOKEN, 'HF_TOKEN': REPO_TOKEN}, self.hub(org_code=400, repo_code=401)),
                 ({}, self.hub()))
        for tokens, hub in cases:
            with self.subTest(tokens=sorted(tokens)):
                pick, rows, exit_message, calls = self.each_workflow(hub, tokens)
                self.assertIsNone(pick)
                self.assertIn(f'verified write authorization for {SPACE}', exit_message)
                self.assertFalse(any(row.get('can_write') for row in rows))
                if not tokens:
                    self.assertEqual(rows, [{'secret': 'HF_ORG_TOKEN', 'present': False},
                                            {'secret': 'HF_TOKEN', 'present': False}])
                    self.assertEqual(calls, [])


WHOAMI = 'https://huggingface.co/api/whoami-v2'
SPACE_INFO = f'https://huggingface.co/api/spaces/{SPACE}?expand=resourceGroup'
