# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://bitbucket.org/ned/coveragepy/src/default/NOTICE.txt

import os, sys

# Invoke functions in os and sys so we can see if we measure code there.
x = sys.getfilesystemencoding()
y = os.getcwd()
