import os
import re
from datetime import timedelta
import subprocess
from copy import deepcopy


SAVE_FORMAT = "{title}-{start}-{duration}.{extension}"


def exec(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if result.stderr:
        return result.stderr, False
    return result.stdout, True


class YT:
    def __init__(self, url, code=278):
        self.url = url
        self.meta = {
            "url": url,
            "code": code,
            "title": None,
            "format": None,
            "yt-filename": None,
            "save-name": None,
            "id": None
        }

    @staticmethod
    def clean_text(text):
        text = re.sub(r"(\\x..|\\n)", r"", text)
        text = re.sub(r"[^ a-zA-Z0-9\-\.]", r"", text)
        text = text.strip()
        return text

    def _get_meta(self):
        if not self.meta.get("title"):
            command = f"yt-dlp -f {self.meta.get('code')} -e {self.url}"
            output, status = exec(command)
            if not status:
                raise Exception(output)
            # Removing characters that don't fit us-ascii encoding as minio doesn't allow them
            # in metadata.
            output = str(output)[2:-1]
            self.meta["title"] = self.clean_text(output)

        if not self.meta.get("id"):
            command = f"yt-dlp -f {self.meta.get('code')} --get-id {self.url}"
            output, status = exec(command)
            if not status:
                raise Exception(output)
            self.meta["id"] = output.decode("utf-8").strip()

        if not self.meta.get("format"):
            command = f"yt-dlp -f {self.meta.get('code')} --get-format {self.url}"
            output, status = exec(command)
            if not status:
                raise Exception(output)
            self.meta["format"] = output.decode("utf-8").strip()

        if not self.meta.get("yt-filename"):
            command = f"yt-dlp -f {self.meta.get('code')} --get-filename {self.url}"
            output, status = exec(command)
            if not status:
                raise Exception(output)
            output = str(output)[2:-1]
            self.meta["yt-filename"] = self.clean_text(output)

        ext = self.meta.get("yt-filename").split(".")[-1]
        self.meta["save-name"] = f"{self.meta.get('title')}-{self.meta.get('code')}.{ext}"

        return self.meta

    def download(self):
        if os.path.exists(self.meta.get('save-name') or ""):
            return

        self._get_meta()
        command = f"yt-dlp -f {self.meta.get('code')} {self.meta.get('url')} -o '{self.meta.get('save-name')}'"
        output, status = exec(command)
        if not status:
            raise Exception(output)

    def get_clip_meta(self, clip_prefix="", start=0, stop=None):
        self._check_clip_args(clip_prefix, start, stop)
        meta = deepcopy(self._get_meta())

        duration = stop - start if stop else None
        name, ext = os.path.splitext(meta.get("save-name"))
        ext = ext.strip(".")
        clip_name = SAVE_FORMAT.format(title=clip_prefix + name, start=start,
                                       duration=duration, extension=ext)

        meta["clip-name"] = clip_name
        meta["clip-start"] = start
        meta["clip-stop"] = stop

        return meta

    def _check_clip_args(self, clip_prefix, start, stop):
        if start == 0 and stop is None:
            raise ValueError("start and stop MUST NOT be 0 and None at the same time as that means the entire file.")

    def clip(self, clip_prefix="", start=0, stop=None, overwrite=False):
        self._check_clip_args(clip_prefix, start, stop)

        clip_filepath = self.get_clip_meta(clip_prefix, start, stop)["clip-name"]
        if not os.path.exists(self.meta.get("save-name") or ""):
            try:
                self.download()
            except NotImplementedError:
                pass

        if not overwrite and os.path.exists(clip_filepath):
            return

        duration = stop - start if stop else None
        # Leaving out ```-c copy``` from the ffmpeg command despite it making for faster clipping
        # because it skips ffmpeg re-encoding and therefore the clips can be inaccurate by as much as 3 seconds.
        if duration:
            command = f"ffmpeg -y -ss {timedelta(seconds=start)} -i \'{self.meta.get('save-name')}\' " \
                      f"-t {timedelta(seconds=duration)} '{clip_filepath}' -loglevel error"
        else:
            command = f"ffmpeg -y -ss {timedelta(seconds=start)} -i \'{self.meta.get('save-name')}\' " \
                      f"'{clip_filepath}' -loglevel error"

        output, status = exec(command)
        if not status:
            raise Exception(output)

        return clip_filepath

    @staticmethod
    def upload(filename, objstore, meta, update=False):
        if not meta:
            raise ValueError("meta MUST be specified.")
        stats, error = objstore.stat(filename)

        if not error and not update:
            return False

        if not os.path.exists(filename):
            raise FileNotFoundError(filename)

        objstore.upload(filename, filename, meta)
        os.remove(filename)
        return True







