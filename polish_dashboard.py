"""Apply repeatable layout and visible subtitles; no backup file needed."""
import json
from pathlib import Path

path = Path('grafana/dashboard.json')
dashboard = json.loads(path.read_text(encoding='utf-8'))
SUBTITLES = {
    1: 'scrape health', 2: 'system scrape health', 3: 'loaded on CPU',
    4: 'since app start', 5: 'since app start', 6: 'running + queued',
    7: '1-minute rate', 8: 'since app start',
    9: '5-minute estimates', 10: '5-minute mean',
    11: 'VM % vs. bulk jobs', 12: 'VM % vs. bulk jobs',
    13: 'available-space basis', 14: 'RSS vs. weights',
    15: '5-minute estimate', 16: 'since app start',
    17: '1-minute ratio', 18: '5-minute mean',
    19: 'running + queued', 20: '16 shared buckets',
}
for panel in dashboard['panels']:
    number = panel['id']
    title = panel['title'].split(' | ', 1)[0]
    # The suffix is a visible subtitle in the panel header, not an unsupported JSON field.
    panel['title'] = title + ' | ' + SUBTITLES[number]
    if number <= 6:
        index = number - 1
        panel['gridPos'].update(x=(index % 3)*8, y=(index//3)*4, w=8, h=4)
    elif number <= 18:
        index = number - 7
        panel['gridPos'].update(x=(index % 2)*12, y=8+(index//2)*8, w=12, h=8)
    elif number == 19:
        panel['gridPos'].update(x=0, y=56, w=24, h=6)
    else:
        panel['gridPos'].update(x=0, y=62, w=24, h=7)
    if panel['type'] == 'timeseries':
        custom = panel['fieldConfig']['defaults']['custom']
        if not custom['axisLabel'].endswith(' · linear'):
            custom['axisLabel'] += ' · linear'
        if number in (7, 19):
            custom['axisSoftMax'] = 1 if number == 7 else 2
        for override in panel['fieldConfig']['overrides']:
            if override['matcher'] == {'id': 'byName', 'options': 'Active bulk jobs'}:
                properties = override['properties']
                properties[:] = [p for p in properties if p['id'] != 'custom.axisSoftMax']
                properties.append({'id': 'custom.axisSoftMax', 'value': 2})
                for prop in properties:
                    if prop['id'] == 'custom.axisLabel' and not prop['value'].endswith(' · linear'):
                        prop['value'] += ' · linear'
    if number == 20:
        panel['transformations'] = [{
            'id': 'organize',
            'options': {
                'excludeByName': {'Time': True},
                'indexByName': {'client_bucket': 0, 'mode': 1, 'status': 2, 'Value': 3},
                'renameByName': {'client_bucket': 'Client bucket', 'mode': 'Mode',
                                 'status': 'Outcome', 'Value': 'Jobs'},
            },
        }]
dashboard['version'] = 3
path.write_text(json.dumps(dashboard, indent=2) + '\n', encoding='utf-8')
print('Updated:', path)
print('Panels:', len(dashboard['panels']))
print('Refresh:', dashboard['refresh'])
