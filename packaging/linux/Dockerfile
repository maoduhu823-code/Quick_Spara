# Quick_Sparam Linux 打包镜像
# 基镜：manylinux2014 = CentOS 7 + glibc 2.17
# 产物：在 dist-linux/Quick_Sparam/ 下，可直接拷到目标 CentOS 7 / RHEL 7 服务器运行
#
# 单独构建：docker build -f packaging/linux/Dockerfile -t quicksparam-builder .
# 配套调用：见项目根 build_linux.ps1

FROM quay.io/pypa/manylinux2014_x86_64

# 选 cp311（与桌面 Python 3.12 较接近，且 manylinux2014 完整支持 PyQt5 wheel）
# 如需更换 Python 版本，改下面这一行即可
ENV PYBIN=/opt/python/cp311-cp311/bin
ENV PATH=$PYBIN:$PATH
# 锁定 qtpy 后端为 PyQt5（容器内根本没装 PyQt6，但显式声明更稳）
ENV QT_API=pyqt5

# 运行时依赖（PyQt5 wheel 已自带 Qt5 so，但仍需系统级 X / 字体库做最小链接）
RUN yum install -y \
        libX11 libXext libXrender libXrandr libXi libXcursor libXtst \
        libxkbcommon libxkbcommon-x11 \
        fontconfig dejavu-sans-fonts wqy-zenhei-fonts \
        mesa-libGL \
    && yum clean all

WORKDIR /src

# 依赖层（独立 COPY 以利用缓存：requirements 不变时不重装）
COPY packaging/linux/requirements-linux.txt /tmp/requirements-linux.txt
RUN python -m pip install --upgrade pip wheel setuptools \
    && python -m pip install --no-cache-dir -r /tmp/requirements-linux.txt

# 默认入口：执行打包；项目源码在运行时通过 -v 挂载到 /src
# 产物路径用 --distpath/--workpath 隔离，避免与 Windows 的 dist/ 冲突
ENTRYPOINT ["bash", "-lc"]
CMD ["pyinstaller --noconfirm --clean \
      --distpath /src/dist-linux \
      --workpath /src/build-linux \
      /src/Quick_Sparam_linux.spec && \
      echo '--- ldd 检查 (应全部 <= GLIBC_2.17) ---' && \
      objdump -T /src/dist-linux/Quick_Sparam/Quick_Sparam 2>/dev/null \
        | grep -oP 'GLIBC_\\K[0-9.]+' | sort -uV | tail -5"]
