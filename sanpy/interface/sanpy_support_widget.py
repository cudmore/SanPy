import requests
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt

from sanpy.sanpyLogger import get_logger, getLoggerFile

logger = get_logger(__name__)

def send_support_email(mail_to: str, message: str) -> dict:
    """
    Send a support email to the developer.

    Args:
        mail_to (str): The email address of the recipient.
        message (str): The message to send.

    Returns:
        dict: A dictionary containing the status and message.
        - status: "ok" if the email was sent successfully, "error" otherwise.
    """
    data = {
        "email": mail_to,
        "message": message
    }
    response = requests.post(
        "https://formspree.io/f/mwpqrayn",
        data=data,
        headers={"Accept": "application/json"},
        timeout=5
    )

    if response.status_code == 200:
        return {"status": "ok", "message": "Support message sent!"}
    else:
        return {"status": "error", "message": response.text}

class SupportDialog(QDialog):
    """
    Modal dialog for sending support emails.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send Support Email")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        
        # Email field
        email_layout = QHBoxLayout()
        email_label = QLabel("Your Email:")
        self.email_edit = QLineEdit()
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_edit)
        layout.addLayout(email_layout)
        
        # Institution field
        inst_layout = QHBoxLayout()
        inst_label = QLabel("Institution:")
        self.inst_edit = QLineEdit()
        inst_layout.addWidget(inst_label)
        inst_layout.addWidget(self.inst_edit)
        layout.addLayout(inst_layout)
        
        # Lab field
        lab_layout = QHBoxLayout()
        lab_label = QLabel("Lab:")
        self.lab_edit = QLineEdit()
        lab_layout.addWidget(lab_label)
        lab_layout.addWidget(self.lab_edit)
        layout.addLayout(lab_layout)
        
        # Message field
        message_label = QLabel("Message (optional):")
        layout.addWidget(message_label)
        
        self.message_edit = QTextEdit()
        self.message_edit.setMinimumHeight(200)
        layout.addWidget(self.message_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_email)
        self.send_button.setDefault(True)  # Make Send the default button
        button_layout.addWidget(self.send_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def send_email(self):
        """Send the support email."""
        # Get form data
        from_email = self.email_edit.text().strip()
        from_institution = self.inst_edit.text().strip()
        from_lab = self.lab_edit.text().strip()
        user_message = self.message_edit.toPlainText().strip()
        
        # Validate required fields
        if not from_email:
            QMessageBox.warning(self, "Missing Email", "Please enter your email address.")
            return
            
        if not user_message:
            user_message = "No message provided"
        
        # Get log file content
        try:
            logFile = open(getLoggerFile(), 'r').read()
        except Exception as e:
            logger.error(f"Could not read log file: {e}")
            logFile = "Could not read log file"
        
        # Get system info from SanPyApp
        from sanpy.interface.sanpy_app import SanPyApp
        app = SanPyApp.instance()
        version_info = app._getVersionInfo()
        system_info_str = "\n".join([f"{k}: {v}" for k, v in version_info.items()])
        
        # Construct message
        message = f"""
From: {from_email}
Institution: {from_institution}
Lab: {from_lab}

User Message: {user_message}

System Info:
{system_info_str}

SanPy Log File:
{logFile}"""
        
        # Send email
        try:
            _ret = send_support_email(mail_to="mapmanagercore@gmail.com", message=message)
            
            if _ret["status"] == "ok":
                QMessageBox.information(self, "Success", "Support message sent successfully to 'mapmanagercore@gmail.com'.\nWe will get back soon!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", f"Failed to send message: {_ret['message']}")
                
        except Exception as e:
            logger.error(f"Error sending support email: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while sending the message: {str(e)}")

def show_support_dialog(parent=None):
    """
    Show the support dialog.
    
    Args:
        parent: Parent widget for the dialog
        
    Returns:
        bool: True if the dialog was accepted (email sent), False if cancelled
    """
    dialog = SupportDialog(parent)
    return dialog.exec_() == QDialog.Accepted

def send_example():
   from_email = 'robert.cudmore@gmail.com'
   from_institution = 'UCDavis'
   from_lab = 'Cudmore Lab'   
   
   user_message = 'Hi, having this problem'
   
   # open log file and make a str
   logFile = open(getLoggerFile(), 'r').read()
   
   message=f"""
    From: {from_email}
    Institution: {from_institution}
    Lab: {from_lab}

    User Message: {user_message}

    SanPy Log File:
    {logFile}"""

   print(message)
   
   if 0:
      _ret = send_support_email(mail_to="mapmanagercore@gmail.com",
                       message=message)
      print(_ret)

def show_dialog_example():
    """Example of how to show the support dialog."""
    from sanpy.interface.sanpy_app import SanPyApp
    import sys
    
    app = SanPyApp(sys.argv)
    result = show_support_dialog()
    print(f"Dialog result: {result}")
    sys.exit()
      
if __name__ == "__main__":
    # send_example()
    show_dialog_example()