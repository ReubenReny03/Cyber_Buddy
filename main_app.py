import requests
import json
from typing import Dict, Optional
import time
import sys
import os
from datetime import datetime
import os.path
from pathlib import Path
from typing import List
import readline  # Add this at the top with other imports

class OllamaChat:
    def __init__(self, model_name: str = "lillyv2", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.history = []
        self.context = ""
        self.current_path = os.path.expanduser("~")  # Start from user's home directory
        
    def generate_response(self, prompt: str, stream: bool = True) -> str:
        """Generate a response from the model"""
        # Dynamically adjust the prompt based on whether code analysis is needed
        code_keywords = ["fix", "improve", "update", "change", "modify", "code", "error", "bug"]
        is_code_request = any(keyword in prompt.lower() for keyword in code_keywords)
        
        if is_code_request:
            system_prompt = (
                "You are a code-focused AI assistant. When given code, provide direct code improvements "
                "rather than suggestions. Format all code responses in markdown code blocks with the "
                "appropriate language identifier. Show only the relevant code sections that need changes."
            )
        else:
            system_prompt = (
                "You are an AI assistant analyzing files and providing information. "
                "Give clear, concise explanations and analysis based on the file content."
            )

        full_prompt = f"{system_prompt}\n\nContext (loaded file):\n{self.context}\n\nUser Question: {prompt}"
        
        url = f"{self.base_url}/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": stream
        }
        
        # DEBUG: Log the request data (remove this in production)
        # print("\n=== DEBUG: Request Data ===")
        #print(f"URL: {url}")
        #print(f"Headers: {headers}")
        #print(f"Data: {json.dumps(data, indent=2)}")
        #print("=========================\n")
        
        try:
            if stream:
                return self._handle_streaming_response(url, headers, data)
            else:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()["response"]
                
        except requests.exceptions.RequestException as e:
            print(f"\nError: {str(e)}")
            return "Error: Failed to communicate with Ollama server"
            
    def _handle_streaming_response(self, url: str, headers: Dict, data: Dict) -> str:
        """Handle streaming response from the model"""
        full_response = []
        try:
            with requests.post(url, headers=headers, json=data, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        json_response = json.loads(line)
                        chunk = json_response.get("response", "")
                        full_response.append(chunk)
                        print(chunk, end="", flush=True)
                        
                print("\n")  # New line after response
                return "".join(full_response)
                
        except requests.exceptions.RequestException as e:
            print(f"\nError: {str(e)}")
            return "Error: Failed to communicate with Ollama server"
            
    def save_history(self, filename: Optional[str] = None) -> None:
        """Save chat history to a file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_history_{timestamp}.txt"
            
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for entry in self.history:
                    f.write(f"{entry['role']}: {entry['content']}\n")
            print(f"\nChat history saved to {filename}")
        except IOError as e:
            print(f"\nError saving chat history: {str(e)}")
            
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def load_file_content(self, file_path: str) -> bool:
        """Load content from a file to use as context"""
        try:
            # Construct the full path using current_path
            full_path = os.path.join(self.current_path, file_path)
            
            if not os.path.exists(full_path):
                print(f"\nError: File '{full_path}' does not exist")
                return False
                
            with open(full_path, 'r', encoding='utf-8') as f:
                self.context = f.read()
            print(f"\nLoaded content from: {full_path}")
            return True
        except Exception as e:
            print(f"\nError loading file: {str(e)}")
            return False

    def get_directory_info(self, path: str = None) -> str:
        """Get information about files and directories in the specified path"""
        try:
            target_path = path or self.current_path
            entries = os.listdir(target_path)
            
            info = f"\nDirectory contents of {target_path}:\n"
            files = []
            dirs = []
            
            for entry in entries:
                full_path = os.path.join(target_path, entry)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    files.append(f"📄 {entry} ({self.format_size(size)})")
                else:
                    dirs.append(f"📁 {entry}/")
            
            return info + "\nDirectories:\n" + "\n".join(sorted(dirs)) + \
                   "\n\nFiles:\n" + "\n".join(sorted(files))
        except Exception as e:
            return f"\nError reading directory: {str(e)}"
                   
    def format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    
    def change_directory(self, path: str) -> bool:
        """Change current working directory"""
        try:
            new_path = os.path.abspath(os.path.join(self.current_path, path))
            if os.path.exists(new_path) and os.path.isdir(new_path):
                self.current_path = new_path
                print(f"\nChanged directory to: {new_path}")
                return True
            else:
                print(f"\nError: Directory '{path}' does not exist")
                return False
        except Exception as e:
            print(f"\nError changing directory: {str(e)}")
            return False

    def create_directory(self, dirname: str) -> bool:
        """Create a new directory"""
        try:
            new_dir = os.path.join(self.current_path, dirname)
            os.makedirs(new_dir, exist_ok=True)
            print(f"\nCreated directory: {new_dir}")
            return True
        except Exception as e:
            print(f"\nError creating directory: {str(e)}")
            return False

    def open_editor(self, filename: str) -> bool:
        """Open file in text editor"""
        try:
            filepath = os.path.join(self.current_path, filename)
            if os.name == 'nt':  # Windows
                os.system(f"notepad {filepath}")
            else:  # Unix-like
                os.system(f"nano {filepath}")
            return True
        except Exception as e:
            print(f"\nError opening editor: {str(e)}")
            return False

    def run_npm_command(self, command: str) -> bool:
        """Run npm commands"""
        try:
            full_command = f"npm {command}"
            print(f"\nExecuting: {full_command}")
            os.system(full_command)
            return True
        except Exception as e:
            print(f"\nError executing npm command: {str(e)}")
            return False

    def run_npx_command(self, command: str) -> bool:
        """Run npx commands"""
        try:
            full_command = f"npx {command}"
            print(f"\nExecuting: {full_command}")
            os.system(full_command)
            return True
        except Exception as e:
            print(f"\nError executing npx command: {str(e)}")
            return False

    def setup_tab_completion(self):
        """Setup tab completion for file and directory names"""
        def complete(text, state):
            # Get the current line buffer and cursor position
            line = readline.get_line_buffer()
            
            # Handle different commands
            if line.startswith('cd ') or line.startswith('load ') or line.startswith('nano '):
                cmd = line.split()[0]
                # Get the path being typed (everything after the command)
                path = ' '.join(line.split()[1:])
                
                # Get the directory to look in
                if path.startswith('/'):
                    base_dir = '/'
                else:
                    base_dir = self.current_path
                
                # Get all matching files/directories
                try:
                    if not text:  # If no text typed yet, show all files
                        completions = os.listdir(base_dir)
                    else:
                        # Get the directory part and file part of what's typed
                        dir_part = os.path.dirname(text)
                        file_part = os.path.basename(text)
                        
                        if dir_part:
                            search_dir = os.path.join(base_dir, dir_part)
                        else:
                            search_dir = base_dir
                            
                        completions = [f for f in os.listdir(search_dir)
                                     if f.startswith(file_part)]
                        
                        # Add directory part back to completions
                        if dir_part:
                            completions = [os.path.join(dir_part, f) for f in completions]
                            
                    # Add trailing slash to directories
                    completions = [f + ('/' if os.path.isdir(os.path.join(base_dir, f)) else ' ')
                                 for f in completions]
                except OSError:
                    completions = []
                
                try:
                    return completions[state]
                except IndexError:
                    return None
            
            return None
        
        readline.parse_and_bind('tab: complete')
        readline.set_completer(complete)
        readline.set_completer_delims(' \t\n;')

def main():
    print("Initializing Ollama Chat...")
    chat = OllamaChat()
    chat.setup_tab_completion()
    print(f"Chat initialized with model: {chat.model_name}")
    print("\nType 'quit', 'exit', or press Ctrl+C to end the chat")
    print("Type 'save' to save the chat history")
    print("Type 'clear' to clear the screen")
    print("Type 'load <file_path>' to load content from a file")
    print("Type 'ls' to list current directory contents")
    print("Type 'cd <path>' to change directory")
    print("Type 'mkdir <dirname>' to create a directory")
    print("Type 'nano <filename>' to edit a file")
    print("Type 'npm <command>' to run npm commands")
    print("Type 'npx <command>' to run npx commands")
    print("\n" + "="*50 + "\n")
    
    try:
        while True:
            user_input = input(f"\n[{chat.current_path}] You: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                break
            elif user_input.lower() == 'save':
                chat.save_history()
                continue
            elif user_input.lower() == 'clear':
                chat.clear_screen()
                continue
            elif user_input.lower() == 'ls':
                print(chat.get_directory_info())
                continue
            elif user_input.lower().startswith('cd '):
                path = user_input[3:].strip()
                chat.change_directory(path)
                continue
            elif user_input.lower().startswith('load '):
                file_path = user_input[5:].strip()
                chat.load_file_content(file_path)
                continue
            elif user_input.lower().startswith('mkdir '):
                dirname = user_input[6:].strip()
                chat.create_directory(dirname)
                continue
            elif user_input.lower().startswith('nano '):
                filename = user_input[5:].strip()
                chat.open_editor(filename)
                continue
            elif user_input.lower().startswith('npm '):
                command = user_input[4:].strip()
                chat.run_npm_command(command)
                continue
            elif user_input.lower().startswith('npx '):
                command = user_input[4:].strip()
                chat.run_npx_command(command)
                continue
            elif not user_input:
                continue
                
            chat.history.append({"role": "user", "content": user_input})
            
            print("\nAssistant: ", end="")
            response = chat.generate_response(user_input)
            chat.history.append({"role": "assistant", "content": response})
            
    except KeyboardInterrupt:
        print("\n\nExiting chat...")
    
    if chat.history:
        save = input("\nWould you like to save the chat history? (y/n): ").lower()
        if save == 'y':
            chat.save_history()
    
    print("\nThank you for using Ollama Chat!")

if __name__ == "__main__":
    main()
