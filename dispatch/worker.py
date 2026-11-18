def run_sequential(queue, sessions, results):
    processed = 0
    while True:
        task = queue.claim()
        if task is None:
            return processed
        try:
            payload = sessions.request(task['tenant'], task['asset'])
            results.accept(task, payload)
            queue.finish(task['id'])
            processed += 1
        except Exception as error:
            queue.fail(task['id'], str(error))
