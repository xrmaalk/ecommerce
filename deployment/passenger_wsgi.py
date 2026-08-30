from config.wsgi import application
import os
import sys
PROJECT_ROOT = "/home/u77326/domains/api.organicemperor.com/private_html/backend"
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
