# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

from django.conf import settings

from evennia import utils
from world.texts import WORLD_TEXTS

CONNECTION_SCREEN = """
|b==============================================================|n
 {}

 Bienvenido a |g{}|n, versión {}.

 Si ya tienes una cuenta, conéctate escribiendo:
      |wconnect <usuario> <contraseña>|n
 Si necesitas crear una cuenta, escribe (sin los <>):
      |wcreate <usuario> <contraseña>|n

 Si tu nombre de usuario tiene espacios, escríbelo entre comillas.
 Escribe |whelp|n para más información. |wlook|n vuelve a mostrar esta pantalla.
|b==============================================================|n""".format(
    WORLD_TEXTS["system_welcome"], settings.SERVERNAME, utils.get_evennia_version("short")
)
