import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from gateway_smoke import GatewaySmoke, check, physical_ipv4_addresses, main
from test_compose_isolation import CONFLICTS


class GatewayIsolationTests(unittest.TestCase):
    def test_explicit_ci_context_is_forwarded_and_remote_context_is_rejected(self):
        with patch('sys.argv', ['gateway_smoke.py', '--context', 'default', '--config-only']), \
                patch('gateway_smoke.GatewaySmoke') as factory, patch('gateway_smoke.check') as run:
            main()
        self.assertEqual(factory.call_args.args[1], 'default')
        run.assert_called_once_with(factory.return_value, True)
        with patch('sys.argv', ['gateway_smoke.py', '--context', 'production-remote']), \
                patch('gateway_smoke.GatewaySmoke') as factory:
            with self.assertRaises(SystemExit):
                main()
        factory.assert_not_called()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='afisha-pr12-unit-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.smoke = GatewaySmoke(self.temp.name)
        self.config = json.loads(self.smoke.compose('config', '--format', 'json'))

    def test_real_gateway_config_only_ignores_conflicting_environment(self):
        with patch.dict(os.environ, {**CONFLICTS, 'NGINX_PROXY_IP':'*', 'GATEWAY_SUBNET':'0.0.0.0/0'}):
            result = subprocess.run(['bash', str(Path(__file__).with_name('gateway-smoke.sh')), '--config-only'],
                                    text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS isolated config:', result.stdout)
        self.assertNotIn('Checking gateway build', result.stdout)

    def test_unsafe_gateway_values_fail_before_any_mutation(self):
        mutations = [
            lambda c:c['services']['nginx']['networks']['gateway'].update(ipv4_address='172.30.123.5'),
            lambda c:c['services']['nginx']['volumes'][0].update(read_only=False),
            lambda c:c['services']['nginx']['volumes'][0].update(source=str(Path.home())),
            lambda c:c['services']['nginx']['ports'][0].update(host_ip='0.0.0.0'),
            lambda c:c['services']['backend']['environment'].update(TRUSTED_NGINX_IP='*'),
            lambda c:c['services']['backend']['environment'].update(DATABASE_URL=CONFLICTS['DATABASE_URL']),
            lambda c:c['volumes']['afisha_db_data'].update(name='afisha_db_data'),
            lambda c:c['networks']['gateway'].update(external=True),
            lambda c:c['services'].update(foreign={}),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                config=copy.deepcopy(self.config)
                mutate(config)
                with patch.object(self.smoke,'local_daemon'), patch.object(self.smoke,'run',return_value=json.dumps(config)) as run:
                    with self.assertRaises((RuntimeError, KeyError)):check(self.smoke)
                    self.assertEqual(run.call_count,1)
                    self.assertIn('config',run.call_args.args)

    def test_gateway_collision_is_read_only(self):
        with patch.object(self.smoke,'run',return_value=self.smoke.gateway) as run:
            with self.assertRaises(RuntimeError):self.smoke.validate(self.config)
        self.assertEqual(run.call_args.args[:2],('network','ls'))

    def test_client_refuses_unvalidated_execution(self):
        with patch.object(self.smoke,'run') as run:
            with self.assertRaises(RuntimeError):self.smoke.client('a','172.30.123.5','')
        run.assert_not_called()

    def test_physical_interface_selection_excludes_vpn_and_loopback(self):
        interfaces = 'lo0: flags=0\n\tinet 127.0.0.1 netmask 0xff000000\nutun0: flags=0\n\tinet 198.18.0.1 netmask 0xffff0000\nen0: flags=0\n\tinet 192.168.0.12 netmask 0xffffff00\nen1: flags=0\n\tinet 169.254.1.2 netmask 0xffff0000\n'
        self.assertEqual(physical_ipv4_addresses(interfaces), ['192.168.0.12'])


if __name__ == '__main__':
    unittest.main()
