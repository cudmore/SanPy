# Author: Robert Cudmore
# Date: 20181118

import os, json

import tkinter
from tkinter import ttk
from tkinter import filedialog

from pprint import pprint

#from bRandomChunks import bRandomChunks
import bDialog

#
# menus
class bMenus:

	def __init__(self, app):

		self.app = app
		self.root  = app.root
		
		"""
		# put this concept back in
		self.showVideoFilesBool = tkinter.BooleanVar()
		self.showVideoFilesBool.set(self.app.configDict['showVideoFiles'])
		
		self.showEventsBool = tkinter.BooleanVar()
		self.showEventsBool.set(self.app.configDict['showEvents'])
		
		self.blindInterfaceBool = tkinter.BooleanVar()
		self.blindInterfaceBool.set(self.app.configDict['blindInterface'])
		"""
		
		# main menu bar
		menubar = tkinter.Menu(self.root)
		
		# app
		appmenu = tkinter.Menu(menubar, name='apple')
		appmenu.add_command(label="About Video Annotate", command=self.about)
		appmenu.add_separator()
		"""
		# put concept back in
		appmenu.add_command(label="Preferences...", command=self.preferences)
		menubar.add_cascade(menu=appmenu)
		"""
		
		# file
		filemenu = tkinter.Menu(menubar, tearoff=0)
		filemenu.add_command(label="Open Folder ...", command=self.open_folder)
		filemenu.add_separator()
		filemenu.add_command(label="Save Options", command=self.save_options)
		filemenu.add_separator()
		'''
		filemenu.add_command(label="Generate Chunks ...", command=self.generateChunks)
		filemenu.add_separator()
		'''
		'''
		filemenu.add_command(label="Save Preferences", command=self.app.savePreferences)
		filemenu.add_separator()
		'''
		#filemenu.add_command(label="Quit", command=self.root.quit)
		filemenu.add_command(label="Quit", command=self.app.onClose) #, accelerator="Command-P")

		# window
		self.windowmenu = tkinter.Menu(menubar, tearoff=0)
		self.windowmenu.add_command(label="Meta Window", command=self.open_meta_window)
		
		"""
		# put this concept back in
		self.windowmenu.add_checkbutton(label="Video Files", onvalue=1, offvalue=False, variable=self.showVideoFilesBool, command=self.togglevideofiles)
		self.windowmenu.add_checkbutton(label="Events", onvalue=1, offvalue=False, variable=self.showEventsBool, command=self.toggleevents)
		self.windowmenu.add_separator()
		self.windowmenu.add_checkbutton(label="Blind Interface", onvalue=1, offvalue=False, variable=self.blindInterfaceBool, command=self.blindInterface)
		"""
		
		# append all menus to main menu bar
		menubar.add_cascade(menu=filemenu, label='File')
		#menubar.add_cascade(menu=chunkmenu, label='Chunks')
		menubar.add_cascade(menu=self.windowmenu, label='Window')

		# display the menu
		self.root['menu'] = [menubar]

	def about(self):
		bDialog.bAboutDialog(self.app.root)
		#self.app.showAboutDialog()

	def open_folder(self):
		print("open a folder with video files")
		path = ''
		#path =  filedialog.askdirectory()
		#print('path:', path)
		self.app.loadFolder(path)

	def save_options(self):
		print('bMenus.save_options()')
		self.app.preferencesSave()
		
	def open_meta_window(self):
		self.app.metaWindow3()
