"""
纯端口/频率字符串解析器，不依赖任何 UI 框架。
调用方负责把 ValueError 转换成用户提示。
"""


def parse_port_input(input_str: str, type: str = 'port') -> list:
    """
    解析端口或频率输入字符串。

    支持格式:
        1:5          → [1,2,3,4,5]
        1:2:5        → [1,3,5]  (start:step:end)
        [1,3,5]      → [1,3,5]
        1 3 5        → [1,3,5]
        1，3，5      → [1,3,5]  (全角逗号)

    type='port' 返回 list[int]；type='freq' 返回 list[float]

    Raises:
        ValueError: 输入格式无效或为空
    """
    if not input_str or not input_str.strip():
        raise ValueError("输入为空")

    cleaned = input_str.strip().strip('[]')
    cleaned = cleaned.replace('，', ',').replace('：', ':')
    convert = float if type == 'freq' else int

    if ':' in cleaned:
        parts = []
        for part in cleaned.split(':'):
            parts.extend(part.strip().split())
        try:
            parts = list(map(convert, parts))
        except ValueError:
            raise ValueError(f"冒号分隔符中包含非数字内容: '{input_str}'")

        if len(parts) == 2:
            start, end = parts
            step = 1.0 if type == 'freq' else 1
        elif len(parts) == 3:
            start, step, end = parts
        else:
            raise ValueError("冒号格式应为 start:end 或 start:step:end")

        if type == 'freq':
            result: list = []
            current = start
            while (step > 0 and current <= end + 1e-12) or (step < 0 and current >= end - 1e-12):
                result.append(round(current, 10))
                current += step
            return result
        else:
            return list(range(int(start), int(end) + 1, int(step)))
    else:
        if ',' in cleaned:
            try:
                return [convert(num.strip()) for num in cleaned.split(',') if num.strip()]
            except ValueError:
                raise ValueError(f"逗号分隔列表中包含非数字内容: '{input_str}'")
        else:
            numbers = cleaned.split()
            if not numbers:
                raise ValueError("输入为空")
            try:
                return list(map(convert, numbers))
            except ValueError:
                raise ValueError(f"空格分隔列表中包含非数字内容: '{input_str}'")
