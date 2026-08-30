import subprocess
import os

os.chdir(r'C:\Users\THE EYE INFORMATIQUE\Desktop\livestock_marketplace')
result = subprocess.run(['python', 'manage.py', 'compilemessages'], capture_output=True, text=True)
print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)