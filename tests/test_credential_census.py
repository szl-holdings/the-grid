"""Exercise the exact metadata predicate embedded in both workflow censuses."""
import ast
import copy
import unittest
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
