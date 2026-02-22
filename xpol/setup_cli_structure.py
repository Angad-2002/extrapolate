import os
import pathlib

def create_cli_structure():
    base_dir = pathlib.Path(__file__).parent / 'cli'
    
    # Create main directories
    directories = [
        '',  # cli root
        'commands',
        'ai',
        'interactive',
        'config',
        'utils',
    ]
    
    # Create directories
    for dir_path in directories:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py in each directory
        init_file = full_path / '__init__.py'
        init_file.touch()

if __name__ == '__main__':
    create_cli_structure()
