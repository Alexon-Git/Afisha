"""Isolated local gateway test. Extends, never relaxes, the PR-10 runner."""
import argparse
import copy
import ipaddress
import json
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'public/tests'))
from compose_smoke import Smoke, require, check

STARTUP = '''python -c 'import ipaddress, os; ipaddress.IPv4Address(os.environ["TRUSTED_NGINX_IP"])' &&
alembic upgrade head && python create_admin.py &&
exec uvicorn app.main:app --host 0.0.0.0 --port 8039
--proxy-headers --forwarded-allow-ips="$TRUSTED_NGINX_IP"'''


def physical_ipv4_addresses(ifconfig):
    addresses = []
    interface = ''
    for line in ifconfig.splitlines():
        if line and not line[0].isspace():
            interface = line.split(':', 1)[0]
        match = re.match(r'\s+inet (\d+\.\d+\.\d+\.\d+)\b', line)
        if re.fullmatch(r'en\d+', interface) and match:
            address = ipaddress.ip_address(match[1])
            if not (address.is_loopback or address.is_link_local or address.is_unspecified):
                addresses.append(str(address))
    return addresses


class GatewaySmoke(Smoke):
    def __init__(self, directory, context='desktop-linux'):
        super().__init__(directory, context)
        self.project = self.project.replace('pr10', 'pr12')
        self.volume = self.project + '_data'
        self.network = self.project + '_afisha'
        self.gateway = self.project + '_gateway'
        self.ingress = self.project + '_ingress'
        self.created_clients = []
        self.values.update(POSTGRES_VOLUME_NAME=self.volume, GATEWAY_PORT='58080',
                           GATEWAY_SUBNET='172.30.123.0/29', NGINX_PROXY_IP='172.30.123.2',
                           BACKEND_GATEWAY_IP='172.30.123.3', PUBLIC_GATEWAY_IP='172.30.123.4',
                           SITE_URL='',
                           LOGIN_SOURCE_LIMIT='3', LOGIN_ACCOUNT_LIMIT='1000')
        self.env_file.write_text(''.join(f'{key}={value}\n' for key, value in self.values.items()))

    def compose(self, *args, input=None):
        if self.frozen:
            return super().compose(*args, input=input)
        command = ['compose', '--project-name', self.project, '--env-file', str(self.env_file)]
        for file in ('docker-compose.yml', 'docker-compose.public.yml', 'docker-compose.gateway.yml', 'docker-compose.trusted-proxy.yml'):
            command += ['-f', str(ROOT / 'backend' / file)]
        return self.run(*command, *args, input=input)

    def validate(self, config):
        require(set(config.get('services', {})) == {'db', 'backend', 'public', 'nginx'}, 'Unexpected gateway services')
        require(set(config.get('networks', {})) == {'afisha', 'gateway', 'ingress'}, 'Unexpected gateway networks')
        require(config['networks']['ingress'] in ({'name': self.ingress}, {'name': self.ingress, 'ipam': {}}), 'Unexpected ingress network')
        gateway = config['networks']['gateway']
        require(gateway == {'name': self.gateway, 'internal': True,
                            'ipam': {'config': [{'subnet': '172.30.123.0/29'}]}}, 'Unexpected gateway network')
        projected = copy.deepcopy(config)
        require(projected['services']['public']['environment'].pop('SITE_URL') == '', 'Unexpected local SITE_URL')
        nginx = projected['services'].pop('nginx')
        require(set(nginx) == {'build', 'ports', 'volumes', 'depends_on', 'networks', 'read_only', 'tmpfs',
                              'cap_drop', 'security_opt', 'pids_limit', 'command', 'entrypoint'}, 'Unexpected Nginx options')
        require(nginx.get('command') is None and nginx.get('entrypoint') is None, 'Unexpected Nginx command')
        require(nginx['build'] == {'context': str(ROOT), 'dockerfile': 'deploy/nginx/Dockerfile'}, 'Unexpected Nginx build')
        require(nginx['networks'] == {'gateway': {'ipv4_address': '172.30.123.2'}, 'ingress': None}, 'Unexpected proxy IP')
        require(nginx['read_only'] and nginx['cap_drop'] == ['ALL'] and nginx['security_opt'] == ['no-new-privileges:true'], 'Unsafe Nginx privileges')
        mounts = nginx['volumes']
        require(len(mounts) == 1 and mounts[0]['type'] == 'bind' and mounts[0]['source'] == str(self.uploads)
                and mounts[0]['target'] == '/srv/uploads' and mounts[0]['read_only'], 'Unsafe Nginx uploads')
        ports = nginx['ports']
        require(len(ports) == 1 and ports[0]['host_ip'] == '127.0.0.1' and str(ports[0]['published']) == '58080'
                and ports[0]['target'] == 8080, 'Unsafe Nginx ports')
        backend = projected['services']['backend']
        command = backend.pop('command')
        require(command[:2] == ['sh', '-ec'] and len(command) == 3 and
                ' '.join(command[2].replace('$$', '$').split()) == ' '.join(STARTUP.split()), 'Unexpected trusted-proxy launcher')
        require(backend['environment'].pop('TRUSTED_NGINX_IP') == '172.30.123.2', 'Unsafe trusted proxy')
        for service, address in (('backend', '172.30.123.3'), ('public', '172.30.123.4')):
            require(projected['services'][service]['networks'].pop('gateway') == {'ipv4_address': address}, 'Unexpected service IP')
        projected['networks'].pop('gateway')
        projected['networks'].pop('ingress')
        super().validate(projected)
        existing = self.run('network', 'ls', '--format', '{{.Name}}').splitlines()
        require(self.gateway not in existing and self.ingress not in existing, 'Gateway network already exists')
        # Docker refuses overlaps too, but detect them before build/up.
        for identifier in self.run('network', 'ls', '-q').splitlines():
            network = json.loads(self.run('network', 'inspect', identifier))[0]
            for subnet in network.get('IPAM', {}).get('Config') or []:
                value = subnet.get('Subnet', '')
                if ':' not in value and value:
                    require(not ipaddress.ip_network('172.30.123.0/29').overlaps(ipaddress.ip_network(value)), 'Gateway subnet already in use')

    def client(self, suffix, address, script):
        require(self.started and self.validated and self.fresh, 'Unvalidated test client')
        require(suffix in {'a', 'b'} and address in {'172.30.123.5', '172.30.123.6'}, 'Unexpected client identity')
        name = self.project + '-client-' + suffix
        require(name not in self.run('ps', '-a', '--format', '{{.Names}}').splitlines(), 'Client already exists')
        self.created_clients.append(name)
        image = self.compose('images', '-q', 'backend').strip()
        wrapped = 'import traceback\ntry:\n    exec(compile(' + repr(script) + ', "<gateway-client>", "exec"))\n    print("GATEWAY_CLIENT_PASS")\nexcept Exception as error:\n    print("GATEWAY_CLIENT_FAILURE", type(error).__name__, traceback.extract_tb(error.__traceback__)[-1].lineno)\n'
        result = self.run('run', '--rm', '-i', '--name', name,
                        '--label', 'com.docker.compose.project=' + self.project,
                        '--network', self.gateway, '--ip', address, '--read-only', '--cap-drop', 'ALL',
                        '--security-opt', 'no-new-privileges:true', image, 'python', '-', input=wrapped)
        # Emit only a synthetic failure location, never response data or secrets.
        if result.strip().startswith('GATEWAY_CLIENT_FAILURE'):
            print(result.strip(), flush=True)
        require(result.strip() == 'GATEWAY_CLIENT_PASS', 'Gateway client regression failed')

    def execute(self):
        require(self.validated and self.fresh, 'Unvalidated gateway')
        print('Checking gateway build', flush=True)
        self.compose('build', 'backend', 'public', 'nginx')
        self.started = True
        self.compose('up', '--detach', '--wait', '--wait-timeout', '240')
        print('Checking nginx -t and routed requests', flush=True)
        self.compose('exec', '-T', 'nginx', 'nginx', '-t')
        # This writes only to the new, validated disposable database.
        self.compose('exec', '-T', 'backend', 'python', '-', input='''
from app.database import SessionLocal
from app.models.organizer import Organizer
with SessionLocal.begin() as db:
    db.add(Organizer(name="Gateway test organizer", public_contact="test-only designated public contact"))
''')
        script = (ROOT / 'deploy/tests/gateway_requests.py').read_text()
        config = {'username': self.values['ADMIN_USERNAME'], 'password': self.values['ADMIN_PASSWORD']}
        # Credentials travel via stdin only. Never argv/env/logs.
        script = 'TEST_LOGIN = ' + repr(config) + '\n' + script
        self.client('a', '172.30.123.5', script)
        self.client('b', '172.30.123.6', '''
from urllib.request import Request, urlopen
from urllib.error import HTTPError
try:
    urlopen(Request("http://nginx:8080/api/auth/login", data=b"username=second-source&password=wrong", method="POST"))
except HTTPError as error:
    assert error.code == 401, "Independent source was rate limited"
else:
    raise AssertionError("Wrong password accepted")
''')
        # Public is an untrusted peer, even on the same gateway network.
        self.compose('exec', '-T', 'public', 'node', '-', input='''
(async()=>{for(let i=0;i<4;i++){
const r=await fetch('http://172.30.123.3:8039/auth/login',{method:'POST',headers:{
'Content-Type':'application/x-www-form-urlencoded','X-Forwarded-For':'198.51.100.'+(20+i),
'Forwarded':'for=203.0.113.'+i,'X-Real-IP':'192.0.2.'+i},body:'username=peer-'+i+'&password=wrong'});
if(r.status!==(i<3?401:429))process.exit(1);
}})().catch(()=>process.exit(1));
''')
        for service in ('db', 'backend', 'public', 'nginx'):
            identifier = self.compose('ps', '-q', service).strip()
            container = json.loads(self.run('inspect', identifier))[0]
            require(container['State']['Health']['Status'] == 'healthy', 'Gateway health failed')
            for bindings in container['HostConfig']['PortBindings'].values():
                require(all(binding['HostIp'] == '127.0.0.1' for binding in bindings or []), 'Unsafe actual binding')
            require(any(container['NetworkSettings']['Ports'].values()), 'Host ports were not actually published')
        from urllib.request import urlopen
        with urlopen('http://127.0.0.1:58080/api/health', timeout=10) as response:
            require(response.status == 200, 'Host gateway unreachable')
        # Do not infer LAN IP from default routes: a VPN/TUN may intercept them.
        if sys.platform == 'darwin':
            interfaces = subprocess.run(['/sbin/ifconfig'], env=self.environment, text=True, capture_output=True, check=True)
            addresses = physical_ipv4_addresses(interfaces.stdout)
        else:
            addresses = [info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                         if not ipaddress.ip_address(info[4][0]).is_loopback]
        require(addresses, 'Non-loopback LAN interface unavailable')
        for local_address in set(addresses):
            for port in (58039, 58040):
                try:
                    connection = socket.create_connection((local_address, port), timeout=2)
                except OSError:
                    continue
                connection.close()
                raise RuntimeError('Backend or PostgreSQL reachable on non-loopback host interface')
        print('PASS non-loopback host interface: backend and PostgreSQL connections refused', flush=True)
        print('PASS gateway: nginx -t, routing, CRA assets, login, CRUD, upload, editorial actions, hidden 404, source isolation and untrusted peer', flush=True)

    def cleanup(self):
        if self.started and self.validated and self.fresh:
            for name in self.created_clients:
                identifiers = self.run('ps', '-aq', '--filter', 'name=^/' + name + '$').splitlines()
                for identifier in identifiers:
                    container = json.loads(self.run('inspect', identifier))[0]
                    require(container['Name'] == '/' + name and
                            container['Config']['Labels'].get('com.docker.compose.project') == self.project,
                            'Refusing cleanup of an unowned client')
                    self.run('rm', '-f', identifier)
        super().cleanup()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-only', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='afisha-pr12-', dir='/tmp') as directory:
        check(GatewaySmoke(directory), args.config_only)


if __name__ == '__main__':
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except (Exception, KeyboardInterrupt):
        print('BLOCKED: gateway check failed; sensitive diagnostics withheld', file=sys.stderr)
        sys.exit(1)
