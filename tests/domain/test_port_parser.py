"""QS_domain/port_parser.py 的单元测试（不需要 QApplication）。"""

import pytest
from QS_domain.port_parser import parse_port_input


class TestParsePortInputPort:
    def test_space_separated(self):
        assert parse_port_input("1 2 3") == [1, 2, 3]

    def test_colon_range(self):
        assert parse_port_input("1:5") == [1, 2, 3, 4, 5]

    def test_colon_step(self):
        assert parse_port_input("1:2:7") == [1, 3, 5, 7]

    def test_comma_separated(self):
        assert parse_port_input("1,3,5") == [1, 3, 5]

    def test_fullwidth_comma(self):
        assert parse_port_input("1，3，5") == [1, 3, 5]

    def test_fullwidth_colon(self):
        assert parse_port_input("1：5") == [1, 2, 3, 4, 5]

    def test_brackets(self):
        assert parse_port_input("[1 2 3]") == [1, 2, 3]

    def test_single_port(self):
        assert parse_port_input("3") == [3]

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_port_input("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            parse_port_input("   ")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError):
            parse_port_input("a b c")

    def test_bad_colon_raises(self):
        with pytest.raises(ValueError):
            parse_port_input("1:2:3:4")


class TestParsePortInputFreq:
    def test_float_space(self):
        result = parse_port_input("1.0 2.5 3.0", type='freq')
        assert result == pytest.approx([1.0, 2.5, 3.0])

    def test_freq_range(self):
        result = parse_port_input("1.0:0.5:2.0", type='freq')
        assert result == pytest.approx([1.0, 1.5, 2.0])

    def test_freq_simple_range(self):
        result = parse_port_input("0:3", type='freq')
        assert result == pytest.approx([0.0, 1.0, 2.0, 3.0])
