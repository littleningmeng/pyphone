# -*- coding: utf-8 -*-
import os
import locale
import gettext

os.environ["LANG"] = locale.getdefaultlocale()[0]
_ = gettext.translation("lang", "locale", fallback=True).gettext

