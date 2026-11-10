"""
Script to update existing users in the database.
Run this once to categorize existing users as either admin-created or demo users.

Since we cannot determine which users were created by signup vs admin,
you'll need to manually classify them. By default, this marks all as admin-created.
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'melonestay.settings')
django.setup()

from accounts.models import AdminAccount

def update_users():
    """
    Update existing users to set is_demo_user flag.
    
    By default, marks all existing users as admin-created (is_demo_user=False).
    If you know specific users that came from signup, you can add logic to mark them as True.
    """
    
    # Get all users that don't have is_demo_user set (NULL or False)
    users = AdminAccount.objects.all()
    
    print(f"\nFound {users.count()} total users in database\n")
    
    # Option 1: Mark ALL existing users as admin-created (safe default)
    admin_count = users.filter(is_demo_user=False).update(is_demo_user=False)
    print(f"✓ Marked all users as admin-created")
    
    # Option 2: If you want to mark specific users as demo users based on criteria:
    # For example, users without license_key might be from signup
    # demo_users = AdminAccount.objects.filter(license_key='')
    # demo_count = demo_users.update(is_demo_user=True)
    # print(f"✓ Marked {demo_count} users as demo users (no license key)")
    
    print("\n" + "="*50)
    print("Summary:")
    print(f"  Admin users (created by superuser): {AdminAccount.objects.filter(is_demo_user=False).count()}")
    print(f"  Demo users (from signup): {AdminAccount.objects.filter(is_demo_user=True).count()}")
    print("="*50 + "\n")

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Updating existing users in database...")
    print("="*50 + "\n")
    
    response = input("This will update all existing users. Continue? (yes/no): ")
    if response.lower() == 'yes':
        update_users()
        print("✓ Update complete!\n")
    else:
        print("✗ Update cancelled\n")
