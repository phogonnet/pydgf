zip -9 /tmp/pydgf.zip __main__.py pydgf/*
echo '#!/usr/bin/env python3' | cat - /tmp/pydgf.zip > pydgf.py
chmod +x pydgf.py