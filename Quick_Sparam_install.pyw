# 双击启动精简版（无控制台窗口）——通过 QS_LIMITED=1 让 Quick_Sparam_B 进精简模式
import os

os.environ['QS_LIMITED'] = '1'

from Quick_Sparam_B import main


if __name__ == '__main__':
    main()
