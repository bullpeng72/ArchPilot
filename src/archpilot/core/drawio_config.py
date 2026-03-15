"""draw.io Desktop 설정 파일 경로 탐색 및 읽기/쓰기."""

from __future__ import annotations

import json
import os
import platform
import shutil
import struct
import urllib.parse
from pathlib import Path
from typing import Optional


def find_drawio_config_path() -> Path:
    """OS별 draw.io Desktop config.json 경로를 반환.

    파일이 없어도 '생성해야 할 경로'를 반환한다.
    """
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        candidates = [
            home / "Library" / "Application Support" / "draw.io" / "config.json",
            home / ".config" / "draw.io" / "config.json",
        ]
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        candidates = [appdata / "draw.io" / "config.json"]
    else:  # Linux
        candidates = [
            home / ".config" / "draw.io" / "config.json",
            home / ".draw.io" / "config.json",
        ]

    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def find_drawio_executable() -> Optional[Path]:
    """draw.io Desktop 실행 파일 경로를 탐색한다."""
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        for p in [
            Path("/Applications/draw.io.app"),
            home / "Applications" / "draw.io.app",
        ]:
            if p.exists():
                return p

    elif system == "Windows":
        localappdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        for p in [
            Path("C:/Program Files/draw.io/draw.io.exe"),        # 시스템 설치
            Path("C:/Program Files (x86)/draw.io/draw.io.exe"),  # 32bit 시스템 설치
            localappdata / "Programs" / "draw.io" / "draw.io.exe",  # 사용자 레벨 설치
        ]:
            if p.exists():
                return p
        exe = shutil.which("draw.io") or shutil.which("drawio")
        if exe:
            return Path(exe)

    else:  # Linux
        exe = shutil.which("drawio") or shutil.which("draw.io")
        if exe:
            return Path(exe)
        for p in [
            Path("/opt/draw.io/draw.io"),
            Path("/usr/bin/drawio"),
            Path("/snap/bin/drawio"),             # Snap 심볼릭 링크
            home / ".local" / "bin" / "drawio",
        ]:
            if p.exists():
                return p

    return None


def read_drawio_config(config_path: Path) -> dict:
    """config.json을 읽어 dict로 반환. 파일이 없으면 빈 dict."""
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def write_drawio_config(config_path: Path, config: dict) -> None:
    """config dict를 config.json에 저장. 부모 디렉토리를 자동 생성한다."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def make_custom_library_entry(lib_id: str, title: str, file_path: Path) -> str:
    """draw.io Desktop customLibraries 배열에 들어가는 항목 문자열을 생성한다.

    형식: "S" + encodeURIComponent(절대경로)

    draw.io Desktop(Electron) 소스 분석 결과:
    - DesktopLibrary.prototype.getHash() = 'S' + encodeURIComponent(fileObj.path)
    - 'S' 서비스는 loadDesktopLib(filePath) → readGraphFile로 로컬 파일을 읽음
    - 'R' 서비스는 remoteInvoke(postMessage) 방식으로 embed 전용이라 Desktop에서는 동작 안 함
    """
    import urllib.parse

    return "S" + urllib.parse.quote(str(file_path))


def parse_custom_library_id(entry: str) -> str | None:
    """customLibraries 항목에서 ArchPilot 라이브러리 여부를 확인한다. 아니면 None."""
    import urllib.parse

    if entry.startswith("S"):
        # S<encodedPath> 형식 — 경로에 archpilot이 포함되면 우리 항목
        path = urllib.parse.unquote(entry[1:])
        return "archpilot" if "archpilot" in path.lower() else None
    return None


# ── Electron localStorage (LevelDB) 직접 조작 ─────────────────────────────────

def find_drawio_localstorage_path() -> Optional[Path]:
    """draw.io Desktop의 Electron localStorage LevelDB 경로를 반환."""
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        candidates = [
            home / "Library" / "Application Support" / "draw.io" / "Local Storage" / "leveldb",
        ]
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        candidates = [
            appdata / "draw.io" / "Local Storage" / "leveldb",
        ]
    else:  # Linux
        candidates = [
            home / ".config" / "draw.io" / "Local Storage" / "leveldb",   # 일반 설치 / deb
            home / "snap" / "drawio" / "common" / ".config" / "draw.io" / "Local Storage" / "leveldb",  # Snap
        ]

    for p in candidates:
        if p.exists():
            return p
    return None


def inject_custom_library(lib_path: Path) -> bool:
    """draw.io Desktop의 localStorage에 ArchPilot 라이브러리를 등록한다.

    draw.io가 실행 중이 아닐 때 호출해야 한다.
    LevelDB log 파일에 새 WriteBatch 레코드를 추가하는 방식으로 동작한다.

    Returns:
        True if successful, False otherwise.
    """
    ldb_dir = find_drawio_localstorage_path()
    if ldb_dir is None:
        return False

    # LevelDB WAL 파일 (현재 활성 log 파일) 탐색
    log_files = sorted(ldb_dir.glob("*.log"))
    if not log_files:
        return False
    log_file = log_files[-1]  # 가장 최근 log 파일

    try:
        data = log_file.read_bytes()
    except OSError:
        return False

    # 현재 .drawio-config 값과 마지막 시퀀스 번호 파악
    current_config, last_seq = _read_drawio_config_from_ldb(data)
    if current_config is None:
        # 설정이 없으면 기본값 사용
        current_config = {
            "language": "",
            "configVersion": None,
            "customFonts": [],
            "libraries": "general;uml;er;bpmn;flowchart;basic;arrows2",
            "customLibraries": ["L.scratchpad"],
            "plugins": [],
            "recentColors": [],
            "formatWidth": "240",
            "createTarget": False,
            "pageFormat": {"x": 0, "y": 0, "width": 827, "height": 1169},
            "search": True,
            "showStartScreen": False,
            "version": 18,
            "unit": 1,
            "isRulerOn": False,
            "ui": "",
        }

    # customLibraries 업데이트
    lib_entry = "S" + urllib.parse.quote(str(lib_path), safe="")
    custom_libs: list[str] = current_config.get("customLibraries", [])
    custom_libs = [e for e in custom_libs if "archpilot" not in e.lower()]
    custom_libs.append(lib_entry)
    current_config["customLibraries"] = custom_libs

    # built-in 섹션(General, Misc 등) 숨김: ArchPilot만 표시
    current_config["libraries"] = ""

    # 새 LevelDB 레코드 생성 후 append
    record = _make_ldb_record(current_config, last_seq + 1)
    try:
        with open(log_file, "ab") as f:
            f.write(record)
        return True
    except OSError:
        return False


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift  # 0x7F = 0b01111111: lower 7-bit payload mask
        if not (b & 0x80):             # 0x80 = 0b10000000: MSB continuation bit
            break
        shift += 7
    return result, offset


def _write_varint(n: int) -> bytes:
    result = b""
    while n >= 0x80:                           # values < 128 fit in a single byte
        result += bytes([0x80 | (n & 0x7F)])   # 0x80: set continuation bit; 0x7F: 7-bit payload
        n >>= 7
    return result + bytes([n])


def _make_crc32c_table() -> list[int]:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            # 0x82F63B78: CRC32C (Castagnoli) polynomial in bit-reversed form
            crc = (crc >> 1) ^ 0x82F63B78 if crc & 1 else crc >> 1
        table.append(crc)
    return table


_CRC32C_TABLE: list[int] = _make_crc32c_table()


def _crc32c(data: bytes) -> int:
    """CRC32C (Castagnoli) 순수 Python 구현."""
    crc = 0xFFFFFFFF
    for b in data:
        crc = _CRC32C_TABLE[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


def _mask_crc32c(crc: int) -> int:
    return (((crc >> 15) | (crc << 17)) + 0xa282ead8) & 0xFFFFFFFF


def _read_drawio_config_from_ldb(data: bytes) -> tuple[Optional[dict], int]:
    """LevelDB log 데이터에서 마지막 .drawio-config 값과 시퀀스 번호를 반환."""
    pos = 0
    last_seq = 0
    last_config = None
    key_target = b"_file://\x00\x01.drawio-config"

    while pos < len(data):
        if pos + 7 > len(data):
            break
        length = struct.unpack_from("<H", data, pos + 4)[0]
        rec_type = data[pos + 6]
        pos += 7
        if length == 0:
            break
        batch_data = data[pos:pos + length]
        pos += length
        if rec_type != 1 or len(batch_data) < 12:
            continue

        seq = struct.unpack_from("<Q", batch_data, 0)[0]
        count = struct.unpack_from("<I", batch_data, 8)[0]
        bpos = 12
        for _ in range(count):
            if bpos >= len(batch_data):
                break
            ktype = batch_data[bpos]
            bpos += 1
            klen, bpos = _read_varint(batch_data, bpos)
            key = batch_data[bpos:bpos + klen]
            bpos += klen
            if ktype == 1:  # PUT
                vlen, bpos = _read_varint(batch_data, bpos)
                value = batch_data[bpos:bpos + vlen]
                bpos += vlen
                if key == key_target and len(value) > 1:
                    try:
                        last_config = json.loads(value[1:].decode("utf-8"))
                        last_seq = seq
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            elif ktype == 0:  # DELETE
                if key == key_target:
                    last_config = None
        if seq > last_seq:
            last_seq = seq

    return last_config, last_seq


def _make_ldb_record(config_dict: dict, seq_num: int) -> bytes:
    """draw.io-config를 설정하는 LevelDB log 레코드를 생성한다."""
    key = b"_file://\x00\x01.drawio-config"
    value_json = json.dumps(config_dict, ensure_ascii=False, separators=(",", ":"))
    value = b"\x01" + value_json.encode("utf-8")

    # WriteBatch: [seq:8][count:4][PUT][key_len][key][val_len][val]
    batch = struct.pack("<QI", seq_num, 1)
    batch += bytes([1])  # PUT type
    batch += _write_varint(len(key))
    batch += key
    batch += _write_varint(len(value))
    batch += value

    # Masked CRC32C of [type=0x01][batch]
    crc = _mask_crc32c(_crc32c(bytes([1]) + batch))
    return struct.pack("<IHB", crc, len(batch), 1) + batch
