from manager import FileManager

def main():
    file_manager = FileManager()
    while True:
        command = input("Enter command (list, cd, mkdir, rmdir, create, read, write, delete, copy, move, rename, exit): ").strip().split()
        if command[0] == "list":
            file_manager.list_directory()
        elif command[0] == "cd":
            if len(command) == 2:
                file_manager.change_directory(command[1])
            else:
                print("Usage: cd <directory>")
        elif command[0] == "mkdir":
            if len(command) == 2:
                file_manager.create_directory(command[1])
            else:
                print("Usage: mkdir <directory_name>")
        elif command[0] == "rmdir":
            if len(command) == 2:
                file_manager.delete_directory(command[1])
            else:
                print("Usage: rmdir <directory_name>")
        elif command[0] == "create":
            if len(command) == 2:
                file_manager.create_file(command[1])
            else:
                print("Usage: create <file_name>")
        elif command[0] == "read":
            if len(command) == 2:
                file_manager.read_file(command[1])
            else:
                print("Usage: read <file_name>")
        elif command[0] == "write":
            if len(command) >= 3:
                file_manager.write_file(command[1], ' '.join(command[2:]))
            else:
                print("Usage: write <file_name> <content>")
        elif command[0] == "delete":
            if len(command) == 2:
                file_manager.delete_file(command[1])
            else:
                print("Usage: delete <file_name>")
        elif command[0] == "copy":
            if len(command) == 3:
                file_manager.copy_file(command[1], command[2])
            else:
                print("Usage: copy <source_file> <destination_file>")
        elif command[0] == "move":
            if len(command) == 3:
                file_manager.move_file(command[1], command[2])
            else:
                print("Usage: move <source_file> <destination_file>")
        elif command[0] == "rename":
            if len(command) == 3:
                file_manager.rename_file(command[1], command[2])
            else:
                print("Usage: rename <old_name> <new_name>")
        elif command[0] == "exit":
            break
        else:
            print("Invalid command.")

if __name__ == "__main__":
    main()

    