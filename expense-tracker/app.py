"""Pocket Ledger: local Python + SQLite expense tracker. No packages required."""
import csv
import io
import secrets
import sqlite3
import webbrowser
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlencode

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'expenses.db'
TOKEN = secrets.token_urlsafe(32)
CATEGORIES = ['Food', 'Transport', 'Shopping', 'Bills', 'Education', 'Health', 'Entertainment', 'Salary', 'Other']

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def initialize():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>0), category TEXT NOT NULL, description TEXT NOT NULL, day TEXT NOT NULL)')

def validate(data):
    if data.get('kind') not in ('income', 'expense') or data.get('category') not in CATEGORIES:
        raise ValueError('Choose a valid type and category.')
    try:
        amount = Decimal(data.get('amount', ''))
        if not amount.is_finite() or not 0 < amount <= 1000000000 or amount.as_tuple().exponent < -2:
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise ValueError('Enter a positive amount with at most two decimal places.')
    day = date.fromisoformat(data.get('day', '')).isoformat()
    description = data.get('description', '').strip()
    if not 1 <= len(description) <= 120:
        raise ValueError('Description must contain 1 to 120 characters.')
    return data['kind'], int(amount * 100), data['category'], description, day

def money(paise):
    return f'₹{paise / 100:,.2f}'

def hidden(name, value):
    return f'<input type="hidden" name="{name}" value="{escape(str(value), quote=True)}">'

def page(rows, month, edit=None, message=''):
    selected = dict(edit) if edit else dict(kind='expense', amount='', category='Food', description='', day=date.today().isoformat(), id='')
    def options(values, current):
        return ''.join(f'<option value="{v}" {"selected" if v == current else ""}>{v.title()}</option>' for v in values)
    income = sum(r['amount'] for r in rows if r['kind'] == 'income')
    expense = sum(r['amount'] for r in rows if r['kind'] == 'expense')
    cards = ''.join(f'<article><span>{label}</span><strong>{money(value)}</strong></article>' for label, value in [('Net balance', income-expense), ('Income', income), ('Expenses', expense)])
    table = ''
    totals = {}
    for r in rows:
        if r['kind'] == 'expense':
            totals[r['category']] = totals.get(r['category'], 0) + r['amount']
        table += f'''<tr><td>{r['day']}</td><td>{escape(r['description'])}</td><td>{r['category']}</td><td class="{r['kind']}">{'+' if r['kind']=='income' else '−'}{money(r['amount'])}</td><td><div class="actions"><a href="/?{urlencode(dict(month=month, edit=r['id']))}">Edit</a><form method="post" action="/delete" onsubmit="return confirm('Delete this transaction?')">{hidden('token', TOKEN)}{hidden('id',r['id'])}{hidden('month',month)}<button class="delete">Delete</button></form></div></td></tr>'''
    chart = ''.join(f'<div class="category"><div>{c} <b>{money(a)}</b></div><progress max="{expense}" value="{a}"></progress></div>' for c,a in sorted(totals.items(), key=lambda x:-x[1])) or '<p>No spending in this period.</p>'
    amount = f"{selected['amount']/100:.2f}" if edit else ''
    body = f'''<header><b>◈ Pocket Ledger</b><span>Personal finance, made clear.</span></header><p class="eyebrow">YOUR MONEY AT A GLANCE</p><h1>Small habits. Better balance.</h1><p>Track what comes in. Understand what goes out.</p><div class="toolbar"><form method="get"><label for="month">Reporting month</label><input id="month" type="month" name="month" value="{escape(month)}"><button>Apply</button><a href="/?month=">All time</a></form><a class="button" href="/export?{urlencode(dict(month=month))}" download="transactions.csv">Export CSV ↓</a></div><div class="cards">{cards}</div><div class="layout"><section><h2>{'Edit transaction' if edit else 'Add a transaction'}</h2><p role="status">{escape(message)}</p><form method="post" action="/save">{hidden('token',TOKEN)}{hidden('id',selected['id'])}{hidden('month',month)}<label for="kind">Type</label><select id="kind" name="kind">{options(['expense','income'],selected['kind'])}</select><label for="amount">Amount (₹)</label><input id="amount" name="amount" type="number" min="0.01" max="1000000000" step="0.01" value="{amount}" required><label for="description">Description</label><input id="description" name="description" maxlength="120" value="{escape(selected['description'],quote=True)}" placeholder="e.g. Lunch at college" required><label for="category">Category</label><select id="category" name="category">{options(CATEGORIES,selected['category'])}</select><label for="day">Date</label><input id="day" name="day" type="date" value="{selected['day']}" required><button class="save">Save transaction</button></form><p><a href="/?{urlencode(dict(month=month))}">Clear / cancel editing</a></p></section><section><div class="heading"><h2>Transactions</h2><span>{len(rows)} records</span></div><div class="scroll"><table><thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Amount</th><th>Actions</th></tr></thead><tbody>{table}</tbody></table></div>{'' if rows else '<p class="empty">Your story starts here. Add your first transaction.</p>'}<h2 class="chart-title">Spending by category</h2>{chart}</section></div><footer>Local SQLite storage · Indian rupees · Totals reflect the selected period</footer>'''
    css = (ROOT/'style.css').read_text(encoding='utf-8')
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pocket Ledger</title><style>{css}</style></head><body><main>{body}</main></body></html>'

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, kind='text/html; charset=utf-8'):
        body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path not in ('/', '/export'):
            return self.reply(404,'Not found')
        params = parse_qs(parsed.query,keep_blank_values=True)
        month = params.get('month',[date.today().isoformat()[:7]])[0]
        try:
            if month: date.fromisoformat(month+'-01')
            with connect() as db:
                rows = db.execute("SELECT * FROM transactions WHERE (?='' OR substr(day,1,7)=?) ORDER BY day DESC,id DESC",(month,month)).fetchall()
                edit = db.execute('SELECT * FROM transactions WHERE id=?',(int(params['edit'][0]),)).fetchone() if 'edit' in params else None
            if parsed.path == '/export':
                output = io.StringIO(newline='')
                writer = csv.writer(output)
                writer.writerow(['Date','Type','Category','Description','Amount (INR)'])
                for r in rows:
                    description = r['description']
                    if description.startswith(('=','+','-','@','\t','\r','\n')): description = "'"+description
                    writer.writerow([r['day'],r['kind'],r['category'],description,f"{r['amount']/100:.2f}"])
                return self.reply(200,'\ufeff'+output.getvalue(),'text/csv; charset=utf-8')
            self.reply(200,page(rows,month,edit,params.get('message',[''])[0]))
        except ValueError:
            self.reply(400,'Invalid month or transaction ID. <a href="/">Go back</a>')
    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length',0))
            if not 0 < size <= 8192: raise ValueError('Invalid request size.')
            data = {k:v[0] for k,v in parse_qs(self.rfile.read(size).decode(),keep_blank_values=True).items()}
            if not secrets.compare_digest(data.get('token',''),TOKEN):
                return self.reply(403,'Refresh the page before trying again.')
            with connect() as db:
                if self.path == '/save':
                    values = validate(data)
                    if data.get('id'):
                        cursor = db.execute('UPDATE transactions SET kind=?,amount=?,category=?,description=?,day=? WHERE id=?',values+(int(data['id']),))
                    else:
                        cursor = db.execute('INSERT INTO transactions(kind,amount,category,description,day) VALUES(?,?,?,?,?)',values)
                elif self.path == '/delete':
                    cursor = db.execute('DELETE FROM transactions WHERE id=?',(int(data['id']),))
                else: return self.reply(404,'Not found')
                if cursor.rowcount == 0: raise ValueError('Transaction no longer exists.')
            self.send_response(303)
            self.send_header('Location','/?'+urlencode(dict(month=data.get('month',''),message='Transaction saved.' if self.path=='/save' else 'Transaction deleted.')))
            self.end_headers()
        except (ValueError,KeyError,UnicodeError) as error:
            self.reply(400,escape(str(error))+' <a href="/">Go back</a>')

if __name__ == '__main__':
    initialize()
    server = HTTPServer(('127.0.0.1',8000),Handler)
    print('Open http://127.0.0.1:8000 — press Ctrl+C to stop.')
    webbrowser.open('http://127.0.0.1:8000')
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
