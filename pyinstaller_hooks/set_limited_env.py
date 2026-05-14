# PyInstaller runtime hook：在 main script 之前置入 QS_LIMITED=1。
# 仅由 Quick_Sparam_install.spec 引用；source 模式不会跑这个文件。
import os

os.environ['QS_LIMITED'] = '1'
