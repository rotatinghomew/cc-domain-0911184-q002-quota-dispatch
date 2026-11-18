import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from dispatch.platform import serve
from dispatch.queue import Queue
from dispatch.results import ResultBook
from dispatch.session import SessionPool
from dispatch.worker import run_sequential


class DispatchTests(unittest.TestCase):
    def test_sequential_pipeline_persists(self):
        with tempfile.TemporaryDirectory() as directory, serve() as (url, platform):
            queue = Queue(Path(directory) / 'queue.db')
            results = ResultBook(Path(directory) / 'results.db')
            queue.add('a', 'alpha', 'cover')
            queue.add('b', 'beta', 'subtitle')
            self.assertEqual(run_sequential(queue, SessionPool(url, platform.tokens), results), 2)
            self.assertEqual([row['state'] for row in queue.rows()], ['done', 'done'])
            self.assertEqual(len(results.all()), 2)
            self.assertEqual(run_sequential(queue, SessionPool(url, platform.tokens), results), 0)

    def test_ownership_and_idempotent_acceptance(self):
        results = ResultBook(':memory:')
        task = {'id': 'a', 'tenant': 'alpha', 'asset': 'cover'}
        payload = {'tenant': 'alpha', 'asset': 'cover', 'content': 'a'}
        results.accept(task, payload)
        results.accept(task, payload)
        self.assertEqual(len(results.all()), 1)
        with self.assertRaises(ValueError):
            results.accept(task, {**payload, 'tenant': 'beta'})
        with self.assertRaises(ValueError):
            results.accept(task, {**payload, 'content': 'changed'})

    def test_shared_quota_protocol(self):
        with serve() as (url, platform):
            platform.remaining = 1
            pool = SessionPool(url, platform.tokens)
            pool.request('alpha', 'one')
            with self.assertRaises(HTTPError) as error:
                pool.request('beta', 'two')
            self.assertEqual(error.exception.code, 429)
            self.assertEqual(error.exception.headers['Retry-After'], '60')
            platform.now = 60
            self.assertEqual(pool.request('beta', 'two')['tenant'], 'beta')

    def test_session_refresh_is_tenant_scoped(self):
        with serve() as (url, platform):
            pool = SessionPool(url, platform.tokens)
            request = Request(url + '/session', data=json.dumps({'tenant': 'alpha'}).encode(), method='POST')
            with urlopen(request) as response:
                refreshed = json.load(response)
            self.assertEqual(refreshed['generation'], 2)
            with self.assertRaises(HTTPError) as error:
                pool.request('alpha', 'one')
            self.assertEqual(error.exception.code, 401)
            self.assertEqual(pool.request('beta', 'two')['tenant'], 'beta')

    def test_failure_is_visible(self):
        with serve() as (url, platform):
            queue = Queue(':memory:')
            queue.add('a', 'alpha', 'one')
            platform.remaining = 0
            run_sequential(queue, SessionPool(url, platform.tokens), ResultBook(':memory:'))
            self.assertEqual(queue.rows()[0]['state'], 'failed')
            self.assertIn('429', queue.rows()[0]['reason'])
