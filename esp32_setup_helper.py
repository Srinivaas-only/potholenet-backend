#!/usr/bin/env python3
"""
PotholeNet ESP32-CAM Setup Helper
Automates firmware installation and testing
Usage: python esp32_setup_helper.py
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_status(status, msg):
    colors = {
        'info': Colors.BLUE,
        'success': Colors.GREEN,
        'warning': Colors.YELLOW,
        'error': Colors.RED,
    }
    color = colors.get(status, Colors.RESET)
    prefix = {
        'info': '[ℹ]',
        'success': '[✓]',
        'warning': '[!]',
        'error': '[✗]',
    }
    print(f"{color}{prefix[status]} {msg}{Colors.RESET}")


def run_command(cmd, check=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


class ESPSetupHelper:
    def __init__(self, port="COM3"):
        self.port = port
        self.firmware_file = "esp32_cam_firmware.py"
    
    def check_prerequisites(self):
        """Check if required tools are installed"""
        print_status('info', "Checking prerequisites...")
        
        tools = {
            'esptool.py': 'esptool',
            'ampy': 'adafruit-ampy',
        }
        
        missing = []
        for cmd, package in tools.items():
            success, _, _ = run_command(f"{cmd} --version")
            if success:
                print_status('success', f"{cmd} found")
            else:
                print_status('warning', f"{cmd} not found")
                missing.append(package)
        
        if missing:
            print_status('error', f"Missing tools: {', '.join(missing)}")
            print(f"Install with: pip install {' '.join(missing)}")
            return False
        
        return True
    
    def list_ports(self):
        """List available COM ports"""
        print_status('info', "Available COM ports:")
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            if ports:
                for port in ports:
                    print(f"  - {port.device} ({port.description})")
                return [p.device for p in ports]
            else:
                print_status('warning', "No COM ports found")
                return []
        except ImportError:
            print_status('warning', "pyserial not installed. Run: pip install pyserial")
            return []
    
    def flash_micropython(self, firmware_bin):
        """Flash MicroPython firmware"""
        print_status('info', f"Erasing flash on {self.port}...")
        success, _, err = run_command(
            f"esptool.py --chip esp32 --port {self.port} erase_flash"
        )
        if not success:
            print_status('error', f"Erase failed: {err}")
            return False
        print_status('success', "Flash erased")
        
        print_status('info', f"Flashing MicroPython from {firmware_bin}...")
        success, _, err = run_command(
            f"esptool.py --chip esp32 --port {self.port} write_flash "
            f"-z 0x1000 {firmware_bin}"
        )
        if not success:
            print_status('error', f"Flash failed: {err}")
            return False
        print_status('success', "MicroPython flashed successfully")
        return True
    
    def upload_firmware(self):
        """Upload PotholeNet firmware to device"""
        if not os.path.exists(self.firmware_file):
            print_status('error', f"{self.firmware_file} not found in current directory")
            return False
        
        print_status('info', f"Uploading {self.firmware_file} to {self.port}...")
        success, _, err = run_command(
            f"ampy --port {self.port} put {self.firmware_file} main.py"
        )
        if not success:
            print_status('error', f"Upload failed: {err}")
            return False
        print_status('success', "Firmware uploaded as main.py")
        return True
    
    def list_device_files(self):
        """List files on device"""
        print_status('info', "Files on device:")
        success, out, err = run_command(f"ampy --port {self.port} ls")
        if success:
            print(out)
        else:
            print_status('error', f"Failed to list files: {err}")
    
    def soft_reset(self):
        """Soft reset device"""
        print_status('info', f"Soft resetting {self.port}...")
        reset_script = """
import machine
machine.soft_reset()
"""
        # Write script to temp file and run it
        with open('_reset.py', 'w') as f:
            f.write(reset_script)
        
        success, _, err = run_command(f"ampy --port {self.port} run _reset.py")
        os.remove('_reset.py')
        
        if success:
            print_status('success', "Device reset")
            time.sleep(2)
        else:
            print_status('warning', f"Reset may have failed: {err}")
    
    def configure_firmware(self, ssid, password, host, port):
        """Create configured copy of firmware"""
        if not os.path.exists(self.firmware_file):
            print_status('error', f"{self.firmware_file} not found")
            return False
        
        print_status('info', "Updating firmware configuration...")
        
        with open(self.firmware_file, 'r') as f:
            content = f.read()
        
        # Replace configuration values
        replacements = {
            'WIFI_SSID = "YOUR_SSID"': f'WIFI_SSID = "{ssid}"',
            'WIFI_PASSWORD = "YOUR_PASSWORD"': f'WIFI_PASSWORD = "{password}"',
            'BACKEND_HOST = "192.168.1.100"': f'BACKEND_HOST = "{host}"',
            'BACKEND_PORT = 8000': f'BACKEND_PORT = {port}',
        }
        
        for old, new in replacements.items():
            if old in content:
                content = content.replace(old, new)
                print_status('success', f"Updated: {old.split('=')[0].strip()}")
            else:
                print_status('warning', f"Could not find: {old}")
        
        with open(self.firmware_file, 'w') as f:
            f.write(content)
        
        print_status('success', "Firmware configuration updated")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="PotholeNet ESP32-CAM Setup Helper"
    )
    parser.add_argument(
        '--port', default='COM3', help='COM port (default: COM3)'
    )
    parser.add_argument(
        '--action', choices=['check', 'upload', 'reset', 'list', 'configure', 'test'],
        help='Action to perform'
    )
    parser.add_argument(
        '--firmware', help='MicroPython firmware file to flash'
    )
    parser.add_argument('--ssid', help='WiFi SSID')
    parser.add_argument('--password', help='WiFi password')
    parser.add_argument('--host', default='192.168.1.100', help='Backend host IP')
    parser.add_argument('--port-backend', type=int, default=8000, help='Backend port')
    
    args = parser.parse_args()
    
    helper = ESPSetupHelper(args.port)
    
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"PotholeNet ESP32-CAM Setup Helper")
    print(f"Port: {args.port}")
    print(f"{'='*60}{Colors.RESET}\n")
    
    # Default action: interactive menu
    if not args.action:
        print("Available actions:")
        print("  1. check    - Check prerequisites")
        print("  2. upload   - Upload firmware")
        print("  3. reset    - Soft reset device")
        print("  4. list     - List device files")
        print("  5. configure - Configure WiFi/backend")
        print("  6. test     - Test backend connection")
        print("\nRun: python esp32_setup_helper.py --action <action> --port <port>")
        return
    
    if args.action == 'check':
        if helper.check_prerequisites():
            print_status('success', "All prerequisites installed!")
            helper.list_ports()
    
    elif args.action == 'upload':
        if helper.upload_firmware():
            print_status('info', "Next: python esp32_setup_helper.py --action reset --port {args.port}")
    
    elif args.action == 'reset':
        helper.soft_reset()
    
    elif args.action == 'list':
        helper.list_device_files()
    
    elif args.action == 'configure':
        if args.ssid and args.password:
            if helper.configure_firmware(args.ssid, args.password, args.host, args.port_backend):
                print_status('success', "Firmware configured!")
                print_status('info', f"Now run: python esp32_setup_helper.py --action upload --port {args.port}")
        else:
            print_status('error', "Please provide --ssid and --password")
    
    elif args.action == 'test':
        print_status('info', "Testing backend connection...")
        print(f"Backend URL: http://{args.host}:{args.port_backend}/detect/dual-mode")
        print("\nTo test, upload an image:")
        print(f"  curl -X POST \\")
        print(f"    -F 'image=@test.jpg' \\")
        print(f"    -F 'mode=driving' \\")
        print(f"    http://{args.host}:{args.port_backend}/detect/dual-mode")


if __name__ == "__main__":
    main()
