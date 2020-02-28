@echo off
rem 先得到po文件，然后编辑lang_tmp.po
rem 执行 msgfmt -o lang.mo lang.po 得到lang.mo文件，拷贝到locale/LANG/LC_MESSAGES/lang.mo
cd .. && xgettext -o locale/lang_tmp.po main_widget.py
echo ok
