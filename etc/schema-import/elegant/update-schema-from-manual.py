
from pykern import pkio, pkjson
import glob
import re

# wget --recursive --no-clobber --page-requisites --html-extension --convert-links --domains ops.aps.anl.gov --no-parent https://ops.aps.anl.gov/manuals/elegant_latest/elegant.html

files = {}
models = {}

for html_file in glob.glob('manual/*.html'):
    #print(html_file)
    name = None
    with pkio.open_text(html_file, encoding='cp1252') as f:
        text = f.read()
    state = 'name'
    fields = []
    for line in text.split('\n'):
        if state == 'name':
            m = re.match(r'.*<title>\s*(.*?)(\&.*)?\s*(</title>.*|$)', line)
            if m:
                name = m.group(1)
                if ' ' in name:
                    continue
                if name in ('HKPOLY', 'bunched_beam_moments', 'SCRIPT'):
                    continue
                files[name] = html_file
                assert name not in models, f'duplicate name: {name}'
                models[name] = fields
                state = 'field_start'
            continue
        if state == 'field_start':
            if re.search('^&amp;{}'.format(name), line):
                state = 'fields'
            # class="td11">Parameter Name </td><td  style="white-space:nowrap; text-align:left;" id="TBL-120-1-2"
            elif re.search(r'>Parameter Name\s*<', line):
                state = 'table_fields'
            continue
        if state == 'fields':
            # &#x00A0;<br />&amp;end
            if re.search(r'>&amp;end$', line):
                state = 'done'
            else:
                # &#x00A0;<br />&#x00A0;&#x00A0;&#x00A0;&#x00A0;STRING&#x00A0;bunch&#x00A0;=&#x00A0;NULL;
                line = re.sub(r'&#x00A0;', ' ', line)
                line = re.sub(r'.*?<br />', '', line)
                line = re.sub(r'^\s+', '', line)
                f = line.split(' ')[1]
                assert f, f'line split failed: {line}'
                if f in ('balance_terms', 'output_monitors_only') and f in fields:
                    continue
                assert f not in fields, f'duplicate field: {name} {f}'
                f = re.sub(r'\[.*', '', f)
                f = re.sub(r';', '', f)
                if f == 'removed_pegged':
                    f = 'remove_pegged'
                fields.append(f)
            continue
        if state == 'table_fields':
            if re.search(r'class="td11">\s+</td></tr></table></div>', line):
                state = 'field_start'
            else:
                m = re.match('^class="td11">([a-zA-Z]\S*?)\s*</td>.*?style="white-space:nowrap; text-align:left;".*$', line)
                if m:
                    f = m.group(1)
                    if f == 'STRING':
                        continue
                    if f.upper() == f:
                        assert f, f'line split failed: {line}'
                        assert f not in fields, f'duplicate field: {name} {f}: {line}'
                        fields.append(f.lower())
    assert name
    if name in models and not models[name]:
        del models[name]

schema = pkjson.load_any(pkio.read_text(
    '~/src/radiasoft/sirepo/sirepo/package_data/static/json/elegant-schema.json'))

for name in sorted(models):
    m = None
    if name.upper() == name:
        m = name
    else:
        m = f'command_{name}'
    if m in schema.model:
        print_header = False
        for f in models[name]:
            if f == 'printout_format':
                continue
            if m == 'command_link_elements' and f == 'minimium':
                continue
            if m == 'command_load_parameters' and f == 'filename_list':
                continue
            if m == 'command_optimization_setup' and re.search('interrupt_file', f):
                continue
            if m == 'command_run_setup' and f in ('rootname', 'semaphore_file', 'search_path'):
                continue
            if m == 'command_sdds_beam' and f == 'input_list':
                continue
            if m == 'command_track' and f == 'interrupt_file':
                continue
            if f not in schema.model[m]:
                if m == 'BRAT' and f == 'method':
                    continue
                if m == 'command_global_settings' and re.search(r'mpi', f):
                    continue
                if not print_header:
                    print_header = True
                    print('{} {}'.format(m, files.get(name, 'none')))
                print(f' + {f}')
        for f in schema.model[m]:
            if m == 'command_link_elements' and f == 'minimum':
                continue
            if m == 'command_track' and f in ('use_linear_chromatic_matrix', 'longitudinal_ring_only'):
                continue
            if m == 'command_tune_shift_with_amplitude' and f == 'sparse_grid':
                continue
            if f == 'name':
                continue
            if f not in models[name]:
                if re.search(r'[a-z](X|Y)$', f):
                    continue
                if not print_header:
                    print_header = True
                    print('{} {}'.format(m, files.get(name, 'none')))
                print(f' - {f}')
    else:
        if m in ('command_semaphores', 'command_subprocess'):
            continue
        print('{} {}'.format(m, files.get(name, 'none')))
        print(f'+ {m} {files[name]}')
        for f in models[name]:
            print(f' {f}')

for view in schema.view:
    if view.upper() == view or re.search(r'^command_', view):
        for f in schema.view[view].advanced:
            assert f in schema.model[view], f'missing {view} {f}'

for m in schema.model:
    if m.upper() == m or re.search(r'^command_', m):
        for f in schema.model[m]:
            if re.search(r'(X|Y)$', f):
                continue
            assert f in schema.view[m].advanced, f'missing view field {m} {f}'


types = {}
for m in schema.model:
    if m.upper() == m or re.search(r'^command_', m):
        for f in schema.model[m]:
            row = schema.model[m][f]
            if f != 'name' and not re.search(r'(X|Y)$', f):
                assert len(row) >= 4, f'missing tooltip: {m} {f}'
            t = row[1]
            assert not re.search(r'^\d', str(t)), f'invalid type: {m} {f} {t}'
            types[t] = True

print('types:\n {}'.format('\n '.join(sorted(types.keys()))))
