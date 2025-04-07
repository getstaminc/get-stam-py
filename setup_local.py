import os
import subprocess

def run_command(command):
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {command}")
        exit(1)

# Step 1: Create the local database
print("Creating local database...")
run_command("createdb your_local_db")

# Step 2: Run Alembic migrations
print("Running Alembic migrations...")
run_command("alembic upgrade head")

print("Local database setup complete!")