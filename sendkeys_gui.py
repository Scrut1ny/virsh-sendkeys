#!/usr/bin/env python3
import sys
import subprocess
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSpinBox, QTextEdit, QPushButton, QCheckBox,
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont

# -------------------------------
# Utility Functions
# -------------------------------

def run_cmd(cmd: list[str]) -> str:
    """Run a system command and return its output, or an empty string if it fails."""
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return ""

def get_domains() -> list[str]:
    """Retrieve available domains from virsh."""
    output = run_cmd(["sudo", "virsh", "list", "--all"])
    lines = output.splitlines()[2:]
    return [line.split()[1] for line in lines if len(line.split()) > 1]

def send_keys(domain: str, key_sequence: list[str], holdtime_str: str):
    """Send keypress to a virsh domain using send-key."""
    cmd = ["sudo", "virsh", "send-key", domain, "--codeset", "usb", *key_sequence, "--holdtime", holdtime_str]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

# -------------------------------
# Key Map (Pre-computed constant)
# -------------------------------

def _build_key_map() -> dict[str, list[str]]:
    """Build and pre-compute key map as lists for optimal performance."""
    base_symbols = {
        '-': '0x2d', '=': '0x2e', '[': '0x2f', ']': '0x30', '\\': '0x64',
        ';': '0x33', "'": '0x34', ',': '0x36', '.': '0x37', '/': '0x38', '`': '0x35'
    }
    shift_pairs = {
        '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
        ';': ':', "'": '"', ',': '<', '.': '>', '/': '?', '`': '~'
    }

    key_map_str = {
        **{chr(c): f"0x{c - 93:02x}" for c in range(97, 123)},
        **{chr(c): f"0xe1 0x{c - 61:02x}" for c in range(65, 91)},
        **{str(i): f"0x{0x1d + i:02x}" for i in range(1, 10)},
        "0": "0x27",
        **{s: f"0xe1 0x{0x1d + i:02x}" for s, i in zip("!@#$%^&*()", range(1, 11))},
        **base_symbols,
        **{shift_pairs[k]: f"0xe1 {v}" for k, v in base_symbols.items() if k in shift_pairs},
        " ": "0x2c", "\n": "0x28", "\t": "0x2b",
    }

    return {char: seq.split() for char, seq in key_map_str.items()}

KEY_MAP = _build_key_map()

# -------------------------------
# Worker Thread
# -------------------------------

class KeySenderThread(QThread):
    """Thread to send keys without blocking the UI."""
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, domain: str, text: str, holdtime: int, pause_time: int, debug: bool):
        super().__init__()
        self.domain = domain
        self.text = text
        self.holdtime = str(holdtime)
        self.pause_time = pause_time / 1000
        self.debug = debug
        self._is_running = True

    def run(self):
        try:
            for char in self.text:
                if not self._is_running:
                    break

                key_sequence = KEY_MAP.get(char)
                if not key_sequence:
                    if self.debug:
                        self.progress.emit(f"⚠ Unsupported char skipped: {repr(char)}")
                    continue

                if self.debug:
                    formatted_seq = " + ".join(key_sequence) if len(key_sequence) > 1 else key_sequence[0]
                    self.progress.emit(f"→ Sending: {repr(char)} ({formatted_seq})")

                send_keys(self.domain, key_sequence, self.holdtime)

                if char == " ":
                    if self.debug:
                        self.progress.emit(f"⏸ Space detected → pausing {self.pause_time*1000:.0f}ms...")
                    time.sleep(self.pause_time)

            if self._is_running:
                self.progress.emit("✓ Complete")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def stop(self):
        self._is_running = False

# -------------------------------
# Main GUI Application
# -------------------------------

class VirshKeySenderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virsh SendKeys GUI")
        self.setGeometry(100, 100, 550, 600)
        self.setMinimumSize(QSize(450, 530))

        self.worker_thread = None
        self.apply_dark_theme()
        self.setup_ui()

    def setup_ui(self):
        """Setup UI components."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 10)

        # Configuration Group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        config_layout.setSpacing(10)

        # Top row: Domain and Debug Mode
        top_layout = QHBoxLayout()
        top_layout.setSpacing(5)
        top_layout.setContentsMargins(0, 0, 0, 0)

        domain_layout = QHBoxLayout()
        domain_layout.setSpacing(3)
        domain_layout.addWidget(QLabel("Domain:"))
        self.domain_combo = QComboBox()
        self.refresh_domains()
        self.domain_combo.setMinimumWidth(150)
        domain_layout.addWidget(self.domain_combo)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_domains)
        refresh_btn.setMaximumWidth(65)
        refresh_btn.setMaximumHeight(26)
        domain_layout.addWidget(refresh_btn)
        top_layout.addLayout(domain_layout)

        top_layout.addStretch()

        self.debug_check = QCheckBox("Debug Mode")
        top_layout.addWidget(self.debug_check)

        config_layout.addLayout(top_layout)

        # Bottom row: Timing controls (stacked vertically)
        timing_layout = QVBoxLayout()
        timing_layout.setSpacing(6)

        # Keypress Hold Time
        holdtime_layout = QHBoxLayout()
        holdtime_layout.setSpacing(5)
        holdtime_label = QLabel("Keypress Hold Time (ms):")
        holdtime_label.setMinimumWidth(180)
        holdtime_layout.addWidget(holdtime_label)
        self.holdtime_spin = QSpinBox()
        self.holdtime_spin.setMinimum(0)
        self.holdtime_spin.setMaximum(5000)
        self.holdtime_spin.setValue(100)
        self.holdtime_spin.setMaximumWidth(90)
        self.holdtime_spin.setMinimumHeight(32)
        holdtime_layout.addWidget(self.holdtime_spin)
        holdtime_layout.addStretch()
        timing_layout.addLayout(holdtime_layout)

        # Spacebar Pause Time
        pause_layout = QHBoxLayout()
        pause_layout.setSpacing(5)
        pause_label = QLabel("Spacebar Pause Time (ms):")
        pause_label.setMinimumWidth(180)
        pause_layout.addWidget(pause_label)
        self.pause_spin = QSpinBox()
        self.pause_spin.setMinimum(0)
        self.pause_spin.setMaximum(5000)
        self.pause_spin.setValue(300)
        self.pause_spin.setMaximumWidth(90)
        self.pause_spin.setMinimumHeight(32)
        pause_layout.addWidget(self.pause_spin)
        pause_layout.addStretch()
        timing_layout.addLayout(pause_layout)

        config_layout.addLayout(timing_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Input Group
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(5, 5, 5, 5)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to send to the selected domain...")
        self.text_input.setMinimumHeight(90)
        self.text_input.setMaximumHeight(120)
        input_layout.addWidget(self.text_input)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Output Group
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(5, 5, 5, 5)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(80)
        self.output_text.setMaximumHeight(120)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Button Group
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_text)
        self.send_btn.setMinimumHeight(32)
        button_layout.addWidget(self.send_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_sending)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(32)
        button_layout.addWidget(self.stop_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_output)
        clear_btn.setMinimumHeight(32)
        button_layout.addWidget(clear_btn)

        layout.addLayout(button_layout)

        # Footer with credits
        credits_label = QLabel(
            'Developed by <a href="https://github.com/Scrut1ny" style="color: #0d47a1; text-decoration: none;">Scrut1ny</a> | '
            '<a href="https://github.com/Scrut1ny/virsh-sendkeys" style="color: #0d47a1; text-decoration: none;">Project Repository</a>'
        )
        credits_label.setOpenExternalLinks(True)
        credits_font = QFont()
        credits_font.setPointSize(8)
        credits_label.setFont(credits_font)
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(credits_label)

        main_widget.setLayout(layout)

    def apply_dark_theme(self):
        """Apply dark theme stylesheet."""
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; }
            QGroupBox { color: #e0e0e0; border: 1px solid #404040; border-radius: 5px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
            QLabel { color: #e0e0e0; }
            QComboBox { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #404040; border-radius: 4px; padding: 5px; }
            QComboBox::drop-down { border: none; background-color: #2d2d2d; }
            QComboBox QAbstractItemView { background-color: #2d2d2d; color: #e0e0e0; selection-background-color: #0d47a1; border: 1px solid #404040; }
            QSpinBox { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #404040; border-radius: 4px; padding: 4px; font-size: 14px; }
            QSpinBox::up-button { width: 24px; }
            QSpinBox::down-button { width: 24px; }
            QTextEdit { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #404040; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #0d47a1; color: #ffffff; border: none; border-radius: 4px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #1565c0; }
            QPushButton:pressed { background-color: #0a3d91; }
            QPushButton:disabled { background-color: #404040; color: #808080; }
            QCheckBox { color: #e0e0e0; spacing: 5px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:unchecked { background-color: #2d2d2d; border: 1px solid #404040; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #0d47a1; border: 1px solid #0d47a1; border-radius: 3px; }
        """)

    def refresh_domains(self):
        """Refresh the list of available domains."""
        self.domain_combo.clear()
        domains = get_domains()
        if not domains:
            self.domain_combo.addItem("(No domains found)")
            self.output_text.setText("⚠ No domains found. Make sure virsh is available and sudo access is granted.")
        else:
            self.domain_combo.addItems(domains)

    def send_text(self):
        """Send the text from input to the selected domain."""
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Already sending text. Please wait or click Stop.")
            return

        text = self.text_input.toPlainText()
        if not text:
            QMessageBox.warning(self, "Warning", "Please enter text to send.")
            return

        domain = self.domain_combo.currentText()
        if domain == "(No domains found)":
            QMessageBox.critical(self, "Error", "No valid domain selected.")
            return

        self.output_text.clear()
        self.output_text.append("◄ Starting transmission...\n")

        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.worker_thread = KeySenderThread(
            domain, text, self.holdtime_spin.value(),
            self.pause_spin.value(), self.debug_check.isChecked()
        )
        self.worker_thread.progress.connect(self.on_progress)
        self.worker_thread.finished.connect(self.on_finished)
        self.worker_thread.error.connect(self.on_error)
        self.worker_thread.start()

    def stop_sending(self):
        """Stop the current transmission."""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.output_text.append("\n◄ Stopping transmission...")

    def on_progress(self, message: str):
        """Handle progress updates from worker thread."""
        self.output_text.append(message)

    def on_error(self, error: str):
        """Handle errors from worker thread."""
        self.output_text.append(f"\n✗ Error: {error}")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error}")

    def on_finished(self):
        """Handle worker thread completion."""
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def clear_output(self):
        """Clear the output text area."""
        self.output_text.clear()

# -------------------------------
# Main Entry Point
# -------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VirshKeySenderGUI()
    window.show()
    sys.exit(app.exec())
