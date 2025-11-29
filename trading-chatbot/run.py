import uvicorn
import sys
import os
from pathlib import Path

# Add current directory to sys.path
# Ensure we are adding the directory containing 'src'
current_dir = Path(__file__).parent.resolve()
sys.path.append(str(current_dir))

if __name__ == "__main__":
    # Change working directory to the script's directory
    os.chdir(current_dir)
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
