"""drawio_config.py 유닛 테스트 — varint, CRC32C, LDB 레코드."""

import json
import struct
from pathlib import Path

import pytest

from archpilot.core.drawio_config import (
    _DEFAULT_LIBRARIES,
    _crc32c,
    _make_ldb_record,
    _mask_crc32c,
    _read_drawio_config_from_ldb,
    _read_varint,
    _write_varint,
    find_drawio_config_path,
    remove_custom_library,
)


# ── varint 인코딩/디코딩 라운드트립 ──────────────────────────────────────────

class TestVarint:
    @pytest.mark.parametrize("n", [0, 1, 63, 127, 128, 255, 300, 16383, 16384, 65535, 2**21])
    def test_roundtrip(self, n):
        encoded = _write_varint(n)
        decoded, _ = _read_varint(encoded, 0)
        assert decoded == n

    def test_single_byte_for_small_values(self):
        # 0~127은 1바이트로 인코딩
        for n in range(128):
            assert len(_write_varint(n)) == 1

    def test_two_bytes_for_128(self):
        assert len(_write_varint(128)) == 2

    def test_offset_advances(self):
        data = _write_varint(300) + _write_varint(1)
        v1, pos = _read_varint(data, 0)
        v2, pos2 = _read_varint(data, pos)
        assert v1 == 300
        assert v2 == 1

    def test_zero(self):
        encoded = _write_varint(0)
        assert encoded == bytes([0])
        decoded, _ = _read_varint(encoded, 0)
        assert decoded == 0


# ── CRC32C 해시 ──────────────────────────────────────────────────────────────

class TestCRC32C:
    def test_empty_bytes(self):
        # 알려진 값: CRC32C("") = 0x00000000
        assert _crc32c(b"") == 0x00000000

    def test_known_value(self):
        # 알려진 CRC32C("123456789") = 0xE3069283
        assert _crc32c(b"123456789") == 0xE3069283

    def test_different_data_different_crc(self):
        assert _crc32c(b"hello") != _crc32c(b"world")

    def test_same_data_same_crc(self):
        assert _crc32c(b"test") == _crc32c(b"test")

    def test_mask_is_deterministic(self):
        crc = _crc32c(b"test")
        assert _mask_crc32c(crc) == _mask_crc32c(crc)

    def test_mask_differs_from_raw(self):
        crc = _crc32c(b"test")
        assert _mask_crc32c(crc) != crc


# ── LDB 레코드 구조 ──────────────────────────────────────────────────────────

class TestMakeLdbRecord:
    def test_returns_bytes(self):
        config = {"test": True}
        record = _make_ldb_record(config, seq_num=1)
        assert isinstance(record, bytes)

    def test_header_length(self):
        config = {"x": 1}
        record = _make_ldb_record(config, seq_num=1)
        # 헤더: CRC(4) + length(2) + type(1) = 7바이트
        assert len(record) >= 7

    def test_record_type_byte(self):
        config = {"x": 1}
        record = _make_ldb_record(config, seq_num=1)
        # type 바이트 (offset 6) == 1 (kFullType)
        assert record[6] == 1

    def test_crc_validates(self):
        config = {"customLibraries": ["S/path/to/lib.xml"]}
        record = _make_ldb_record(config, seq_num=42)
        # 첫 4바이트는 masked CRC
        stored_crc = struct.unpack_from("<I", record, 0)[0]
        assert stored_crc != 0

    def test_seq_num_in_batch(self):
        config = {}
        record = _make_ldb_record(config, seq_num=99)
        # batch 데이터는 offset 7부터
        batch = record[7:]
        seq = struct.unpack_from("<Q", batch, 0)[0]
        assert seq == 99

    def test_roundtrip_via_read(self):
        """생성한 레코드를 _read_drawio_config_from_ldb로 파싱하면 원본과 동일해야 한다."""
        config = {
            "customLibraries": ["S%2Fhome%2Fuser%2Farchpilot.xml"],
            "libraries": "",
        }
        record = _make_ldb_record(config, seq_num=1)
        parsed_config, last_seq = _read_drawio_config_from_ldb(record)
        assert parsed_config is not None
        assert parsed_config["customLibraries"] == config["customLibraries"]
        assert last_seq == 1


# ── find_drawio_config_path ──────────────────────────────────────────────────

class TestFindDrawioConfigPath:
    def test_returns_path_object(self):
        from pathlib import Path
        result = find_drawio_config_path()
        assert isinstance(result, Path)

    def test_parent_is_draw_io(self):
        result = find_drawio_config_path()
        # 경로에 draw.io 폴더가 포함되어야 함
        parts = [p.lower() for p in result.parts]
        assert any("draw.io" in p for p in parts)

    def test_filename_is_config_json(self):
        result = find_drawio_config_path()
        assert result.name == "config.json"


# ── remove_custom_library ────────────────────────────────────────────────────

class TestRemoveCustomLibrary:
    def _make_ldb_dir(self, tmp_path: Path, config: dict, seq: int = 1) -> Path:
        """임시 LevelDB 디렉토리와 .log 파일을 생성한다."""
        ldb_dir = tmp_path / "leveldb"
        ldb_dir.mkdir()
        record = _make_ldb_record(config, seq_num=seq)
        (ldb_dir / "000001.log").write_bytes(record)
        return ldb_dir

    def test_removes_archpilot_entry(self, tmp_path, monkeypatch):
        config = {
            "customLibraries": ["S%2Fhome%2Fuser%2F.archpilot%2Farchpilot-library.drawio.xml", "L.scratchpad"],
            "libraries": "",
        }
        ldb_dir = self._make_ldb_dir(tmp_path, config)
        monkeypatch.setattr(
            "archpilot.core.drawio_config.find_drawio_localstorage_path",
            lambda: ldb_dir,
        )

        result = remove_custom_library()
        assert result is True

        data = (ldb_dir / "000001.log").read_bytes()
        parsed, _ = _read_drawio_config_from_ldb(data)
        assert parsed is not None
        assert not any("archpilot" in e.lower() for e in parsed["customLibraries"])
        assert "L.scratchpad" in parsed["customLibraries"]

    def test_restores_default_libraries(self, tmp_path, monkeypatch):
        config = {"customLibraries": ["S%2Farchpilot.xml"], "libraries": ""}
        ldb_dir = self._make_ldb_dir(tmp_path, config)
        monkeypatch.setattr(
            "archpilot.core.drawio_config.find_drawio_localstorage_path",
            lambda: ldb_dir,
        )

        remove_custom_library()
        data = (ldb_dir / "000001.log").read_bytes()
        parsed, _ = _read_drawio_config_from_ldb(data)
        assert parsed["libraries"] == _DEFAULT_LIBRARIES

    def test_no_op_when_already_clean(self, tmp_path, monkeypatch):
        config = {"customLibraries": ["L.scratchpad"], "libraries": _DEFAULT_LIBRARIES}
        ldb_dir = self._make_ldb_dir(tmp_path, config, seq=5)
        monkeypatch.setattr(
            "archpilot.core.drawio_config.find_drawio_localstorage_path",
            lambda: ldb_dir,
        )

        result = remove_custom_library()
        assert result is True
        # 이미 깨끗한 상태이므로 새 레코드를 쓰지 않아야 함 — log 크기 동일
        original_size = len(_make_ldb_record(config, seq_num=5))
        assert (ldb_dir / "000001.log").stat().st_size == original_size

    def test_returns_true_when_no_config(self, tmp_path, monkeypatch):
        """LDB에 .drawio-config가 없어도 True를 반환한다."""
        ldb_dir = tmp_path / "leveldb"
        ldb_dir.mkdir()
        (ldb_dir / "000001.log").write_bytes(b"")
        monkeypatch.setattr(
            "archpilot.core.drawio_config.find_drawio_localstorage_path",
            lambda: ldb_dir,
        )
        assert remove_custom_library() is True

    def test_returns_false_when_no_ldb(self, monkeypatch):
        monkeypatch.setattr(
            "archpilot.core.drawio_config.find_drawio_localstorage_path",
            lambda: None,
        )
        assert remove_custom_library() is False

    def test_returns_false_when_no_log_files(self, tmp_path, monkeypatch):
        ldb_dir = tmp_path / "leveldb"
        ldb_dir.mkdir()
        monkeypatch.setattr(
            "archpilot.core.drawio_config.find_drawio_localstorage_path",
            lambda: ldb_dir,
        )
        assert remove_custom_library() is False
