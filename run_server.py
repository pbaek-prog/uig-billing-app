"""Launch script for US Immigration Group Billing System."""
import subprocess
import sys
import os

def main():
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    port = 8501

    # Check if 8501 is likely in use (yr-rent-app), fall back to 8510
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('localhost', 8501)) == 0:
            port = 8510
            print(f"Port 8501 in use, using port {port}")

    print(f"\n{'='*50}")
    print("  US Immigration Group - Billing System")
    print(f"  Starting on http://localhost:{port}")
    print(f"{'='*50}\n")

    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", str(port),
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false",
    ])

if __name__ == "__main__":
    main()
