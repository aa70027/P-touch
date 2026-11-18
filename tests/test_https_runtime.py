"""Regression: frozen HTTPS must retain the runtime's certificate policy."""
from pathlib import Path
import ssl
import time
from unittest.mock import Mock
import pytest
from labelstudio import runtime_ssl
from labelstudio import updater

def test_https_still_verifies_certificates_and_hostname():
    context=runtime_ssl.verified_context()
    assert context.verify_mode==ssl.CERT_REQUIRED
    assert context.check_hostname is True

def test_missing_policy_is_actionable(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime_ssl,'policy_required',lambda:True)
    monkeypatch.setattr(ssl,'__file__',str(tmp_path/'ssl.py'))
    with pytest.raises(ValueError,match='HTTPS_RUNTIME_FILE_MISSING'):
        runtime_ssl.verified_context()

def test_required_policy_packaging_path(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime_ssl,'policy_required',lambda:True)
    monkeypatch.setattr(ssl,'__file__',str(tmp_path/'ssl.py'))
    policy=tmp_path/runtime_ssl.POLICY_NAME;policy.write_bytes(b'policy fixture')
    assert runtime_ssl.required_runtime_files()==[policy]

def test_standard_python_needs_no_extra_policy(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime_ssl,'policy_required',lambda:False)
    monkeypatch.setattr(ssl,'__file__',str(tmp_path/'ssl.py'))
    assert runtime_ssl.required_runtime_files()==[]

def test_urlopen_receives_verified_context(monkeypatch):
    opener=Mock(return_value=object());monkeypatch.setattr(updater,'urlopen',opener)
    updater.request(updater.API)
    options=opener.call_args.kwargs
    assert options['timeout']==30
    assert options['context'].verify_mode==ssl.CERT_REQUIRED
    assert options['context'].check_hostname is True

def test_full_error_report_survives_restart(tmp_path,monkeypatch):
    def fail(*args):raise FileNotFoundError(2,'missing runtime file','policy.pem')
    monkeypatch.setattr(updater,'release_info',fail)
    worker=updater.Updater(tmp_path);worker.check()
    deadline=time.monotonic()+5
    while worker.busy and time.monotonic()<deadline:time.sleep(.01)
    report=updater.Updater(tmp_path).snapshot()
    assert report['state']=='error'
    assert report['error_type']=='FileNotFoundError'
    assert report['error_stage']=='checking'
    assert 'Traceback' in report['diagnostic_log'] and 'policy.pem' in report['diagnostic_log']
