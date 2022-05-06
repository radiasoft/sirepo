file_names = [
    'server.py',
    'auth/__init__.py',
    'auth/bluesky.py',
    'auth/email.py',
    'auth/github.py',
    'auth/guest.py',
    'comsol_register.py',
    'job_api.py',
    'sim_api/jupyterhublogin.py',
    'srtime.py',
    'status.py',
]

for file_name in file_names:
    lines = ['import sirepo.api\n']
    with open(file_name, 'r') as file:
        for line in file:
            lines.append(line)

    for i, line in enumerate(lines):
        if line.startswith('@api_perm'):
            lines.insert(i, 'class _API(sirepo.api.APIBase):\n')
            j = i + 1
            while lines[j].startswith('@api_perm') or lines[j].startswith('def api') or lines[j].startswith('    ') or lines[j].startswith('#') or lines[j] == '\n':
                if lines[j].startswith('def api'):
                    l = lines[j].split('(')
                    assert len(l) == 2
                    if l[1].startswith(')'):
                        add_self = '(self'
                    else:
                        add_self = '(self, '
                    lines[j] = l[0] + add_self + l[1]
                lines[j] = '    ' + lines[j]
                j += 1
            lines[j - 1] = lines[j - 1][4:]
            lines[j - 2] = lines[j - 2][4:]
            break

    with open(file_name, 'w') as file:
        file.writelines(lines)
