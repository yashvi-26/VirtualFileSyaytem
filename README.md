This project implements a Virtual File Management System in Python that simulates the core functionalities of a real operating system’s file system — including file and directory creation, navigation, permissions, and basic file operations — all within memory.

🚀 Features

📁 Directory Operations

Create directories (mkdir)

Navigate between directories (cd, pwd)

List contents (ls)

📄 File Operations

Create files (touch)

View contents (cat)

Write or modify file data (write)

Copy or move files (cp, mv)

Delete files or directories (rm)

🔐 Permissions Management

Change file permissions using octal notation (chmod)

⚙️ Filesystem Simulation

Uses inodes, blocks, and metadata (permissions, timestamps, ownership)

Mimics a basic Unix-like filesystem structure

Tracks free/allocated blocks and file sizes dynamically
