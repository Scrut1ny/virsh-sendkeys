# SendKeys

SendKeys is a Bash script that allows you to send keystrokes to a selected virtual machine (domain) managed by `virsh`.

## What It Does

- **Domain Selection:** The script fetches all available domains from `virsh` (skipping header lines) and displays them as a numbered list.
- **User Prompt:** It asks the user to select one of these domains by entering the corresponding number.
- **Keystroke Simulation:** Once a domain is selected, the script reads text input from the user. For each character in the input, it looks up the corresponding USB HID key code from a predefined associative array.
- **Sending Keystrokes:** The script sends the matched key codes to the selected domain using the `sudo virsh send-key` command.

## How to Use

1. **Prerequisites:**  
   - Ensure you have the `virsh` command available (as part of the libvirt package).
   - Run the script with the necessary permissions to use `sudo`.

2. **Run the Script:**  
   Open your terminal and execute:
   ```bash
   ./sendkeys.sh
   ```

3. **Follow On-Screen Prompts:**  
   - Select a domain by entering the corresponding number.
   - Enter the text you would like to send. Each keystroke will be transmitted to the chosen domain.

## Additional Notes

- The script continuously prompts for text input until it is manually terminated.
- It handles a variety of characters including lowercase and uppercase letters, numbers, and special characters by mapping them to their USB HID key codes.

---

https://github.com/user-attachments/assets/f9446345-e9c1-444a-9ad4-00cbd0bfa3af
