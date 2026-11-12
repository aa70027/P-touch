import contextlib
import hashlib
import json
import logging
import logging.handlers
import os
from pathlib import Path
import secrets
import sqlite3
import time
import uuid
from argon2 import PasswordHasher
from .models import Settings

PASSWORDS = PasswordHasher()


class Store:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ('assets', 'logs', 'jobs', 'backups'):
            (self.root / name).mkdir(exist_ok=True)
        self.db = self.root / 'studio.sqlite3'
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT,
                  role TEXT NOT NULL, share TEXT NOT NULL, disabled INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL, csrf TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS resources(id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
                  owner TEXT NOT NULL, scope TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, state TEXT NOT NULL,
                  total INTEGER NOT NULL, sent INTEGER NOT NULL DEFAULT 0, confirmed INTEGER NOT NULL DEFAULT 0,
                  simulated INTEGER NOT NULL DEFAULT 0, error TEXT, created REAL NOT NULL, updated REAL NOT NULL,
                  payload TEXT NOT NULL, cancel INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, time REAL NOT NULL, user_id TEXT,
                  action TEXT NOT NULL, detail TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS ix_resources_kind ON resources(kind);
                CREATE INDEX IF NOT EXISTS ix_audit_time ON audit(time);
            ''')
            db.execute('INSERT OR IGNORE INTO settings VALUES(1,?)', (Settings().model_dump_json(),))
            db.execute('INSERT OR IGNORE INTO users VALUES(?,?,?,?,?,?,?)',
                       ('local', 'local', None, 'admin', '{}', 0, time.time()))
            # A crash must never silently resend a potentially printed label.
            db.execute("UPDATE jobs SET state='interrupted',error='RESTART_REQUIRES_REVIEW' WHERE state IN ('queued','running','waiting')")
        self.logger = logging.getLogger('labelstudio.' + str(self.root))
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.handlers.RotatingFileHandler(self.root/'logs'/'application.log', maxBytes=5_000_000, backupCount=5, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            self.logger.addHandler(handler)

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def settings(self):
        with self.connect() as db:
            return Settings.model_validate_json(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])

    def save_settings(self, value):
        with self.connect() as db:
            db.execute('UPDATE settings SET data=? WHERE id=1', (value.model_dump_json(),))

    def audit(self, user, action, detail=''):
        with self.connect() as db:
            db.execute('INSERT INTO audit(time,user_id,action,detail) VALUES(?,?,?,?)', (time.time(), user, action, str(detail)[:2000]))
        self.logger.info('%s %s %s', user, action, detail)

    def user(self, ident):
        with self.connect() as db:
            row = db.execute('SELECT * FROM users WHERE id=?', (ident,)).fetchone()
            return dict(row) if row else None

    def public_user(self, value):
        return {k: (json.loads(v) if k == 'share' else v) for k, v in value.items() if k != 'password'}

    def visible(self, resource, user):
        if resource['owner'] == user['id'] or resource['scope'] == 'shared':
            return True
        if resource['scope'] == 'private':
            return False
        owner = self.user(resource['owner'])
        return bool(owner and json.loads(owner['share']).get(resource['kind'], False))

    def resources(self, user, kind=None):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM resources' + (' WHERE kind=?' if kind else '') + ' ORDER BY updated DESC', (kind,) if kind else ()).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            if self.visible(item, user):
                item['payload'] = json.loads(item['payload'])
                result.append(item)
        return result

    def resource(self, ident, user):
        with self.connect() as db:
            row = db.execute('SELECT * FROM resources WHERE id=?', (ident,)).fetchone()
        if not row or not self.visible(row, user):
            raise KeyError('RESOURCE_NOT_FOUND')
        item = dict(row)
        item['payload'] = json.loads(item['payload'])
        return item

    def save_resource(self, user, kind, name, payload, scope='inherit', ident=None):
        now = time.time()
        if ident:
            old = self.resource(ident, user)
            if old['owner'] != user['id']:
                raise PermissionError('OWNER_ONLY')
        ident = ident or uuid.uuid4().hex
        with self.connect() as db:
            db.execute('''INSERT INTO resources VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                       name=excluded.name,scope=excluded.scope,payload=excluded.payload,updated=excluded.updated''',
                       (ident, kind, name, user['id'], scope, json.dumps(payload, ensure_ascii=False), now, now))
        self.audit(user['id'], 'resource.save', f'{kind}:{ident}')
        return self.resource(ident, user)

    def login(self, username, password):
        with self.connect() as db:
            row = db.execute('SELECT * FROM users WHERE username=? AND disabled=0', (username,)).fetchone()
            try:
                if not row or not row['password'] or not PASSWORDS.verify(row['password'], password):
                    return None
            except Exception:
                return None
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), row['id'], time.time()+43200, csrf))
            return token, csrf, self.public_user(dict(row))

    def session(self, token):
        with self.connect() as db:
            row = db.execute('SELECT * FROM sessions WHERE token=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not row:
            return None
        user = self.user(row['user_id'])
        return (user, row['csrf']) if user and not user['disabled'] else None

    def backup(self):
        name = f'backup-{time.strftime("%Y%m%d-%H%M%S")}-{secrets.token_hex(3)}.sqlite3'
        with self.connect() as source:
            target = sqlite3.connect(self.root/'backups'/name)
            try:
                source.backup(target)
            finally:
                target.close()
        return name


def default_data_dir():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CableLabelStudio'
