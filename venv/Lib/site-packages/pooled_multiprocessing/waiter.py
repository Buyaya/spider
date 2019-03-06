from threading import Event, Lock


class Waiter(Event):
    """
    waiter = Waiter(3)  # wait for 3 tasks
    waiter.wait()  # wait for task complete
    waiter.result  # list of result
    """
    def __init__(self, task):
        super(Waiter, self).__init__()
        self.result = list()
        self.task = task
        self.lock = Lock()

    def __repr__(self):
        return "<Event-{} finish={} task={} result={}>" \
            .format(id(self.result), self.is_set(), self.task, len(self.result))

    def put_data(self, result):
        with self.lock:
            self.task -= 1
            self.result.extend(result)
            if self.task == 0:
                self.set()
