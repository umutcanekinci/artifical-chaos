#-# Importing Packages #-#
import os

__location__ = os.getcwd()

def SetLocation():

    pass

class FilePath(str):

    def __new__(cls, name: str, folder, extension) -> None:

        if folder:

            return super().__new__(cls, __location__ + "/" + folder + "/" + name + "." + extension)
        
        else:

            return super().__new__(cls, __location__ + "/" + name + "." + extension)       

class ImagePath(FilePath):
    
    def __new__(cls, name: str, folder=None, extension="png") -> None:

        if folder:

            return super().__new__(cls, name, "assets/images/" + folder, extension)
        
        else:

            return super().__new__(cls, name, "assets/images/", extension)

class FontPath(FilePath):
    
    def __new__(cls, name: str, folder=None, extension="ttf") -> None:

        if folder:

            return super().__new__(cls, name, "assets/fonts/" + folder, extension)
        else:

            return super().__new__(cls, name, "assets/fonts/", extension)
    
class SoundPath(FilePath): 
    
    def __new__(cls, name: str, folder=None, extension="ogg") -> None:

        if folder:

            return super().__new__(cls, name, "assets/sounds/" + folder, extension)
        else:

            return super().__new__(cls, name, "assets/sounds/", extension)