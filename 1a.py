import socket
import threading
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import calendar
import os
import json

DATA_FILE = "users.json"
RECEIVED_DIR = "received_entries"
os.makedirs(RECEIVED_DIR, exist_ok=True)

lock = threading.Lock()

# Load data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
        for user in users:
            if "shared_entries" not in users[user]:
                users[user]["shared_entries"] = []
        return users
    return {
        "alice": {"password": "alice123", "tasks": [], "messages": [], "diary_entries": [], "important_dates": {},"shared_entries": []},
        "bob": {"password": "bob123", "tasks": [], "messages": [], "diary_entries": [], "important_dates": {},"shared_entries": []},
        "carol": {"password": "carol123", "tasks": [], "messages": [], "diary_entries": [], "important_dates": {},"shared_entries": []},
        "dave": {"password": "dave123", "tasks": [], "messages": [], "diary_entries": [], "important_dates": {},"shared_entries": []}
    }

# Save data
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

users = load_data()

def handle_client(conn, addr):
    conn.send(b"Enter your username: ")
    username = conn.recv(1024).decode().strip()

    conn.send(b"Enter your password: ")
    password = conn.recv(1024).decode().strip()

    with lock:
        while True:
            if username in users and users[username]["password"] == password:
                break
            conn.send(b"\nInvalid username or password. Try again.\n")
            conn.send(b"Enter your username: ")
            username = conn.recv(1024).decode().strip()
            conn.send(b"Enter your password: ")
            password = conn.recv(1024).decode().strip()

    conn.send(f"\nWelcome, {username}!\n".encode())

    now = datetime.now().strftime("%Y-%m-%d")
    with lock:
        due_tasks = [task for task in users[username]["tasks"] if not task["completed"] and task["date"] <= now]

    if due_tasks:
        conn.send("\nYou have due tasks:\n".encode())
        for i, task in enumerate(due_tasks, 1):
            conn.send(f"{i}. {task['desc']} (Due: {task['date']})\n".encode())

    with lock:
        messages = users[username]["messages"]
        if messages:
            conn.send("\nYou have messages:\n".encode())
            for msg in messages:
                if msg.startswith("__FILE__:"):
                    parts = msg.split(":", 3)
                    sender, filename, content = parts[1], parts[2], parts[3]
                    filepath = os.path.join(RECEIVED_DIR, f"{username}_from_{sender}_{filename}")
                    with open(filepath, "w") as f:
                        f.write(content)
                    conn.send(f"\nReceived diary entry from {sender}, saved as {filepath}\n".encode())
                elif msg.startswith("__SHARED__"):
                    parts = msg.split(":")
                    owner, filename = parts[1], parts[2]
                    if "shared_entries" not in users[username]:
                        users[username]["shared_entries"] = []
                    users[username]["shared_entries"].append({"owner": owner, "filename": filename})
                    conn.send(f"\n{owner} shared a diary entry: {filename}\n".encode())
                else:
                    conn.send(f"- {msg}\n".encode())
            users[username]["messages"].clear()
            save_data()

    while True:
        menu = (
            "\nChoose an option:\n"
            "1. View tasks\n"
            "2. Add a new task\n"
            "3. Mark task as complete\n"
            "4. Send message to another user\n"
            "5. Add important date\n"
            "6. Write diary entry\n"
            "7. Send diary entry to another user\n"
            "8. View received diary entries\n"
            "9. View your calendar\n"
            "10. View other users' calendars\n"
            
            "11. Edit a diary entry\n"
            "12. Edit shared diary entries\n"
            "13. Logout\n"
            "Enter choice: "
        )
        conn.send(menu.encode())
        try:
            choice = conn.recv(1024).decode().strip()
        except:
            break

        with lock:
            if choice == "1":
                tasks = users[username]["tasks"]
                if not tasks:
                    conn.send("\nNo tasks found.\n".encode())
                else:
                    conn.send("\nYour tasks:\n".encode())
                    for i, task in enumerate(tasks, 1):
                        status = "Done" if task["completed"] else "Pending"
                        conn.send(f"{i}. {task['desc']} (Due: {task['date']}) - {status}\n".encode())

            elif choice == "2":
                conn.send(b"\nEnter task description: ")
                desc = conn.recv(1024).decode().strip()
                conn.send(b"Enter due date (YYYY-MM-DD): ")
                date = conn.recv(1024).decode().strip()
                users[username]["tasks"].append({"desc": desc, "date": date, "completed": False})
                save_data()
                conn.send("Task added.\n".encode())

            elif choice == "3":
                tasks = users[username]["tasks"]
                if not tasks:
                    conn.send(b"\nNo tasks to mark.\n")
                    continue
                conn.send(b"\nEnter task number to mark as complete: ")
                try:
                    num = int(conn.recv(1024).decode().strip())
                    if 1 <= num <= len(tasks):
                        tasks[num - 1]["completed"] = True
                        save_data()
                        conn.send("Task marked as complete.\n".encode())
                    else:
                        conn.send("Invalid task number.\n".encode())
                except:
                    conn.send("Invalid input.\n".encode())

            elif choice == "4":
                conn.send(b"Enter recipient username: ")
                recipient = conn.recv(1024).decode().strip()
                if recipient not in users:
                    conn.send(b"User not found.\n")
                    continue
                conn.send(b"Enter message: ")
                msg = conn.recv(1024).decode().strip()
                users[recipient]["messages"].append(f"From {username}: {msg}")
                save_data()
                conn.send(b"Message sent.\n")

            elif choice == "5":
                conn.send(b"Enter date (YYYY-MM-DD): ")
                date = conn.recv(1024).decode().strip()
                conn.send(b"Enter note: ")
                note = conn.recv(1024).decode().strip()
                if date not in users[username]["important_dates"]:
                    users[username]["important_dates"][date] = []
                users[username]["important_dates"][date].append(note)
                save_data()
                conn.send(b"Important date added.\n")

            elif choice == "6":
                conn.send(b"\nEnter your diary entry (end with a single line '.'): \n")
                lines = []
                while True:
                    line = conn.recv(1024).decode().strip()
                    if line == ".":
                        break
                    lines.append(line)
                entry_text = "\n".join(lines)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{username}_{timestamp}.txt"
                with open(filename, "w") as f:
                    f.write(entry_text)
                if "diary_entries" not in users[username]:
                    users[username]["diary_entries"] = []
                users[username]["diary_entries"].append(filename)
                save_data()
                conn.send(f"Diary saved as {filename}\n\n".encode())

            elif choice == "7":
                entries = users[username]["diary_entries"]
                if not entries:
                    conn.send(b"\nNo diary entries to send.\n")
                    continue
                conn.send(b"\nYour diary entries:\n")
                for i, f in enumerate(entries, 1):
                    conn.send(f"{i}. {f}\n".encode())
                conn.send(b"Enter number of diary entry to send: ")
                try:
                    num = int(conn.recv(1024).decode().strip())
                    filename = entries[num - 1]
                except:
                    conn.send(b"Invalid input.\n")
                    continue
                conn.send(b"Enter recipient username: ")
                recipient = conn.recv(1024).decode().strip()
                if recipient not in users:
                    conn.send(b"Recipient not found.\n")
                    continue
                try:
                    users[recipient]["messages"].append(f"__SHARED__:{username}:{filename}")
                    save_data()
                    conn.send(b"Diary entry sent as a shared file.\n")
                except:
                    conn.send(b"Error reading file.\n")

            elif choice == "8":
                files = [f for f in os.listdir(RECEIVED_DIR) if f.startswith(f"{username}_from_")]
                if not files:
                    conn.send(b"\nNo received diary entries found.\n")
                else:
                    conn.send(b"\nReceived diary entries:\n")
                    for f in files:
                        conn.send(f"- {f}\n".encode())

            elif choice == "9":
                important = users[username].get("important_dates", {})
                tasks = users[username].get("tasks", [])
                show_calendar(important, tasks)
                conn.send(b"\nCalendar closed. Press Enter to continue...\n")

            elif choice == "10":
                conn.send(b"Enter username to view their calendar: ")
                other = conn.recv(1024).decode().strip()
                if other not in users:
                    conn.send(b"User not found.\n")
                else:
                    important = users[other].get("important_dates", {})
                    tasks = users[other].get("tasks", [])
                    show_calendar(important, tasks)
                    conn.send(b"\nCalendar closed. Press Enter to continue...\n")

            elif choice == "13":
                conn.send(b"\nLogged out. Bye!\n")
                break

            elif choice == "11":
                entries = users[username].get("diary_entries", [])
                if not entries:
                    conn.send(b"\nNo diary entries to edit.\n")
                    continue
                conn.send(b"\nYour diary entries:\n")
                for i, f in enumerate(entries, 1):
                    conn.send(f"{i}. {f}\n".encode())
                conn.send(b"Enter number of diary entry to edit: ")
                try:
                    num = int(conn.recv(1024).decode().strip())
                    filename = entries[num - 1]
                except:
                    conn.send(b"Invalid input.\n")
                    continue
                if not os.path.exists(filename):
                    conn.send(b"File not found.\n")
                    continue
                with open(filename, "r") as f:
                    lines = f.readlines()
                conn.send(b"\nCurrent content:\n")
                for idx, line in enumerate(lines, 1):
                    conn.send(f"{idx}: {line}".encode())
                conn.send((
                    "\nChoose an action:\n"
                    "1. Edit a line\n"
                    "2. Delete a line\n"
                    "3. Add a new line\n"
                    "4. Save and exit\n"
                ).encode())
                while True:
                    conn.send(b"\nEnter your choice (1-4): ")
                    action = conn.recv(1024).decode().strip()
                    if action == "1":
                        conn.send(b"Enter line number to edit: ")
                        try:
                            line_num = int(conn.recv(1024).decode().strip()) - 1
                            if 0 <= line_num < len(lines):
                                conn.send(b"Enter new content: ")
                                new_line = conn.recv(1024).decode().strip() + "\n"
                                lines[line_num] = new_line
                                conn.send(b"Line updated.\n")
                            else:
                                conn.send(b"Invalid line number.\n")
                        except:
                            conn.send(b"Invalid input.\n")
                    elif action == "2":
                        conn.send(b"Enter line number to delete: ")
                        try:
                            line_num = int(conn.recv(1024).decode().strip()) - 1
                            if 0 <= line_num < len(lines):
                                lines.pop(line_num)
                                conn.send(b"Line deleted.\n")
                            else:
                                conn.send(b"Invalid line number.\n")
                        except:
                            conn.send(b"Invalid input.\n")
                    elif action == "3":
                        conn.send(b"Enter new line content: ")
                        new_line = conn.recv(1024).decode().strip() + "\n"
                        lines.append(new_line)
                        conn.send(b"Line added.\n")

                    elif action == "4":
                        with open(filename, "w") as f:
                            f.writelines(lines)
                        conn.send(b"Diary entry saved.\n")
                        break

                    else:
                        conn.send(b"Invalid action.\n")

            elif choice == "12":
                shared_entries = users[username].get("shared_entries", [])
                if not shared_entries:
                    conn.send(b"\nNo shared entries to edit.\n")
                    continue
                conn.send(b"\nShared diary entries:\n")
                for i, entry in enumerate(shared_entries, 1):
                    conn.send(f"{i}. {entry['filename']} (from {entry['owner']})\n".encode())
                conn.send(b"Enter number of entry to edit: ")
                try:
                    num = int(conn.recv(1024).decode().strip())
                    entry = shared_entries[num - 1]
                except:
                    conn.send(b"Invalid input.\n")
                    continue
                owner, filename = entry["owner"], entry["filename"]
                if not os.path.exists(filename):
                    conn.send(b"Original file not found.\n")
                    continue
                with open(filename, "r") as f:
                    lines = f.readlines()
                conn.send(b"\nCurrent content:\n")
                for idx, line in enumerate(lines, 1):
                    conn.send(f"{idx}: {line}".encode())
                conn.send((
                    "\nChoose an action:\n"
                    "1. Edit a line\n"
                    "2. Delete a line\n"
                    "3. Add a new line\n"
                    "4. Save and exit\n"
                ).encode())

                while True:
                    conn.send(b"\nEnter your choice (1-4): ")
                    action = conn.recv(1024).decode().strip()

                    if action == "1":
                        conn.send(b"Enter line number to edit: ")
                        try:
                            line_num = int(conn.recv(1024).decode().strip()) - 1
                            if 0 <= line_num < len(lines):
                                conn.send(b"Enter new content: ")
                                new_line = conn.recv(1024).decode().strip() + "\n"
                                lines[line_num] = new_line
                                conn.send(b"Line updated.\n")
                            else:
                                conn.send(b"Invalid line number.\n")
                        except:
                            conn.send(b"Invalid input.\n")

                    elif action == "2":
                        conn.send(b"Enter line number to delete: ")
                        try:
                            line_num = int(conn.recv(1024).decode().strip()) - 1
                            if 0 <= line_num < len(lines):
                                lines.pop(line_num)
                                conn.send(b"Line deleted.\n")
                            else:
                                conn.send(b"Invalid line number.\n")
                        except:
                            conn.send(b"Invalid input.\n")

                    elif action == "3":
                        conn.send(b"Enter new line content: ")
                        new_line = conn.recv(1024).decode().strip() + "\n"
                        lines.append(new_line)
                        conn.send(b"Line added.\n")

                    elif action == "4":
                        with open(filename, "w") as f:
                            f.writelines(lines)
                        conn.send(b"Diary entry saved.\n")
                        break

                    else:
                        conn.send(b"Invalid action.\n")

            else:
                conn.send(b"Invalid option.\n")

    conn.close()


def show_calendar(important_dates, due_tasks):
    root = tk.Tk()
    root.title("Calendar")

    year = datetime.now().year
    month = datetime.now().month
    cal = calendar.Calendar()

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for idx, day in enumerate(days):
        tk.Label(root, text=day, font=('Arial', 10, 'bold')).grid(row=0, column=idx)

    important_set = set(important_dates.keys())
    due_task_set = {task["date"] for task in due_tasks if not task["completed"]}

    row = 1
    col = 0
    for day, weekday in cal.itermonthdays2(year, month):
        if day == 0:
            tk.Label(root, text="").grid(row=row, column=col)
        else:
            date_str = f"{year}-{month:02d}-{day:02d}"
            label = tk.Label(root, text=str(day), width=4, height=2, relief="ridge", borderwidth=1)
            if date_str in important_set and date_str in due_task_set:
                label.config(fg="red", bg="yellow")
            elif date_str in important_set:
                label.config(fg="red")
            elif date_str in due_task_set:
                label.config(bg="yellow")
            label.grid(row=row, column=col)

        col += 1
        if col > 6:
            col = 0
            row += 1

    def close_on_q(event):
        root.destroy()

    root.bind('q', close_on_q)
    root.mainloop()


def start_server(host='0.0.0.0', port=1204):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"Server started on {host}:{port}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    start_server()

