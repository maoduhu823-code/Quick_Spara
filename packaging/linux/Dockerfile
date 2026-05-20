# Quick_Sparam Linux 打包镜像
# 基镜：manylinux2014 = CentOS 7 + glibc 2.17
# 产物：在 dist-linux/Quick_Sparam/ 下，可直接拷到目标 CentOS 7 / RHEL 7 服务器运行
#
# 单独构建：docker build -f packaging/linux/Dockerfile -t quicksparam-builder .
# 配套调用：见项目根 build_linux.ps1

FROM quay.io/pypa/manylinux2014_x86_64

# 运行时依赖（PyQt5 wheel 已自带 Qt5 so，但仍需系统级 X / 字体库做最小链接）
# xcb-util-* 是 PyQt5 平台插件 libqxcb.so 的必需运行时依赖，缺失会导致目标机启动报
# "could not load Qt platform plugin xcb"。装上后 pyinstaller 会一并打入 dist。
# 保持在最前以稳住 docker 层缓存（CentOS 7 EOL 后 vault.centos.org DNS 偶发失败）
RUN yum install -y \
        libX11 libXext libXrender libXrandr libXi libXcursor libXtst \
        libxkbcommon libxkbcommon-x11 \
        xcb-util xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm \
        libXcomposite \
        fontconfig dejavu-sans-fonts wqy-zenhei-fonts \
        mesa-libGL \
    && yum clean all

# manylinux2014 自带的 /opt/python/cp311-cp311 是「为打 wheel 优化」的静态 Python，
# 不含 libpython3.11.so，PyInstaller 会报 PythonLibraryNotFoundError。
# 改用 python-build-standalone 的 install_only 构建：含 libpython3.11.so 且仍以 glibc 2.17 为目标。
ARG PBS_URL=https://github.com/astral-sh/python-build-standalone/releases/download/20260510/cpython-3.11.15%2B20260510-x86_64-unknown-linux-gnu-install_only.tar.gz
RUN mkdir -p /opt/python-shared \
    && curl -fsSL "$PBS_URL" | tar -xz -C /opt/python-shared --strip-components=1

ENV PYBIN=/opt/python-shared/bin
ENV PATH=$PYBIN:$PATH
ENV LD_LIBRARY_PATH=/opt/python-shared/lib
# 锁定 qtpy 后端为 PyQt5（容器内根本没装 PyQt6，但显式声明更稳）
ENV QT_API=pyqt5

WORKDIR /src

# 依赖层（独立 COPY 以利用缓存：requirements 不变时不重装）
# setuptools 锁 <80：80+ 移除了 pkg_resources，会导致 altgraph/pyinstaller 启动失败
COPY packaging/linux/requirements-linux.txt /tmp/requirements-linux.txt
RUN python -m pip install --upgrade 'pip' 'wheel' 'setuptools<80' \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && python -m pip install --no-cache-dir \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --retries 10 --timeout 120 \
        -r /tmp/requirements-linux.txt

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
