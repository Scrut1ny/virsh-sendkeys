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
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

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
    lines = output.splitlines()[2:]  # Skip header lines
    return [line.split()[1] for line in lines if len(line.split()) > 1]

def send_keys(domain: str, key_sequence: list[str], holdtime_str: str):
    """Send keypress to a virsh domain using send-key."""
    cmd = ["sudo", "virsh", "send-key", domain, "--codeset", "usb", *key_sequence, "--holdtime", holdtime_str]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

# -------------------------------
# Key Map (Pre-computed constant for maximum performance)
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
        # a–z
        **{chr(c): f"0x{c - 93:02x}" for c in range(97, 123)},
        # A–Z
        **{chr(c): f"0xe1 0x{c - 61:02x}" for c in range(65, 91)},
        # Numbers 1–0
        **{str(i): f"0x{0x1d + i:02x}" for i in range(1, 10)},
        "0": "0x27",
        # Shifted numbers !@#$%^&*()
        **{s: f"0xe1 0x{0x1d + i:02x}" for s, i in zip("!@#$%^&*()", range(1, 11))},
        # Symbols
        **base_symbols,
        # Shifted symbols
        **{shift_pairs[k]: f"0xe1 {v}" for k, v in base_symbols.items() if k in shift_pairs},
        # Space and controls
        " ": "0x2c", "\n": "0x28", "\t": "0x2b",
    }

    # Pre-split all sequences into lists for zero runtime overhead
    return {char: seq.split() for char, seq in key_map_str.items()}

KEY_MAP = _build_key_map()

# -------------------------------
# Worker Thread for sending keys
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
        self.holdtime = holdtime
        self.pause_time = pause_time / 1000  # Convert to seconds
        self.debug = debug
        self._is_running = True

    def run(self):
        try:
            holdtime_str = str(self.holdtime)
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

                send_keys(self.domain, key_sequence, holdtime_str)

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
# Custom SpinBox with styled buttons and arrows
# -------------------------------

class StyledSpinBox(QSpinBox):
    """SpinBox with styled up/down buttons and visible arrows."""
    def __init__(self):
        super().__init__()
        self.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)

# -------------------------------
# Main GUI Application
# -------------------------------

class VirshKeySenderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virsh Key Sender")
        self.setGeometry(100, 100, 550, 600)
        self.setMinimumSize(QSize(450, 530))

        # Apply dark theme
        self.apply_dark_theme()

        # Initialize worker thread
        self.worker_thread = None

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 10)

        # Configuration Group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        config_layout.setSpacing(8)

        # Domain selection
        domain_layout = QHBoxLayout()
        domain_layout.addWidget(QLabel("Domain:"))
        self.domain_combo = QComboBox()
        self.refresh_domains()
        domain_layout.addWidget(self.domain_combo)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_domains)
        refresh_btn.setMaximumWidth(70)
        refresh_btn.setMaximumHeight(28)
        domain_layout.addWidget(refresh_btn)
        config_layout.addLayout(domain_layout)

        # Hold time and Pause time side by side
        timing_layout = QHBoxLayout()
        timing_layout.setSpacing(15)

        # Keypress Hold Time
        holdtime_sub_layout = QHBoxLayout()
        holdtime_sub_layout.setSpacing(5)
        holdtime_sub_layout.addWidget(QLabel("Keypress Hold Time (ms):"))
        self.holdtime_spin = StyledSpinBox()
        self.holdtime_spin.setMinimum(0)
        self.holdtime_spin.setMaximum(5000)
        self.holdtime_spin.setValue(100)
        self.holdtime_spin.setMaximumWidth(70)
        holdtime_sub_layout.addWidget(self.holdtime_spin)
        timing_layout.addLayout(holdtime_sub_layout)

        # Spacebar Pause Time
        pause_sub_layout = QHBoxLayout()
        pause_sub_layout.setSpacing(5)
        pause_sub_layout.addWidget(QLabel("Spacebar Pause Time (ms):"))
        self.pause_spin = StyledSpinBox()
        self.pause_spin.setMinimum(0)
        self.pause_spin.setMaximum(5000)
        self.pause_spin.setValue(300)
        self.pause_spin.setMaximumWidth(70)
        pause_sub_layout.addWidget(self.pause_spin)
        timing_layout.addLayout(pause_sub_layout)

        config_layout.addLayout(timing_layout)

        # Debug mode
        self.debug_check = QCheckBox("Debug Mode")
        config_layout.addWidget(self.debug_check)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Input Group
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(5, 5, 5, 5)
        input_layout.setSpacing(5)
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
        output_layout.setSpacing(5)
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
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        credits_label = QLabel()
        credits_label.setText(
            'Developed by <a href="https://github.com/Scrut1ny" style="color: #0d47a1; text-decoration: none;">Scrut1ny</a> | '
            '<a href="https://github.com/Scrut1ny/virsh-sendkeys" style="color: #0d47a1; text-decoration: none;">Project Repository</a>'
        )
        credits_label.setOpenExternalLinks(True)
        credits_font = QFont()
        credits_font.setPointSize(8)
        credits_label.setFont(credits_font)
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(credits_label)

        layout.addLayout(footer_layout)

        main_widget.setLayout(layout)

    def apply_dark_theme(self):
        """Apply a dark theme to the application."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        QGroupBox {
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        QLabel {
            color: #e0e0e0;
        }
        QComboBox {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 5px;
        }
        QComboBox::drop-down {
            border: none;
            background-color: #2d2d2d;
        }
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #e0e0e0;
            selection-background-color: #0d47a1;
            border: 1px solid #404040;
        }
        QSpinBox {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 3px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #0d47a1;
            border: none;
            width: 20px;
            color: #ffffff;
            font-weight: bold;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #1565c0;
        }
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
            background-color: #0a3d91;
        }
        QTextEdit {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 5px;
        }
        QPushButton {
            background-color: #0d47a1;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 6px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1565c0;
        }
        QPushButton:pressed {
            background-color: #0a3d91;
        }
        QPushButton:disabled {
            background-color: #404040;
            color: #808080;
        }
        QCheckBox {
            color: #e0e0e0;
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #0d47a1;
            border: 1px solid #0d47a1;
            border-radius: 3px;
        }
        """
        self.setStyleSheet(dark_stylesheet)

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
            domain,
            text,
            self.holdtime_spin.value(),
            self.pause_spin.value(),
            self.debug_check.isChecked()
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
