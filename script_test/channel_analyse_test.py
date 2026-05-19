import numpy as np
import matplotlib.pyplot as plt
from scipy import signal, interpolate
import skrf as rf
import math
import matplotlib
matplotlib.use('QtAgg')  # 使用Qt6兼容的后端


class ChannelImpulseAnalyzer:
    def __init__(self, data_rate, time_step, Num_UI=20):
        # ========= 基本参数 =========
        self.data_rate = data_rate
        self.UI = 1 / data_rate
        self.time_step = time_step
        self.sample_rate = 1 / time_step
        self.samples_per_symbol = int(round(self.UI / time_step))
        self.Num_UI = Num_UI

        # ========= FFT 点数（自动） =========
        N_fft_raw = self.Num_UI * self.samples_per_symbol
        self.N_fft = 2 ** math.ceil(math.log2(N_fft_raw))

        # ========= 坐标轴 =========
        self.time = np.arange(self.N_fft) * self.time_step
        self.freq = np.fft.rfftfreq(self.N_fft, d=self.time_step)

        # ========= 信道 =========
        self.H_freq = None
        self.h_time = None
        self.H_freq_rec = None

        # ========= 激励 =========
        self.trapezoidal_pulse = None
        self.pulse_time = None

        # ========= 响应 =========
        self.single_pulse_response = None
        self.response_time = None

        print("========== Analyzer Initialized ==========")
        print(f"Data rate           : {data_rate/1e9:.2f} Gbit/s")
        print(f"Sample rate         : {self.sample_rate/1e9:.2f} GHz")
        print(f"UI width            : {self.UI * 1e12:.2f} ps")
        print(f"Time step           : {time_step*1e12:.2f} ps")
        print(f"Samples / UI        : {self.samples_per_symbol}")
        print(f"FFT points          : {self.N_fft}")
        print(f"Analysis window     : {self.Num_UI} UI")
        print("==========================================")

    # =========================================================
    # 信道生成
    # =========================================================
    def generate_ideal_channel(self, delay=10e-12):
        self.H_freq = np.exp(-1j * 2 * np.pi * self.freq * delay)
        return self.H_freq

    def generate_lossy_channel(self,
                               loss_dc=0,
                               f_3db=20e9,
                               delay=10e-12):
        """
        loss_dc : DC loss in dB
        f_3db   : 3 dB bandwidth (first pole)
        delay   : pure delay
        """
        # === DC gain ===
        A_dc = 10 ** (-loss_dc / 20)
        # === First pole: defines 3 dB bandwidth ===
        H_p1 = 1.0 / np.sqrt(1 + (self.freq / f_3db) ** 2)
        # === Total magnitude response ===
        H_mag = A_dc * H_p1
        # === Pure delay ===
        H_delay = np.exp(-1j * 2 * np.pi * self.freq * delay)

        self.H_freq = H_mag * H_delay
        return self.H_freq

    def generate_tline_mm(self, Zc=50, Zref1=50, Zref2=50, length_mm=10.0, eps_eff=4.0, amp=1):
        """
        Transmission line channel based on ABCD matrix
        using engineering-friendly parameters.

        Parameters
        ----------
        Zc              : characteristic impedance (Ohm)
        Zref1, Zref2    : port reference impedances (Ohm)

        length_mm       : line length in mm
        eps_eff         : effective dielectric constant
        """

        # === 常量 ===
        c = 299792458.0  # m/s
        f = self.freq
        f_ghz = f/1e9

        # === 1. 衰减：dB/mm → Np ===
        a0 = 0.0  # dB/mm
        a1 = 0.02  # dB/mm / sqrt(GHz)
        a2 = 0.002 * 5  # dB/mm / GHz
        alpha_db_per_mm = a0 + amp*(a1 * np.sqrt(f_ghz) + a2 * f_ghz)
        alpha_db_eff = alpha_db_per_mm
        gamma = alpha_db_eff / 8.686  # Np

        # === 2. 相位常数 β ===
        vp = c / np.sqrt(eps_eff)
        length_m = length_mm * 1e-3
        beta = 2 * np.pi * f * length_m / vp

        # === 3. 复传播常数 ===
        Gamma = gamma + 1j * beta

        # === 4. ABCD 矩阵 ===
        A = np.cosh(Gamma)
        B = Zc * np.sinh(Gamma)
        C = (1 / Zc) * np.sinh(Gamma)
        D = np.cosh(Gamma)

        # === 5. ABCD → S21 ===
        denom = (A * Zref2 +
                 B +
                 C * Zref1 * Zref2 +
                 D * Zref1)

        self.H_freq = 2 * np.sqrt(Zref1 * Zref2) / denom
        return self.H_freq

    def load_sparam_channel(self, s_param_file, port_tx=1, port_rx=2):
        nw = rf.Network(s_param_file)
        freq_S = nw.f
        s21 = nw.s[:, port_rx - 1, port_tx - 1]

        mag_db = 20 * np.log10(np.abs(s21) + 1e-12)
        phase = np.unwrap(np.angle(s21))

        mag_i = interpolate.interp1d(freq_S, mag_db,
                                     bounds_error=False,
                                     fill_value='extrapolate')
        pha_i = interpolate.interp1d(freq_S, phase,
                                     bounds_error=False,
                                     fill_value='extrapolate')

        mag = 10 ** (mag_i(self.freq) / 20)
        self.H_freq = mag * np.exp(1j * pha_i(self.freq))
        return self.H_freq

    def generate_time_vtf(self):
        """
        Generate time-domain impulse response from frequency response.
        """
        if self.H_freq is None:
            raise RuntimeError(
                "[ChannelImpulseAnalyzer] H_freq is None.\n"
                "Please generate a channel first, e.g.:\n"
                "  - generate_ideal_channel()\n"
                "  - generate_lossy_channel()\n"
                "  - generate_tline_abcd_mm()\n"
                "  - load_sparam_channel()"
            )

        self.h_time = np.fft.irfft(self.H_freq, n=self.N_fft)
        self.H_freq_rec = np.fft.rfft(self.h_time)

    def generate_trapezoidal_pulse(self,
                                   rise_time_ps=10,
                                   fall_time_ps=10,
                                   delay_ps=100,
                                   pulse_width_UI=1):
        '''
        生成理想梯形单脉冲波形
        :param rise_time_ps:
        :param fall_time_ps:
        :param delay_ps:
        :param pulse_width_UI:
        :return:
        '''
        Ts = self.time_step

        rise_n = max(1, int(rise_time_ps * 1e-12 / Ts))
        fall_n = max(1, int(fall_time_ps * 1e-12 / Ts))
        width_n = int(pulse_width_UI * self.samples_per_symbol)
        delay_n = int(delay_ps * 1e-12 / Ts)

        roof_n = max(1, width_n - (rise_n + fall_n) // 2)

        pulse = np.zeros(rise_n + roof_n + fall_n)
        pulse[:rise_n] = np.linspace(0, 1, rise_n, endpoint=False)
        pulse[rise_n:rise_n + roof_n] = 1
        pulse[-fall_n:] = np.linspace(1, 0, fall_n)

        pulse_delayed = np.zeros(self.N_fft)
        pulse_delayed[delay_n:delay_n + len(pulse)] = pulse

        self.trapezoidal_pulse = pulse_delayed
        self.pulse_time = np.arange(self.N_fft) * Ts

    # =========================================================
    # 单脉冲响应
    # =========================================================
    def compute_single_pulse_response(self):
        if self.h_time is None:
            print("[Info] h_time not found, generating time-domain impulse response.")
            self.generate_time_vtf()
        self.single_pulse_response = signal.fftconvolve(
            self.trapezoidal_pulse,
            self.h_time
        )
        self.single_pulse_response = self.single_pulse_response[: self.N_fft]
        self.response_time = np.arange(len(self.single_pulse_response)) * self.time_step

    def compute_response_of_input(self, waveform_input):
        """
        Compute output response of an input waveform through the channel.
        """

        if self.h_time is None:
            print("[Info] h_time not found, generating time-domain impulse response.")
            self.generate_time_vtf()

        # === 卷积计算 ===
        response_output = signal.fftconvolve(
            waveform_input,
            self.h_time,
            mode='full'
        )

        # === 裁剪到输入长度（因果系统） ===
        data_length = len(waveform_input)
        response_output = response_output[:data_length]

        return response_output

    # =========================================================
    # UI 中心
    # =========================================================
    def find_ui_center(self):
        '''
        确定UI中心位置
        '''
        abs_resp = np.abs(self.single_pulse_response)
        peak_idx = np.argmax(abs_resp)
        half = abs_resp[peak_idx] / 2

        left = np.where(abs_resp[:peak_idx] < half)[0]
        right = np.where(abs_resp[peak_idx:] < half)[0]

        rise = left[-1] + 1
        fall = peak_idx + right[0]

        ui_mid = int((rise + fall) / 2)
        return ui_mid

    # =========================================================
    # 绘图（工程完整版）
    # =========================================================
    def plot_all(self, plot_span_ui=15):
        fig, axs = plt.subplots(2, 2, figsize=(16, 9))
        # === 幅度响应+3dB带宽点 ===
        # === 幅度（dB）===
        mag_rec_db = 20 * np.log10(np.abs(self.H_freq_rec))
        mag_db = 20 * np.log10(np.abs(self.H_freq) + 1e-20)
        mag_ref = np.max(mag_db)
        mag_3db = mag_ref - 3.0
        # === 找到首次跌破 3dB 的频点 ===
        idx_3db = np.where(mag_db <= mag_3db)[0]

        if len(idx_3db) > 0:
            idx_3db = idx_3db[0]
            f_3db = self.freq[idx_3db]
            # print(f"找到3 dB衰减频点：{f_3db / 1e9:.2f} GHz")
        else:
            f_3db = None
            # print(f"未找到3 dB衰减频点")
        print(f'mag_db= {mag_db[1]}')
        # axs[0, 0].semilogx(self.freq / 1e9, mag_db, label="Transfer Function")
        axs[0, 0].plot(self.freq / 1e9, mag_db, label="Transfer Function")
        axs[0, 0].plot(self.freq / 1e9, mag_rec_db, '--', label="TF from iFFT of impulse response")
        if f_3db is not None:
            axs[0, 0].axvline(f_3db / 1e9, color="r", linestyle="--")
            axs[0, 0].text(f_3db / 1e9, mag_3db*0.8, f" f_3dB={f_3db / 1e9:.2f} GHz", fontsize=11)
        axs[0, 0].set_title("Channel Magnitude Response")
        axs[0, 0].set_xlabel("Frequency (GHz)")
        axs[0, 0].set_ylabel("Magnitude (dB)")
        axs[0, 0].grid(True, alpha=0.3)
        axs[0, 0].legend()

        # === 相位响应 ===
        axs[0, 1].plot(self.freq / 1e9, np.angle(self.H_freq))
        axs[0, 1].set_title("Channel Phase Response")
        axs[0, 1].set_xlabel("Frequency (GHz)")
        axs[0, 1].set_ylabel("Phase (rad)")
        axs[0, 1].grid(True, alpha=0.3)

        # ==========时域波形及数据处理==================
        ui_center = self.find_ui_center()

        half_span_samp = plot_span_ui * self.samples_per_symbol // 2
        idx_start = max(0, ui_center - half_span_samp)
        idx_end = idx_start + plot_span_ui * self.samples_per_symbol
        t_start = self.time[idx_start] * 1e12
        t_end = self.time[idx_end] * 1e12
        print(f"Plot span       : {t_start} ~ {t_end} ps")
        # === 冲激响应 ===
        axs[1, 0].plot(self.time * 1e12, self.h_time)
        axs[1, 0].set_title("Impulse Response")
        axs[1, 0].set_xlabel("Time (ps)")
        axs[1, 0].set_ylabel("Amplitude")
        axs[1, 0].set_xlim(t_start, t_end)
        axs[1, 0].grid(True, alpha=0.3)

        # === 单脉冲响应 ===
        axs[1, 1].plot(self.response_time * 1e12, self.trapezoidal_pulse, '--', label="Input Pulse")
        axs[1, 1].plot(self.response_time * 1e12, self.single_pulse_response, label="Single Pulse Response")
        axs[1, 1].set_xlim(t_start, t_end)

        # UI 采样点
        num_pre = plot_span_ui//3
        num_post = plot_span_ui-num_pre-1
        # === 构造 UI indices（以 ui_center 为 main）===
        ui_indices = []

        # pre cursors
        for i in range(num_pre, 0, -1):
            idx = ui_center - i * self.samples_per_symbol
            if idx >= 0:
                ui_indices.append(idx)

        # main cursor
        ui_indices.append(ui_center)

        # post cursors
        for i in range(1, num_post + 1):
            idx = ui_center + i * self.samples_per_symbol
            if idx < len(self.single_pulse_response):
                ui_indices.append(idx)

        ui_indices = np.array(ui_indices, dtype=int)

        axs[1, 1].plot(
            self.response_time[ui_indices] * 1e12,
            self.single_pulse_response[ui_indices],
            'o',
            label="UI Sampling Points"
        )

        axs[1, 1].set_title("Single Pulse Response")
        axs[1, 1].set_xlabel("Time (ps)")
        axs[1, 1].set_ylabel("Amplitude")
        axs[1, 1].grid(True, alpha=0.3)
        axs[1, 1].legend()
        # 逐点标注（pre / main / post + 幅值）
        # === 选择文本锚点：post_cursor2 附近 ===
        anchor_offset = 2  # post_cursor2

        anchor_idx = ui_center + anchor_offset * self.samples_per_symbol
        anchor_idx = min(anchor_idx, len(self.single_pulse_response) - 1)

        x_text = self.response_time[anchor_idx] * 1e12
        y_min, y_max = axs[1, 1].get_ylim()
        y_text = y_max - 0.05 * (y_max - y_min)

        text_lines = []
        # 生成数据文本
        for idx in ui_indices:
            delta = (idx - ui_center) // self.samples_per_symbol
            val = self.single_pulse_response[idx]

            if delta == 0:
                name = "main"
            elif delta < 0:
                name = f"pre{abs(delta)}"
            else:
                name = f"post{delta}"

            text_lines.append(f"{name:>6s} : {val:.3f}")
        line_spacing = 0.06 * np.max(np.abs(self.single_pulse_response))
        # 打印文本
        axs[1, 1].text(
            x_text,
            y_text,
            "\n".join(text_lines),
            fontsize=11,
            ha="left",
            va="top",
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none")
        )

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    channel = ChannelImpulseAnalyzer(
        data_rate=26e9,
        time_step=2e-12,
        Num_UI=30
    )
    s_param_file = 'C:/Users/33202/PycharmProjects/Quick_Sparam/samples/parallel_line.s16p'
    s_param_file1 = 'C:/Users/33202/PycharmProjects/Quick_Sparam/samples/Twinax line-Spara1G.s4p'
    # channel.load_sparam_channel(s_param_file, port_tx=3, port_rx=1)
    channel.generate_lossy_channel(loss_dc=0, f_3db=8e9, delay=100e-12)
    # channel.generate_ideal_channel(delay=100e-12)
    # channel.generate_tline_mm(Zc=50, length_mm=2, amp=10)


    channel.generate_trapezoidal_pulse(
        rise_time_ps=10,
        fall_time_ps=10,
        delay_ps=100,
        pulse_width_UI=1
    )

    channel.compute_single_pulse_response()
    channel.plot_all()
