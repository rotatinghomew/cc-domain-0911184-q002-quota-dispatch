import json
import sqlite3


class ResultBook:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS results(task TEXT PRIMARY KEY, tenant TEXT, payload TEXT)')

    def accept(self, task, payload):
        if task['tenant'] != payload['tenant'] or task['asset'] != payload['asset']:
            raise ValueError('task and payload disagree')
        value = json.dumps(payload, sort_keys=True)
        with self.db:
            existing = self.db.execute('SELECT tenant,payload FROM results WHERE task=?', (task['id'],)).fetchone()
            if existing and existing != (task['tenant'], value):
                raise ValueError('task already accepted different content')
            self.db.execute('INSERT OR IGNORE INTO results VALUES(?,?,?)',
                            (task['id'], task['tenant'], value))

    def all(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM results ORDER BY task')]
