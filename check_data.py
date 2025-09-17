# check_data.py
import sys

# Add project folder to path to find the 'data' module
sys.path.append('.')

print("--- Checking Appointments Data Source ---")

try:
    from data import data

    # Try to load appointments directly
    appointments = data.load_appointments()

    if appointments and isinstance(appointments, list):
        print(f"\n✅ SUCCESS: Found {len(appointments)} appointments in 'json/appointments.json'.")
        print("\nHere is the first appointment found:")
        print(appointments[0])
    elif isinstance(appointments, list):
        print("\n⚠️  WARNING: The file was read, but it contains 0 appointments.")
        print("Please check that your 'json/appointments.json' file is not empty (e.g., not just '[]').")
    else:
        print("\n❌ ERROR: Could not read the appointments data correctly. It is not a list.")

except ImportError:
    print("\n❌ CRITICAL ERROR: Could not find the 'data/data.py' file.")
    print("Make sure this script is in your main project folder.")
except Exception as e:
    print(f"\n❌ CRITICAL ERROR: An unexpected error occurred: {e}")

print("\n--- Test Finished ---")