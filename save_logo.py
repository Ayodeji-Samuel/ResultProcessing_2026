"""
Script to save the EDSU university logo to the correct location.

Usage:
1. Save the EDSU logo image file as 'edsu_logo.png' in this directory
2. Run: python save_logo.py
"""

import os
import shutil

def save_logo():
    # Source file (the EDSU logo you want to use)
    source_files = ['edsu_logo.png', 'university_logo.jpg', 'logo.png']
    destination = os.path.join('app', 'static', 'logos', 'university_logo.jpg')
    
    # Find the logo file
    source = None
    for filename in source_files:
        if os.path.exists(filename):
            source = filename
            break
    
    if not source:
        print("❌ Logo file not found!")
        print(f"   Please save your logo as one of: {', '.join(source_files)}")
        print(f"   in the directory: {os.getcwd()}")
        return False
    
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    # Copy the file
    try:
        shutil.copy2(source, destination)
        print(f"✓ Logo successfully saved to: {destination}")
        print("✓ The logo will now appear in the sidebar and PDF reports")
        return True
    except Exception as e:
        print(f"❌ Error saving logo: {e}")
        return False

if __name__ == '__main__':
    print("EDSU Logo Installation Script")
    print("=" * 50)
    save_logo()
