import sqlite3


class Queue:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY, tenant TEXT, asset TEXT, state TEXT, reason TEXT)''')

    def add(self, task_id, tenant, asset):
        with self.db:
            self.db.execute('INSERT INTO tasks VALUES(?,?,?,?,?)',
                            (task_id, tenant, asset, 'pending', ''))

    def claim(self):
        with self.db:
            row = self.db.execute("SELECT * FROM tasks WHERE state='pending' ORDER BY rowid LIMIT 1").fetchone()
            if row:
                self.db.execute("UPDATE tasks SET state='running' WHERE id=?", (row['id'],))
                return dict(row)

    def finish(self, task_id):
        with self.db:
            self.db.execute("UPDATE tasks SET state='done',reason='' WHERE id=?", (task_id,))

    def fail(self, task_id, reason):
        with self.db:
            self.db.execute("UPDATE tasks SET state='failed',reason=? WHERE id=?", (reason, task_id))

    def rows(self):
        return [dict(row) for row in self.db.execute('SELECT * FROM tasks ORDER BY id')]
