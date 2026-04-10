from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

HWP_SIGNATURE = b"HWP Document File"
FILE_HEADER_SIZE = 256
FLAGS_OFFSET = 36
COMPRESSED_FLAG = 0x01


@dataclass(frozen=True)
class FileHeaderInfo:
    signature: bytes
    version_raw: int
    flags: int

    @property
    def is_compressed(self) -> bool:
        return bool(self.flags & COMPRESSED_FLAG)


def parse_file_header(payload: bytes) -> FileHeaderInfo:
    if len(payload) < FILE_HEADER_SIZE:
        LOGGER.warning(
            "FileHeader is shorter than expected: %d < %d",
            len(payload),
            FILE_HEADER_SIZE,
        )
    if len(payload) < FLAGS_OFFSET + 4:
        raise ValueError("FileHeader is too short to read flags")

    signature = payload[: len(HWP_SIGNATURE)]
    version_raw = struct.unpack_from("<I", payload, 32)[0]
    flags = struct.unpack_from("<I", payload, FLAGS_OFFSET)[0]
    return FileHeaderInfo(
        signature=signature,
        version_raw=version_raw,
        flags=flags,
    )
