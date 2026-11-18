import json
import tempfile
from pathlib import Path
from dispatch.platform import serve
from dispatch.queue import Queue
from dispatch.results import ResultBook
from dispatch.session import SessionPool
from dispatch.worker import run_sequential


def main():
    with tempfile.TemporaryDirectory() as directory, serve() as (url, platform):
        queue = Queue(Path(directory) / 'tasks.sqlite3')
        results = ResultBook(Path(directory) / 'results.sqlite3')
        queue.add('task-a', 'alpha', 'cover-a')
        queue.add('task-b', 'beta', 'subtitle-b')
        count = run_sequential(queue, SessionPool(url, platform.tokens), results)
        print(json.dumps({'processed': count, 'tasks': queue.rows(), 'results': results.all()}))


if __name__ == '__main__':
    main()
