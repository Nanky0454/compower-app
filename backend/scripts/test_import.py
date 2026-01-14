
import sys
import os

# Add the backend directory to sys.path
sys.path.append('/home/korato/Projects/MonoRepoCompower/backend')

try:
    from app import create_app
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
