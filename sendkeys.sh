#!/usr/bin/env bash
set -euo pipefail

# Function to get available domains using virsh.
get_domains() {
    sudo virsh list --all | awk 'NR>2 {print $2}' | sed '/^$/d'
}

# Function to display domains as numbered options.
display_domains() {
    clear; echo -e "\n  <> Select a domain:\n"
    for i in "${!domains[@]}"; do
        printf "  %d) %s\n" $((i+1)) "${domains[$i]}"
    done
}

# Function to validate user's choice.
validate_choice() {
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#domains[@]}" ]; then
        echo -e "\n  <> Invalid selection."
        exit 1
    fi
}

# Function to send keys via virsh command.
send_keys() {
    local char="$1"
    local holdtime="$2"
    local key_value="${key_map[$char]}"
    read -ra key_array <<< "$key_value"
    sudo virsh send-key "$selected_domain" --codeset usb "${key_array[@]}" --holdtime "$holdtime" > /dev/null 2>&1
}

# Get available domains.
mapfile -t domains < <(get_domains)

if [ ${#domains[@]} -eq 0 ]; then
    echo -e "\n  <> No domains found."
    exit 1
fi

# Ask the user if they want to enable debug mode.
clear; echo -e "\n  <> Enable debug mode? (y/n)\n"
read -r -p "  <> #: " debug_choice
debug=false
if [[ "$debug_choice" =~ ^[Yy]$ ]]; then
    debug=true
    echo -e "\n  <> Debug mode enabled."; sleep 1
else
    echo -e "\n  <> Debug mode disabled."; sleep 1
fi

# Display domains and prompt the user for selection.
display_domains
echo ""; read -r -p "  <> #: " choice
validate_choice

# Set chosen domain based on selection.
selected_domain="${domains[$((choice-1))]}"
echo -e "\n  <> Using domain: $selected_domain"

# Prompt for customizable holdtime
echo -e "\n  <> Enter key press hold time in milliseconds (average human key press hold time is 100-200 ms):\n"
read -r -p "  <> #: " holdtime

# Prompt for customizable pause time after space character
echo -e "\n  <> Enter pause time after space character in milliseconds (recommended pause time is 1000 ms):\n"
read -r -p "  <> #: " pause_time_ms

# Associative array mapping characters to USB HID key codes.
declare -A key_map=(
    # Lowercase alphabet
    ['a']=0x04    ['b']=0x05    ['c']=0x06    ['d']=0x07    ['e']=0x08    ['f']=0x09
    ['g']=0x0A    ['h']=0x0B    ['i']=0x0C    ['j']=0x0D    ['k']=0x0E    ['l']=0x0F
    ['m']=0x10    ['n']=0x11    ['o']=0x12    ['p']=0x13    ['q']=0x14    ['r']=0x15
    ['s']=0x16    ['t']=0x17    ['u']=0x18    ['v']=0x19    ['w']=0x1A    ['x']=0x1B
    ['y']=0x1C    ['z']=0x1D

    # Uppercase alphabet + [SHIFT MODIFIER]
    ['A']="0xe1 0x04"   ['B']="0xe1 0x05"   ['C']="0xe1 0x06"   ['D']="0xe1 0x07"
    ['E']="0xe1 0x08"   ['F']="0xe1 0x09"   ['G']="0xe1 0x0A"   ['H']="0xe1 0x0B"
    ['I']="0xe1 0x0C"   ['J']="0xe1 0x0D"   ['K']="0xe1 0x0E"   ['L']="0xe1 0x0F"
    ['M']="0xe1 0x10"   ['N']="0xe1 0x11"   ['O']="0xe1 0x12"   ['P']="0xe1 0x13"
    ['Q']="0xe1 0x14"   ['R']="0xe1 0x15"   ['S']="0xe1 0x16"   ['T']="0xe1 0x17"
    ['U']="0xe1 0x18"   ['V']="0xe1 0x19"   ['W']="0xe1 0x1A"   ['X']="0xe1 0x1B"
    ['Y']="0xe1 0x1C"   ['Z']="0xe1 0x1D"

    # Numbers (0-9)
    ['1']=0x1E    ['2']=0x1F    ['3']=0x20    ['4']=0x21    ['5']=0x22
    ['6']=0x23    ['7']=0x24    ['8']=0x25    ['9']=0x26    ['0']=0x27

    # Numbers (0-9) + [SHIFT MODIFIER]
    ['!']="0xe1 0x1e"   ['@']="0xe1 0x1f"   ['#']="0xe1 0x20"   ['$']="0xe1 0x21"
    ['%']="0xe1 0x22"   ['^']="0xe1 0x23"   ['&']="0xe1 0x24"   ['*']="0xe1 0x25"
    ['(']="0xe1 0x26"   [')']="0xe1 0x27"

    # Special/symbol characters
    ['-']=0x2D    ['=']=0x2E    ['[']=0x2F    [']']=0x30    ['\']=0x64
    [';']=0x33    ["'"]=0x34    [',']=0x36    ['.']=0x37    ['/']=0x38
    ['`']=0x35

    # Special/symbol characters + [SHIFT MODIFIER]
    ['_']="0xe1 0x2D"   ['+']="0xe1 0x2E"   ['{']="0xe1 0x2F"   ['}']="0xe1 0x30"
    ['|']="0xe1 0x64"   [':']="0xe1 0x33"   ['"']="0xe1 0x34"   ['<']="0xe1 0x36"
    ['>']="0xe1 0x37"   ['?']="0xe1 0x38"   ['~']="0xe1 0x35"

    # Space and control keys
    [' ']=0x2C   ['\n']=0x28   ['\t']=0x2B
)

clear

if [ "$debug" = true ]; then
    echo -e "\n  # [DEBUG] <> [domain: $selected_domain] <> [key press/ms: $holdtime] <> [space pause/ms: $pause_time_ms]"
else
    echo -e "\n  # [domain: $selected_domain] <> [key press/ms: $holdtime] <> [space pause/ms: $pause_time_ms]"
fi

# Main loop for entering text and sending keys
while true; do
    echo ""; read -r -p "  <> Enter text: " user_input

    for (( i=0; i<${#user_input}; i++ )); do
        char="${user_input:$i:1}"
        if [[ -n "${key_map[$char]}" ]]; then
            if [ "$debug" = true ]; then
                echo "Sending key: $char"
            fi
            send_keys "$char" "$holdtime"

            # Check if the character is a space and pause if so
            if [[ "$char" == " " ]]; then
                if [ "$debug" = true ]; then
                    echo "Space detected, pausing..."
                fi
                pause_time=$(awk "BEGIN {print $pause_time_ms/1000}")
                sleep "$pause_time"
            fi
        fi
    done

    # Convert holdtime to seconds for sleep command
    sleep_time=$(awk "BEGIN {print $holdtime/1000}")
    sleep "$sleep_time"
done
