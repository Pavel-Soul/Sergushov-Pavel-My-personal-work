import os
import shutil
from cfg import WORKING_DIRECTORY

class FileManager:
    def __init__(self):
        self.current_directory = WORKING_DIRECTORY

    def list_directory(self):
        try:
            contents = os.listdir(self.current_directory)
            for item in contents:
                print(item)
        except FileNotFoundError:
            print("Directory not found.")

    def change_directory(self, new_directory):
        try:
            if os.path.isabs(new_directory):
                os.chdir(new_directory)
                self.current_directory = new_directory
            else:
                new_path = os.path.join(self.current_directory, new_directory)
                os.chdir(new_path)
                self.current_directory = new_path
            print("Directory changed to:", self.current_directory)
        except FileNotFoundError:
            print("Directory not found.")

    def create_directory(self, directory_name):
        try:
            os.mkdir(os.path.join(self.current_directory, directory_name))
            print("Directory created:", directory_name)
        except FileExistsError:
            print("Directory already exists.")

    def delete_directory(self, directory_name):
        try:
            os.rmdir(os.path.join(self.current_directory, directory_name))
            print("Directory deleted:", directory_name)
        except FileNotFoundError:
            print("Directory not found.")

    def create_file(self, file_name):
        try:
            open(os.path.join(self.current_directory, file_name), 'a').close()
            print("File created:", file_name)
        except FileExistsError:
            print("File already exists.")

    def read_file(self, file_name):
        try:
            with open(os.path.join(self.current_directory, file_name), 'r') as file:
                print(file.read())
        except FileNotFoundError:
            print("File not found.")

    def write_file(self, file_name, content):
        try:
            with open(os.path.join(self.current_directory, file_name), 'w') as file:
                file.write(content)
                print("Content written to file:", file_name)
        except FileNotFoundError:
            print("File not found.")

    def delete_file(self, file_name):
        try:
            os.remove(os.path.join(self.current_directory, file_name))
            print("File deleted:", file_name)
        except FileNotFoundError:
            print("File not found.")

    def copy_file(self, source_file, destination_file):
        try:
            shutil.copy2(os.path.join(self.current_directory, source_file), os.path.join(self.current_directory, destination_file))
            print("File copied:", source_file, "->", destination_file)
        except FileNotFoundError:
            print("File not found.")

    def move_file(self, source_file, destination_file):
        try:
            shutil.move(os.path.join(self.current_directory, source_file), os.path.join(self.current_directory, destination_file))
            print("File moved:", source_file, "->", destination_file)
        except FileNotFoundError:
            print("File not found.")

    def rename_file(self, old_name, new_name):
        try:
            os.rename(os.path.join(self.current_directory, old_name), os.path.join(self.current_directory, new_name))
            print("File renamed:", old_name, "->", new_name)
        except FileNotFoundError:
            print("File not found.")