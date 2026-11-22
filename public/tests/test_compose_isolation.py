"""Config-only regressions. Never builds, starts or deletes Docker resources."""
import copy
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from compose_smoke import Smoke, check, main

CONFLICTS = {
    'DATABASE_URL':'postgresql://outsider:foreign-password@production.invalid:5432/real',
    'POSTGRES_VOLUME_NAME':'afisha_db_data', 'UPLOADS_PATH':str(Path.home()),
    'ADMIN_PASSWORD':'foreign-admin', 'POSTGRES_PASSWORD':'foreign-db', 'SECRET_KEY':'foreign-secret',
    'COMPOSE_PROJECT_NAME':'foreign-project','COMPOSE_FILE':'/foreign/compose.yml',
    'COMPOSE_PROFILES':'production','COMPOSE_ENV_FILES':'/foreign/.env',
    'DOCKER_HOST':'tcp://production.invalid:2376','DOCKER_CONTEXT':'production-remote',
    'DOCKER_CONFIG':'/foreign/docker','DOCKER_TLS_VERIFY':'1','DOCKER_CERT_PATH':'/foreign/certs',
}


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='afisha-pr10-unit-',dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.smoke = Smoke(self.temp.name)
        # Real Compose config parser, no containers or daemon writes.
        self.config = json.loads(self.smoke.compose('config','--format','json'))

    def fake_run(self, config, calls, volume_info=None, collision=False, fail_up=False):
        def run(*args, **kwargs):
            calls.append(args)
            if args[0] == 'compose':
                if 'config' in args: return json.dumps(config)
                if 'up' in args and fail_up: raise RuntimeError('up failed')
                return ''
            if args[:2] == ('volume','ls'):
                return self.smoke.volume if volume_info or collision else ''
            if args[:2] == ('volume','inspect'): return json.dumps([volume_info])
            return ''
        return run

    def test_conflicting_shell_is_not_inherited_by_real_config(self):
        with patch.dict(os.environ,CONFLICTS), patch('compose_smoke.subprocess.run', wraps=__import__('subprocess').run) as run:
            config = json.loads(self.smoke.compose('config','--format','json'))
            self.smoke.validate(config)
            self.assertEqual(set(run.call_args.kwargs['env']), {'PATH','HOME'})
            self.assertTrue(set(CONFLICTS).isdisjoint(run.call_args.kwargs['env']))
            command = run.call_args.args[0]
            self.assertIn('--context',command)
            self.assertIn(self.smoke.context,command)
            self.assertNotIn('production-remote',command)
            self.assertEqual(config['volumes']['afisha_db_data']['name'],self.smoke.volume)
            self.assertEqual(config['services']['backend']['volumes'][0]['source'],str(self.smoke.uploads))
            self.assertNotEqual(str(self.smoke.uploads),CONFLICTS['UPLOADS_PATH'])

    def test_remote_context_endpoint_is_rejected_before_daemon_access(self):
        calls=[]
        def inspect(*args,**kwargs):
            calls.append(args)
            return json.dumps([{'Name':self.smoke.context,'Endpoints':{'docker':{'Host':'tcp://production.invalid:2376'}}}])
        with patch.object(self.smoke,'run',side_effect=inspect):
            with self.assertRaises(RuntimeError): check(self.smoke)
        self.assertEqual(calls,[('context','inspect',self.smoke.context)])

    def test_verified_socket_is_pinned_for_subsequent_commands(self):
        for name, endpoint in [('desktop-linux', 'unix://'+str(Path.home()/'.docker/run/docker.sock')),
                               ('default', 'unix:///var/run/docker.sock')]:
            with self.subTest(context=name):
                self.smoke.context = name
                context=[{'Name':name,'Endpoints':{'docker':{'Host':endpoint}}}]
                with patch.object(self.smoke,'run',side_effect=[json.dumps(context),json.dumps({'OSType':'linux'})]), patch.object(Path,'is_socket',return_value=True):
                    self.smoke.local_daemon()
                self.assertEqual(self.smoke.docker[-2:],['--host',endpoint])
                self.assertNotIn('--context',self.smoke.docker)

    def test_real_config_only_cli_with_conflicts_uses_local_daemon_and_cleans_temp(self):
        before=set(Path('/tmp').glob('afisha-pr10-*'))
        result=subprocess.run(['bash',str(Path(__file__).with_name('compose-smoke.sh')),'--config-only'],
                              env={**os.environ,**CONFLICTS},text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('PASS isolated config:',result.stdout)
        self.assertNotIn('PASS Compose:',result.stdout)
        self.assertNotIn('PASS cleanup:',result.stdout)
        self.assertEqual(set(Path('/tmp').glob('afisha-pr10-*')),before)

    def test_main_validation_failure_removes_sensitive_temp_files(self):
        paths=[]
        def fail(smoke):
            paths.append(smoke.directory)
            self.assertTrue(smoke.env_file.exists())
            raise RuntimeError('validation failed')
        with patch('sys.argv',['compose_smoke.py','--config-only']), patch.object(Smoke,'prepare',fail), patch.object(Smoke,'run') as run:
            with self.assertRaises(RuntimeError):main()
        run.assert_not_called()
        self.assertTrue(paths)
        self.assertFalse(paths[0].exists())

    def test_all_unsafe_configurations_fail_before_any_write_or_cleanup(self):
        mutations = [
            lambda c:c.update(name='foreign'),
            lambda c:c['volumes']['afisha_db_data'].update(name='afisha_db_data'),
            lambda c:c['volumes']['afisha_db_data'].update(external=True),
            lambda c:c['volumes']['afisha_db_data'].update(driver_opts={'device':'/user/data','type':'none','o':'bind'}),
            lambda c:c['services']['db']['volumes'][0].update(source='foreign'),
            lambda c:c['services']['backend']['environment'].update(DATABASE_URL=CONFLICTS['DATABASE_URL']),
            lambda c:c['services']['db']['environment'].update(POSTGRES_PASSWORD='foreign'),
            lambda c:c['services']['backend']['environment'].update(ADMIN_PASSWORD='foreign'),
            lambda c:c['services']['backend']['environment'].update(SECRET_KEY='foreign'),
            lambda c:c['services']['backend']['volumes'][0].update(source=CONFLICTS['UPLOADS_PATH']),
            lambda c:c['services']['public']['ports'][0].update(host_ip='0.0.0.0'),
            lambda c:c['services']['backend'].update(networks={'foreign':None}),
            lambda c:c['services'].update(foreign={}),
            lambda c:c['networks']['afisha'].update(external=True),
            lambda c:c['networks']['afisha'].update(driver_opts={'foreign':'option'}),
            lambda c:c['volumes'].update(foreign={'external':True}),
            lambda c:c['services']['public']['environment'].update(INTERNAL_API_URL='https://production.invalid'),
            lambda c:c['services']['public']['build'].update(secrets=['foreign']),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                config=copy.deepcopy(self.config); mutate(config); calls=[]
                with patch.object(self.smoke,'local_daemon'), patch.object(self.smoke,'run',side_effect=self.fake_run(config,calls)):
                    with self.assertRaises(RuntimeError): check(self.smoke)
                self.assertEqual(len(calls),1)
                self.assertIn('config',calls[0])
                self.assertFalse(self.smoke.started)

    def test_config_only_never_writes_docker_resources(self):
        calls=[]
        with patch.object(self.smoke,'local_daemon'), patch.object(self.smoke,'run',side_effect=self.fake_run(self.config,calls)):
            check(self.smoke,config_only=True)
        self.assertTrue(self.smoke.validated)
        self.assertFalse(any('down' in c or 'build' in c or 'up' in c or 'rm' in c for c in calls))
        self.assertEqual(json.loads(self.smoke.frozen.read_text()),self.config)

    def test_preexisting_volume_refuses_up_and_cleanup(self):
        calls=[]
        with patch.object(self.smoke,'local_daemon'), patch.object(self.smoke,'run',side_effect=self.fake_run(self.config,calls,collision=True)):
            with self.assertRaises(RuntimeError): check(self.smoke)
        self.assertFalse(any('down' in c or 'build' in c or 'up' in c or 'rm' in c for c in calls))

    def test_failed_up_cleans_only_new_verified_volume_using_frozen_config(self):
        self.smoke.validate(self.config)
        self.smoke.frozen=Path(self.temp.name)/'validated.json'
        self.smoke.frozen.write_text(json.dumps(self.config))
        self.smoke.validated=self.smoke.fresh=True
        calls=[]
        info={'Name':self.smoke.volume,'Labels':{'com.docker.compose.project':self.smoke.project}}
        with patch.object(self.smoke,'run',side_effect=self.fake_run(self.config,calls,info,fail_up=True)):
            with self.assertRaises(RuntimeError):
                try:self.smoke.execute()
                finally:self.smoke.cleanup()
        self.assertIn(('volume','rm',self.smoke.volume),calls)
        for command in (c for c in calls if c[0]=='compose'):
            self.assertIn(str(self.smoke.frozen),command)
            self.assertIn(self.smoke.project,command)
            self.assertNotIn('-v',command)

    def test_cleanup_refuses_volume_name_or_label_mismatch(self):
        for info in [{'Name':'afisha_db_data','Labels':{'com.docker.compose.project':self.smoke.project}},
                     {'Name':self.smoke.volume,'Labels':{'com.docker.compose.project':'foreign'}}]:
            calls=[]
            self.smoke.started=self.smoke.validated=self.smoke.fresh=True
            with patch.object(self.smoke,'run',side_effect=self.fake_run(self.config,calls,info)):
                with self.assertRaises(RuntimeError):self.smoke.cleanup()
            self.assertNotIn(('volume','rm',self.smoke.volume),calls)


if __name__=='__main__':
    unittest.main()
