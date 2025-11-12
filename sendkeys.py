#!/usr/bin/env python3
import subprocess
import sys
import os
import time

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

def clear_screen():
    """Clear the terminal screen (Linux-only)."""
    print("\033[H\033[J", end="")

def prompt(msg: str, default: str | None = None) -> str:
    """Prompt user for input with optional default."""
    value = input(f"{msg.strip()} ").strip()
    return value or (default or "")

def validate_choice(choice: str, max_choice: int) -> int:
    """Validate and return a numeric domain selection."""
    if not choice.isdigit() or not (1 <= int(choice) <= max_choice):
        sys.exit("\n  <> Invalid selection.")
    return int(choice) - 1

def send_keys(domain: str, char: str, holdtime_str: str, key_sequence: list[str], debug_info: str | None = None):
    """Send keypress to a virsh domain using send-key.
    
    Optimized version with pre-computed values to minimize runtime overhead.
    """
    if debug_info:
        print(debug_info)
    
    # Build command with pre-computed values (no string operations in loop)
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

# Pre-computed module-level constant - built once, used many times
KEY_MAP = _build_key_map()

# -------------------------------
# Main Execution
# -------------------------------

def main():
    # Initial setup - single screen clear
    clear_screen()
    domains = get_domains()
    if not domains:
        sys.exit("\n  <> No domains found.")

    # Consolidated input prompts to reduce I/O operations
    print("\n  <> Configuration:")
    debug = prompt("  <> Enable debug mode? (y/n): ").lower() == "y"
    print(f"  <> Debug mode {'enabled' if debug else 'disabled'}.")
    
    print("\n  <> Available domains:")
    for i, domain in enumerate(domains, start=1):
        print(f"  {i}) {domain}")

    selected_domain = domains[validate_choice(prompt("\n  <> Select domain #: "), len(domains))]
    holdtime = int(prompt("  <> Key press hold time in ms (default 100): ", "100"))
    pause_time_ms = int(prompt("  <> Pause after space in ms (default 300): ", "300"))

    # Pre-compute values outside loop for maximum performance
    holdtime_str = str(holdtime)
    pause_time_sec = pause_time_ms / 1000  # Convert once, not per iteration
    
    # Single final screen clear before main loop
    clear_screen()
    print(f"\n  # [domain: {selected_domain}] <> [hold/ms: {holdtime}] <> [space pause/ms: {pause_time_ms}]")
    print("\n  <> Type text to send. Press Ctrl+C to quit.\n")

    try:
        while True:
            user_input = input("  <> Enter text: ")
            
            # Early exit for empty input
            if not user_input:
                continue
            
            # Process each character with optimized hot path
            for char in user_input:
                key_sequence = KEY_MAP.get(char)
                
                # Early exit for unsupported characters
                if not key_sequence:
                    if debug:
                        print(f"  [DEBUG] Unsupported char skipped: {repr(char)}")
                    continue
                
                # Pre-compute debug string outside send_keys if needed
                debug_info = None
                if debug:
                    formatted_seq = " + ".join(key_sequence) if len(key_sequence) > 1 else key_sequence[0]
                    debug_info = f"  [DEBUG] Sending key: {repr(char)} → {formatted_seq}"
                
                send_keys(selected_domain, char, holdtime_str, key_sequence, debug_info)
                
                # Space pause with pre-computed value
                if char == " ":
                    if debug:
                        print("  [DEBUG] Space detected → pausing...")
                    time.sleep(pause_time_sec)
                    
    except KeyboardInterrupt:
        print("\n  <> Exiting...")
        sys.exit(0)

# -------------------------------
if __name__ == "__main__":
    main()
