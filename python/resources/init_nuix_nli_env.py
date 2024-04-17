from pathlib import Path
from datetime import datetime

from nuix_nli_lib import edrm
from nuix_nli_lib import nli
from nuix_nli_lib import data_types

from nuix_nli_lib.edrm import EntryInterface, FileEntry, DirectoryEntry, MappingEntry, EDRMBuilder, generate_field
from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry, JSONValueEntry, JSONArrayEntry, JSONObjectEntry, JSONFileEntry
from nuix_nli_lib.nli import NLIGenerator

print("                                                                                                           \n" +
      "                                                                                                           \n" +
      "                                                                                                           \n" +
      "     #########      ###**###                                                                               \n" +
      "   #*#*######**###***######***#                                                                            \n" +
      " #**##**#****###*####*******####                                                                           \n" +
      " **##**#**#########*##*#**#**##*#                                                                          \n" +
      "#**#*#***##*###**#*##**###*#*##*##    ##**#####*****###    ##****        *****#  ##*### ##**#        ##*## \n" +
      "#*#**#**#   #######*##  ##*#**####   #****************##  #*****#       ##***** #*****# #*****#    ##****#*\n" +
      " #*#*#*#**#  #**##*#*  ##*##**#*#    #*******#####******# #*****#       #*****# #******  #*****#  #******# \n" +
      " #####*###### ##***  #*###*#*##*     #******#      ******##*****#       #*****# #******   ##****##*****#   \n" +
      "   #*##**#***#  ## ###*##*##**#      #*****#       *****#*#*****#       #*****# #******     #********##    \n" +
      "    #**##**##**   ***##**##**#       #*****#       ##*****#*****#       #*****# #******      ##*****#      \n" +
      "   ***######**     #####*#*#**#      #*****#       ##*****#*****#       #*****# #******     #********#     \n" +
      " #**##**##**# ##**#  #*##*###*##     #*****#       ##*****##****##      #*****# #******   ##***********#   \n" +
      "#*###*##**#  #**##*#   ####**##*#    #*****#       ##***** #*****### ##*#*****# #******  #******# *#****#  \n" +
      "#*##*#####  #####*#*##  #**##*##*#   #*****#       ##*****  ##**********#*****# #****** ##****#    #*****##\n" +
      "#*#**##*# #####*#*#*##*  #**#**#*#    #*****       #*****#   ###********#****## #****## ****##       ****##\n" +
      "**##*###**#*###* #**###**###**####     ###           ###        ##*###    ####    ###    ###          ##*  \n" +
      " ##*###*####*###**##**#*****#####                                                                          \n" +
      "  #**####*####**#*#*##*#*###**##                                                                           \n" +
      "    ##*#***#*##    ##*****#*##                                                                             \n" +
      "                                                                                                           \n" +
      "                                                                                                           \n" +
      "Nuix Logical Image Builder: the nuix_nli_lib packages and its children are available.  Start with:         \n" +
      " --------------------------                                                                                \n" +
      " |  nli = NLIGenerator()  |                                                                                \n" +
      " --------------------------                                                                                "
)
