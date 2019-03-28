##################################################################################
class bAboutDialog:
	"""
	Opens a modal dialog to set the note of an event
	"""
	def __init__(self, parentApp):

		# to make modal
		#self.grab_set()
		# see: http://effbot.org/tkinterbook/tkinter-dialog-windows.htm
		
		self.top = tkinter.Toplevel(parentApp)
		
		self.top.title('About PiE Video Analysis')
		self.top.geometry('320x240')
		
		myPadding = 10
		
		self.top.grid_rowconfigure(0, weight=1)
		self.top.grid_columnconfigure(0, weight=1)

		myFrame = ttk.Frame(self.top)
		myFrame.grid(row=0, column=0, sticky="nsew", padx=myPadding, pady=myPadding)
		
		platformStr = 'Platform: ' + sys.platform
		ttk.Label(myFrame, text=platformStr, anchor="nw").pack(side="top")

		videoAppVersionStr = 'Video App: ' + VideoApp.__version__
		ttk.Label(myFrame, text=videoAppVersionStr, anchor="nw").pack(side="top")

		pythonVersionStr = 'Python: ' + str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2])
		ttk.Label(myFrame, text=pythonVersionStr, anchor="nw").pack(side="top")
		
		tkinterVersionStr = 'tkinter: ' + str(tkinter.TkVersion)
		ttk.Label(myFrame, text=tkinterVersionStr, anchor="nw").pack(side="top")

		okButton = ttk.Button(myFrame, text="OK", command=self.okButton_Callback)
		okButton.pack(side="top", pady=5)

		#self.top.focus_force() # added
		
		self.top.grab_set()
		
		#self.top.grab_set_global()


	def okButton_Callback(self):
		self.top.destroy() # destroy *this, the modal
