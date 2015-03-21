#!/usr/bin/env python


########################################################################################
########################################################################################
########################################################################################
############## This file need to be out one up directory from here (/junar)#############
########################################################################################
########################################################################################
########################################################################################

import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "junar.microsites.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
