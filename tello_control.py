import threading
import cv2
import time
import os
import csv
from djitellopy import tello
from datetime import datetime

# dictionary berisi command movement pada djitellopy, disesuaikan dengan nama fungsi pada library djitellopy
MOVEMENT_COMMANDS = {
    'forward': 'move_forward',
    'back': 'move_backward',
    'left': 'move_left',
    'right': 'move_right',
    'rotateclock': 'rotate_clockwise',
    'rotatecounter': 'rotate_counter_clockwise'
}

MIN_DISTANCE = 20
MAX_DISTANCE = 500
MIN_ANGLE = 1
MAX_ANGLE = 360

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def log_telemetry(drone, stop_event, telemetry_log):
    # Logging telemetry data, diambil dari drone class djitellopy
    while not stop_event.is_set():
        try:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "battery": drone.get_battery(),
                "height": drone.get_height(),
                "altitude": drone.get_distance_tof(),
                "barometer": drone.get_barometer(),
                "temperature": drone.get_temperature(),
                "pitch": drone.get_pitch(),
                "roll": drone.get_roll(),
                "yaw": drone.get_yaw(),
                "speed_x": drone.get_speed_x(),
                "speed_y": drone.get_speed_y(),
                "speed_z": drone.get_speed_z()
            }

            telemetry_log.append(snapshot)

            # Display on terminal
            clear_terminal()
            time.sleep(1)

        except Exception as e:
            print(f"Telemetry error: {e}")
            stop_event.set()

def save_telemetry_to_csv(log, filename="telemetry_log.csv"):
    # Setelah penerbangan, simpan pada csv
    if not log:
        print("No telemetry data to save.")
        return

    keys = log[0].keys()
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(log)
    print(f"\n Telemetry log saved to: {filename}")

def process_tello_video(drone, stop_event):
    # Function process video menggunakan cv2
    while not stop_event.is_set():
        frame = drone.get_frame_read().frame
        if frame is not None:
            cv2.imshow("Tello Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_event.set()
            break
    cv2.destroyAllWindows()

def send_command(drone, stop_event):
    # Kirim command pada drone
    while not stop_event.is_set():
        try:
            command = input("\n> ").strip().lower()
            if not command:
                continue

            if command == 'exit':
                stop_event.set()
                drone.land()
                break
            elif command == 'help':
                print_help()
            else:
                process_command(drone, command)
        except Exception as e:
            print(f"Command error: {e}")

def process_command(drone, command_str):
    tokens = command_str.split()

    if len(tokens) == 2 and tokens[1].isdigit():
        cmd, val = tokens[0], int(tokens[1])
        method_name = MOVEMENT_COMMANDS.get(cmd)

        if not method_name:
            print(f"Unknown command: {cmd}")
            return

        if "rotate" in cmd and not (MIN_ANGLE <= val <= MAX_ANGLE):
            print("Angle must be between 1 and 360 degrees.")
            return
        elif not "rotate" in cmd and not (MIN_DISTANCE <= val <= MAX_DISTANCE):
            print("Distance must be between 20 and 500 cm.")
            return

        getattr(drone, method_name)(val)

    elif len(tokens) == 1:
        cmd = tokens[0]
        if cmd == 'takeoff':
            drone.takeoff()
        elif cmd == 'land':
            drone.land()
        else:
            print(f"Unknown command: {cmd}")
    else:
        print("Invalid command format.")

def print_help():
    print("""
Available Commands:
  takeoff               - Drone takes off
  land                  - Drone lands
  forward <cm>          - Move forward (20–500 cm)
  back <cm>             - Move backward (20–500 cm)
  left <cm>             - Move left (20–500 cm)
  right <cm>            - Move right (20–500 cm)
  rotateclock <deg>     - Rotate clockwise (1–360°)
  rotatecounter <deg>   - Rotate counter-clockwise (1–360°)
  help                  - Show this help message
  exit                  - Land and exit
""")

def main():
    drone = tello.Tello()
    stop_event = threading.Event()
    telemetry_log = []

    try:
        drone.connect()
        drone.streamon()

        video_thread = threading.Thread(target=process_tello_video, args=(drone, stop_event))
        telemetry_thread = threading.Thread(target=telemetry_panel, args=(drone, stop_event, telemetry_log))

        video_thread.start()
        telemetry_thread.start()

        send_command(drone, stop_event)

        video_thread.join()
        telemetry_thread.join()

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt - landing...")
        stop_event.set()
        drone.land()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            drone.streamoff()
            drone.end()
        except:
            pass
        save_telemetry_to_csv(telemetry_log)
        print("Drone session ended.")

if __name__ == "__main__":
    main()
