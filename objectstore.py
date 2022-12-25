import os
from typing import Union, List, Tuple, Any
import logging

from minio import Minio
from minio.error import MinioException, S3Error


logger = logging.getLogger(__name__)

MINIO_ACCESS_KEY = os.getenv("MINIO_USER_ACCESSKEY")
MINIO_SECRET_KEY = os.getenv("MINIO_USER_SECRETKEY")
MINIO_URL = os.getenv("MINIO_URL")


class ObjectStore:
    def __init__(self, bucket, setup=True):
        access_key = MINIO_ACCESS_KEY
        secret_key = MINIO_SECRET_KEY
        host = MINIO_URL

        self.client = Minio(host,
                            access_key=access_key,
                            secret_key=secret_key,
                            secure=True,
                            region='eu-east-1')
        self.bucket = bucket

        if setup:
            self.setup()

        return

    def setup(self):
        """
        Creates a new object store for a specific bucket.
        :project: the name of the project
        """

        try:
            self.client.make_bucket(self.bucket)
        except MinioException as err:
            print(err.message)
            return False

        return True

    def upload(self, objname, filepath, metadata=None):
        try:
            self.client.fput_object(self.bucket, objname, filepath,
                                    metadata=metadata)
        except Exception as exc:
            print(exc)
            return False

        return True

    def list(self):
        return self.client.list_objects(self.bucket)

    def remove(self, objname) -> Union[bool, None]:
        self.client.remove_object(self.bucket, objname)
        
    def stat(self, objname):
        try:
            return self.client.stat_object(self.bucket, objname), None
        except S3Error as s3_err:
            return None, s3_err

    def download(self, objname, download_path):
        return self.client.fget_object(self.bucket, objname, download_path)
