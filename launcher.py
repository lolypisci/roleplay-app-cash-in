import tkinter as tk
from tkinter import messagebox
import subprocess
import webbrowser

def update_code():
    msg = commit_entry.get().strip()
    if not msg:
        messagebox.showwarning("Missing Commit Message", "Please enter a commit message.")
        return
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)
        messagebox.showinfo("Success", "Code updated successfully.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Git error:\n{e}")

def open_teacher_view():
    webbrowser.open("https://roleplay-app-cash-in-production.up.railway.app")

def open_student_app():
    subprocess.Popen(["python", "student_app.py"])

root = tk.Tk()
root.title("Roleplay App Launcher")

tk.Label(root, text="Commit message:").pack(pady=(10, 0))
commit_entry = tk.Entry(root, width=50)
commit_entry.pack(pady=(0, 10))

tk.Button(root, text="Update Code (Git)", command=update_code, width=30).pack(pady=5)
tk.Button(root, text="Open Teacher View", command=open_teacher_view, width=30).pack(pady=5)
tk.Button(root, text="Open Student App", command=open_student_app, width=30).pack(pady=5)

root.mainloop()
