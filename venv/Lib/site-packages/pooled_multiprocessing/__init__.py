from multiprocessing import get_context, current_process
from threading import Thread, RLock, Event
from time import time
from psutil import cpu_count
from more_itertools import chunked
import logging
import os
from .waiter import Waiter


cpu_un_logical = cpu_count(False)
cpu_logical = cpu_count(True)

if cpu_logical and cpu_un_logical:
    cpu_num = min(cpu_logical, cpu_un_logical)
elif cpu_un_logical and cpu_logical is None:
    cpu_num = cpu_un_logical
elif cpu_logical and cpu_un_logical is None:
    cpu_num = cpu_logical
else:
    cpu_num = os.cpu_count()

processes = list()
process_index = 0
lock = RLock()


def _process(index, input_que, output_que):
    while True:
        try:
            fnc, args_list, kwargs, t = input_que.get()
            # print("S", index, round((time() - t) * 1000, 3), "mSec")
            if isinstance(args_list[0], tuple) or isinstance(args_list[0], list):
                result = [fnc(*args, **kwargs) for args in args_list]
            else:
                result = [fnc(args, **kwargs) for args in args_list]
            # print("E", index, round((time() - t) * 1000, 3), "mSec")
            output_que.put(result)
            del fnc, args_list, kwargs, result
        except Exception as e:
            error = "Error on pool {}: {}".format(index, e)
            logging.error(error)
            output_que.put([error])


def add_pool_process(add_num):
    if current_process().name != "MainProcess":
        return
    if add_num == 0:
        return
    global process_index
    with lock:
        # create
        cxt = get_context('spawn')
        for index in range(1 + process_index, add_num + process_index + 1):
            event = Event()
            event.set()
            input_que = cxt.Queue()
            output_que = cxt.Queue()
            p = cxt.Process(target=_process, name="Pool{}".format(index), args=(index, input_que, output_que))
            p.daemon = True
            p.start()
            processes.append((p, input_que, output_que, event))
            logging.info("Start pooled process {}".format(index))
            process_index += 1


def mp_map(fnc, data_list, **kwargs):
    assert len(processes) > 0, "It's not main process?"
    chunk_list = [list() for i in range(cpu_num)]
    for index, data in enumerate(data_list):
        chunk_list[index % cpu_num].append(data)
    result = list()
    work = list()
    task = 0
    # throw a tasks
    with lock:
        failed_num = 0
        for p in processes.copy():
            process, input_que, output_que, event = p
            if not process.is_alive():
                processes.remove(p)
                failed_num += 1
        add_pool_process(failed_num)
        for (process, input_que, output_que, event), args_list in zip(processes, chunk_list):
            if not process.is_alive():
                raise RuntimeError('Pool process is dead. (task throw)')
            if len(args_list) == 0:
                continue
            s = time()
            event.wait()
            # print(round((time()-s)*1000, 3), "mSec wait")
            event.clear()
            input_que.put((fnc, args_list, kwargs, time()))
            work.append(process)
            task += 1
    # wait results
    for process, input_que, output_que, event in processes:
        if process not in work:
            continue
        if not process.is_alive():
            raise RuntimeError('Pool process is dead. (waiting)')
        if not event.is_set():
            result.extend(output_que.get())
            event.set()
            task -= 1
    if task != 0:
        raise RuntimeError('complete task is 0 but {}'.format(task))
    # return result
    return result


def mp_map_async(fnc, data_list, callback=None, chunk=50, **kwargs):
    def _return(data, w):
        r = mp_map(fnc, data, **kwargs)
        if callback:
            callback(r)
        w.put_data(r)
    assert len(processes) > 0, "It's not main process?"
    chunk_list = list(chunked(data_list, chunk))
    _w = Waiter(task=len(chunk_list))
    for d in chunk_list:
        Thread(target=_return, name="Pooled", args=(d, _w), daemon=True).start()
    return _w, _w.result


def mp_close():
    with lock:
        for process, input_que, output_que, event in processes:
            process.terminate()
            input_que.close()
            output_que.close()
        processes.clear()


# pre-create
# add_pool_process(cpu_num)


__all__ = [
    "cpu_num",
    "add_pool_process",
    "mp_map",
    "mp_map_async",
    "mp_close"
]
