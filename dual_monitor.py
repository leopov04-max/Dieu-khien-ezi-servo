#!/usr/bin/env python3
"""
=============================================================
  DUAL SERIAL MONITOR  -  STM32 BluePill + Arduino Nano
=============================================================
  Mạch 1 - Arduino Nano  : điều khiển EZI-Servo (motor)
  Mạch 2 - STM32 BluePill: đọc cảm biến ADC (PA0, PA1)

  Cách dùng:
    1. Chỉnh ARDUINO_PORT và STM32_PORT bên dưới
    2. Chạy:  python dual_monitor.py
=============================================================
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import time
from datetime import datetime
from collections import deque
import csv
import os

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ============================================================
#  CẤU HÌNH - Chỉnh sửa COM port tại đây
# ============================================================
ARDUINO_PORT = 'COM3'   # Arduino Nano  - điều khiển động cơ
ARDUINO_BAUD = 9600

STM32_PORT   = 'COM4'   # STM32 BluePill - cảm biến ADC
STM32_BAUD   = 115200

PLOT_WINDOW  = 300      # Số điểm hiển thị trên đồ thị (300 điểm × 50ms = 15 giây)
# ============================================================


class DualMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual Serial Monitor  —  STM32 (ADC) + Arduino Nano (Motor)")
        self.root.geometry("1150x720")
        self.root.configure(bg='#1e1e1e')
        self.root.resizable(True, True)

        # Hàng đợi thread-safe
        self.stm32_queue   = queue.Queue()
        self.arduino_queue = queue.Queue()

        # Buffer dữ liệu cho đồ thị
        self.plot_times = deque(maxlen=PLOT_WINDOW)
        self.plot_v1    = deque(maxlen=PLOT_WINDOW)
        self.plot_v2    = deque(maxlen=PLOT_WINDOW)
        self.t0 = time.time()

        # Kết nối serial
        self.arduino_ser = None
        self.running     = True

        # CSV log - bật/tắt thủ công bằng nút GHI LOG
        self.logging_active = False
        self.csv_writer     = None
        self.csv_file       = None
        self.log_path       = None

        self._build_ui()
        self._setup_plot_colors()
        self._start_background_threads()
        self._schedule_ui_update()

    # ----------------------------------------------------------
    #  XÂY DỰNG GIAO DIỆN
    # ----------------------------------------------------------
    def _build_ui(self):
        # === Thanh trên cùng: trạng thái kết nối ===
        top_bar = tk.Frame(self.root, bg='#252526', height=30)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.pack_propagate(False)

        self.stm32_status  = tk.Label(top_bar, text=f"● STM32  {STM32_PORT}",
                                      bg='#252526', fg='#666', font=('Consolas', 9))
        self.stm32_status.pack(side=tk.LEFT, padx=12, pady=5)

        self.arduino_status = tk.Label(top_bar, text=f"● Arduino  {ARDUINO_PORT}",
                                       bg='#252526', fg='#666', font=('Consolas', 9))
        self.arduino_status.pack(side=tk.LEFT, padx=12)

        self.log_status_label = tk.Label(top_bar, text="",
                                         bg='#252526', fg='#4ec9b0', font=('Consolas', 9))
        self.log_status_label.pack(side=tk.RIGHT, padx=12)

        tk.Button(top_bar, text="Quét cổng COM", command=self._show_ports,
                  bg='#3c3c3c', fg='white', font=('Consolas', 8),
                  relief='flat', padx=6).pack(side=tk.RIGHT, padx=6, pady=4)

        # === Giá trị hiện tại (live readout) ===
        live_bar = tk.Frame(self.root, bg='#094771')
        live_bar.pack(fill=tk.X)

        self.live_a0 = tk.Label(live_bar, text="A0 (PA0): --- V",
                                bg='#094771', fg='#7cd0f7',
                                font=('Consolas', 13, 'bold'), padx=20)
        self.live_a0.pack(side=tk.LEFT, pady=4)

        self.live_a1 = tk.Label(live_bar, text="A1 (PA1): --- V",
                                bg='#094771', fg='#ffaa44',
                                font=('Consolas', 13, 'bold'), padx=20)
        self.live_a1.pack(side=tk.LEFT)

        # === Đồ thị matplotlib ===
        plot_frame = tk.Frame(self.root, bg='#1e1e1e')
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 0))

        self.fig, self.ax = plt.subplots(figsize=(11, 3.6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.line1, = self.ax.plot([], [], color='#7cd0f7', linewidth=1.5, label='A0 – PA0')
        self.line2, = self.ax.plot([], [], color='#ffaa44', linewidth=1.5, label='A1 – PA1')
        self.ax.legend(facecolor='#2d2d2d', labelcolor='white', loc='upper right',
                       fontsize=9, framealpha=0.7)

        # === Phần dưới: log + điều khiển ===
        bottom = tk.Frame(self.root, bg='#1e1e1e')
        bottom.pack(fill=tk.BOTH, padx=6, pady=4)

        # Log Arduino (bên trái)
        log_frame = tk.LabelFrame(bottom, text="  Phản hồi từ Arduino (Motor)  ",
                                  fg='#ffcc44', bg='#1e1e1e', font=('Consolas', 9))
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        self.motor_log = scrolledtext.ScrolledText(
            log_frame, height=7, bg='#0d0d0d', fg='#cccccc',
            font=('Consolas', 9), insertbackground='white',
            state=tk.DISABLED, wrap=tk.WORD)
        self.motor_log.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        self.motor_log.tag_config('sent',   foreground='#9cdcfe')
        self.motor_log.tag_config('recv',   foreground='#cccccc')
        self.motor_log.tag_config('ok',     foreground='#4ec9b0')
        self.motor_log.tag_config('error',  foreground='#f44747')

        # Bảng điều khiển động cơ (bên phải)
        ctrl = tk.LabelFrame(bottom, text="  Điều khiển Động cơ  ",
                             fg='#9cdcfe', bg='#1e1e1e', font=('Consolas', 9))
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, ipadx=10)

        tk.Label(ctrl, text="Vị trí đích (mm):",
                 bg='#1e1e1e', fg='#cccccc', font=('Consolas', 9)).pack(pady=(10, 2))

        self.cmd_entry = tk.Entry(ctrl, width=12, bg='#2d2d2d', fg='white',
                                  font=('Consolas', 14, 'bold'),
                                  insertbackground='white', justify='center',
                                  relief='flat', bd=4)
        self.cmd_entry.pack(pady=2, ipady=3)
        self.cmd_entry.bind('<Return>', self._on_send)

        tk.Button(ctrl, text="  GỬI  ", command=self._on_send,
                  bg='#0e639c', fg='white', font=('Consolas', 10, 'bold'),
                  relief='flat', padx=8, pady=5).pack(pady=(5, 3), fill=tk.X, padx=10)

        tk.Button(ctrl, text="  HOME  ", command=lambda: self._send_cmd("home"),
                  bg='#6b2fad', fg='white', font=('Consolas', 10, 'bold'),
                  relief='flat', padx=8, pady=5).pack(pady=3, fill=tk.X, padx=10)

        tk.Button(ctrl, text="  STOP  ", command=lambda: self._send_cmd("stop"),
                  bg='#a31515', fg='white', font=('Consolas', 10, 'bold'),
                  relief='flat', padx=8, pady=5).pack(pady=3, fill=tk.X, padx=10)

        # Nút bật/tắt ghi log
        self.log_btn = tk.Button(ctrl, text="  GHI LOG  ", command=self._toggle_log,
                                 bg='#1e6b3c', fg='white', font=('Consolas', 10, 'bold'),
                                 relief='flat', padx=8, pady=5)
        self.log_btn.pack(pady=(8, 3), fill=tk.X, padx=10)

        # Thanh trạng thái dưới cùng
        self.status_var = tk.StringVar(value="Khởi động...")
        tk.Label(self.root, textvariable=self.status_var,
                 bg='#007acc', fg='white', anchor='w',
                 font=('Consolas', 8), padx=8).pack(fill=tk.X, side=tk.BOTTOM)

    def _setup_plot_colors(self):
        self.fig.patch.set_facecolor('#1e1e1e')
        self.ax.set_facecolor('#252526')
        for spine in self.ax.spines.values():
            spine.set_color('#555')
        self.ax.tick_params(colors='#aaaaaa', labelsize=8)
        self.ax.set_xlabel('Thời gian (s)', color='#aaaaaa', fontsize=9)
        self.ax.set_ylabel('Điện áp (V)', color='#aaaaaa', fontsize=9)
        self.ax.set_title('STM32 ADC  —  Dữ liệu cảm biến thời gian thực', color='white', fontsize=10, pad=6)
        self.ax.set_ylim(-0.2, 3.6)
        self.ax.grid(True, color='#3a3a3a', linewidth=0.5, linestyle='--')
        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    # ----------------------------------------------------------
    #  THREADS ĐỌC SERIAL
    # ----------------------------------------------------------
    def _start_background_threads(self):
        threading.Thread(target=self._stm32_reader_loop,   daemon=True).start()
        threading.Thread(target=self._arduino_reader_loop, daemon=True).start()

    def _stm32_reader_loop(self):
        """Thread liên tục đọc dữ liệu ADC từ STM32."""
        first_fail = True
        while self.running:
            try:
                with serial.Serial(STM32_PORT, STM32_BAUD, timeout=0.15) as ser:
                    first_fail = True
                    self.stm32_queue.put(('OK', f"STM32 kết nối thành công tại {STM32_PORT}"))
                    while self.running:
                        raw = ser.readline()
                        if not raw:
                            continue
                        text = raw.decode('utf-8', errors='replace').strip()
                        if text:
                            self.stm32_queue.put(('DATA', text))
            except serial.SerialException as e:
                if first_fail:
                    self.stm32_queue.put(('ERR', f"STM32 ({STM32_PORT}): {e}"))
                    first_fail = False
                time.sleep(2)

    def _arduino_reader_loop(self):
        """Thread liên tục kết nối và đọc phản hồi từ Arduino."""
        first_fail = True
        while self.running:
            try:
                ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=0.15)
                self.arduino_ser = ser
                first_fail = True
                time.sleep(1.8)   # Chờ Arduino reset sau khi mở cổng
                self.arduino_queue.put(('OK', f"Arduino kết nối thành công tại {ARDUINO_PORT}"))
                while self.running:
                    raw = ser.readline()
                    if raw:
                        text = raw.decode('utf-8', errors='replace').strip()
                        if text:
                            self.arduino_queue.put(('RECV', text))
            except serial.SerialException as e:
                self.arduino_ser = None
                if first_fail:
                    self.arduino_queue.put(('ERR', f"Arduino ({ARDUINO_PORT}): {e}"))
                    first_fail = False
                time.sleep(2)

    # ----------------------------------------------------------
    #  CẬP NHẬT GIAO DIỆN (chạy trên main thread)
    # ----------------------------------------------------------
    def _schedule_ui_update(self):
        self._flush_queues()
        if self.running:
            self.root.after(80, self._schedule_ui_update)  # ~12 lần/giây

    def _flush_queues(self):
        plot_dirty = False

        # --- STM32 queue ---
        while not self.stm32_queue.empty():
            kind, data = self.stm32_queue.get_nowait()
            if kind == 'DATA':
                parts = data.split()
                if len(parts) >= 2:
                    try:
                        v1 = float(parts[0])
                        v2 = float(parts[1])
                        t  = time.time() - self.t0
                        self.plot_times.append(t)
                        self.plot_v1.append(v1)
                        self.plot_v2.append(v2)
                        self.live_a0.config(text=f"A0 (PA0): {v1:+.3f} V")
                        self.live_a1.config(text=f"A1 (PA1): {v2:+.3f} V")
                        if self.logging_active and self.csv_writer:
                            self.csv_writer.writerow([f"{t:.3f}", f"{v1:.4f}", f"{v2:.4f}", ""])
                        plot_dirty = True
                    except ValueError:
                        pass
            elif kind == 'OK':
                self.stm32_status.config(fg='#4ec9b0', text=f"● STM32  {STM32_PORT}  ✓")
                self._set_status(data)
            elif kind == 'ERR':
                self.stm32_status.config(fg='#f44747', text=f"● STM32  {STM32_PORT}  ✗")
                self._set_status(data)

        # Cập nhật đồ thị chỉ khi có dữ liệu mới
        if plot_dirty and len(self.plot_times) >= 2:
            xs = list(self.plot_times)
            self.line1.set_data(xs, list(self.plot_v1))
            self.line2.set_data(xs, list(self.plot_v2))
            self.ax.set_xlim(xs[0], max(xs[-1], xs[0] + 1.0))
            self.canvas.draw_idle()

        # --- Arduino queue ---
        while not self.arduino_queue.empty():
            kind, data = self.arduino_queue.get_nowait()
            ts = datetime.now().strftime('%H:%M:%S')
            if kind == 'RECV':
                self._log_motor(f"[{ts}]  {data}\n", 'recv')
            elif kind == 'OK':
                self.arduino_status.config(fg='#4ec9b0', text=f"● Arduino  {ARDUINO_PORT}  ✓")
                self._log_motor(f"[{ts}]  {data}\n", 'ok')
                self._set_status(data)
            elif kind == 'ERR':
                self.arduino_status.config(fg='#f44747', text=f"● Arduino  {ARDUINO_PORT}  ✗")
                self._log_motor(f"[{ts}]  {data}\n", 'error')
                self._set_status(data)
            elif kind == 'SENT':
                self._log_motor(f"[{ts}]  >> GỬI: {data}\n", 'sent')

    # ----------------------------------------------------------
    #  GỬI LỆNH ĐIỀU KHIỂN MOTOR
    # ----------------------------------------------------------
    def _on_send(self, _event=None):
        cmd = self.cmd_entry.get().strip()
        if cmd:
            self._send_cmd(cmd)
            self.cmd_entry.delete(0, tk.END)

    def _send_cmd(self, cmd: str):
        if self.arduino_ser and self.arduino_ser.is_open:
            try:
                self.arduino_ser.write((cmd + '\n').encode('utf-8'))
                self.arduino_queue.put(('SENT', cmd))
                if self.logging_active and self.csv_writer:
                    t = time.time() - self.t0
                    self.csv_writer.writerow([f"{t:.3f}", "", "", cmd])
            except serial.SerialException as e:
                messagebox.showerror("Lỗi gửi", str(e))
        else:
            messagebox.showwarning("Chưa kết nối",
                                   f"Arduino tại {ARDUINO_PORT} chưa kết nối.\n"
                                   "Kiểm tra lại cổng COM.")

    # ----------------------------------------------------------
    #  BẬT / TẮT GHI LOG
    # ----------------------------------------------------------
    def _toggle_log(self):
        if not self.logging_active:
            fname = f"sensor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.csv_file   = open(fname, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(['time_s', 'A0_V', 'A1_V', 'motor_cmd'])
            self.log_path   = os.path.abspath(fname)
            self.logging_active = True
            self.log_btn.config(text="  DỪNG LOG  ", bg='#a31515')
            self.log_status_label.config(text=f"📄 {os.path.basename(self.log_path)}")
            self._set_status(f"Bắt đầu ghi log: {os.path.basename(self.log_path)}")
        else:
            self.logging_active = False
            if self.csv_file:
                self.csv_file.close()
                self.csv_file   = None
                self.csv_writer = None
            self.log_btn.config(text="  GHI LOG  ", bg='#1e6b3c')
            self.log_status_label.config(text="")
            self._set_status(f"Đã lưu log: {self.log_path}")

    # ----------------------------------------------------------
    #  TIỆN ÍCH
    # ----------------------------------------------------------
    def _log_motor(self, text: str, tag: str = 'recv'):
        self.motor_log.config(state=tk.NORMAL)
        self.motor_log.insert(tk.END, text, tag)
        self.motor_log.see(tk.END)
        self.motor_log.config(state=tk.DISABLED)

    def _set_status(self, msg: str):
        ts = datetime.now().strftime('%H:%M:%S')
        self.status_var.set(f"  {ts}  |  {msg}")

    def _show_ports(self):
        ports = serial.tools.list_ports.comports()
        if not ports:
            messagebox.showinfo("Cổng COM", "Không tìm thấy cổng COM nào.")
            return
        info = "\n".join(f"{p.device:8}  {p.description}" for p in sorted(ports))
        messagebox.showinfo("Cổng COM khả dụng", info)

    def on_close(self):
        self.running = False
        if self.arduino_ser:
            try:
                self.arduino_ser.close()
            except Exception:
                pass
        if self.logging_active and self.csv_file:
            self.csv_file.close()
            print(f"[LOG] Đã lưu: {self.log_path}")
        plt.close('all')
        self.root.destroy()


# ============================================================
#  KHỞI CHẠY
# ============================================================
def main():
    root = tk.Tk()
    app  = DualMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
