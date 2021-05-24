import tkinter
from tkinter import filedialog


root = tkinter.Tk()
root.withdraw()
dirname = filedialog.askdirectory(parent=root,initialdir="/",title='Please select a directory')
if dirname:
	print('dirname:', dirname)
else:
	print('cancelled')