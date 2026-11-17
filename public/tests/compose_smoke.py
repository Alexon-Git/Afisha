"""Fail-closed local Compose smoke. No third-party Python dependencies."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class Smoke:
    def __init__(self, directory, context="desktop-linux"):
        self.directory = Path(directory).resolve()
        self.uploads = self.directory / "uploads"
        self.uploads.mkdir()
        self.uploads.chmod(0o777)  # Disposable mount only.
        self.project = "afisha_pr10_" + secrets.token_hex(12)
        self.volume = self.project + "_data"
        self.network = self.project + "_afisha"
        self.started = self.validated = self.fresh = False
        self.frozen = None
        # Equivalent to env -i: no inherited COMPOSE_*, DOCKER_*, DB or secrets.
        self.environment = {"PATH": '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin', "HOME": str(Path.home())}
        docker = next((p for p in (Path('/usr/local/bin/docker'), Path('/usr/bin/docker')) if p.is_file()), None)
        require(docker is not None, "Docker CLI not found in approved system paths")
        require(context in {"desktop-linux", "default"}, "Unapproved Docker context")
        self.context = context
        self.docker = [str(docker), "--config", str(Path.home() / '.docker'), "--context", context]
        password = 'pr10-test-' + secrets.token_hex(24)
        self.values = {
            'POSTGRES_PASSWORD': password,
            'DATABASE_URL': f'postgresql://afisha:{password}@db:5432/afisha_db',
            'SECRET_KEY': 'pr10-test-' + secrets.token_hex(32),
            'ADMIN_PASSWORD': 'pr10-test-' + secrets.token_hex(24),
            'ADMIN_USERNAME': 'pr10_test_admin', 'ADMIN_EMAIL': 'pr10@example.invalid',
            'ALGORITHM': 'HS256', 'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'LOGIN_ACCOUNT_LIMIT': '5', 'LOGIN_SOURCE_LIMIT': '30', 'LOGIN_WINDOW_SECONDS': '900',
            'POSTGRES_VOLUME_NAME': self.volume, 'UPLOADS_PATH': str(self.uploads),
            'BACKEND_UID': '1000', 'BACKEND_GID': '1000',
            'POSTGRES_PORT': '58039', 'BACKEND_PORT': '58040', 'PUBLIC_PORT': '53010',
        }
        self.env_file = self.directory / 'test.env'
        self.env_file.touch(mode=0o600)
        self.env_file.write_text(''.join(f'{k}={v}\n' for k, v in self.values.items()))

    def run(self, *args, input=None):
        result = subprocess.run(self.docker + list(args), env=self.environment,
                                input=input, text=True, capture_output=True)
        # Never print argv/stderr/config: they can contain credentials.
        require(result.returncode == 0, 'Docker command failed (diagnostics withheld)')
        return result.stdout

    def compose(self, *args, input=None):
        files = [self.frozen] if self.frozen else [ROOT/'backend/docker-compose.yml', ROOT/'backend/docker-compose.public.yml']
        command = ['compose', '--project-name', self.project, '--env-file', str(self.env_file)]
        for file in files:
            command += ['-f', str(file)]
        return self.run(*command, *args, input=input)

    def local_daemon(self):
        info = json.loads(self.run('context', 'inspect', self.context))
        expected = ('unix://' + str(Path.home()/'.docker/run/docker.sock')
                    if self.context == 'desktop-linux' else 'unix:///var/run/docker.sock')
        require(len(info) == 1 and info[0]['Name'] == self.context and
                info[0]['Endpoints']['docker']['Host'] == expected,
                'Docker context is not an approved local Unix socket')
        require(Path(expected.removeprefix('unix://')).is_socket(), 'Local Docker socket unavailable')
        # Pin the verified socket, not mutable context metadata/current context.
        self.docker = self.docker[:3] + ['--host',expected]
        info = json.loads(self.run('info', '--format', '{{json .}}'))
        require(info.get('OSType') == 'linux', 'Expected a local Linux Docker daemon')

    def validate(self, config):
        require(config.get('name') == self.project, 'Unexpected project')
        require(set(config.get('services', {})) == {'db', 'backend', 'public'}, 'Unexpected services')
        require(set(config.get('volumes', {})) == {'afisha_db_data'}, 'Unexpected volumes')
        volume = config['volumes']['afisha_db_data']
        require(volume == {'name':self.volume}, 'Unsafe DB volume/options')
        require(set(config.get('networks', {})) == {'afisha'}, 'Unexpected networks')
        network = config['networks']['afisha']
        require(network in ({'name':self.network},{'name':self.network,'ipam':{}}), 'Unsafe network/options')
        require(not config.get('secrets') and not config.get('configs'), 'Unexpected secret inputs')
        services = config['services']
        keys = {'DATABASE_URL','SECRET_KEY','ALGORITHM','ACCESS_TOKEN_EXPIRE_MINUTES','LOGIN_ACCOUNT_LIMIT',
                'LOGIN_SOURCE_LIMIT','LOGIN_WINDOW_SECONDS','ADMIN_USERNAME','ADMIN_PASSWORD','ADMIN_EMAIL'}
        environments = {
            'db': {'POSTGRES_USER':'afisha','POSTGRES_DB':'afisha_db','POSTGRES_PASSWORD':self.values['POSTGRES_PASSWORD']},
            'backend': {key:self.values[key] for key in keys},
            'public': {'INTERNAL_API_URL':'http://backend:8039'},
        }
        ports = {'db':(5432,'58039'), 'backend':(8039,'58040'), 'public':(3000,'53010')}
        forbidden = {'command','entrypoint','env_file','secrets','configs','container_name','network_mode',
                     'extra_hosts','volumes_from','devices','privileged','profiles'}
        allowed = {'build','cap_drop','command','depends_on','entrypoint','environment','healthcheck',
                   'image','init','networks','pids_limit','ports','read_only','security_opt',
                   'stop_grace_period','tmpfs','user','volumes'}
        for name, service in services.items():
            require(set(service) <= allowed, 'Unexpected service setting')
            require(service.get('environment') == environments[name], 'Unexpected environment')
            require(set(service.get('networks', {})) == {'afisha'}, 'Unexpected service network')
            # Compose materializes command/entrypoint as null by default.
            # Empty lists/strings still override image defaults and are rejected.
            require(all(service.get(key) is None for key in forbidden), 'Unexpected service override')
            require(len(service.get('ports', [])) == 1, 'Unexpected ports')
            port = service['ports'][0]
            require(port.get('host_ip') == '127.0.0.1' and port.get('target') == ports[name][0]
                    and str(port.get('published')) == ports[name][1], 'Unsafe port mapping')
        require(services['db'].get('image') == 'postgres:17', 'Unexpected DB image')
        mounts = services['db'].get('volumes', [])
        require(len(mounts) == 1 and mounts[0].get('type') == 'volume' and
                mounts[0].get('source') == 'afisha_db_data' and mounts[0].get('target') == '/var/lib/postgresql/data', 'Unsafe DB mount')
        mounts = services['backend'].get('volumes', [])
        require(len(mounts) == 1 and mounts[0].get('type') == 'bind' and
                mounts[0].get('source') == str(self.uploads) and mounts[0].get('target') == '/app/app/static/uploads', 'Unsafe uploads mount')
        require(not services['public'].get('volumes'), 'Unexpected public mount')
        for name in ('backend', 'public'):
            build = services[name].get('build', {})
            expected = {'context':str(ROOT/name),'dockerfile':'Dockerfile'}
            if name == 'public':
                expected['args'] = {'NEXT_PUBLIC_API_BASE':'/api'}
            require(build == expected and not services[name].get('image'), 'Unexpected build source/options/image')

    def prepare(self):
        self.local_daemon()
        config = json.loads(self.compose('config', '--format', 'json'))
        self.validate(config)
        # Reject all pre-existing resources, even those with matching labels.
        require(self.volume not in self.run('volume','ls','--format','{{.Name}}').splitlines(), 'Test volume already exists')
        require(self.network not in self.run('network','ls','--format','{{.Name}}').splitlines(), 'Test network already exists')
        require(not self.run('ps','-aq','--filter','label=com.docker.compose.project='+self.project).strip(), 'Test project already exists')
        self.fresh = True
        self.frozen = self.directory/'validated.json'
        self.frozen.touch(mode=0o600)
        self.frozen.write_text(json.dumps(config))
        self.validated = True  # All later commands use this frozen config.
        print('PASS isolated config:', self.project, self.volume, flush=True)

    def execute(self):
        require(self.validated and self.fresh, 'Configuration not validated')
        self.compose('build','backend','public')
        self.started = True  # Even a partially failed up needs scoped cleanup.
        self.compose('up','--detach','--wait','--wait-timeout','180')
        self.compose('exec','-T','public','node','-',input="""
const a=require('node:assert/strict');
(async()=>{
a.equal(process.getuid(),1000);
for(const k of ['DATABASE_URL','SECRET_KEY','ADMIN_PASSWORD','POSTGRES_PASSWORD'])a.equal(process.env[k],undefined);
a.equal(process.env.INTERNAL_API_URL,'http://backend:8039');
a.deepEqual(await(await fetch(process.env.INTERNAL_API_URL+'/health')).json(),{status:'healthy'});
a.equal((await(await fetch(process.env.INTERNAL_API_URL+'/events/')).json()).total_items,0);
const r=await fetch('http://127.0.0.1:3000');a.equal(r.status,200);a.match(await r.text(),/Мероприятий пока нет/);
a.equal((await fetch('http://127.0.0.1:3000/health')).status,200);
})().catch(()=>process.exit(1));
""")
        for service in ('db','backend','public'):
            identifier = self.compose('ps','-q',service).strip()
            container = json.loads(self.run('inspect',identifier))[0]
            require(container['State']['Health']['Status'] == 'healthy', 'Unhealthy test container')
            require(service == 'db' or container['HostConfig']['ReadonlyRootfs'], 'Expected read-only rootfs')
            require(container['Config']['Labels']['com.docker.compose.project'] == self.project, 'Unexpected container owner')
            for bindings in container['HostConfig']['PortBindings'].values():
                require(all(b['HostIp'] == '127.0.0.1' for b in bindings or []), 'Unsafe actual port')
        self.compose('stop','backend')
        self.compose('exec','-T','public','node','-',input="""
(async()=>{const a=require('node:assert/strict');const r=await fetch('http://127.0.0.1:3000');a.equal(r.status,200);
const html=await r.text();a.match(html,/Сервис временно недоступен/);a.doesNotMatch(html,/backend:8039|INTERNAL_API_URL|Traceback/);
a.equal((await fetch('http://127.0.0.1:3000/health')).status,200);})().catch(()=>process.exit(1));
""")
        print('PASS Compose: PG17/backend/public health, DNS, non-root, ports, controlled fallback',flush=True)

    def cleanup(self):
        if not (self.started and self.validated and self.fresh):
            return
        self.compose('down')  # No -v or --remove-orphans. Frozen config only.
        if self.volume in self.run('volume','ls','--format','{{.Name}}').splitlines():
            info = json.loads(self.run('volume','inspect',self.volume))[0]
            require(info.get('Name') == self.volume and info.get('Labels',{}).get('com.docker.compose.project') == self.project,
                    'Refusing volume cleanup: unexpected identity')
            self.run('volume','rm',self.volume)
        print('PASS cleanup:',self.project,self.volume,flush=True)


def check(smoke, config_only=False):
    try:
        smoke.prepare()
        if not config_only:
            smoke.execute()
    finally:
        smoke.cleanup()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-only', action='store_true')
    parser.add_argument('--context', choices=('desktop-linux','default'), default='desktop-linux')
    args = parser.parse_args()
    # Ignore inherited TMPDIR; never reuse a user uploads directory.
    with tempfile.TemporaryDirectory(prefix='afisha-pr10-',dir='/tmp') as directory:
        smoke = Smoke(directory,args.context)
        check(smoke,args.config_only)


if __name__ == '__main__':
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    try:
        main()
    except (Exception, KeyboardInterrupt):
        print('BLOCKED: validation/execution failed; sensitive diagnostics withheld',file=sys.stderr)
        sys.exit(1)
