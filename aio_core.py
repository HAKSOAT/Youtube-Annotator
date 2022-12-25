import os
from asyncio import create_subprocess_shell, subprocess as aio_subprocess
from datetime import timedelta

from core import SAVE_FORMAT


async def aio_exec(command):
    result = await create_subprocess_shell(command, stdout=aio_subprocess.PIPE, stderr=aio_subprocess.PIPE)
    stdout, stderr = await result.communicate()
    if stderr:
        return stderr, False
    else:
        return stdout, True


class AIO_YT:
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

    async def _get_meta(self):
        if not self.meta.get("title"):
            command = f"yt-dlp -f {self.meta.get('code')} -e {self.url}"
            output, status = await aio_exec(command)
            if not status:
                raise Exception(output)
            self.meta["title"] = output.decode("utf-8").strip()

        if not self.meta.get("id"):
            command = f"yt-dlp -f {self.meta.get('code')} --get-id {self.url}"
            output, status = await aio_exec(command)
            if not status:
                raise Exception(output)
            self.meta["id"] = output.decode("utf-8").strip()

        if not self.meta.get("format"):
            command = f"yt-dlp -f {self.meta.get('code')} --get-format {self.url}"
            output, status = await aio_exec(command)
            if not status:
                raise Exception(output)
            self.meta["format"] = output.decode("utf-8").strip()

        if not self.meta.get("yt-filename"):
            command = f"yt-dlp -f {self.meta.get('code')} --get-filename {self.url}"
            output, status = await aio_exec(command)
            if not status:
                raise Exception(output)
            self.meta["yt-filename"] = output.decode("utf-8").strip()

        ext = self.meta.get("yt-filename").split(".")[-1]
        self.meta["save-name"] = f"{self.meta.get('title')}-{self.meta.get('code')}.{ext}"

        return self.meta

    async def download(self):
        if os.path.exists(self.meta.get('save-name') or ""):
            return

        await self._get_meta()
        command = f"yt-dlp -f {self.meta.get('code')} {self.meta.get('url')} -o '{self.meta.get('save-name')}'"
        output, status = await aio_exec(command)
        if not status:
            raise Exception(output)

    async def clip(self, start=0, stop=None, overwrite=False):
        if start == 0 and stop is None:
            raise ValueError("start and stop MUST NOT be 0 and None at the same time as that means the entire file.")

        if not os.path.exists(self.meta.get("save-name") or ""):
            try:
                await self.download()
            except NotImplementedError:
                pass

        duration = stop - start if stop else None
        name, ext = os.path.splitext(self.meta.get("save-name"))
        ext = ext.strip(".")
        clip_filepath = SAVE_FORMAT.format(title=name, start=start, duration=duration, extension=ext)
        overwrite = "-y" if overwrite else "-n"
        if duration:
            command = f"ffmpeg {overwrite} -ss {timedelta(seconds=start)} -i \'{self.meta.get('save-name')}\' " \
                      f"-t {timedelta(seconds=duration)} -c copy '{clip_filepath}' -loglevel error"
        else:
            command = f"ffmpeg {overwrite} -ss {timedelta(seconds=start)} -i \'{self.meta.get('save-name')}\' " \
                      f"-c copy '{clip_filepath}' -loglevel error"

        output, status = await aio_exec(command)
        if not status:
            raise Exception(output)
