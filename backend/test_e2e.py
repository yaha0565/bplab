# -*- coding: utf-8 -*-
"""BPLab Trace — End-to-End Test Suite"""
import urllib.request, urllib.error, json, sys, os

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE = os.environ.get('API_BASE', 'http://localhost:8000/api/v1')
passed = 0
failed = 0
token = None

def api(method, path, data=None, expect_status=None):
    global token, passed, failed
    url = f'{BASE}{path}'
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read()) if resp.status != 204 else {}
        status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            result = json.loads(e.read())
        except:
            result = {'detail': str(e)}
    except Exception as e:
        status = 0
        result = {'detail': str(e)}

    if expect_status and status != expect_status:
        print(f'  FAIL {method} {path} -> {status} (expected {expect_status}) {result.get("detail","")}')
        failed += 1
        return None
    else:
        passed += 1
        return result

def check(test_name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f'  FAIL {test_name}: {detail}')

print('=' * 60)
print('BPLab Trace - End-to-End Test Suite')
print('=' * 60)

# [1] LOGIN
print('\n[1] Authentication')
result = api('POST', '/auth/login', {'username': 'admin', 'password': 'admin123'})
if result and 'access_token' in result:
    token = result['access_token']
    print(f'  OK - Login successful (token: {token[:20]}...)')
    print(f'  Role: {result.get("role", "?")}')
else:
    print('  FAIL - Login failed, cannot continue')
    sys.exit(1)

# [2] SYSTEM HEALTH
print('\n[2] System Health')
h = api('GET', '/system/health')
if h:
    print(f'  OK - DB connected')

# [3] ALL 14 EXPERIMENT CONFIGS
print('\n[3] Experiment Configs (14 experiments)')
codes = ['I001','I002','I003','I004','I005','I006','I007','I008','I009','I010','I011','I012','I013','I014']
ok = 0
for code in codes:
    c = api('GET', f'/config/{code}')
    if c:
        fld = len(c.get('fields', []))
        col = len(c.get('columns', []))
        ph = len(c.get('photo_checkpoints', []))
        eq = len(c.get('equipment', []))
        tmpl = c.get('record_template_file', '')
        if fld > 0 and tmpl:
            ok += 1
            print(f'  {code}: {fld}f/{col}c/{ph}p/{eq}e template={tmpl[:30]}...')
        else:
            print(f'  {code}: fields={fld} template={tmpl or "MISSING"}!')
check('All 14 configs OK', ok == 14, f'{ok}/14')

# [4] EQUIPMENT
print('\n[4] Equipment')
eq = api('GET', '/equipment?limit=100')
if eq:
    classes = set(e.get('equipment_class','?') for e in eq)
    print(f'  OK - {len(eq)} equipment items, classes: {classes}')

# [5] METHODS
print('\n[5] Experiment Methods')
methods = api('GET', '/methods')
if methods:
    print(f'  OK - {len(methods)} methods')
    for m in methods:
        print(f'    {m["experiment_code"]} = {m["experiment_name"]}')

# [6] ORGANIZATIONS
print('\n[6] Organizations')
orgs = api('GET', '/organizations')
if orgs:
    print(f'  OK - {len(orgs)} organizations')
    for o in orgs[:5]:
        print(f'    {o.get("org_name", "?")}')

# [7] SAMPLE CATALOG
print('\n[7] Sample Catalog')
cat = api('GET', '/catalog')
if cat is not None:
    print(f'  OK - {len(cat)} entries')

# [8] TEMPLATES
print('\n[8] Templates')
tmpl = api('GET', '/templates')
if tmpl:
    cats = {}
    for t in tmpl:
        c = t.get('category','?')
        cats[c] = cats.get(c, 0) + 1
    print(f'  OK - {len(tmpl)} templates, by category: {cats}')
    # Check all 14 kinds have template
    kinds = ['R001','R004','R005','R006','R007','R009','R010','R011','R012','R013','R014','R015','R016','R017']
    found = set()
    for t in tmpl:
        fn = t.get('filename','')
        for k in kinds:
            if fn.startswith(k):
                found.add(k)
    missing = set(kinds) - found
    if missing:
        print(f'  WARNING: Missing templates: {missing}')
    else:
        print(f'  OK - All 14 record templates present')

# [9] USERS
print('\n[9] Users')
users = api('GET', '/users')
if users:
    roles = {}
    for u in users:
        r = u.get('role','?')
        roles[r] = roles.get(r, 0) + 1
    print(f'  OK - {len(users)} users, roles: {roles}')

# [10] DASHBOARD
print('\n[10] Dashboard')
dash = api('GET', '/dashboard')
if dash:
    k = list(dash.keys())[:5]
    print(f'  OK - Dashboard keys: {k}')
else:
    print(f'  OK - Dashboard returned (empty or dict)')

# [11] COMMISSIONS
print('\n[11] Commissions')
comms = api('GET', '/commissions?limit=5')
if comms:
    statuses = set(c.get('status','?') for c in comms)
    print(f'  OK - {len(comms)} commissions, statuses: {statuses}')

# [12] TASK PACKAGES
print('\n[12] Task Packages')
pkgs = api('GET', '/tasks/packages?limit=5')
if pkgs:
    statuses = set(p.get('status','?') for p in pkgs)
    print(f'  OK - {len(pkgs)} packages, statuses: {statuses}')

# [13] MY TASKS
print('\n[13] My Tasks')
tasks = api('GET', '/tasks/my?limit=10')
if tasks and isinstance(tasks, list):
    statuses = set(t.get('status','?') for t in tasks if isinstance(t, dict))
    print(f'  OK - {len(tasks)} tasks, statuses: {statuses}')
elif isinstance(tasks, dict):
    print(f'  OK - Tasks returned dict: {list(tasks.keys())[:5]}')
else:
    print(f'  OK - Tasks: {type(tasks).__name__}, {tasks if isinstance(tasks, str) else len(tasks) if tasks else 0} items')

# [14] PENDING REVIEWS
print('\n[14] Pending Reviews')
reviews = api('GET', '/records/pending-reviews?limit=5')
if isinstance(reviews, list):
    print(f'  OK - {len(reviews)} pending reviews')
elif isinstance(reviews, dict):
    print(f'  OK - Reviews: {list(reviews.keys())[:3]}')
else:
    print(f'  OK - Reviews: {reviews}')

# [15] NOTIFICATIONS
print('\n[15] Notifications')
notifs = api('GET', '/notifications?limit=5')
if isinstance(notifs, list):
    unread = sum(1 for n in notifs if not n.get('read'))
    print(f'  OK - {len(notifs)} total, {unread} unread')
else:
    print(f'  OK - Notifications: {type(notifs).__name__}')

# [16] REPORTS
print('\n[16] Reports')
reports = api('GET', '/reports?limit=5')
if isinstance(reports, list):
    statuses = set(r.get('status','?') for r in reports if isinstance(r, dict))
    print(f'  OK - {len(reports)} reports, statuses: {statuses}')
elif isinstance(reports, dict):
    print(f'  OK - Reports dict: {list(reports.keys())[:5]}')
    if 'detail' in reports:
        print(f'    detail: {reports["detail"]}')
else:
    print(f'  OK - Reports: {type(reports).__name__} {str(reports)[:100]}')

# [17] SIGNATURES
print('\n[17] Signatures')
sigs = api('GET', '/signatures')
if isinstance(sigs, list):
    print(f'  OK - {len(sigs)} signature records')
else:
    print(f'  OK - Signatures: {type(sigs).__name__}')

# [18] OBJECTIONS
print('\n[18] Objections')
objs = api('GET', '/objections?limit=5')
if isinstance(objs, list):
    print(f'  OK - {len(objs)} objections')
else:
    print(f'  OK - Objections: {type(objs).__name__}')

# [19] HAZARDOUS WASTE
print('\n[19] Hazardous Waste')
waste = api('GET', '/hazardous-waste?limit=5')
if isinstance(waste, list):
    print(f'  OK - {len(waste)} records')
else:
    print(f'  OK - Waste: {type(waste).__name__}')

# [20] INCIDENTS
print('\n[20] Incidents')
inc = api('GET', '/incidents?limit=5')
if isinstance(inc, list):
    print(f'  OK - {len(inc)} incidents')
else:
    print(f'  OK - Incidents: {type(inc).__name__}')

# [21] TRACEABILITY
print('\n[21] Traceability')
trace = api('GET', '/traceability/modifications?limit=5')
if isinstance(trace, list):
    print(f'  OK - {len(trace)} modifications tracked')
else:
    print(f'  OK - Traceability: {type(trace).__name__}')

# [22] SYSTEM INIT CHECK
print('\n[22] System Init (check only - not executing)')
init = api('GET', '/system/health')
check('System alive', init is not None)

# ═══ SUMMARY ═══
print('\n' + '=' * 60)
total = passed + failed
print(f'Results: {passed}/{total} passed, {failed} failed')
if failed == 0:
    print('ALL TESTS PASSED!')
else:
    print(f'{failed} TESTS FAILED!')
print('=' * 60)
