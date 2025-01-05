import os
import hashlib
import subprocess
import re
from datetime import datetime
import ntplib

# from ui.app import start_app # for run in console: e.g. `python license.py`
from EasyDiceApply.ui.app import start_app # for compile to exe

# Function to get the CPU ID using WMIC (Windows specific)
def get_cpu_id():
    try:
        output = subprocess.check_output(['wmic', 'cpu', 'get', 'ProcessorId'], shell=True)
        cpu_id = output.decode().split('\n')[1].strip()
        return cpu_id
    except Exception as e:
        print(f"Error fetching CPU ID: {e}")
        return None

# Function to get MAC address of the first network interface
def get_mac_address():
    try:
        interfaces = os.popen('getmac').read().splitlines()
        for interface in interfaces:
            mac = re.search(r'[A-F0-9]{2}(-[A-F0-9]{2}){5}', interface)
            if mac:
                return mac.group(0)
    except Exception as e:
        print(f"Error fetching MAC Address: {e}")
    return None

# Function to generate a license key by hashing the machine ID
def generate_license_key(machine_id):
    secret = 'em83v07m341049mc!@(*UIJpewimj_#(*_M51910948Y'
    return hashlib.sha256((machine_id + secret).encode()).hexdigest()

# Function to validate the license key
def validate_license(machine_id, stored_license):
    generated_key = generate_license_key(machine_id)
    return generated_key == stored_license

# Function to get current internet date-time
def get_current_internet_datetime(length=15):
    try:
        client = ntplib.NTPClient()
        response = client.request('time.google.com', version=3)
        now = datetime.fromtimestamp(response.tx_time)
        return now.strftime('%Y%m%d%H%M%S')[:length]
    except Exception as e:
        print(f"Error fetching internet time: {e}")
        return None

# Function to calculate date difference in days
def calculate_date_difference(date1, date2):
    try:
        formatted_date1 = datetime.strptime(date1, "%Y%m%d")
        formatted_date2 = datetime.strptime(date2, "%Y%m%d")
        difference = abs((formatted_date1 - formatted_date2).days)
        return difference
    except ValueError as e:
        print(f"Error calculating date difference: {e}")
        return None

# Main function to perform license validation
def main():
    cpu_id = get_cpu_id()
    mac_address = get_mac_address()

    if not cpu_id or not mac_address:
        print('Failed to fetch CPU ID or MAC address.')
        return

    machine_id = f"{cpu_id}-{mac_address}"

    try:
        with open('license.key', 'r') as file:
            stored_license = file.read().strip()

        expired_date = int(stored_license[-10:]) // 77
        internet_datetime = get_current_internet_datetime(8)
        
        if not internet_datetime or int(expired_date) < int(internet_datetime):
            print('License is expired.')
            print('Your Machine ID:', machine_id)
            return

        days_left = calculate_date_difference(str(expired_date), internet_datetime)
        stored_license = stored_license[:-10]
    except Exception as e:
        print(f"Unable to open license file: {e}")
        print('Your Machine ID:', machine_id)
        return

    if validate_license(machine_id, stored_license):
        print(f"License will expire in {days_left} days.\n")
        try:
            start_app()
        except OSError as e:
            print(e)
            
        # Launch server or required functionality
        # Example: os.system('python server.py')
    else:
        print('License is invalid.')
        print('Your Machine ID:', machine_id)
        with open('machineNumber.txt', 'w') as file:
            file.write(machine_id)
        print('Your Machine Number saved to machineNumber.txt')

if __name__ == "__main__":
    main()
