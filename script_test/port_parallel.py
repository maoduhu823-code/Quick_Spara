import skrf as rf
import numpy as np

# 1. 加载 S2P 文件
ntw = rf.Network('../input_test/StackupDemo1_test_renorm_R.s2p')

# 2. 获取 Y 参数矩阵，其 shape 为 (f, 2, 2)
# y[:, 0, 0] 是 Y11, y[:, 0, 1] 是 Y12, 依此类推
y_orig = ntw.y

# 3. 按照并联规则计算新的导纳：Y_new = Y11 + Y12 + Y21 + Y22
# 这样会将 (f, 2, 2) 的矩阵在最后两个维度上求和，变为 (f,)
y_sum = y_orig.sum(axis=(1, 2))

# 4. 将 shape 调整为 (f, 1, 1) 以符合 skrf 的 Network 构造要求
y_new = y_sum[:, np.newaxis, np.newaxis]

# 5. 创建新的 S1P 网络
# 注意：z0 默认取原网络第一个端口的阻抗（通常是 50）
ntw_s1p = rf.Network(frequency=ntw.frequency, y=y_new, z0=ntw.z0[:, 0])
# 保存为 Touchstone 文件 (.s1p)
# 你可以指定完整路径，如果不写路径则保存在当前脚本目录下
output_filename = './port_parallel.s1p'
ntw_s1p.write_touchstone(output_filename)

print(f"转换完成，S1P 文件已保存至: {output_filename}")