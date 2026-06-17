import sys
import traceback

with open("test_output.txt", "w") as f:
    f.write("Starting test_db.py...\n")
    try:
        f.write("Importing database...\n")
        import database
        f.write("Database imported successfully.\n")
        f.write("Calling get_db_connection...\n")
        conn = database.get_db_connection()
        f.write(f"Connection result: {conn}\n")
    except BaseException as e:
        f.write("An exception occurred:\n")
        traceback.print_exc(file=f)
        f.write(str(e) + "\n")
    f.write("Finished test_db.py.\n")
print("Done writing to file.")
