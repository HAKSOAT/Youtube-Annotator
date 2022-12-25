# TODO: Setup logging

from queue import Queue
from time import sleep
from threading import Thread

from objectstore import ObjectStore
import streamlit as st
from streamlit import session_state as ss

from core import YT


def display(queue):
    st.write("# The YouTube Annotator")

    throw = st.selectbox("Judo throw", ["Seoi Nage", "Tai Otoshi", "Kouchi Gari",
                                        "Osoto Gari", "Hiza Guruma", "Uchi Mata",
                                        "Grip Battle", "Ne Waza Battle"], index=0)
    url = st.text_input("Enter YouTube URL")
    start_seconds = st.text_input("Enter start seconds")
    end_seconds = st.text_input("Enter end seconds")

    extract = st.button("Extract clip")
    if extract:
        job = {
            "url": url,
            "start": start_seconds,
            "end": end_seconds,
            "throw": throw
        }
        print("INSERTED")
        # TODO: Add a cache here to ensure a job does not already exist in the queue.
        queue.put(job)


def get_sec(time_str):
    """Get seconds from time."""
    parts = time_str.split(':')
    if len(parts) == 1:
        parts = [0, 0] + parts
    elif len(parts) == 2:
        parts = [0] + parts
    h, m, s = parts
    return int(h) * 3600 + int(m) * 60 + int(s)


def consumer(queue: Queue):
    objstore = ObjectStore("judo-throws")
    while True:
        if queue.empty():
            print("QUEUE IS EMPTY")
            sleep(1)
            continue
        job = queue.get()
        yt = YT(job.get("url"))
        start = get_sec(job.get("start"))
        end = get_sec(job.get("end"))
        clip_meta = yt.get_clip_meta(f"{job.get('throw')}-", start, end)
        stat, error = objstore.stat(clip_meta["clip-name"])
        if error:
            yt.clip(f"{job.get('throw')}-", start, end)
            yt.upload(clip_meta["clip-name"], objstore, clip_meta)

        print("DONE.")
        queue.task_done()


def make_consumers(n: int = 3):
    if "consumers" in ss:
        return ss["queue"], ss["consumers"]

    queue = Queue()
    futures = []
    for i in range(n):
        worker = Thread(target=consumer, args=(queue,))
        worker.daemon = True
        worker.start()
        futures.append(worker)

    if "consumers" not in ss:
        ss["consumers"] = futures
        ss["queue"] = queue

    return queue, futures


queue, _ = make_consumers()
display(queue)
