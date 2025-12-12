import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def convert_bools():
    sql = """
    ALTER TABLE auth_user
    ALTER COLUMN is_superuser TYPE integer USING (CASE WHEN is_superuser THEN 1 ELSE 0 END),
    ALTER COLUMN is_staff TYPE integer USING (CASE WHEN is_staff THEN 1 ELSE 0 END),
    ALTER COLUMN is_active TYPE integer USING (CASE WHEN is_active THEN 1 ELSE 0 END);
    
    ALTER TABLE auth_user ALTER COLUMN is_superuser SET DEFAULT 0;
    ALTER TABLE auth_user ALTER COLUMN is_staff SET DEFAULT 0;
    ALTER TABLE auth_user ALTER COLUMN is_active SET DEFAULT 1;
    """
    
    with connection.cursor() as cursor:
        try:
            print("Executing ALTER TABLE statements...")
            cursor.execute(sql)
            print("Successfully converted auth_user boolean columns to integers.")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == '__main__':
    convert_bools()
