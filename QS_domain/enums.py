from enum import Enum


class ParamType(Enum):
    S = 'S参数'
    Y = 'Y参数'
    Z = 'Z参数'
    TIME_DOMAIN = '时域'


class DisplayMode(Enum):
    MAG_DB       = '幅度(dB)'
    MAG_ABS      = '幅度(abs)'
    PHASE_DEG    = '相位(度)'
    PHASE_RAD    = '相位(rad)'
    UNWRAP_DEG   = 'unwrap相位(度)'
    UNWRAP_RAD   = 'unwrap相位(rad)'
    GROUP_DELAY  = '群延迟(fs)'
    REAL         = '实部'
    IMAG         = '虚部'
    IMPEDANCE_M  = '阻抗(mΩ)'
    ADMITTANCE   = '导纳(abs)'
    ESR          = '实部(ESR)'
    CAPACITANCE  = '电容(pF)'
    TDR          = 'TDR阻抗'
    STEP         = '阶跃响应'
    IMPULSE      = '冲激响应'
    PULSE        = '脉冲响应'


class FitMethod(Enum):
    POLYNOMIAL = 'n次多项式'
    IEEE_8023  = 'IEEE_std_802.3-2022'
    SAVGOL     = '平滑函数'
