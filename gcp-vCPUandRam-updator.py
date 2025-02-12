import subprocess
import json
import os
import sys
import shutil

def execute_gcloud_command(command):
    try:
        gcloud_path = shutil.which("gcloud")
        if not gcloud_path:
            print("gcloud is not installed or not in PATH. Please configure it.")
            sys.exit(1)

        command[0] = gcloud_path

        process = subprocess.Popen([gcloud_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            print(f"Error checking gcloud version: {stderr.decode()}")
            sys.exit(1)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"Error executing command: {stderr.decode()}")
            sys.exit(1)

        return stdout.decode()

    except Exception as e:
        print(f"Error executing subprocess: {e}")
        sys.exit(1)

def get_instance_details(project_id, server_ip):
    command = [
        "gcloud", "compute", "instances", "list",
        f"--project={project_id}",
        "--format=json"
    ]
    output = execute_gcloud_command(command)

    try:
        instances = json.loads(output)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from gcloud output: {e}")
        sys.exit(1)

    for instance in instances:
        for network_interface in instance.get("networkInterfaces", []):
            if network_interface.get("networkIP") == server_ip:
                return instance

    print(f"No instance found with IP: {server_ip}")
    sys.exit(1)

def select_option(options, prompt):
    for idx, option in enumerate(options, start=1):
        print(f"{idx}. {option}")
    while True:
        try:
            choice = int(input(prompt))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def stop_instance(project_id, instance_name, zone):
    print("Stopping the instance...")
    command = [
        "gcloud", "compute", "instances", "stop", instance_name,
        f"--project={project_id}",
        f"--zone={zone}"
    ]
    execute_gcloud_command(command)
    print("Instance stopped successfully!")

def start_instance(project_id, instance_name, zone):
    print("Starting the instance...")
    command = [
        "gcloud", "compute", "instances", "start", instance_name,
        f"--project={project_id}",
        f"--zone={zone}"
    ]
    execute_gcloud_command(command)
    print("Instance started successfully!")

def list_machine_types(zone):
    command = [
        "gcloud", "compute", "machine-types", "list",
        f"--zones={zone}",
        "--format=json"
    ]
    output = execute_gcloud_command(command)

    try:
        machine_types = json.loads(output)
        return machine_types
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from gcloud output: {e}")
        sys.exit(1)

def main():
    print("=== GCP Instance Updater ===")
    project_id = input("Enter your GCP Project ID: ").strip()
    server_ip = input("Enter the IP address of the server: ").strip()

    instance = get_instance_details(project_id, server_ip)
    print(f"Instance found: {instance['name']} in zone: {instance['zone']}")

    zone = instance["zone"].split("/")[-1]
    instance_name = instance["name"]

    machine_types = list_machine_types(zone)

    # Group machine types by series
    series_dict = {}
    for mt in machine_types:
        series = mt["name"].split("-")[0]
        series_dict.setdefault(series, []).append(mt["name"])

    # Let user select a series
    print("Available series:")
    selected_series = select_option(list(series_dict.keys()), "Select a series: ")

    # Display machine types in the selected series
    print("Available machine types:")
    options = series_dict[selected_series] + ["Custom Configuration"]
    selected_machine_type = select_option(options, "Select a machine type or choose custom configuration: ")

    if selected_machine_type == "Custom Configuration":
        while True:
            try:
                vcpus = int(input("Enter the number of vCPUs: ").strip())
                if vcpus <= 0:
                    print("Number of vCPUs must be greater than 0. Try again.")
                    continue
                break
            except ValueError:
                print("Invalid input. Please enter a valid number for vCPUs.")

        while True:
            try:
                ram = int(input("Enter the amount of RAM (GB): ").strip())
                if ram <= 0:
                    print("RAM must be greater than 0 GB. Try again.")
                    continue
                break
            except ValueError:
                print("Invalid input. Please enter a valid number for RAM.")

        machine_type = f"{selected_series}-custom-{vcpus}-{ram * 1024}"
    else:
        machine_type = selected_machine_type

    print(f"Selected machine type: {machine_type}")

    stop_instance(project_id, instance_name, zone)

    print("Updating instance configuration...")
    update_command = [
        "gcloud", "compute", "instances", "set-machine-type", instance_name,
        f"--project={project_id}",
        f"--zone={zone}",
        f"--machine-type={machine_type}"
    ]
    execute_gcloud_command(update_command)
    print("Instance updated successfully!")

    start_instance(project_id, instance_name, zone)

if __name__ == "__main__":
    main()
