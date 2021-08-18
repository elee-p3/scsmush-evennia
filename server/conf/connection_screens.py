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

CONNECTION_SCREEN = """
|b==============================================================|n
MMMMMMMMMMMMMWXko:'..  ...';coOXMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMWN0koc,.. ....;dKWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMNKkl;'....,xNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMWXkl'...lXMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWXx;..cKMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMNx,.cKMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWN0c.lXMWNXKXNWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMWXko:;:,..;c:,'',:lONMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMWOl,.......  .........:kNMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMNKxc......................'l0WMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMWKd:...........................'cxXMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMWKo'.   .......................... .:OWMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMXd'..   ..  .......................  .,dXMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMKxkx;....  ....... .';;;,,,;.....  .  .'cOWMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMM0:..    ..  . .'cddlc;..;oc....   . .',;dNMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMM0;...      .'..,x000OOkl;:c;....   .';',;,l0WMMMMMMMMMMMMMMMM
WMMMMMMMMMMMMMMMMMKc,cd;     .cxocdO00000000Oo'.      .cK0l:ol:kNMMMMMMMMMMMMMMM
lkXMMMMMMMMMMMMMMMNKXW0c.    .o00OkOOOOkkkxxx:...     .dWMXllkxcoKMMMMMMMMMMMMMM
o;:xXMMMMMMMMMMMMMMMMMWXx,'..,cdxdllxxxxxxddc'.,:,.,c,cXMMMKlo0OllOWMMMMMMMMMMMM
Nx;,:xXMMMMMMMMMMMMMMMMN0xocdkxxxdoodoolccc:,;cclc:c00KMMMMWOlx0kocxNMMMMMMMMMMM
MWOc;;ckXMMMMMMMMMMWXKXxcoclkkkxxdlcc:::::::ldddol;:0MMMMMMMWkoxdxxloKWMMMMMMMMM
MMW0occ;ckNMMMMMMMWklol;,clloddoolccccloodddxxddool:oKWMMMMMMNdoddkxolOWMMMMMMMM
MMMMXdclc:lkNMMMMMMKdddccoolcloddddddxkkOkxoc;,'..,col0MMMMMMMKooxdoxdlxXMMMMMMM
MMMMMNxlllccoONMMMMMOlc,':c;,;okO0000Oxlc:,.      .;loKMMMMMMMWklxdloxxodKMMMMMM
MMMMMMWOlllooloONMMMXdll,'..,cok0Okdc;''....      .,cOMMMMMMMMMNdodlclkkoo0WMMMM
MMMMMMMWKollldoldONMWkll,,cc:,;ll:,''','...       ..cONMMMMMMMMM0lllclx0OddkNMMM
MMMMMMMMMXxllloddod0NNd,':ol;..''',,,,..   .'.     ..':kNMMMMMMMWd;cclxKKkxdkXMM
MMMMMMMMMMNkllllodoldkc.,cl,..',,,,,'..  .lo;.       ..,kWMMMMMMM0c:coOXX0xxkxXM
MMMMMMMMMMMW0olllldxo;',,''..',,,,'......oNx,.    ......cXMMMMMMMNo:oxO0OOkdkddK
MMMMMMMMMMMMMKdllloOk;,,,,,,,,,,''.. .'d0XWd'.   ..,c:;,;kWMMMMMMNdcxkOOOOOkOKol
MMMMMMMMMMMMMMNxllodl,,,,,,,,,,'... .;OWMMNl''.....cddol;lXMMMMMWOoooxk00OOkKWXo
MMMMMMMMMMMMMMMWOll:,,,,,,,,,,,'... ..oNWMXc,;.....;cc:;;cKMMMMWOdOklcldxkxkKKOd
MMMMMMMMMMMMMMWN0c'....'',,,'..........:ldd;;c'.. .,cccc:;xNMMWOdOK0xlcclox0OdoO
MMMMMMMMMMMMWk:;'......'''...|ySTAR|n....  .....,l;....cddddocl0MWOdOKKKklclox0kllOW
MMMMMMMMMMMMWO;.............|yCHASER|n.'...  ....:;...'oxooololOWOdkKKK0xlldkOdco0WM
MMMMMMMMMWKxc,...............|ySTORY|n.''.........;'...:dlllldlxOook0KKkdodkklcdXMMM
MMMMMMMMWk,. .. .............|rMUSH|n......''.....,'....:lccld:;llloxxdddxko:lOWMMMM
MMMMMMMMXc. ... .............  ...............'......;:::c,'clccllodxoccxXMMMMMM
MMMMMMMMWd.....  ..'.....  .....  ....'..........  ...,,;;c:;:llooooccdKMMMMMMMM
MMMMMMMMM0;.....  ..............  ....''''''. ..  .'coollc:;'';:cc:cxKWMMMMMMMMM
MMMMMMMMMWXo'.'..................  ..........   ....:oc;;,.....'''lXMMMMMMMMMMMM
MMMMMMMMMMMNo......................  ...... ... ......'...'...'',c0MMMMMMMMMMMMM
MMMMMMMMMMMMXc......'.      ...................  ......'..'',dKXXNMMMMMMMMMMMMMM
MMMMMMMMMMMMMXo,'........... ..'................,cl;.....,::dNMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMWX0Oo'..........................;lolc,....;0WNWMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMWd........................;llc,....';;:0MMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMX:....................';::,........:::xNMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMk'...................''..........lxl:l0MMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMNl............ ............... .cO0dc:kWMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMM0:.........................   .;k0Oo;oNMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMWXx:'.........   .,c:......... 'd00d:cOMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMWX0x;.....  ...oXN0c........'oO0xc:dNMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMXo'........:OXMNl.''...':ok0klcl0MMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMWk:'......dNWMNo,cl;,coccodollcxWMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMN0ko,'cldOXMXl,coc,:olcccccollKMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWOo:'.:o:':do,';;'......';clolkMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMWNX0Okkd,........... .'.  ..... .'ldlOMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMWKxdlclodxl.....    .. ...   ....  .;oONMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMWNK0Okxollc::::;.. ...    .   ..   ...    ;KMMMMMMMMMMMMMMMMMMMM
MMMMMMMMWNXKOxxddoollloool:'....    . .       ..   ... .  .oNMMMMMMMMMMMMMMMMMMM
MMMMMMMWklllccloooollcccc:..   ..   ........  ..           .lXMMMMMMMMMMMMMMMMMM
MMMMMMMMN0OOOkkkkkkkkOOOkd'   .............  .,,          ..'kMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMW0c.         ....,:lxOc     .......;0MMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMW0dlc:;;:cok0KXNWMMMKc.        .'kWMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWWWWMMMMMMMMMMMMXo.    ..;lOWMMMMMMMMMMMMMMMMMMM

 If you have an existing account, connect to it by typing:
      |wconnect <username> <password>|n
 If you need to create an account, type (without the <>'s):
      |wcreate <username> <password>|n

 Enter |whelp|n for more info. |wlook|n will re-show this screen.
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
