activate_this = '/var/www/emmorph_venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

import sys
sys.path.append('/var/www/emmorph_venv/emMorphPyREST')

from humorrest import app as application

sys.stdout = sys.stderr
