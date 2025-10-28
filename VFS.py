import time

class Inode:
    def __init__(self, inode_id, is_dir=False, permissions=0o755):
        self.id = inode_id
        self.is_dir = is_dir
        self.permissions = permissions  
        self.size = 0
        self.blocks = [] 
        self.created = time.time()
        self.modified = time.time()
        self.owner = "user"  

class File:
    def __init__(self, inode):
        self.inode = inode
        self.data = b""  

    def read(self):
        return self.data.decode('utf-8', errors='ignore')

    def write(self, content):
        self.data = content.encode('utf-8')
        self.inode.size = len(self.data)
        self.inode.modified = time.time()

class Directory:
    def __init__(self, inode):
        self.inode = inode
        self.entries = {}  

    def add_entry(self, name, inode_id):
        self.entries[name] = inode_id

    def remove_entry(self, name):
        if name in self.entries:
            del self.entries[name]

class VirtualFileSystem:
    def __init__(self, total_blocks=1000, block_size=1024):
        self.total_blocks = total_blocks
        self.block_size = block_size
        self.free_blocks = set(range(total_blocks))
        self.inodes = {}  
        self.files = {}   
        self.next_inode_id = 0
        self.current_dir = self._create_root()

    def _create_root(self):
        inode = Inode(self.next_inode_id, is_dir=True)
        self.inodes[self.next_inode_id] = inode
        self.files[self.next_inode_id] = Directory(inode)
        self.next_inode_id += 1
        return self.next_inode_id - 1

    def _allocate_inode(self, is_dir=False, permissions=0o755):
        inode_id = self.next_inode_id
        self.next_inode_id += 1
        inode = Inode(inode_id, is_dir, permissions)
        self.inodes[inode_id] = inode
        return inode

    def _allocate_blocks(self, size):
        needed = (size + self.block_size - 1) // self.block_size
        if len(self.free_blocks) < needed:
            raise Exception("Out of space")
        blocks = []
        for _ in range(needed):
            block = self.free_blocks.pop()
            blocks.append(block)
        return blocks

    def _resolve_path(self, path):
        parts = path.split('/')
        current = self.current_dir
        for part in parts[:-1]:  
            if part == "..":
                current = 0  
            elif part in self.files[current].entries:
                inode_id = self.files[current].entries[part]
                if self.inodes[inode_id].is_dir:
                    current = inode_id
                else:
                    raise Exception(f"'{part}' is not a directory")
            else:
                raise Exception(f"Directory '{part}' not found")
        name = parts[-1]
        return current, name

    def mkdir(self, name):
        if name in self.files[self.current_dir].entries:
            raise Exception("Directory exists")
        inode = self._allocate_inode(is_dir=True)
        self.files[inode.id] = Directory(inode)
        self.files[self.current_dir].add_entry(name, inode.id)

    def touch(self, name):
        if name in self.files[self.current_dir].entries:
            raise Exception("File exists")
        inode = self._allocate_inode(is_dir=False)
        self.files[inode.id] = File(inode)
        self.files[self.current_dir].add_entry(name, inode.id)

    def ls(self):
        dir_obj = self.files[self.current_dir]
        return list(dir_obj.entries.keys())

    def cd(self, path):
        if path == "..":
            if self.current_dir != 0:
                self.current_dir = 0
        elif path in self.files[self.current_dir].entries:
            inode_id = self.files[self.current_dir].entries[path]
            if self.inodes[inode_id].is_dir:
                self.current_dir = inode_id
            else:
                raise Exception("Not a directory")
        else:
            raise Exception("Directory not found")

    def cat(self, name):
        if name not in self.files[self.current_dir].entries:
            raise Exception("File not found")
        inode_id = self.files[self.current_dir].entries[name]
        file_obj = self.files[inode_id]
        if isinstance(file_obj, Directory):
            raise Exception("Is a directory")
        return file_obj.read()

    def write(self, name, content):
        if name not in self.files[self.current_dir].entries:
            raise Exception("File not found")
        inode_id = self.files[self.current_dir].entries[name]
        file_obj = self.files[inode_id]
        if isinstance(file_obj, Directory):
            raise Exception("Is a directory")
        file_obj.write(content)
        size = len(file_obj.data)
        needed = (size + self.block_size - 1) // self.block_size
        if len(file_obj.inode.blocks) < needed:
            additional = self._allocate_blocks(size - len(file_obj.inode.blocks) * self.block_size)
            file_obj.inode.blocks.extend(additional)

    def rm(self, name):
        if name not in self.files[self.current_dir].entries:
            raise Exception("Not found")
        inode_id = self.files[self.current_dir].entries[name]
        for block in self.inodes[inode_id].blocks:
            self.free_blocks.add(block)
        del self.inodes[inode_id]
        del self.files[inode_id]
        self.files[self.current_dir].remove_entry(name)

    def pwd(self):
        return f"/ (inode {self.current_dir})"

    def chmod(self, name, permissions):
        if name not in self.files[self.current_dir].entries:
            raise Exception("Not found")
        inode_id = self.files[self.current_dir].entries[name]
        self.inodes[inode_id].permissions = int(permissions, 8)

    def cp(self, src, dest):
        src_dir, src_name = self._resolve_path(src)
        if src_name not in self.files[src_dir].entries:
            raise Exception("Source file not found")
        src_inode_id = self.files[src_dir].entries[src_name]
        src_file = self.files[src_inode_id]
        if isinstance(src_file, Directory):
            raise Exception("Copying directories not supported yet")
        
        dest_dir, dest_name = self._resolve_path(dest)
        if dest_name in self.files[dest_dir].entries:
            raise Exception("Destination already exists")
        
        new_inode = self._allocate_inode(is_dir=False, permissions=self.inodes[src_inode_id].permissions)
        new_file = File(new_inode)
        new_file.data = src_file.data 
        new_inode.size = len(new_file.data)
        new_inode.blocks = self._allocate_blocks(new_inode.size)  
        self.files[new_inode.id] = new_file
        self.files[dest_dir].add_entry(dest_name, new_inode.id)

    def mv(self, src, dest):
        src_dir, src_name = self._resolve_path(src)
        dest_dir, dest_name = self._resolve_path(dest)
        
        if src_name not in self.files[src_dir].entries:
            raise Exception("Source file not found")
        src_inode_id = self.files[src_dir].entries[src_name]
        src_file = self.files[src_inode_id]
        if isinstance(src_file, Directory):
            raise Exception("Moving directories not supported yet")
        
        if dest_name in self.files[dest_dir].entries:
            raise Exception("Destination already exists")
        
        if src_dir == dest_dir:
            self.files[src_dir].entries[dest_name] = src_inode_id
            del self.files[src_dir].entries[src_name]
        else:
            self.cp(src, dest)
            self.files[src_dir].remove_entry(src_name)

if __name__ == "__main__":
    fs = VirtualFileSystem()
    print("Virtual File System Initialized")
    print("Type 'help' for commands or 'exit' to quit.")
    
    while True:
        try:
            cmd_input = input("VFMS> ").strip()
            if not cmd_input:
                continue
            cmd_parts = cmd_input.split()
            command = cmd_parts[0].lower()
            args = cmd_parts[1:]
            
            if command == "exit":
                print("Exiting VFMS.")
                break
            elif command == "help":
                print("Available commands:")
                print("  mkdir <name>     - Create a directory")
                print("  touch <name>     - Create a file")
                print("  ls               - List current directory contents")
                print("  cd <path>        - Change directory (.. for root)")
                print("  cat <name>       - Display file contents")
                print("  write <name> <content> - Write content to file")
                print("  cp <src> <dest>  - Copy file (e.g., cp file1.txt file2.txt or cp file1.txt dir/file2.txt)")
                print("  mv <src> <dest>  - Move file (e.g., mv file1.txt file2.txt)")
                print("  rm <name>        - Remove file or directory")
                print("  pwd              - Print current directory")
                print("  chmod <name> <perm> - Change permissions (octal, e.g., 755)")
                print("  exit             - Quit the program")
            elif command == "mkdir" and len(args) == 1:
                fs.mkdir(args[0])
                print(f"Directory '{args[0]}' created.")
            elif command == "touch" and len(args) == 1:
                fs.touch(args[0])
                print(f"File '{args[0]}' created.")
            elif command == "ls":
                contents = fs.ls()
                print("Contents:", contents if contents else "Empty")
            elif command == "cd" and len(args) == 1:
                fs.cd(args[0])
                print(f"Changed to {fs.pwd()}")
            elif command == "cat" and len(args) == 1:
                content = fs.cat(args[0])
                print(f"Content of '{args[0]}':\n{content}")
            elif command == "write" and len(args) >= 2:
                name = args[0]
                content = " ".join(args[1:])
                fs.write(name, content)
                print(f"Written to '{name}'.")
            elif command == "cp" and len(args) == 2:
                fs.cp(args[0], args[1])
                print(f"Copied '{args[0]}' to '{args[1]}'.")
            elif command == "mv" and len(args) == 2:
                fs.mv(args[0], args[1])
                print(f"Moved '{args[0]}' to '{args[1]}'.")
            elif command == "rm" and len(args) == 1:
                fs.rm(args[0])
                print(f"'{args[0]}' removed.")
            elif command == "pwd":
                print(fs.pwd())
            elif command == "chmod" and len(args) == 2:
                fs.chmod(args[0], args[1])
                print(f"Permissions for '{args[0]}' changed to {args[1]}.")
            else:
                print("Invalid command or arguments. Type 'help' for usage.")
        except Exception as e:
            print(f"Error: {e}")
