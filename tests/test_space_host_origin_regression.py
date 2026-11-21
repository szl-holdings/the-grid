"""Synthetic negative controls: Hub metadata must not direct runner GETs off the owning Space."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

script=Path(__file__).resolve().parents[1]/".github"/"scripts"/"hf_space_drift.py"
spec=importlib.util.spec_from_file_location("pinned_drift_module",script)
drift=importlib.util.module_from_spec(spec)
spec.loader.exec_module(drift)
SPACE="SZLHOLDINGS/the-grid"
GOOD="https://szlholdings-the-grid.hf.space"
SHA="a"*40

class ProviderHostNegativeControls(unittest.TestCase):
    def check(self,host):
        called=[]
        def fake_get(url,timeout=30,**kwargs):
            called.append(url)
            if url==f"{drift.HUB}/api/spaces/{SPACE}":
                return 200,json.dumps({"sha":SHA,"runtime":{"sha":SHA,"stage":"RUNNING"},"host":host}).encode()
            if "/tree/" in url:
                return 200,json.dumps([{"path":"play.html","type":"file","oid":"b"*40}]).encode()
            return 200,b"synthetic-public-bytes"
        with patch.object(drift,"get",side_effect=fake_get):
            drift.observe(SPACE,["play.html"],{"/":"play.html"})
        return called

    def test_expected_hf_space_host_still_read(self):
        calls=self.check(GOOD)
        self.assertIn(GOOD+"/",calls)

    def test_loopback_host_from_metadata_must_never_be_requested(self):
        calls=self.check("http://127.0.0.1:8123")
        self.assertFalse(any(u.startswith("http://127.0.0.1") for u in calls),calls)

    def test_unrelated_https_host_from_metadata_must_never_be_requested(self):
        calls=self.check("https://unrelated.example")
        self.assertFalse(any(u.startswith("https://unrelated.example") for u in calls),calls)

    def test_invalid_origin_is_reported_as_blocked_not_success(self):
        result={"api_status":200,"api":{"sha":SHA,"runtime":{"stage":"RUNNING","sha":SHA}},
                "host_valid":False,"hub_oids":{"play.html":"b"*40},"tree_status":200,"smoke":{}}
        found=drift.problems(result,{"play.html":"b"*40},["play.html"],{"/":"play.html"})
        self.assertTrue(any("expected owning HTTPS" in msg for msg in found))

    def test_served_get_uses_redirect_refusing_opener(self):
        from urllib.error import HTTPError
        from io import BytesIO
        from unittest.mock import Mock
        opener=Mock()
        url=GOOD+"/"
        opener.open.side_effect=HTTPError(url,302,"synthetic redirect",{"Location":"http://127.0.0.1/"},BytesIO(b""))
        with patch.object(drift.urllib.request,"build_opener",return_value=opener) as build:
            status,body=drift.get(url,no_redirect=True)
        self.assertEqual((status,body),(302,b""))
        self.assertIsInstance(build.call_args.args[0],drift._RefuseRedirect)
        self.assertIsNone(build.call_args.args[0].redirect_request(None,None,302,"",{},"http://127.0.0.1/"))
if __name__=="__main__":
    unittest.main()
